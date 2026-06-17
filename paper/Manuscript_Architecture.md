# Manuscript Architecture for an Automation in Construction-style Submission

## Target article logic

This manuscript is positioned as a construction information technology methods paper. The paper should be judged on whether the proposed workflow improves the reliability, traceability, and usefulness of scenario-personalized safety training material under fair comparisons. The writing should therefore avoid promotional claims and make every major claim testable through baseline experiments, ablations, or expert evaluation.

One-sentence argument:

> For high-risk construction safety training, the study develops a scenario-personalized Agentic RAG workflow that links accident cases to regulatory clauses before generation and constrains output through deterministic grounding and bounded arbitration.

## Working title

Scenario-personalized safety training for high-risk construction operations using dual-evidence Agentic RAG

## Section structure

### 1. Introduction

Purpose: establish the need for scenario-specific and evidence-grounded construction safety training.

Expected movement:

1. Construction safety training remains important but often weakly coupled with task-specific site risks.
2. Personalized safety training has been explored, but worker-profile-based personalization requires data that may be difficult to obtain or sensitive to deploy.
3. LLM and RAG methods can generate training content, but ordinary RAG may produce weak evidence associations, unsupported citations, and norm-case mismatch.
4. This study proposes a scenario-personalized dual-evidence Agentic RAG method.
5. Contributions: scenario-oriented evidence base, case-to-norm evidence chain, deterministic grounding with arbitration, and comparative evaluation.

### 2. Literature Review

Purpose: position the paper against safety training, RAG, accident-report reuse, and evidence reliability.

Subsections:

1. Construction safety training and personalized learning.
2. LLM and RAG for construction knowledge delivery.
3. Accident reports as safety training evidence.
4. Evidence grounding and reliability in safety-critical generation.
5. Research gaps and objectives.

### 3. Methodology

Purpose: describe a reproducible method, not a software demo.

Source file: `paper/3 Methodology/Methodology.md`.

Subsections:

1. Framework overview.
2. Scenario-oriented regulation evidence base.
3. Accident-case evidence base.
4. Case-to-norm cross-document evidence chain.
5. Dual-evidence retrieval and query rewriting.
6. Evidence-grounded authoring.
7. Consistency checking and arbitration.
8. Dual-mode orchestration.
9. Output and experimental variables.

### 4. Experimental Design

Purpose: make the method falsifiable.

Required parts:

1. Dataset construction and statistics.
2. Retrieval and case-to-norm link evaluation.
3. Training material generation baselines.
4. Ablation experiments.
5. Expert evaluation protocol.
6. Runtime and cost diagnostics.

Baselines:

1. LLM only.
2. Norm-only RAG.
3. Dual-evidence naive RAG.
4. Optimized RAG without arbitration.
5. Proposed method.

Ablations:

1. Without case evidence.
2. Without case-to-norm linker.
3. Without query rewriting.
4. Without deterministic grounding.
5. Without arbitration.

Metrics:

1. Norm citation validity.
2. Evidence grounding rate.
3. Hallucinated citation rate.
4. Hazard coverage.
5. Case relevance.
6. Case-to-norm link resolution rate.
7. Linked norm coverage.
8. Training usefulness score.
9. LLM calls, retrieval calls, node steps, and wall-clock time.

### 5. Results and Analysis

Purpose: report evidence before interpretation.

Expected order:

1. Data and link-resolution statistics.
2. Retrieval performance.
3. Training material quality against baselines.
4. Ablation results.
5. Expert evaluation results.
6. Runtime and cost analysis.

### 6. Discussion

Purpose: explain what the results mean and where they stop.

Required points:

1. Why scenario-personalized training is practical when worker-profile data are unavailable.
2. Why case-to-norm linking is different from simply placing cases and regulations in the same prompt.
3. Why deterministic grounding is necessary for safety-critical generated training material.
4. Trade-off between deliberative generation quality and runtime overhead.
5. Limitations: case scale, OCR quality, expert sample size, and lack of field deployment.

### 7. Conclusion

Purpose: close with bounded claims.

Expected movement:

1. Restate the method contribution.
2. Summarize the decisive evidence after experiments are available.
3. State the implication for construction safety training.
4. Clarify the boundary and next step.

## Style guardrails

1. Use concise, factual prose.
2. Avoid claims that cannot be tied to an experiment.
3. Use "is designed to" before results exist, and "improves" only after a metric supports it.
4. Do not frame the paper as a general chatbot or mobile application.
5. Do not claim worker-level personalization.
6. Do not claim knowledge graph reasoning.
7. Keep module descriptions in the order input, operation, output, and evaluation hook.
8. Keep results and discussion separate: Results report observations; Discussion interprets them.

## Immediate writing sequence

1. Finalize `paper/3 Methodology/Methodology.md`.
2. Write `paper/Experimental_Design.md` after test tasks and metrics are fixed.
3. Write Results only after baseline, ablation, and expert evaluation outputs exist.
4. Write Introduction after Methodology and Experimental Design are stable.
5. Write Abstract last, capped at 150 words for Automation in Construction style.
