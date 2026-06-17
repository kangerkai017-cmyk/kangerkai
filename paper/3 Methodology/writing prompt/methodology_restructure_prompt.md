# Methodology Restructure and Writing Prompt

## 0. Purpose

This document is a reusable prompt and writing specification for restructuring Chapter 3, Methodology, into a coherent high-level journal style suitable for journals such as *Automation in Construction* and *Computers in Industry*.

The current eight-subsection version is too close to a module-by-module system description. The revised Methodology should instead be organized around a small number of core methodological mechanisms. Each subsection should answer one technical question, explain why the mechanism is needed, describe how it works, and indicate how it will be evaluated.

The target structure is:

```text
3. Methodology
3.1 Overall framework of scenario-personalized dual-evidence safety training
3.2 Scenario-oriented dual-evidence knowledge base
3.3 Case-to-norm evidence linking and dual-path retrieval
3.4 Grounded deliberative generation and output control
```

## 1. Core Paper Argument

Use this one-sentence argument as the anchor for all Methods writing:

> For high-risk construction safety training, this study develops a scenario-personalized Agentic RAG workflow that links accident cases to regulatory clauses before generation and constrains the generated training material through deterministic grounding and bounded arbitration.

The Methodology must support this argument without drifting into unrelated claims.

### 1.1 What the method is

The method is a scenario-personalized, dual-evidence, consistency-constrained Agentic RAG framework for construction safety training.

It uses:

- high-risk work scenarios as the personalization unit;
- construction safety regulations as normative evidence;
- accident reports as cautionary evidence;
- case-to-norm cross-document links to connect accident evidence with regulatory clauses;
- deterministic `chunk_id` grounding to prevent fabricated citations;
- bounded arbitration to handle hallucination, evidence insufficiency, and norm-case conflicts.

### 1.2 What the method is not

Do not frame this paper as:

- a general construction chatbot;
- a worker-profile personalization system;
- a knowledge graph reasoning system;
- a mobile application paper;
- a broad LLM safety assistant without construction-domain evidence constraints.

These topics may appear in Related Work only as comparison points.

## 2. Writing Style Requirements

Use the tone of high-level engineering information journals:

- concise and factual;
- problem-driven rather than promotional;
- methodologically explicit;
- reproducible enough for a reader to rebuild the pipeline;
- every novelty claim tied to a mechanism and an evaluable metric.

Avoid:

- "innovative", "powerful", "excellent", "advanced", "intelligent" unless supported by results;
- saying the method "solves" a problem before experimental evidence exists;
- long lists of agents without explaining why each control step is needed;
- treating RAG as a black-box prompt engineering system;
- overclaiming field deployment or training effectiveness before expert/user studies are complete.

Preferred wording:

- "is designed to";
- "provides a traceable evidence path";
- "reduces the need for the language model to infer";
- "enables evaluation through";
- "constrains generated citations by";
- "supports", "allows", "provides", "records", "checks".

Use stronger wording only after experimental results support it:

- "improves";
- "reduces";
- "outperforms";
- "achieves".

## 3. Revised Methodology Structure

### 3.1 Overall framework of scenario-personalized dual-evidence safety training

#### Purpose

This subsection gives the reader the full method in one view. It should answer:

> What is the proposed framework, what problem does it address, and how do the major components relate?

#### Main message

The proposed method personalizes safety training at the level of high-risk work scenarios rather than individual worker profiles, and it generates training material by combining normative evidence from regulations with cautionary evidence from accident cases under evidence-grounding constraints.

#### Content to include

Write this subsection in the following order:

1. Define the task.
   - Input: a high-risk work topic or work scenario.
   - Output: structured pre-task safety training material and, optionally, a focused safety Q&A response.
2. Explain the personalization unit.
   - Use high-risk work scenario, hazards, accident type, and training objective.
   - Explicitly contrast this with worker-profile-based personalization.
3. Explain the dual evidence idea.
   - Regulations answer "what must be done".
   - Accident cases answer "why it matters".
4. Explain the overall pipeline.
   - Scenario interpretation.
   - Risk planning and query rewriting.
   - Norm and case retrieval.
   - Case-to-norm linking.
   - Evidence-grounded authoring.
   - Consistency checking and arbitration.
   - Final training output or Q&A output.
5. End with a roadmap sentence.
   - Section 3.2 builds the evidence base.
   - Section 3.3 links and retrieves evidence.
   - Section 3.4 controls generation and output reliability.

#### Possible prose skeleton

```text
This study formulates pre-task construction safety training as a scenario-personalized evidence-grounded generation task. Given a high-risk work topic, the framework first specifies the work scenario and associated hazards, then retrieves regulatory requirements and accident cases that correspond to the scenario, and finally generates a structured training material whose claims are traceable to retrieved evidence.

The personalization unit is not a worker profile. Instead, the framework uses the work scenario, hazard type, accident mechanism, and training objective to organize evidence. This design is intended for settings where individual worker records, violation histories, and real-time location data are unavailable or sensitive to use.

The framework consists of three technical layers...
```

#### Figure needed

Use **Fig. 1: Overall framework**.

You can keep the current first figure as the base, but revise it so that it reads as a high-level method figure rather than a detailed software flowchart.

Recommended visual layout:

```text
Input layer
  High-risk work topic / scenario
  Hazard and training objective

Evidence substrate
  Regulation evidence base
  Accident-case evidence base
  Shared tags and chunk_id metadata

Evidence linking and retrieval
  Risk planner
  Query rewriter
  Norm retriever
  Case retriever
  Case-to-norm linker

Grounded generation control
  Evidence-grounded authoring
  Consistency checker
  Arbitration

Outputs
  Pre-task training material
  In-situ safety Q&A
  Diagnostics and citations
```

Figure design guidance:

- Use 4 horizontal bands or 4 vertical blocks.
- Do not put every LangGraph node in the figure.
- Highlight the two evidence streams and the case-to-norm bridge.
- Show the training output and Q&A output as two branches at the end.
- Keep labels short and technical.

---

### 3.2 Scenario-oriented dual-evidence knowledge base

#### Purpose

This subsection explains how the evidence substrate is constructed. It should answer:

> What are the two evidence bases, how are they represented, and why are scenario and hazard metadata necessary?

#### Main message

The evidence base is organized around high-risk work scenarios and hazards, not around generic documents. Regulation chunks provide article-level authoritative requirements, while accident chunks provide causal and consequence evidence. Shared tags and stable identifiers make the two evidence types retrievable, linkable, and auditable.

#### Content to include

Write this subsection in the following order:

1. Explain why a normal text chunk database is insufficient.
   - Safety training requires exact regulatory citation.
   - Accident warnings must be traceable to source cases.
   - Scenario/hazard relevance matters more than generic semantic similarity.
2. Define norm evidence.
   - Article-level chunks.
   - Stable `chunk_id`.
   - `standard_code`, `article_id`, `text`, `scenario_tags`, `hazard_tags`, `requirement_type`, `metadata`, `embedding`.
3. Define case evidence.
   - Structured accident chunks.
   - `case_id`, `accident_type`, `process`, `causes`, `consequences`, `related_standards`, `scenario_tags`, `hazard_tags`, `metadata`, `embedding`.
4. Explain the functional division.
   - Norm evidence: authoritative requirement.
   - Case evidence: warning, mechanism, consequence.
5. Explain why shared metadata matters.
   - It supports dual retrieval.
   - It supports case-to-norm linking.
   - It supports final citation checking.

#### Formula or representation to include

Use compact tuple representations:

```text
c_i^R = (chunk_id, standard_code, article_id, text, metadata,
         scenario_tags, hazard_tags, requirement_type, embedding)

c_j^A = (chunk_id, case_id, accident_type, process, causes,
         consequences, related_standards, metadata,
         scenario_tags, hazard_tags, embedding)
```

Do not overload this subsection with retrieval equations. Save RRF and linking formulas for Section 3.3.

#### Possible prose skeleton

```text
The evidence base is designed as a task-oriented repository rather than a general construction document store. The primary indexing cues are the work scenario and hazard type because the same standard or accident report may support different training objectives under different site conditions.

Regulation evidence is segmented at article level...

Accident evidence is structured into case-level and cause-level chunks...

Together, these two representations allow the system to retrieve not only textually similar content but also evidence that matches the operational scenario, hazard mechanism, and citation requirements of the training task.
```

#### Figure needed

Use **Fig. 2: Scenario-oriented dual-evidence knowledge base**.

Recommended visual layout:

```text
Left branch: Regulation evidence
  Safety standards
  OCR / text cleaning
  Article-level segmentation
  Norm chunk schema
  Norm evidence base

Right branch: Accident evidence
  Accident reports
  Case structuring
  Summary and cause chunks
  Case chunk schema
  Accident-case evidence base

Shared middle/bottom layer:
  scenario_tags
  hazard_tags
  stable chunk_id
  source metadata
  embeddings and lexical index
```

Figure design guidance:

- Use two parallel columns.
- Put shared metadata as a central or bottom layer connecting both columns.
- Show `related_standards` only in the case column, and point it toward the next section.
- Do not include generation or arbitration in this figure.

---

### 3.3 Case-to-norm evidence linking and dual-path retrieval

#### Purpose

This subsection explains the core mechanism of the paper. It should answer:

> How does the method turn separate regulation and accident retrieval into a connected evidence chain?

#### Main message

Instead of retrieving regulations and accident cases independently and leaving their relationship for the language model to infer, the method resolves article-level references from retrieved cases to exact regulation chunks during retrieval. This creates a closed evidence chain before generation.

#### Content to include

Write this subsection in the following order:

1. State the failure mode of ordinary dual-path RAG.
   - Norm and case chunks are retrieved in parallel.
   - The relation between them is inferred in the prompt.
   - This can create plausible but incorrect associations.
2. Explain risk planning and query rewriting.
   - Scenario agent specifies task conditions.
   - Risk planner identifies hazards.
   - Query rewriter produces norm-oriented and case-oriented queries.
3. Explain hybrid retrieval.
   - BM25 for exact terms and standard identifiers.
   - Dense retrieval for semantic paraphrase.
   - Tag retrieval for scenario and hazard constraints.
   - RRF fuses ranked lists.
4. Explain case-to-norm linking.
   - Read `related_standards` from retrieved cases.
   - Normalize references to `standard_code:article_id`.
   - Resolve references through exact lookup.
   - Inject linked norm chunks into the norm evidence set.
   - Mark provenance with `linked_from_case`.
5. Explain the resulting evidence package.
   - norm evidence;
   - case evidence;
   - linked norm evidence;
   - evidence identifiers;
   - retrieval diagnostics.
6. Explain why this is evaluable.
   - link resolution rate;
   - linked norm coverage;
   - citation validity;
   - retrieval recall.

#### Equations to include

RRF:

```latex
\mathrm{RRF}(c) = \sum_{r \in R} \frac{1}{k + \mathrm{rank}_r(c)}.
```

Case-to-norm link:

```latex
\mathcal{R}(A) = \bigcup_{a \in A} \mathrm{related\_standards}(a),
```

```latex
\mathcal{L}(A) =
\{\, c \in \mathcal{C}_R \mid
\langle \mathrm{standard\_code}(c), \mathrm{article\_id}(c) \rangle
\in \mathcal{R}(A) \,\}.
```

#### Possible prose skeleton

```text
The key limitation of ordinary dual-evidence RAG is that retrieval does not define the relation between the two evidence types. A regulation chunk and an accident chunk may both be relevant to the same query, but this does not imply that the accident violated the retrieved regulation. The proposed case-to-norm linker addresses this problem by resolving the structured regulatory references stored in accident cases before generation.

Given a training scenario, the risk planner...
```

#### Figure needed

Use **Fig. 3: Case-to-norm linking and dual-path retrieval**.

Recommended visual layout:

```text
Input scenario
  -> Scenario interpretation
  -> Risk planner
  -> Query rewriter

Two retrieval paths:
  Norm-oriented queries -> Norm retriever -> Retrieved norm chunks
  Case-oriented queries -> Case retriever -> Retrieved case chunks

Linking path:
  Retrieved case chunks
  -> related_standards
  -> exact lookup by standard_code:article_id
  -> linked norm chunks
  -> merged dual-evidence package

Evidence chain callout:
  accident case -> related clause -> safety requirement -> consequence warning
```

Figure design guidance:

- This is the most important module figure.
- Make the case-to-norm arrow visually prominent.
- Clearly distinguish:
  - similarity retrieval;
  - deterministic exact lookup;
  - final merged evidence package.
- Add small labels for evaluable variables:
  - link resolution rate;
  - linked norm coverage;
  - citation validity.

---

### 3.4 Grounded deliberative generation and output control

#### Purpose

This subsection explains how the system controls generation after evidence retrieval. It should answer:

> How does the method ensure that generated training material remains grounded, consistent, and auditable?

#### Main message

The generation process is not a single prompt over retrieved text. It is a bounded deliberative workflow in which the language model selects evidence identifiers, deterministic code reconstructs citations, the checker audits grounding and semantic consistency, and arbitration applies issue-specific remedies.

#### Content to include

Write this subsection in the following order:

1. Explain why retrieval alone is insufficient.
   - Retrieved evidence can still be ignored or misused.
   - The language model may fabricate article numbers or exaggerate cases.
   - Case-derived experience may conflict with formal regulation.
2. Explain evidence-grounded authoring.
   - LLM drafts training content.
   - LLM selects `chunk_id` values.
   - System backfills cited text and metadata from evidence package.
   - LLM does not invent citation content.
3. Explain deterministic grounding.
   - Current retrieved evidence IDs define valid citation set.
   - Invalid IDs are discarded or flagged.
   - This is task-independent and works for both training and Q&A.
4. Explain consistency checking.
   - Deterministic grounding check.
   - Semantic review for exaggeration, insufficiency, or norm-case conflict.
5. Explain arbitration.
   - `hallucination` -> re-ground with same evidence.
   - `evidence_insufficient` -> bounded targeted retrieval.
   - `norm_case_conflict` -> norm-over-case policy and human-review flag.
   - `passed` -> final output.
6. Explain output structure and diagnostics.
   - Structured training material.
   - Citations and evidence provenance.
   - Process diagnostics for evaluation.
7. Explain dual-mode orchestration briefly at the end.
   - Mode A: full training generation.
   - Mode B: lightweight Q&A over the same evidence substrate.

#### Equation to include

Grounded citation set:

```latex
\mathcal{G} = \{\, s \in S \mid s \in \mathcal{E} \,\}.
```

where:

- \(\mathcal{E}\) is the set of valid retrieved or linked evidence identifiers in the current round;
- \(S\) is the set of identifiers selected by the authoring agent;
- identifiers outside \(\mathcal{E}\) are invalid citations.

#### Possible prose skeleton

```text
Constructing a linked evidence package does not by itself guarantee reliable training material. If the evidence package is passed to a single unconstrained generation call, the model may ignore the linked clauses, fabricate citation identifiers, or use an accident case in a way that conflicts with formal regulation. The proposed workflow therefore separates authoring, grounding, checking, and arbitration.

During authoring, the language model is allowed to select evidence but not to create evidence...
```

#### Figure needed

Use **Fig. 4: Grounded deliberative generation and arbitration**.

Recommended visual layout:

```text
Linked dual-evidence package
  -> Evidence-grounded authoring
      LLM selects chunk_id
      System backfills text and metadata
  -> Draft training material
  -> Consistency checker
      deterministic grounding check
      semantic consistency review
  -> Arbitration
      pass -> final training material
      hallucination -> re-grounding
      evidence insufficient -> targeted retrieval
      norm-case conflict -> norm-over-case + human review

Output side:
  structured training material
  safety Q&A answer
  citations and diagnostics
```

Figure design guidance:

- Use a three-tier or swimlane layout:
  1. Authoring
  2. Checking
  3. Arbitration
- Show loops, but keep them bounded.
- Put `MAX_RETRIES` and `dialogue_budget` as small annotations, not central elements.
- Put final output on the right.
- If the figure becomes crowded, move Mode A/Mode B to Fig. 1 and keep Fig. 4 focused only on generation control.

---

## 4. Full AI Writing Prompt

Use the following prompt when asking an AI model or co-author to rewrite the Methodology section.

```text
You are helping write the Methodology section of an English journal article targeting Automation in Construction / Computers in Industry style.

Task:
Rewrite Chapter 3, Methodology, into four coherent subsections rather than a module-by-module list.

Target structure:
3. Methodology
3.1 Overall framework of scenario-personalized dual-evidence safety training
3.2 Scenario-oriented dual-evidence knowledge base
3.3 Case-to-norm evidence linking and dual-path retrieval
3.4 Grounded deliberative generation and output control

Paper context:
The study proposes a scenario-personalized, dual-evidence Agentic RAG method for high-risk construction safety training. The system uses high-risk work scenarios, not worker profiles, as the personalization unit. It retrieves construction safety regulations as normative evidence and accident reports as cautionary evidence. The core mechanism is a case-to-norm cross-document evidence chain: retrieved accident cases contain related_standards references, and the system resolves those references to exact regulation chunks by standard_code and article_id before generation. The generated training material is controlled by deterministic chunk_id grounding, consistency checking, and bounded arbitration.

Core claim:
For high-risk construction safety training, the method links accident cases to regulatory clauses before generation and constrains generated training material through deterministic grounding and bounded arbitration.

Writing style:
Use concise, factual, high-level engineering journal prose. Avoid promotional language. Do not call the method innovative or powerful. Do not claim worker-level personalization, knowledge graph reasoning, or mobile application contribution. Make every method claim tied to a reproducible mechanism or an evaluation variable.

Subsection requirements:

3.1 Overall framework:
- Define the task input and output.
- Explain why personalization is scenario-based rather than worker-profile-based.
- Introduce the two evidence types: regulations and accident cases.
- Summarize the whole pipeline from scenario interpretation to final training/Q&A output.
- Refer to Fig. 1 as the overall framework.

3.2 Scenario-oriented dual-evidence knowledge base:
- Explain why a generic text chunk store is insufficient.
- Define norm evidence schema:
  c_i^R = (chunk_id, standard_code, article_id, text, metadata, scenario_tags, hazard_tags, requirement_type, embedding).
- Define case evidence schema:
  c_j^A = (chunk_id, case_id, accident_type, process, causes, consequences, related_standards, metadata, scenario_tags, hazard_tags, embedding).
- Explain the functional distinction: norm evidence provides authoritative requirements; case evidence provides accident mechanisms and warning consequences.
- Refer to Fig. 2 as the dual-evidence knowledge base.

3.3 Case-to-norm evidence linking and dual-path retrieval:
- Explain the failure of ordinary dual-path RAG: regulations and cases are retrieved together but not explicitly joined.
- Explain risk planning and query rewriting.
- Explain BM25, dense-vector, and tag-based retrieval with RRF.
- Include RRF equation.
- Explain case-to-norm linking:
  collect related_standards from retrieved cases,
  resolve standard_code:article_id by exact lookup,
  inject linked norm chunks into norm evidence,
  mark linked_from_case provenance.
- Include case-to-norm link equations.
- Explain evaluation variables: link resolution rate, linked norm coverage, citation validity.
- Refer to Fig. 3 as the linking and retrieval module.

3.4 Grounded deliberative generation and output control:
- Explain why retrieval alone is insufficient.
- Explain that the LLM selects chunk_id identifiers but does not write citation text from memory.
- Explain deterministic grounding:
  G = {s in S | s in E}.
- Explain consistency checking: deterministic citation check plus semantic review.
- Explain arbitration rules:
  hallucination -> re-grounding;
  evidence_insufficient -> bounded targeted retrieval;
  norm_case_conflict -> norm-over-case policy and human-review flag;
  passed -> final output.
- Explain output structure: scenario, risk-identification prompt, expected hazards, norm requirements, accident warnings, operation points, remedial feedback, quiz.
- Briefly explain dual-mode orchestration: Mode A full training generation; Mode B lightweight safety Q&A.
- Refer to Fig. 4 as grounded generation and arbitration.

Do not:
- create unsupported experimental results;
- invent references;
- add unrelated mobile app details;
- describe every LangGraph node as a separate subsection;
- use more than four Methodology subsections.

Output:
Write polished English manuscript prose with equations in LaTeX and figure references. Keep the section around 2500-3200 words.
```

## 5. Figure Request Summary for Redrawing

### Fig. 1 Overall framework

Purpose:

Show the full method at a high level.

Must include:

- high-risk work topic / scenario input;
- scenario and hazard personalization;
- dual evidence substrate;
- case-to-norm bridge;
- grounded Agentic RAG generation;
- final training material and Q&A output.

Do not include:

- too many individual implementation nodes;
- low-level code names;
- UI/mobile app details.

### Fig. 2 Scenario-oriented dual-evidence knowledge base

Purpose:

Show how regulations and accident reports become retrievable evidence.

Must include:

- regulation document processing;
- accident report structuring;
- norm chunk schema;
- case chunk schema;
- shared scenario/hazard tags;
- stable identifiers and source metadata.

### Fig. 3 Case-to-norm linking and dual-path retrieval

Purpose:

Show the core evidence-chain mechanism.

Must include:

- scenario/risk planning;
- query rewriting;
- norm retrieval path;
- case retrieval path;
- `related_standards`;
- exact norm lookup;
- linked dual-evidence package;
- evidence chain callout.

This is the most important figure.

### Fig. 4 Grounded deliberative generation and arbitration

Purpose:

Show how generated material is controlled after retrieval.

Must include:

- LLM selects `chunk_id`;
- system backfills citation text and metadata;
- deterministic grounding;
- semantic consistency review;
- arbitration branches;
- final output and diagnostics.

## 6. Self-check Before Finalizing the Rewritten Methodology

Use this checklist after rewriting:

- [ ] The Methodology has only 3-4 subsections.
- [ ] The four subsections form a clear sequence: framework -> evidence base -> evidence linking/retrieval -> grounded generation/output.
- [ ] The text does not read like a software module inventory.
- [ ] The case-to-norm link is clearly presented as the core mechanism.
- [ ] The method is distinguished from ordinary RAG without overstating results.
- [ ] The method is distinguished from worker-profile personalization.
- [ ] The method does not claim knowledge graph reasoning.
- [ ] Every figure has a clear role and is referenced in the text.
- [ ] Every equation is introduced before it appears and interpreted after it appears.
- [ ] All generated-output reliability claims are tied to grounding, consistency checking, or arbitration.
- [ ] Experimental variables are mentioned, but no unperformed results are invented.
