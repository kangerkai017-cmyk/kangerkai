# Submission audit for `Automation_in_Construction_full_draft.md`

## Target journal and article stance

- Target journal: Automation in Construction.
- Article type assumed: research article / construction safety information technology methods paper.
- Current file: `paper/Automation_in_Construction_full_draft.md`.
- Writing stance: method-level traceability and reliability for scenario-personalized safety-training generation.
- The manuscript does not claim measured worker learning gains, behavior change, incident reduction, or expert-panel scores.

## Current manuscript structure

- Highlights
- Abstract
- Keywords
- 1 Introduction
- 2 Related work
- 3 Methodology
- 4 Experimental design
- 5 Results
- 6 Discussion
- 7 Conclusions
- Declarations
- References

## Current section word counts

These were checked after the rewrite with a simple token-style word counter.

- Abstract: 270 words
- Introduction: above 1,400 words
- Related work: above 1,700 words
- Methodology: above 3,400 words
- Experimental design: above 1,300 words
- Results: above 1,800 words
- Discussion: above 1,500 words
- Conclusions: within the requested 450-650 word range
- Total manuscript: about 14,150 words including references and declarations

## Evidence used from the current project

- Dataset: `data/eval/training_tasks_v1.jsonl`, 46 tasks.
- Corpus reports:
  - `data/chunks/norm_import_report.json`: 1,791 regulation chunks from 23 standards.
  - `data/chunks/case_import_report.json`: 152 accident chunks from 76 cases.
- Main benchmark:
  - `data/eval/experiments/full_bench_20260604_0335/REPORT.md`
  - `data/eval/experiments/full_bench_20260604_0335/summary.json`
  - `data/eval/experiments/full_bench_20260604_0335/metrics.csv`
- Ablation:
  - `data/eval/experiments/full_ablation_20260604_0714/REPORT.md`
  - `data/eval/experiments/full_ablation_20260604_0714/summary.json`
  - `data/eval/experiments/full_ablation_20260604_0714/metrics.csv`
- Method source: `paper/3 Methodology/Methodology.md`.

## Main non-fabrication choices

- No fabricated expert-evaluation scores were added.
- Expert and field validation are stated only as future work.
- Temporary-electricity results are reported as under-sampled.
- Tier-W norm recall is explained as proxy-gold sensitivity rather than generalized failure.
- Experiments are reported with the actual LLM in the available result files: `Qwen3.5-9B-Q5_K_M`.
- Later or alternative model configurations are not retroactively described as experiment backends.

## Reference expansion audit

- The manuscript now contains 50 numbered references.
- All 50 references include DOI links or DOI-backed arXiv records that were queried through Crossref/DOI metadata.
- The expansion prioritizes Automation in Construction and similar high-level AEC, construction informatics, construction management, safety science, and engineering AI venues:
  - Automation in Construction
  - Advanced Engineering Informatics
  - Journal of Construction Engineering and Management
  - Journal of Computing in Civil Engineering
  - Safety Science
  - Accident Analysis & Prevention
  - Computers in Industry
  - Journal of Information Technology in Construction
- A small number of non-journal method references are retained because they are foundational for the method stack: RAG, DPR, BM25, RRF, hallucination, ReAct, CoT, Toolformer, Self-RAG, and Transformer architecture.
- No title-only reference entries remain.

## Reference checks still needed before submission

- Verify final punctuation, capitalization, initials, and use of `et al.` against the target Elsevier reference style.
- Confirm whether the journal wants arXiv method records replaced by conference/publisher versions where available.
- Confirm whether accented author names should be preserved in the final submission encoding or transliterated.
- Re-check journal quartiles and impact indicators if the cover letter needs to justify reference venue quality; quartiles are not normally listed in the manuscript References section.

## Before submission

1. Add author names, affiliations, corresponding author details, acknowledgements, funding, and CRediT roles.
2. Decide whether to add expert review. If the article remains a method-level traceability paper, the current automated evidence is coherent. If it claims training effectiveness, expert or field evaluation is required.
3. Confirm final figure files, paths, numbering, and journal-resolution requirements.
4. Convert Markdown to the required Word or LaTeX submission format.
5. Check all references in Elsevier style and update in-text citations if the journal requires numbered cross-references in the main text.
6. Review standards and accident-report redistribution restrictions before any public dataset release.
