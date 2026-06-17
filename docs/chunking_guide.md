# Chunking Guide

## Status

This is the long-term chunk style guide for the safety-training RAG project. Parser implementation, schema changes, and future data imports should follow this document before writing JSONL or rebuilding Elasticsearch indexes.

Current execution rule:

- The formal norm library has been built from this guide.
- Current pipeline version is `norm_chunker_v2` (article-number repair + slimmed text header).
- Current `data/chunks/norm_chunks.jsonl` contains 1455 norm chunks after article-break repair, OCR recovery for selected standards, durable low-quality filtering, the `JGJ-33-2012` relevance whitelist, and whitelist-managed imports for `JGJ-276-2012`, `JGJ-130-2011`, `JGJ-162-2008`, `JGJ-59-2011`, `GB-51210-2016`, and `JGJ-202-2010`.
- Current Elasticsearch `safety_norm_chunks` index contains 1455 documents.
- The tag vocabulary is externalized to `data/taxonomy/tags.yaml` and shared by the chunk pipeline and the retrieval layer (`src/tags.py`). It is the single human-maintained extension point for new tags/standards.
- Keep mock data out of formal indexes.
- mock 数据不得进入正式索引。
- Mock runtime data has been removed. If mock data is needed again, keep it only under `tests/fixtures/`.
- Treat the case library rules below as the future contract for accident-case ingestion.
- Use Elasticsearch as the only formal retrieval backend.
- Do not build, query, or fall back to Chroma in formal workflows.
- Accident cases will be chunked next from `data/事故案例收集.md`.

## 1. Core Principles

- Every chunk must be traceable to its original file, page, chapter, article, table, figure, or case source.
- Every chunk must be reproducible. Re-running the same pipeline on unchanged input should produce the same `chunk_id`.
- Every chunk must carry enough context for retrieval. Do not store isolated keywords or orphaned table values.
- All tags must come from the project taxonomy. If a new tag is needed, add it to the taxonomy before importing the data.
- Official indexes must not contain mock ids such as `norm_001` or `case_001`.
- Formal JSONL files and Elasticsearch indexes must not contain `norm_001` or `case_001`.
- Mock examples may be reintroduced only as test fixtures under `tests/fixtures/`, and formal index scripts must not read that directory.

## Artifact Policy

- `data/chunks/norm_chunks.jsonl` is the formal norm chunk input for `safety_norm_chunks`.
- `data/chunks/norm_import_report.json` is the formal import report for the current norm chunks.
- `data/chunks/*.bak` files are manual backups only. They must not be read by chunk builders, index builders, retrieval checks, or evaluation scripts.
- `data/output.json` is a runtime output from `scripts/run_training.py`. It must not be used as a norm source, case source, chunk input, index input, or evaluation dataset.
- Formal norm sources are the chapter-level PDF/TXT/DOCX assets under `rag_data/rag_data/` and `脚手架规范文表图切分/脚手架规范文表图切分/`.
- `data/cache/extracted/` is a reusable extraction cache. Keep it; it is not a formal source and must not be indexed directly.
- Formal scripts should read explicit source roots or explicit JSONL paths, not broad recursive data globs that could include backups or runtime output.

## 2. Norm Chunk Contract

Use `schema_version: norm_v1` for formal norm chunks.

Required core fields:

```text
schema_version
doc_type
chunk_id
chunk_kind
source_name
source_path
standard_code
chapter
article_id
page_start
page_end
title
text
scenario_tags
hazard_tags
requirement_type
asset_path
related_article_id
content_hash
pipeline_version
```

Field rules:

- `doc_type`: fixed as `norm`.
- `chunk_kind`: one of `article`, `table`, `figure`, `formula`, `term`, `supplement`.
- `chunk_id`: stable format, preferably `norm::{standard_code}::{chunk_kind}::{article_or_item_id}`.
- `source_path`: path to the text-bearing file used to create the chunk.
- `asset_path`: path to the original table, figure, or formula PDF when different from `source_path`.
- `related_article_id`: article or chapter associated with a table, figure, formula, or supplement.
- `content_hash`: hash of normalized chunk content and source identity.
- `pipeline_version`: parser and rule version that produced the chunk.

Norm text template (`norm_chunker_v2`, slimmed for signal-to-noise):

```text
标准：{standard_name}
章节：{chapter}
编号：{article_id or title}
正文：{source text or explanation}
```

Rationale: `chunk_kind`, `scenario_tags`, and `hazard_tags` already live in dedicated
Elasticsearch keyword fields (boosted in BM25 and used by the tag route), so repeating
them inside `text` only diluted the embedding/BM25 signal of short articles. They are
intentionally omitted from the `text` header.

Chunking rules:

- Article chunks come from chapter PDFs and should be split by article number when possible.
- Long articles may be split by natural paragraph when they exceed about 1200 Chinese characters, but all parts keep the same `article_id`.
- Table chunks are independent chunks with `chunk_kind=table`.
- Figure chunks are independent chunks with `chunk_kind=figure`.
- Formula chunks are independent chunks with `chunk_kind=formula`.
- Table, figure, and formula chunks should link back through `related_article_id`.

Structured norm chunk v2 rules:

- Structure-first chunking is the default for norm documents.
- Do not use fixed-size chunks or sliding window as the default norm strategy.
- Identify the chapter title tree first.
- Identify article numbers after chapter titles.
- Identify clauses, items, numbered lists, and subitems after article numbers.
- Use fallback overlap only after structure parsing and repair fail.
- The preferred hierarchy is standard / chapter / article / clause / item.
- If nested article, clause, or item chunks are implemented later, `parent_chunk_id` may be added as an optional relationship field while `related_article_id` remains the link for tables, figures, and formulas.

Article number repair rules (implemented in `norm_chunker._repair_article_breaks`):

- Repair PDF extraction splits in article numbers before article detection. The repair
  anchors on the dot and joins a dot followed by optional spaces/newline + a digit, e.g.
  `3.\n6` → `3.6` and `1. 0. 1` → `1.0.1`. Anchoring on the dot (not the leading digit)
  avoids the overlapping-match stall on adjacent levels like `1.0. 2`.
- `N.0.M` numbering (e.g. `1.0.1`, `9.0.5`) is **legitimate** GB/JGJ article numbering
  (common in 总则 chapters), not a defect — do not "normalize" it away.
- Run the repair over the raw extracted text, then split by the article pattern
  `^\s*((?:\d+\.)+\d+)\s+(.+)$`.
- For OCR text that drops the space after article numbers (for example `1.0.1为...`),
  the parser may fall back to a no-space article matcher only when the strict matcher
  finds no articles. The OCR fallback should accept three-level-or-deeper article
  numbers to avoid table-of-contents entries such as `3.1` becoming formal chunks.
- Do not keep failed article-detection chapters as permanent whole-chapter chunks; the
  space/line-break repair reduced whole-chapter fallbacks from 10 to 5.
- Remaining fallbacks are inherently structureless content: appendices (附录, which carry
  tables/figures rather than numbered articles) and OCR-garbled 总则 (e.g. GB-51210 where
  `0` was mis-extracted as the letter `o`: `1. o.1`). These need cleaned source text, not
  a riskier global regex.
- If a standard still cannot be parsed structurally, add cleaned source text before
  rebuilding the formal index.

Durable quality filters (implemented before writing `norm_chunks.jsonl`):

- Drop article/term chunks whose `article_id` contains any numeric level greater than
  99. These are OCR/PDF split artifacts such as `1205.27`, not real article numbers.
- Drop malformed article identifiers such as `0.x`, isolated `N.0`, overlong glued
  numeric levels, and obviously concatenated multi-article ids. These are OCR/table
  artifacts, not stable citable provisions.
- If an article/term `chunk_id` collides, keep the first occurrence and discard the
  later fragment. Do not emit article `-dup-N` ids.
- Table, figure, and formula chunks may keep legal `-dup-N` ids when multiple assets
  legitimately share the same item id.
- Drop all appendices, appendix-numbered assets (`图A.*`, `表A.*`, `公式A.*`, etc.),
  references, and whole-chapter fallback ids (`ch-*`). The formal index should contain
  precise, directly citable evidence rather than calculation examples or broad
  reference tables.
- Drop chunks with high-confidence OCR garble patterns already observed in source
  texts, such as broken safety-belt terms, corrupted electrical terminology, and
  unreadable safety-net test fragments.
- Drop `JGJ-33-2012` pure section-heading chunks such as `8.3 混凝土搅拌运输车`.
- For `JGJ-33-2012`, index only material relevant to the paper/case line:
  chapters 1 and 2 for general machinery safety background, chapter 4 for building
  lifting machinery, and sections `8.4.x`/`8.5.x` plus relevant chapter-8 table notes
  for concrete pumps and pump trucks. Source PDF/TXT files remain in place; this only
  controls the formal JSONL and Elasticsearch content.
- For newly added broad standards, use a whitelist policy before indexing. Current
  whitelist-managed standards are `JGJ-276-2012` (lifting/rigging and high-signal
  hoisting requirements), `JGJ-130-2011` (strict scaffold erection/dismantling,
  inspection, acceptance, and safety-management articles only), `JGJ-162-2008`
  (formwork support installation, dismantling, and high-place safety-management
  articles only), `JGJ-59-2011` (safety-management and high-risk-work inspection
  items), `GB-51210-2016` (scaffold safety, materials, erection, dismantling,
  inspection, and management articles only), and `JGJ-202-2010` (tool-type scaffold
  installation/use/lifting/dismantling, hanging basket safety, external protection
  frame acceptance, and management requirements only).
- Drop prefaces, publisher notices, title-page fragments, pure section-title stubs,
  formula/design-calculation noise, and known high-confidence OCR fragments. Broad
  calculation/design clauses are excluded unless they are directly needed by the
  paper's accident-prevention line.

Sliding window rules:

- 规范条文不默认滑窗。
- Use sliding window only for long chapters, overlong paragraphs after failed structural repair, or accident-case narrative text.
- Accident cases are suitable for sliding window because process, causes, consequences, and corrective measures are narrative sections.
- Case narrative overlap should default to 100-150 Chinese characters.
- Norm fallback overlap must be small and must preserve article or section identifiers in metadata and text header.

Title rules:

- 标题必须保留在 metadata 中。
- 标题必须保留在 chunk `text` header 中。
- 正文中的重复页眉、页脚、目录标题可以清洗。
- 不得删除真实的章节、条文、表格、图、公式或案例标题。
- BM25 和 RRF 依赖标题词，删除标题会削弱精确匹配检索和混合融合效果。

Optimization status:

- The current formal norm library is `norm_v1` schema, produced by `norm_chunker_v2`.
- The current JSONL output contains 1455 chunks.
- Article, table, figure, formula, term, and supplement chunk kinds are supported by the contract.
- Each chunk must carry `content_hash` and `pipeline_version`.
- `GB 6095-2021` has OCR-recovered article chunks plus figure chunks and now supports
  safety-belt technical-requirement retrieval. OCR text should still be spot-checked
  for key articles before paper-grade evaluation.
- `JGJ/T46-2024` has been imported from the official MOHURD PDF through OCR cache
  injection and contributes temporary-electricity evidence. OCR text should be treated
  as usable but not perfect; important cited clauses need manual spot checks.
- `JGJ-33-2012` is intentionally whitelisted to 217 chunks in the formal index; the
  complete chapter PDF/TXT sources are retained under `rag_data/rag_data/JGJ-33-2012/`.
- `JGJ-202-2010` is intentionally whitelisted to 53 chunks in the formal index; terms,
  design calculations, formulas, load/section-parameter tables, and heavy OCR fragments
  are excluded. The original uploaded source folder was removed after the cleaned chunks
  and Elasticsearch index were verified. `JGJ-202-2010` is therefore frozen from the
  cleaned JSONL when source files are absent; traceability is by `standard_code`,
  `chapter`, `article_id`, `title`, and `text`, not by requiring the original PDF to
  remain in the project.
- `JGJ-130-2011`, `JGJ-162-2008`, and `GB-51210-2016` are curated by explicit article
  whitelist to keep the norm library light and strongly related to scaffold/formwork
  accident prevention. Design formulas, structural calculation tables, and broad
  non-safety provisions are excluded from the formal index.
- `JGJ-130-2011` now uses chapter-level source files under
  `rag_data/rag_data/JGJ-130-2011/`. The temporary top-level staging folder was removed
  after verification. A few high-value whitelist articles with repeated PDF text-layer
  fragments are repaired at article level before indexing; the final formal count remains
  23 chunks.

## 3. Future Case Chunk Contract

Use `schema_version: case_v1` when the accident case library is added.

The first case-library source is:

```text
data/事故案例收集.md
```

Required core fields:

```text
schema_version
doc_type
chunk_id
chunk_kind
case_id
case_title
accident_type
scenario_tags
hazard_tags
process
causes
consequences
corrective_measures
source_org
source_date
source_path
content_hash
pipeline_version
```

Case chunk kinds:

- `case_summary`: accident overview.
- `case_process`: accident process.
- `case_causes`: direct, indirect, and management causes.
- `case_consequences`: injuries, deaths, economic loss, penalties, or shutdowns.
- `case_measures`: corrective and preventive measures.

Markdown source mapping:

- Case title, accident type, source organization, source date, and source path form the `case_summary` chunk.
- Accident narrative paragraphs form the `case_process` chunk.
- Direct causes, indirect causes, management causes, and common risk-factor analysis form `case_causes` chunks.
- Deaths, injuries, losses, punishments, shutdowns, and investigation outcomes form `case_consequences` chunks.
- Rectification, preventive measures, control suggestions, and lessons learned form `case_measures` chunks.
- If one source section contains multiple semantic parts, split by natural headings and keep the same stable `case_id`.

Case text template:

```text
案例：{case_title}
事故类型：{accident_type}
适用场景：{scenario_tags}
危险源：{hazard_tags}
经过/原因/后果/措施：{section text}
来源：{source_org or source_path}
```

Case rules:

- Case chunks do not need article numbers, but they must be traceable to the original source.
- Corrective measures from cases are experience evidence, not normative requirements.
- If case experience conflicts with a norm requirement, the norm requirement has higher priority.
- Case chunks must share the same `scenario_tags` and `hazard_tags` taxonomy as norm chunks.
- After case chunks are generated, they should be indexed into `safety_case_chunks`.
- `safety_case_chunks` participates in the same Elasticsearch/RRF multi-route retrieval as `safety_norm_chunks`.

## 4. Taxonomy Rules

Active taxonomy file (loaded by `src/tags.py`, shared with retrieval):

```text
data/taxonomy/tags.yaml
```

The taxonomy defines:

- `scenario_rules` / `hazard_rules`: keyword → tag mappings.
- `high_altitude_keywords` / `high_altitude_scenario_tags` / `collapse_scenario_tags`: cross-tag inference.
- `standard_tag_hints`: per-standard-code-prefix tag injection, for standards whose body
  text lacks the trigger keywords or whose PDF extraction is poor (e.g. `GB-6095` → 安全带/坠落防护).
- `scenario_fallback` / `hazard_fallback`: guarantee every chunk has non-empty tags.

Current tagging policy:

- Use deterministic rules first (keyword + standard hints). No LLM-invented tags.
- Add new tags/keywords/standard-hints to `tags.yaml` before importing data that needs them,
  then regenerate chunks and rebuild the index. This is the single human-maintained extension point.
- Keep tag names short, stable, and reusable across norm and case chunks.

Initial scenario tag examples:

- `高处作业`
- `临边作业`
- `洞口作业`
- `攀登作业`
- `悬空作业`
- `操作平台`
- `交叉作业`
- `安全带`
- `安全网`
- `脚手架搭设`
- `脚手架使用`
- `脚手架拆除`
- `检查验收`
- `材料构配件`
- `模板支架`

Initial hazard tag examples:

- `高处坠落`
- `物体打击`
- `坍塌`
- `触电`
- `构件失稳`

Requirement type rules:

- Text containing `严禁` or `不得`: `禁止行为`.
- Text containing `必须`, `应`, or `不应`: `强制性要求`.
- Text containing `检查` or `验收`: `检查验收`.
- Text containing `试验` or `测试`: `试验检测`.
- Parameter tables for loads, distances, grading, or limits: `计算参数`.
- Term chapters: `术语定义`.

## 5. Elasticsearch and Retrieval

Formal indexes:

- `safety_norm_chunks`
- `safety_case_chunks`

Each ES document should store:

- `text` and `title` analyzed with the built-in **`cjk`** analyzer (bigram), not `standard`.
  `standard` tokenizes Chinese into single characters and cripples BM25; `cjk` bigrams
  recover most of the recall with no plugin (IK would need an offline plugin install in the
  ES container). A mapping change requires a full index rebuild.
- `text_vector` as a 1024-dimension dense vector (`VECTOR_DIMS`; embedding output dimension
  is asserted against this at index/query time).
- metadata fields such as `chunk_id`, `doc_type`, `chunk_kind`, `standard_code`, `article_id`, `scenario_tags`, `hazard_tags`, and `requirement_type`;
- `_json` for complete chunk reconstruction.

Default retrieval mode:

```text
rrf_hybrid
```

RRF fusion combines (per-query, not merged-string):

- BM25 route for exact terminology, article numbers, and standard codes;
- dense vector route for semantic similarity;
- tag route over `scenario_tags` (boost 1.0) and `hazard_tags` (boost 2.0), `minimum_should_match=1`.

Each planner query is retrieved separately on the BM25 and vector routes (rather than
concatenating all queries into one diluted string/embedding), and every route's ranked list
is fused by RRF (`RRF_K=60`). The final result is cut to `top_k` (not `top_k*2`).

Reranker may be added after RRF top-k in a later phase. Reranker should not replace RRF.

Chroma is not part of the formal retrieval path. Old Chroma runtime artifacts, dependency, config, and sample index script have been removed and must not be reintroduced for chunk validation, index building, retrieval regression, or Agent evaluation.

Agent outputs must cite chunk-level evidence. Norm requirements should cite `chunk_id`, `standard_code`, `article_id`, and source; case warnings should cite `chunk_id` and source. Do not cite only a broad standard name when chunk evidence is available.

## 6. Metadata and Cache

Metadata is mandatory, not optional. The project needs traceable evidence for safety-training output.

Cache policy:

- Cache extracted PDF/DOCX text under `data/cache/extracted/`.
- Include `content_hash` in every chunk.
- Include `pipeline_version` in every chunk.
- For v1, Elasticsearch may rebuild the full `safety_norm_chunks` index because the data size is still manageable.
- After the case library is added, implement embedding cache or incremental indexing.

Cache keys should include:

- `source_path`
- source file hash
- `schema_version`
- `pipeline_version`

## 7. Import Report

Every formal import should produce a short report containing:

- number of new chunks;
- chunk count by standard or source;
- missing required field count;
- tag distribution;
- oversized chunk count;
- duplicate `chunk_id` count;
- whether mock ids such as `norm_001` or `case_001` are present.
- whether mock fixtures were excluded from formal imports.
- source paths that no longer exist. Missing source paths are warnings, not validation
  failures, when the chunk is an explicitly frozen standard such as `JGJ-202-2010` and
  still carries precise standard/chapter/article provenance.

## 8. Validation Checklist

Before writing to Elasticsearch:

- JSONL exists and every line parses.
- Every chunk passes schema validation.
- Every `chunk_id` is stable and unique.
- Every tag is present in the taxonomy.
- Every chunk has `source_path`, `content_hash`, and `pipeline_version`.
- Formal ES indexes do not include mock norm or case chunks.
- Formal JSONL and ES indexes do not include `norm_001` or `case_001`.
- `tests/fixtures/` is excluded from formal index scripts.
- Table and figure chunks keep their source explanation text and asset paths.
- Mock data must not enter formal indexes.

Before full Agent evaluation:

- Run retrieval checks on fixed queries.
- Inspect top-k results for representative high-risk scenarios.
- Record failed retrieval examples before changing chunk rules.
