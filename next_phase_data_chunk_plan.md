# 下一阶段计划：ES/RRF 规范库、案例库 Chunk 与资料补全

> 状态：当前执行文档。后续开发、数据接入、chunk、索引和验证优先按本文执行。
>
> 当前结论：
> - 规范库 chunk 已生成：`data/chunks/norm_chunks.jsonl` 当前为 **1455 条**（`norm_chunker_v2`，含 ES 去噪、`JGJ-33-2012` 白名单、`JGJ-276-2012`/`JGJ-130-2011`/`JGJ-162-2008`/`JGJ-59-2011`/`GB-51210-2016`/`JGJ-202-2010` 白名单入库、content_hash 去重、附录/参考文献/整章 fallback/坏条文号/高置信 OCR 乱码/出版前言/章节标题 stub/公式设计噪声过滤）。
> - 本地 Elasticsearch 8.15.3 已通过离线镜像导入并运行。
> - `safety_norm_chunks` 已完成建索引，当前正式规范库索引为 **1455 条**。
> - 默认检索后端为 Elasticsearch，默认检索模式为 `rrf_hybrid`；文本字段已用 **cjk 分析器**（非 standard），每条查询逐条检索后 RRF 融合。
> - `GB-39800.6-2023`、`GB-55034-2022`、`GB-5725-2009`、`JGJ-33-2012` 已迁入 `rag_data/rag_data/` 并重建规范索引；`rag_data/staging_cleaned/` 不再作为正式源，历史 staging 工具已归档到 `docs/history/staging_tools/`。
> - 已完成一轮 Agentic RAG 代码级整改（检索层 / Agent-Prompt / Chunking），详见下方"本轮管道优化（已完成）"。
> - Chroma 运行残留已清理：后续不作为 fallback、不作为索引构建目标、不作为 Agent 检索来源。
> - Mock 残留已清理：旧 sample 数据、旧 mock 运行输出和空 `data/sample/` 已移除。
> - `docs/chunking_guide.md` 是唯一 chunk 风格依据；`data/taxonomy/tags.yaml` 是唯一标签词表。

## 本轮管道优化（已完成）

仅针对规范（norm）管道。代码改动均已落地并通过端到端验证（当前重建索引 1455 条、检索回归全模式通过、规范引用带真实 `chunk_id`）。

检索层（`src/retrieval/es_store.py`）：
- 中文文本/标题字段从 `standard` 改为内置 `cjk` 分析器，修复 BM25 中文单字切分问题（cjk 约补回 IK 的 85–90%，离线无需插件）。
- 多条 planner 查询不再拼成一个字符串：每条查询在 BM25/向量路各自检索，连同 tag 路一起 RRF 融合，避免语义平均稀释。
- 修正 RRF 后返回数量：由 `top_k*2` 改为 `top_k`。
- tag 路改为 scenario(boost 1.0)+hazard(boost 2.0) 双 should、`minimum_should_match=1`，不再因单一标签硬过滤掉相关项。
- embedding 维度断言：模型输出维度与 `VECTOR_DIMS` 不一致直接报错。

Agent / Prompt / 证据流（`src/agents/*`、`src/prompts/*`、`src/config.py`）：
- `risk_planner` 查询生成 prompt 增加质量约束与正反例；重试时回传上一轮查询并要求明显不同；查询/情境生成温度提高到 `LLM_QUERY_TEMPERATURE=0.7`。
- 证据文本上限 600→2000，fusion/checker 看到接近全文，支撑真正接地。
- 一致性检查增加**确定性 chunk_id 接地校验**：草稿引用的每个 chunk_id 必须存在于本轮检索证据，否则判 hallucination/evidence_insufficient（不再只靠 LLM 文本比对）。
- **证据接地兜底**：fusion 与 training 的结构化引用列表（`norm_requirements`/`accident_warnings`）若 LLM 留空，则用本轮检索到的 chunk 自动回填，保证引用永不静默为空；案例库为空时输出"暂无相似事故案例"而非编造。
- 5 个 Agent 节点对 `call_llm_json` 失败做安全降级，单次 JSON 失败不再让整条管线崩溃。
- `LLM_MAX_TOKENS` 当前统一为 6144，降低长培训输出被截断概率。

Chunking 通用规则（`src/data_pipeline/norm_chunker.py`、`src/tags.py`、`data/taxonomy/tags.yaml`，`pipeline_version=norm_chunker_v2`）：
- 条文号断裂修复（`3.\n6`→`3.6`、`1. 0. 1`→`1.0.1`，锚定小数点避免相邻级别吞位）；整章 fallback 不进入正式索引。
- ES 去噪过滤已固化：article/term 任一条文号层级 `>99` 的 OCR 伪条号不写入 JSONL；article/term `chunk_id` 碰撞时丢弃后续碎片；table/figure/formula 仍允许合法 `-dup-N`。
- 精确证据过滤已固化：附录、参考文献、附录编号资产（如 `图A.*`/`表A.*`）、整章 fallback `ch-*`、明显坏条文号和高置信 OCR 乱码不写入正式 JSONL/ES。
- `JGJ-33-2012` 采用论文主线白名单：保留第 1、2 章通用机械安全背景，第 4 章建筑起重机械，以及第 8 章 `8.4.x`/`8.5.x` 与相关表格说明；其他机械条文不进入正式 ES，但源 PDF/TXT 保留。
- `JGJ-130-2011`、`JGJ-162-2008`、`GB-51210-2016` 已收紧为精确条文白名单：只保留脚手架/模板支架搭设、使用、拆除、检查验收和安全管理等与论文主线强相关内容；设计计算、结构验算、公式参数表和纯标题 stub 不进入正式 ES。
- `JGJ-130-2011` 已从顶层 staging 归并为正式章节级源 `rag_data/rag_data/JGJ-130-2011/`，验证后删除 staging。最终仍为 23 条强相关 chunk；对少数 PDF 文本层重复碎片做条文级修复，不放宽白名单。
- `JGJ-202-2010` 原始上传资料已按你的授权删除；当前 53 条清洗 chunk 在源文件缺失时从正式 JSONL 冻结保留。论文引用依赖 `standard_code`、章节、条文号和正文，不要求项目继续保存 PDF 原件。
- 标签词表外置到 `data/taxonomy/tags.yaml`（场景/危险源规则、跨标签推断、`standard_tag_hints` 按标准号补标签、兜底），与检索层共用 `src/tags.py`。
- chunk text header 瘦身（去掉 类型/适用场景/危险源 三行，这些已是 ES keyword 字段），提升短条文信噪比。
- PDF 章节文件优先读取同名 `.txt` sidecar 文本，PDF 保留为 `source_path` / `asset_path`，避免依赖易失效的 cache 注入。
- 已新增施工机械、混凝土泵车、起重吊装、个体防护装备、安全帽、绝缘防护、防电弧、安全网等标签规则，并为 `GB-55034`、`JGJ-33`、`GB-5725`、`GB-39800.6`、`JGJ-202` 增加 `standard_tag_hints`。

case→norm 证据链（已落地，Part A）：
- `case_chunker` 解析案例"违反规范"为 `related_standards`（规范化 `标准号:条文号`）。
- `src/retrieval/es_store.py` 新增 `fetch_norm_chunks_by_refs(refs)`：按 `standard_code`+`article_id` 精确取回案例引用的规范条文 chunk，跳过法律名与未入库标准。
- `src/agents/graph.py` 新增 `case_norm_linker` 节点（接在 norm/case 两路检索之后、fusion 之前）：汇总本轮案例的 `related_standards`→取回规范条文→去重并入 `norm_evidence`/`norm_evidence_ids`，标注 `linked_from_case=来源 case_id`；`state.py` 增 `linked_norm_evidence_ids`。
- `NormRequirement` schema 增 `linked_from_case`，`evidence_fusion` 把来源 case 标注盖到引用上，使培训输出呈现 **案例→违反的规范条文→要求** 证据链。
- 验证（GPU embedding + 真实检索，绕开慢的 LLM 节点）：触电/高坠场景下案例 case-01/case-04 的 `JGJ-80-2016:3.0.5`、`GB-6095-2021:5.3.3.x` 等被正确链接进 norm 证据；案例 case-15 的 `JGJ-33-2012:8.5.1`、`JGJ-33-2012:8.5.2` 已能反查到混凝土泵车条文级证据。provenance 正确，grounding id 同步；图编译含新节点。全 LLM 全流程因共享机 9B 模型慢未在限时内跑完（基础设施问题，非代码）。

## 项目层面后续工作（非代码优化）

代码级管道已固化，下面是推进项目所需的**资料/数据/评测/运维**层面工作，按优先级排列：

1. **持续扩充主线规范库（最高）**：只补与当前事故案例和论文主线直接相关的规范。`JGJ-276-2012`、`JGJ-130-2011`、`JGJ-162-2008`、`JGJ-59-2011`、`GB-51210-2016`、`JGJ-202-2010` 已按白名单入库；当前仍可补的是企业管理类 `GB 50656`，以及后续案例明确需要的少量高相关规范。`JGJ 196-2010`、`GB 6067.1-2010` 不在当前计划内。新术语在 `tags.yaml` 扩充。
2. **资料质量抽查（高）**：新入库的 `GB-39800.6-2023`、`GB-55034-2022`、`GB-5725-2009`、`JGJ-33-2012` 已可检索，但 OCR 仍有字符级错字；论文正文引用关键条文前应人工核对原页面。
3. **事故案例库 case_v1（已落地，持续扩充）**：`src/data_pipeline/case_chunker.py` 已实现，从 `data/事故案例收集.md` 解析 23 个案例、每案 2 块（`case_summary` + `case_cause`），共 46 条，写入 `data/chunks/case_chunks.jsonl` 并构建 `safety_case_chunks`（count=46），复用现有 BM25+vector+tag+RRF 检索层。优化点：①不切空的"整改措施"段（数据无此字段）；②解析"违反规范"为 `related_standards`（规范化 `标准号:条文号`），实现案例→规范反查。后续：补充新案例后重跑 `scripts/build_case_chunks.py`+`scripts/build_case_index.py`；做规范库+案例库联合 RRF 回归。
4. **检索回归集固化（中高）**：`scripts/check_es_retrieval.py` 已加入新标准 spot checks 和 case-15→JGJ-33 精确反查；后续继续把"查询→期望命中标准/条文"扩展成更系统的 regression set，每次新增规范/案例后跑一遍，量化召回是否退化。
5. **离线 IK 分词评估（中）**：评估在 ES 容器内离线安装匹配 8.15.3 的 IK 插件；可用则把 `text/title` 分析器从 cjk 切到 `ik_max_word` 并重建索引，预计精确率再提升 5–15%。
6. **RRF 后接 reranker（已落地，可开关）**：`es_store.rerank()` 用 `bge-reranker-v2-m3`（模型已离线缓存）对 RRF top `RERANK_POOL=30` 候选按 max-over-queries 交叉编码重排；`RERANK_ENABLED` 默认 false（正式流程不受影响，置 true 启用）。当前 1455 条规范库已完成 smoke check；如需最新 A/B 数字，重跑 `scripts/eval_retrieval.py`。
7. **检索评测体系（已落地，检索侧）**：`src/evaluation/retrieval_eval.py` + `scripts/eval_retrieval.py`，从案例 `related_standards` 自举 gold（query=案例经过，expected=在库违反条文 chunk_id），输出 recall@k/hit@k/MRR/nDCG@k + case→norm 链接解析率（当前 20/21=95.2%），并对 rerank off/on 做 A/B。注意：当前 gold 仅 6 案（其余只引法律或缺条文号），数据增补后重跑即更稳；培训材料质量评测（接地率/引用有效率/人工评分）仍待补。
8. **OCR 乱码总则修复（低）**：GB-51210 等总则 PDF 存在 `0`→`o` 等 OCR 错误，需人工清洗源文本（不宜用全局正则强改）。

## Summary

当前项目已从 mock 原型推进到真实规范库可检索阶段。本阶段重点是巩固 ES/RRF 检索链路、按统一 chunk contract 处理后续资料，并准备事故案例库 `case_v1` 入库。

后续新增规范资料必须先按 `docs/chunking_guide.md` 生成 norm chunks，再重建 `safety_norm_chunks`；事故案例整理完成后，再生成 case chunks 并构建 `safety_case_chunks`。检索链路只面向 Elasticsearch/RRF，避免旧原型索引污染正式结果。

## Current Completed State

- 规范库 chunk：
  - 输出文件：`data/chunks/norm_chunks.jsonl`
  - 当前数量：1455 条（`norm_chunker_v2`）
  - 导入报告：`data/chunks/norm_import_report.json`
  - 备份：`data/chunks/norm_chunks.jsonl.bak`（旧版人工备份，整改前）。
  - mock 数据不得进入正式索引，正式数据不得包含 `norm_001`、`case_001` 等测试 id。

- Elasticsearch：
  - ES 版本：8.15.3
  - 本地镜像：`docker.elastic.co/elasticsearch/elasticsearch:8.15.3`
  - 规范库 index：`safety_norm_chunks`
  - 案例库 index：`safety_case_chunks`
  - 当前 `safety_norm_chunks` 已建索引，count 为 1455。

- 检索模式：
  - 正式后端：Elasticsearch
  - 默认模式：`rrf_hybrid`
  - 多路召回：`bm25`、`vector`、`tag`
  - RRF 后续可接 reranker，但 reranker 不替代 RRF。

- 旧原型索引：
  - Chroma 不再作为正式流程的一部分。
  - `data/chroma/`、旧 Chroma store、旧 sample index 脚本、`chromadb` 依赖和 `CHROMA_DIR` 配置已移除。
  - 后续构建、验证和 Agent 调用不得依赖 Chroma。
  - 如需保留历史说明，只能出现在明确标记为历史的文档中。

- Mock Cleanup：
  - `src/data_pipeline/sample_data.py` 已移除。
  - 空目录 `data/sample/` 已移除。
  - 旧 mock 运行产物已清理；`scripts/run_training.py` 可以重新生成 `data/output.json`。
  - 当前或后续生成的 `data/output.json` 只是训练运行输出，不得作为规范、案例、chunk、索引或评测输入。
  - 正式索引、导入报告、检索结果中不得出现 `norm_001`、`case_001`。
  - `norm_chunker.py` 中对 `norm_001`、`case_001` 的校验规则必须保留，用作正式导入保护。

## Artifact Policy

- `data/chunks/norm_chunks.jsonl` 是当前规范库正式 chunk 输入。
- `data/chunks/norm_import_report.json` 是当前规范库正式导入报告。
- `data/chunks/*.bak` 只作为人工备份或对照材料，不参与 chunk 构建、索引构建或评测输入。
- `data/output.json` 只作为 `scripts/run_training.py` 的单次运行输出，不参与规范、案例、chunk、索引或评测输入。
- 正式规范源为 `rag_data/rag_data/` 和 `脚手架规范文表图切分/脚手架规范文表图切分/` 下的章节级 PDF/TXT/DOCX。`data/cache/extracted/` 是可复用抽取缓存，保留但不直接作为索引源。
- 正式构建脚本只读取明确指定的 chunk JSONL 和源资料目录，不得递归读取运行输出或备份文件。

- 当前限制：
  - `JGJ/T46-2024` 与 `GB 6095-2021` 正文通过 OCR 缓存进入 chunk；已可检索，但仍建议人工抽查关键条文 OCR 错字。
  - `GB 50194-2014` 已入正式索引，但源 PDF 文本层质量较差，论文引用关键条文前需人工抽查。
  - `GB-39800.6-2023`、`GB-55034-2022`、`GB-5725-2009`、`JGJ-33-2012` 已清洗后入正式索引；字符级 OCR 错字仍需在论文引用前人工核对。
  - `JGJ-202-2010` 当前以 53 条清洗后 chunk 冻结保留，源 PDF 缺失只记录在导入报告的 `missing_source_path_count`，不作为验证失败。
  - `GB/T 3787`、`GB/T 5082`、`JGJ 166`、`JGJ/T 231` 等边缘或条件触发规范不再列入当前主线入库计划。
  - 案例库 case_v1 已 chunk 并建索引（`safety_case_chunks`，46 条 / 23 案）；`data/事故案例收集.md` 后续补充新案例后重跑 case build 脚本即可，无需改代码。

## Chunk Optimization Status

已完成的 chunk 优化：

- 从 mock 原型数据切换到真实规范资料 chunk。
- 规范 chunk 固定为 `norm_v1`，案例库预留为 `case_v1`。
- 使用稳定、可复现的 `chunk_id`，避免随机 UUID。
- 条文、表格、图像说明分类型 chunk，表格和图像通过 `related_article_id` 关联条文。
- 每个正式 chunk 保存 `content_hash` 和 `pipeline_version`，为后续缓存和增量索引做准备。
- PDF/DOCX 提取文本缓存到 `data/cache/extracted/`。
- 每次正式导入必须生成导入报告，记录 chunk 数量、来源分布、缺失字段、标签分布、超长 chunk、重复 ID 和 mock ID。
- 检索侧已从单一路线扩展为 ES `bm25`、`vector`、`tag` 三路召回，并使用 RRF 融合。
- `scripts/check_es_retrieval.py` 已覆盖基础四模式 smoke check、新标准 spot query 和 case-15→JGJ-33 反查。

下一步 chunk 优化：

- 对 `JGJ/T46-2024` 与 `GB 6095-2021` 的 OCR chunk 做关键条文抽查和小范围清洗。
- 继续维护统一标签词表 `data/taxonomy/tags.yaml`。
- 从 `data/事故案例收集.md` 生成 `case_v1` chunks，并构建 `safety_case_chunks`。
- 为案例库加入 embedding cache 或增量索引策略。
- 固定一组检索回归查询，每次新增规范或案例后验证 top-k 结果。

### Norm Chunk v2 Direction

下一版规范 chunk 优化采用结构切分优先，不默认使用 fixed-size 或 sliding window。

规范类资料切分顺序：

1. 标准。
2. 章节。
3. 条。
4. 款。
5. 项。

Norm chunk v2 规则：

- 规范条文默认不滑窗，因为滑窗会破坏条文边界和引用准确性。
- 表格、图、公式独立 chunk，并继续保留 `related_article_id`。
- 若后续实现条、款、项的嵌套 chunk，可引入 `parent_chunk_id`，用于保留父级章节或条文关系。
- 条文识别失败的章节必须做二次规则修复，不得直接长期保留为整章 chunk。
- 对 PDF 抽取造成的条文号断裂进行修复，例如将 `5. / 1` 识别回 `5.1`。
- 对 PDF 抽取造成的异常断行进行修复，避免把同一条文切碎或拼错。
- `GB 3608`、`GB 6095` 这类标准不得退化成整章 chunk；如果条文识别失败，应优先修复规则或补充清洗文本。
- 只有长章节、条文识别失败后的超长段落或事故案例叙事才使用 sliding window 兜底。
- 事故案例适合 sliding window，因为“经过-原因-后果-整改”属于叙事文本。
- 案例叙事 sliding window overlap 默认 100-150 中文字符。
- 标题必须保留在 metadata 和 chunk text header 中。
- 正文中重复页眉、页脚、目录标题可以清洗，但不得完全去掉真实标题。
- BM25 和 RRF 依赖标题词，标题缺失会降低关键词召回和多路融合效果。

## Verification Commands

所有后续验证命令使用项目虚拟环境：

```bash
/home/sicau_kek/miniconda3/envs/myenv/bin/python
```

访问本地 Elasticsearch 时带上本地代理绕过配置：

```bash
NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1
```

推荐验证命令：

```bash
NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1 \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
/home/sicau_kek/miniconda3/envs/myenv/bin/python scripts/check_es_retrieval.py
```

重建规范索引时使用：

```bash
NO_PROXY=localhost,127.0.0.1 no_proxy=localhost,127.0.0.1 \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
/home/sicau_kek/miniconda3/envs/myenv/bin/python scripts/build_norm_index.py
```

## Chunk Contract

实现 parser、重建 JSONL 或新增资料前，必须先阅读 `docs/chunking_guide.md`，并以它作为唯一 chunk 风格依据。

核心约束：

- `chunk_id` 必须稳定、可复现，不使用随机 UUID。
- 规范 chunk 使用 `schema_version=norm_v1`。
- 案例 chunk 后续使用 `schema_version=case_v1`。
- 表格和图像说明独立成 chunk，并通过 `related_article_id` 关联条文。
- `scenario_tags`、`hazard_tags`、`accident_type`、`requirement_type`、`chunk_kind` 必须来自统一词表。
- 每次新增资料必须生成导入报告。
- mock 数据不得进入正式索引。

规范 chunk 核心字段：

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

案例 chunk 核心字段：

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

## Metadata and Cache

- 每个 chunk 必须保存 `content_hash`，用于判断文本内容是否变化。
- 每个 chunk 必须保存 `pipeline_version`，用于追踪 parser、切分规则、标签规则和文本模板版本。
- PDF/DOCX 解析后的纯文本缓存到 `data/cache/extracted/`。
- 当前数据量可控，Elasticsearch 初期允许全量重建 `safety_norm_chunks`。
- 案例库加入后，再实现 embedding cache 或增量索引。
- 缓存命中条件至少包含 `source_path`、源文件内容 hash、`schema_version`、`pipeline_version`。

## Case Library Next Step

当前事故案例资料位于：

```text
data/事故案例收集.md
```

已实现：`src/data_pipeline/case_chunker.py` 从该 Markdown 生成 `case_v1` chunks 并写入 `safety_case_chunks`。

实际切分方案（据数据特点优化，未照搬下方 5 段草案）：每案 2 块，因为案例短、且数据无独立"整改措施"字段，5 段会过度碎片化、measures 段恒空。

- `case_summary`：标题+事故类型+日期+地点+经过+伤亡+经济损失+违反规范+来源（主检索单元）。
- `case_cause`：直接原因+间接原因（成因分析，便于"为何发生"类查询单独命中）。

字段映射：经过→`process`、原因→`causes`、伤亡+损失→`consequences`、违反规范→`related_standards`（规范化 `标准号:条文号`，支持案例→规范反查）、来源→`source_org`/`source_url`、时间→`source_date`(YYYY-MM-DD)、`accident_type` 由标题关键词判定。`case_id=case-NN`（按 md 中"案例 N"编号，稳定可复现）。后续若某案例含独立整改措施段，再加 `case_measure` 块。

原 5 段草案（保留作历史参考）：

案例库约束：

- 案例 chunk 必须能追溯到原始来源。
- 案例整改措施不能自动当作规范要求。
- Agent 生成培训材料时，规范要求优先级高于案例经验。
- 案例 chunk 必须使用与规范 chunk 共享的 `scenario_tags` 和 `hazard_tags` 词表。

## Elasticsearch and RRF Retrieval

正式 ES index：

- `safety_norm_chunks`：规范 chunk。
- `safety_case_chunks`：事故案例 chunk。

默认多路召回：

- `bm25`：条文号、标准号、专业词和精确关键词召回。
- `vector`：语义相似召回。
- `tag`：`scenario_tags`、`hazard_tags`、`chunk_kind`、`standard_code` 等元数据召回。

RRF 融合规则：

- 默认 `RRF_K=60`。
- 同一个 `chunk_id` 在多路结果中合并为一条。
- 排序优先级为 RRF 分数、危险源标签重合、场景标签重合、单路最佳排名。
- 后续 reranker 接在 RRF top 20/30 后，不替代 RRF。

## Agent Architecture Next Step

当前不大改 LangGraph 拓扑，仍保持：

```text
scenario_agent -> risk_planner -> norm_retriever / case_retriever -> evidence_fusion -> consistency_checker -> training_agent
```

优先优化 Agent 节点之间的数据契约：

- State 增加 `retrieval_mode`、`norm_evidence_ids`、`case_evidence_ids`、`case_index_available`、`evidence_diagnostics`。
- Fusion、Checker、Training 共享统一 evidence formatter，避免各节点各自丢字段。
- Agent 输出必须引用 chunk 级证据，不得只引用笼统规范名。
- 规范要求输出统一使用 `article_id`，不得再使用旧的 `article` 字段。
- 规范证据引用必须包含 `chunk_id`、`standard_code`、`article_id` 和来源。
- 案例证据引用必须包含 `chunk_id` 和来源。
- 当 `case_index_available=false` 或 case evidence 为空时，只能输出“暂无相似事故案例”，不得编造案例。

后续架构和性能优化方向：

- 接入 `safety_case_chunks` 后，做规范库 + 案例库联合 RRF 回归。
- 在 RRF top 20/30 后接 reranker，提高最终证据排序质量。
- 记录检索诊断和失败样例，形成可回放的 retrieval regression set。
- 收紧 `TrainingState` 类型，逐步减少 `list[dict]` 和 `Optional[dict]`。
- 将 checker 从文本比对增强为按 `chunk_id` 的证据覆盖检查。

## Skill Usage

- 当前不运行 `setup-matt-pocock-skills` 作为 chunk 或索引的前置条件。
- 写 parser、schema 校验、ID 稳定性和检索回归测试时，可使用 `tdd` skill。
- 如果 PDF/DOCX 解析、条文号切分或 Elasticsearch 入库失败，可使用 `diagnose` skill。
- 当规范库和案例库都跑通后，可使用 `improve-codebase-architecture` skill 复盘数据管线、retriever 和 Agent 边界。

## Test Plan

### 1. 文档检查

- `next_phase_data_chunk_plan.md` 能搜到 `Elasticsearch`、`rrf_hybrid`、`1455`、`safety_norm_chunks`、`Chunk Optimization Status`。
- `docs/chunking_guide.md` 能搜到 `case_summary`、`case_process`、`safety_case_chunks`、`mock 数据不得进入正式索引`。
- `docs/needed_standards.md` 存在，并按事故类型列出后续规范。

### 2. 一致性检查

- 文档明确当前正式检索来源是 ES/RRF。
- 文档明确当前规范库已建索引，案例库已按 `case_v1` chunk 并可随数据补充重建。
- 文档明确后续新增规范必须先按 `docs/chunking_guide.md` 处理，再构建索引。
- 文档明确 mock 残留已清理，`data/output.json` 只是运行产物，不得作为数据源或索引输入。

### 3. 后续执行检查

- 新增规范资料后，先生成 norm chunks，再重建 `safety_norm_chunks`。
- 事故案例更新后，生成 case chunks，再构建 `safety_case_chunks`。
- ES/RRF 检索验证继续使用 `myenv` 和本地 ES。

## Assumptions

- `next_phase_data_chunk_plan.md` 是当前执行文档。
- `docs/chunking_guide.md` 是唯一 chunk 风格依据。
- 后续用户继续手动补规范资料和案例资料，再按统一 guide 做 chunk 与索引。
