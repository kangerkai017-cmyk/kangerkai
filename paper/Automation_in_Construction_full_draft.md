# Scenario-personalized dual-evidence Agentic RAG for traceable construction safety training

## Highlights

- Scenario-level personalization avoids dependence on worker-profile data.
- Accident cases are linked to regulatory clauses before generation.
- Deterministic chunk-id grounding constrains safety citations.
- Two model backends reproduce the case-to-norm recall gain.
- Expanded 58-task validation confirms the trend after corpus growth.

## Abstract

Construction safety training must translate regulations and accident experience into concise, scenario-specific material for high-risk work. Large language models (LLMs) and retrieval-augmented generation (RAG) can retrieve safety documents, but existing workflows often treat regulations and accident reports as parallel text sources and leave the relationship between "what happened" and "which requirement applies" to model inference. This paper proposes a scenario-personalized dual-evidence Agentic RAG workflow for traceable pre-task safety training. The method builds a task-oriented evidence base containing 1,791 regulation chunks from 23 standards and 152 accident-case chunks from 76 cases, retrieves regulation and accident evidence through separate paths, resolves case-to-norm links before generation, and constrains final citations by deterministic chunk-id grounding and bounded arbitration. The workflow was evaluated on 46 high-risk construction training tasks using Qwen3.5-9B-Q5_K_M and DeepSeek v4pro (`deepseek-v4-pro`) as two OpenAI-compatible model backends. With Qwen3.5-9B-Q5_K_M, the proposed method achieved grounding of 1.000, norm recall at k of 0.674, norm citation validity of 0.152, and link resolution of 0.393. With DeepSeek v4pro, it preserved grounding of 1.000 and norm recall of 0.674, with norm citation validity of 0.146 and link resolution of 0.390. Across both backends, optimized dual-evidence RAG remained at norm recall of 0.128 and zero link resolution. Ablations repeated under both backends showed that removing either accident evidence or the case-to-norm linker reduced norm recall to 0.073 and eliminated link resolution. After expanding the corpus to 88 cases and 58 tasks, a DeepSeek v4pro validation again favored the proposed workflow over optimized RAG, with norm recall of 0.586 versus 0.106 and link resolution of 0.349 versus 0.000. The results indicate that explicit cross-document evidence linking is more reliable than simply placing regulation and accident texts in the same prompt. The current study evaluates method-level traceability and reliability; expert and field validation of training effectiveness remain future work.

## Keywords

Construction safety training; Retrieval-augmented generation; Large language model; Agentic RAG; Accident reports; Regulatory compliance; Evidence grounding

## 1. Introduction

Construction safety training is a recurring information-control problem. Workers, supervisors, and safety managers must translate a large body of formal regulations, project procedures, and accident experience into practical guidance for the specific operation about to be performed. The difficulty is most visible in pre-task briefings and toolbox meetings. These settings require material that is short enough for field use, specific enough to match the work scenario, and authoritative enough to support compliance decisions. A briefing for scaffold dismantling should not use the same examples, requirements, and learner questions as a briefing for temporary electricity, lifting operations, or work at height. Yet training material is often prepared from generic checklists or broad safety lectures. Such material may be formally correct, but it can remain weakly connected to the risk mechanisms that workers will encounter in the next task.

The need for scenario-specific training follows from the structure of construction work. Hazards are not only attached to job titles or broad trade categories; they arise from temporary configurations of people, equipment, work surfaces, weather, access routes, protection measures, and management controls. A fall hazard during roof maintenance, a fall hazard at a construction hoist landing, and a fall hazard during suspended-platform work all involve work at height, but the relevant controls, accident mechanisms, and regulatory clauses differ. Similarly, "scaffolding safety" may involve erection, use, alteration, dismantling, inspection, load control, or adjacent falling-object risks. Effective training therefore needs to connect a high-risk work scenario with the regulatory requirements that govern it and with accident cases that make the causal mechanism concrete.

Personalized safety training research has responded to this need by adapting content to worker profiles, behavior, experience, visual attention, location, equipment use, or immersive training states [1-12]. These approaches demonstrate the value of moving beyond one-size-fits-all training. However, they also expose a practical constraint: fine-grained worker data are not always available, shareable, or desirable. Construction projects often involve subcontracted labor, changing crews, temporary work fronts, and limited digital records. Privacy and governance concerns may also restrict the use of worker-level violation history or location traces. For many contractors, supervisors, and training providers, the most stable personalization signal is not a full worker profile but the high-risk work scenario itself: what work is being done, under what condition, with which hazards, and for what training purpose.

LLMs and RAG provide a promising route for generating such scenario-specific training material [23-27,39,40,44,45,50]. Instead of manually authoring a separate briefing for each work situation, a system can retrieve relevant standards and accident reports, then generate a structured explanation, warning, quiz, and remedial feedback. Recent construction safety studies have shown that RAG can improve the quality of generated safety information and that retrieval-based systems can outperform purely parametric LLMs or some fine-tuning settings for safety knowledge retrieval [23-26]. These findings are important because construction safety answers often require current or domain-specific evidence that should not be expected to reside reliably in model parameters. However, retrieving text does not by itself solve the problem of reliable safety training generation. A model may ignore a retrieved clause, cite an article that was not retrieved, conflate similar requirements, or infer an unsupported relationship between an accident case and a regulation.

The distinction between retrieval and traceability is especially important in construction safety because many outputs have an implicit compliance function. A training point that tells workers to inspect a scaffold tie, use a full-body harness, maintain a protective distance, or stop an operation in unsafe weather is not only educational text. It is also an operational instruction that may be audited after an incident. If the system cannot show which clause or case supports the instruction, a safety manager cannot easily check whether the generated material is suitable for the project, whether it reflects the current evidence base, or whether it has mixed requirements from different work phases. Traceability is therefore not an optional interface feature; it is part of the reliability requirement for using generated text in a safety-management workflow.

This evidence-linking failure is central to construction safety training. Regulations and accident cases play different roles in a training explanation. Regulations define what must be done, including mandatory protective measures, inspection requirements, prohibited actions, and procedural constraints. Accident cases explain why those requirements matter, how control failures occur, and what consequences follow when unsafe conditions are not corrected. A conventional dual-evidence RAG system can retrieve both types of documents and place them in the prompt, but it usually does not define the relationship between them. It leaves the language model to infer which clause an accident case supports or violates. In a safety-critical setting, that inference is too weak a foundation for auditable training material.

This paper addresses the gap by treating pre-task construction safety training as a dual-evidence and evidence-control task rather than a general chatbot task. The proposed workflow retrieves regulations and accident cases through separate paths, but it does not stop at parallel retrieval. When retrieved accident cases contain article-level references to standards, the system resolves those references against the regulation corpus before generation. The resulting case-to-norm chain gives the authoring model a structured evidence path from accident mechanism to related regulatory requirement. The model is then used to organize training material and select evidence identifiers, while citation text and metadata are reconstructed deterministically from retrieved chunks. This division of labor is deliberate: the LLM handles interpretation and organization, but the evidence layer controls provenance.

The approach also responds to a practical limitation of many construction document collections. Safety standards, accident investigation reports, and training manuals are not written in the same style. Standards are normative and compact; accident reports are narrative and causal; training documents are pedagogical. Prior work on accident-report mining, safety requirement extraction, and automated compliance checking shows that these document types need structure-aware processing rather than generic text matching [13-17,28,34-38]. A query such as "workers dismantling scaffolding near an opening" may retrieve accident reports describing falls, but the governing article may be expressed in terms of protective facilities, acceptance inspection, or high-place operations. Conversely, a regulation search may retrieve a clause that is correct but abstract, leaving the generated training material without a concrete case that shows how the hazard develops. The proposed method treats these differences as a reason to maintain separate evidence paths and then connect them through structured references.

The proposed workflow is implemented as a LangGraph-style Agentic RAG system with typed state, bounded routes, and deterministic citation checks. It supports two operational modes. The main mode generates full pre-task training material, including scenario description, risk-identification questions, expected hazards, regulatory requirements, accident warnings, operational points, learner-evaluation guidance, remedial feedback, and quiz questions. A shorter question-answering mode uses the same evidence substrate for focused safety queries. Both modes share the same principle: externally presented regulatory claims and accident warnings must be traceable to retrieved or linked evidence.

This design makes the paper's scope deliberately narrower than several adjacent goals. It does not attempt to build a complete learner model, replace expert safety engineers, or prove that generated material improves worker behavior in the field. It instead asks whether a safety-training generation pipeline can make its evidence chain more reliable. This scope is important because automated traceability is a prerequisite for stronger deployment claims. If a generated training document cannot reliably identify its supporting standards and accident cases, then downstream expert review, classroom testing, or field validation becomes harder to interpret.

The study is also motivated by reproducibility. A safety-training generator should not be judged only by a few appealing examples, because the same prompt may behave differently across scenarios, evidence gaps, and model runs. A benchmark with fixed tasks, fixed corpora, baseline variants, ablations, and strict provenance metrics makes it possible to ask which part of the workflow is responsible for improvement. This is why the evaluation emphasizes recall, grounding, link resolution, and ablation effects rather than subjective impressions of fluency.

The contribution of this paper is threefold. First, it presents a scenario-oriented dual-evidence safety knowledge base that structures construction regulations and accident reports using stable chunk identifiers, scenario tags, hazard tags, and article-level references. Second, it introduces a case-to-norm linking mechanism that resolves regulatory clauses from retrieved accident cases before generation, converting accident experience into an explicit cross-document evidence chain. Third, it proposes a grounded Agentic RAG workflow that constrains citations through deterministic chunk-id membership and uses bounded arbitration routes for hallucination, evidence insufficiency, and norm-case conflict. The main evaluation uses 46 high-risk construction safety training tasks derived from 76 accident cases. Five system variants are compared with two LLM backends, and five mechanism-level ablations are repeated under the same two-backend setting. A supplementary expanded validation uses 58 tasks after increasing the accident corpus to 88 cases, with emphasis on the enlarged temporary-electricity subset. The paper is positioned as a construction safety information technology and traceability method study, not as a field intervention study of training effectiveness.

## 2. Related work

### 2.1. Personalized and scenario-specific construction safety training

Construction safety training has long faced a transfer problem: workers may receive safety knowledge in classrooms or general orientations, but must apply it under dynamic site conditions where hazards are temporary, local, and task-specific. Conventional training can communicate rules, but it often struggles to adapt examples and feedback to the situation in which a worker will act. This has motivated research into personalized and context-aware training systems. Prior work has used visual-attention measurements, computer vision, virtual reality, augmented reality, conversational agents, and knowledge-based systems to adjust training content or feedback according to learner characteristics, observed behavior, or task context [1-12,30-33]. The underlying assumption is consistent across these studies: safety learning improves when the learner is shown risks that resemble the work they perform and when feedback targets the hazards they failed to recognize.

Immersive and interactive systems are especially relevant because they make hidden hazards visible and allow learners to experience consequences without real exposure. Eye-tracking and visual-search studies have shown that hazard recognition can be connected with how workers inspect a scene, while VR-based safety training can create repeated practice environments for dangerous operations [2-12]. Conversational AI and LLM-enabled tutors extend this direction by allowing trainees to ask questions and receive adaptive explanations [1,27]. Recent personalized safety-training frameworks have also combined LLM agents with knowledge graph reasoning, indicating a broader shift from static training materials toward dynamically assembled safety knowledge [27,28,34,35].

However, personalization is not a single technical requirement. It can be defined at different units of analysis: the individual worker, the crew, the trade, the task, the equipment, the location, or the accident mechanism. Worker-profile personalization is powerful when reliable data are available, but it is difficult to evaluate and deploy in many construction settings. Worker histories, location traces, sensor streams, and violation records may be incomplete, sensitive, or unavailable across subcontractors. A method that depends on such data can be hard to reproduce in research and hard to adopt in small or temporary projects.

This study therefore uses the high-risk work scenario as the unit of personalization. A scenario is defined by the work activity, site condition, hazard type, accident mechanism, and training objective. Scenario-level personalization is less individualized than a full worker model, but it matches how many safety briefings are actually prepared. Supervisors typically begin from the planned task: "today we dismantle scaffolding", "today we operate lifting equipment", or "today we work near temporary electrical systems". The proposed method uses that task description to retrieve regulatory and accident evidence, generate risk-identification questions, and select accident warnings. The distinction from prior personalization work is not that worker profiles are unimportant, but that scenario evidence is a practical and auditable minimum unit for automated safety training generation.

### 2.2. LLMs and RAG in construction safety knowledge retrieval

LLMs have recently been explored for construction safety regulation extraction, risk analysis, safety question answering, and training-material generation. Their strength is linguistic flexibility: they can explain dense regulatory language, summarize accident narratives, and assemble coherent instruction from heterogeneous evidence. Their weakness is equally important: without external evidence control, they may produce fluent but unsupported safety claims. This risk is amplified in construction safety because regulations contain exact article numbers, conditions, exceptions, and mandatory wording. A plausible answer that cites the wrong clause is not merely a stylistic error; it can undermine compliance and accountability.

RAG addresses part of this problem by augmenting generation with retrieved documents. In general NLP, RAG combines parametric model knowledge with non-parametric memory and has been shown to improve knowledge-intensive generation [39,40,44]. In construction, recent studies have evaluated RAG for safety information generation, safety management knowledge retrieval, building-code interpretation, and construction management question answering [23-26]. These studies show that retrieval can improve answer relevance and reduce reliance on model memory. They also show that retrieval quality, chunking strategy, domain-specific corpora, and citation discipline strongly affect output reliability.

The construction safety setting adds two complications to ordinary RAG. First, topical relevance is not enough. A retrieved clause may discuss the same hazard but not the same operation, work phase, or control requirement. Second, training material often needs more than one evidence type. Regulations provide authority, while accident cases provide causal experience and consequence-based warning. A norm-only RAG system can produce rule-like output but may lack vivid risk explanation. A case-only or case-heavy system can produce compelling stories but may not identify the governing requirement. A dual-evidence system can retrieve both, but unless their relationship is structured, it may still rely on model inference to connect them.

This paper therefore treats RAG as an evidence-control architecture rather than only as a retrieval add-on. The proposed workflow separates norm retrieval and case retrieval because the two corpora use different language. It then resolves case-to-norm references before generation, so the link between accident case and regulatory clause is represented as data rather than inferred in prose. This differs from conventional dual-source prompting, where both sources are placed in context but the model must decide how they relate. For safety training, the difference is material: a generated warning should be traceable not only to an accident narrative, but also to the formal requirement that the accident helps explain.

### 2.3. Accident cases as reusable safety knowledge

Accident reports are a critical but underused knowledge source for safety training. Regulations tend to state what should be done; accident reports show how systems fail when controls are absent, ignored, or poorly managed. A single accident report can contain unsafe acts, missing protections, equipment defects, management failures, environmental conditions, emergency-response problems, and consequences. These elements make accident cases useful for training because they help learners connect abstract requirements with concrete causal pathways [13-22].

Accident cases are also difficult to use computationally. They are often written as narrative documents rather than structured datasets. They may contain multiple causes, multiple responsible parties, and references to several standards. Some reports cite exact article numbers; others cite only a standard name or provide no formal reference. Case titles, dates, processes, causes, and consequences can be inconsistently formatted. If a model is asked to infer regulatory violations directly from such narratives, the output may become plausible but unverified. The more similar the regulations are, the easier it is for a model to select a nearby but incorrect article.

Knowledge reuse from accident reports therefore requires more structure than ordinary document retrieval. At minimum, cases need stable identifiers, accident-type labels, scenario tags, hazard tags, causal summaries, source metadata, and explicit related-standard fields when available. These fields allow accident cases to function as cautionary evidence rather than as unbounded narrative context. They also make evaluation possible: a system can be tested on whether it retrieves expected cases, resolves referenced standards, and uses accident-derived evidence without replacing formal requirements.

The proposed knowledge base follows this logic. Each accident case is represented by a summary chunk and a cause-oriented chunk. Each chunk stores accident type, process, causes, consequences, scenario tags, hazard tags, and related-standard references. The related-standard field is the bridge from experience to regulation. When a retrieved case cites an article, the system resolves that article against the regulation corpus and injects the linked norm chunk into the evidence package. This design changes the role of accident cases in generation. They are not merely stories added for engagement; they become structured triggers for retrieving and explaining authoritative requirements.

### 2.4. Grounding, provenance, and reliability in safety-critical generation

Safety-critical generation requires a stronger notion of grounding than general answer relevance. In open-domain applications, a generated answer may be considered acceptable if it is broadly correct and cites a relevant passage. In construction safety training, the output may instruct workers on protective equipment, prohibited operations, inspection requirements, or emergency controls. The cost of an unsupported claim is therefore high. A model that invents a clause number, omits a necessary condition, or attributes an accident cause to the wrong requirement can create false confidence.

Grounding can be approached in several ways, including source attribution, retrieval-constrained decoding, post-hoc citation checking, fact verification, and human review. The need for such controls is reinforced by studies of hallucination in natural-language generation and by recent RAG work that adds retrieval, critique, or tool-use loops around LLMs [43-49]. The present study uses a simple but strict deterministic rule: a cited chunk identifier is valid only if it belongs to the evidence package retrieved or linked in the current run. The language model may select chunk identifiers, but it does not generate citation text, article numbers, standard names, or source metadata from memory. These fields are reconstructed from the evidence store. This rule does not prove that the selected article is the best article, but it prevents a class of unsupported citation errors and makes every cited source auditable.

The method also separates deterministic grounding from semantic consistency checking. Deterministic grounding verifies set membership and provenance. Semantic checking evaluates whether the draft overstates evidence, lacks support, or contains norm-case conflict. A bounded arbitration layer then routes different issue types to different corrective actions. Hallucination returns to authoring with the same evidence package. Evidence insufficiency can return to retrieval if the budget allows. Norm-case conflict applies a norm-over-case policy and flags the issue for human review. This is intentionally more constrained than open-ended "self-reflection", which can be difficult to reproduce and audit.

This separation is also important for evaluation. A system may retrieve the right source but cite it incorrectly, cite a valid source that does not support the claim, or produce a reasonable claim without preserving its provenance. These are different failure modes and should not be collapsed into a single accuracy score. Construction safety applications need metrics that distinguish retrieval recall, citation validity, grounding, link resolution, and semantic adequacy. The evaluation in this paper follows this principle by reporting both evidence-substrate metrics and final-output metrics, while leaving direct learning outcomes for later expert and field studies.

Accordingly, the proposed method is closer to a traceable safety-information pipeline than to an unconstrained tutoring agent.

The contribution relative to prior grounded generation work is the adaptation of provenance control to the structure of construction safety evidence. The system uses article-level regulation chunks, case chunks, related-standard references, stable chunk identifiers, and typed graph state. Reliability is therefore pursued not only through better prompting, but also through data modeling and workflow control. This is consistent with the broader direction of construction automation research, where AI systems are increasingly expected to be inspectable, reproducible, and aligned with domain-specific information structures.

## 3. Methodology

### 3.1. Overall framework of scenario-personalized dual-evidence safety training

This study formulates pre-task construction safety training as a scenario-personalized and evidence-grounded generation task. Given a high-risk construction work topic, the proposed method first interprets the corresponding work scenario and risk context, then retrieves two complementary types of evidence, namely regulatory requirements and accident cases, and finally generates structured safety training material whose key claims are traceable to retrieved evidence. The method is designed for safety briefings, toolbox training, and focused safety question answering, where the generated content must be operationally relevant, technically reliable, and auditable.

The personalization unit in this study is the high-risk work scenario rather than an individual worker profile. Existing personalized safety training systems often depend on worker attributes, job roles, violation records, equipment usage, location information, or mobile-device context. Although such information can support fine-grained personalization, it may be difficult to obtain in research settings and may introduce privacy, deployment, and data-governance constraints. In contrast, this study organizes personalization around the work activity, hazard type, accident mechanism, and training objective. For example, scaffold dismantling, temporary electrical work, lifting operations, and work at height are treated as distinct training scenarios. Each scenario determines the hazards to be covered, the regulatory clauses to be retrieved, and the accident mechanisms to be explained. This design preserves the operational specificity required for construction safety training while avoiding dependence on personal worker data.

The framework uses two complementary evidence types. Regulation evidence provides authoritative safety requirements, including mandatory protective measures, prohibited actions, inspection items, and procedural constraints. Accident-case evidence provides experiential and cautionary support, including how accidents occurred, which unsafe acts or conditions contributed to them, and what consequences followed. These two evidence types answer different training questions. Regulations clarify what must be done, whereas accident cases explain why the requirement matters in practice. Training material based only on regulations may be accurate but abstract, while material based only on accident cases may be vivid but insufficiently authoritative. Therefore, the proposed method treats regulation evidence and accident-case evidence as a joint evidence substrate for generating safety training content.

The workflow is implemented as a LangGraph-based Agentic RAG system rather than a linear retrieve-then-generate prompt chain. Specifically, the training workflow is compiled as a `StateGraph` over a shared `TrainingState`. Each agent, node, or subgraph reads selected state fields, writes structured outputs back into the same state, and transfers control through explicit graph edges. This design makes the agentic process reproducible and inspectable. The system does not rely on several independent chat agents negotiating through unconstrained natural language. Instead, it relies on typed state updates, evidence identifiers, conditional routes, and bounded loops that can be logged, checked, and evaluated.

At the graph level, the method contains three coordinated subgraphs. The evidence acquisition subgraph receives the interpreted scenario, plans hazards, rewrites queries, retrieves regulation and accident evidence through separate paths, and resolves case-to-norm links. The authoring subgraph fuses the retrieved evidence, selects valid `chunk_id` citations, reconstructs citation content from retrieved chunks, and drafts structured training material. The arbitration subgraph reviews checker outputs and decides whether the workflow should return to evidence acquisition, return to authoring, apply a norm-over-case policy, or release the output. The top-level route is therefore:

```text
scenario_agent -> evidence_subgraph -> authoring_subgraph
-> arbitration_subgraph -> training_agent
```

Conditional routes are triggered when the checker identifies hallucinated citations, evidence insufficiency, or norm-case conflict. Only hallucination and evidence insufficiency form bounded loops; norm-case conflict is handled through the norm-over-case policy and a human-review flag.

Figure 1 summarizes the overall workflow in three stages. Figure 1a shows how a high-risk work topic is converted into a scenario-specific training state through scenario interpretation and risk planning. Figure 1b shows how regulation evidence and accident-case evidence are retrieved through separate paths and connected through case-to-norm linking. Figure 1c shows how the linked evidence package is converted into structured training material through grounded authoring, consistency checking, and bounded arbitration.

![Figure 1. Overall workflow of the proposed scenario-personalized dual-evidence Agentic RAG safety training method.](<3 Methodology/figures/fig1.png>)

**Figure 1. Overall workflow of the proposed scenario-personalized dual-evidence Agentic RAG method.** (a) A high-risk work topic is converted into a scenario-specific training state through scenario interpretation and risk planning. (b) Regulation and accident-case evidence are retrieved through separate paths and linked through case-to-norm lookup. (c) The linked evidence package is converted into structured training material through grounded authoring, consistency checking, and bounded arbitration.

The remainder of this section follows the framework structure. Section 3.2 describes how the scenario-oriented dual-evidence knowledge base is constructed. Section 3.3 presents the case-to-norm linking mechanism and the dual-path retrieval process. Section 3.4 explains how the linked evidence package is converted into grounded training material and controlled through consistency checking and arbitration.

### 3.2. Scenario-oriented dual-evidence knowledge base

The evidence base is designed as a task-oriented repository rather than a general construction document store. In a generic RAG system, source documents are often divided into fixed-size chunks and retrieved mainly by text similarity. This strategy is insufficient for construction safety training for three reasons. First, regulatory requirements must be cited at the article level because compliance-related claims are normally asserted against specific clauses. Second, accident warnings must remain traceable to source cases because unsupported or exaggerated accident descriptions can reduce credibility and may mislead trainees. Third, the relevance of a regulation or accident case depends not only on semantic similarity, but also on the work scenario, hazard mechanism, and training purpose. The proposed evidence base therefore combines stable identifiers, source metadata, scenario tags, hazard tags, and vector representations.

Regulation evidence is segmented at the level of regulatory articles whenever the source structure allows article-level parsing. Tables, figures, definitions, and explanatory notes are retained as separate chunks when they contain safety-relevant information or support the interpretation of article-level requirements. Each norm chunk is represented as:

```text
c_i^R = (chunk_id, standard_code, article_id, text, metadata,
         scenario_tags, hazard_tags, requirement_type, embedding).
```

The `chunk_id` is a stable provenance anchor constructed from the standard code and article identifier, such as `JGJ-80-2016:3.0.5`. The `standard_code` and `article_id` fields support exact citation and exact lookup. The `text` field stores the regulatory content. The `metadata` field retains the standard name, chapter, title, source path, and chunk type. The `scenario_tags` field records relevant work scenarios, such as work at height, temporary electricity, scaffold use, scaffold dismantling, lifting operations, and construction machinery. The `hazard_tags` field records risk types, such as fall from height, electric shock, object strike, collapse, mechanical injury, lifting injury, and management deficiency. The `requirement_type` field distinguishes mandatory requirements, prohibited behaviors, inspection requirements, protective measures, definitions, tables, and other regulatory functions.

Accident evidence is structured around accident events and their causal descriptions. The raw accident report is not treated as a single undifferentiated text block. Instead, each case is parsed into chunks that preserve the accident process, causal factors, consequences, and available regulatory references. Each case chunk is represented as:

```text
c_j^A = (chunk_id, case_id, accident_type, process, causes,
         consequences, related_standards, metadata,
         scenario_tags, hazard_tags, embedding).
```

The `case_id` identifies the accident case across chunks. The `accident_type` field records the primary accident category, such as fall from height, object strike, electric shock, collapse, mechanical injury, or lifting injury. The `process` field describes how the accident unfolded. The `causes` field records direct and indirect causes, including unsafe acts, missing protections, equipment defects, management failures, and environmental conditions. The `consequences` field records casualties, losses, or reported outcomes. The `related_standards` field stores article-level references to regulations when such references are available in the original report or can be verified during data preparation. These references are normalized into a `standard_code:article_id` form whenever possible.

The two evidence types play different methodological roles. Norm chunks provide the authoritative basis for safety requirements, while accident chunks provide causal warnings and consequence explanations. This separation prevents accident-derived experience from being treated as a substitute for formal regulation. At the same time, it prevents regulatory clauses from being presented as abstract rules without practical accident context. Shared scenario and hazard metadata make it possible to retrieve both types of evidence for the same work situation, while stable `chunk_id` values make it possible to verify whether final citations were actually retrieved in the current evidence package.

![Figure 2. Scenario-oriented dual-evidence knowledge base.](<3 Methodology/figures/fig2.png>)

**Figure 2. Scenario-oriented dual-evidence knowledge base.** Regulation documents are processed into article-level norm chunks with stable regulatory identifiers. Accident reports are structured into case chunks containing accident process, causes, consequences, and related-standard references. Both evidence bases share scenario tags, hazard tags, source metadata, lexical indexes, and vector representations, enabling scenario-oriented retrieval and cross-document evidence linking.

This representation also makes the evidence base evaluable. The norm corpus can be assessed by citation completeness, article-level coverage, tag quality, and retrieval recall. The accident corpus can be assessed by case coverage, accident-type distribution, source traceability, and the proportion of cases with article-level `related_standards`. These variables are important because the quality of the generated training material depends on whether the evidence substrate contains retrievable, traceable, and linkable information.

### 3.3. Case-to-norm evidence linking and dual-path retrieval

A key limitation of ordinary dual-evidence RAG is that retrieval alone does not define the relationship between the two evidence types. A regulation chunk and an accident chunk may both be relevant to a query, but this does not necessarily mean that the retrieved accident violated the retrieved regulation. If the relationship is left for the language model to infer during generation, the model may produce plausible but incorrect associations, especially when multiple similar clauses, hazards, and work procedures appear in the same scenario. The proposed case-to-norm linker addresses this problem by resolving structured regulatory references from retrieved accident cases before generation.

The retrieval process begins with scenario and risk planning. Given a high-risk work topic, the scenario interpretation module specifies the work activity, site condition, risk clues, and training objective. The risk planner then identifies the hazards that should be covered and decomposes the task into two retrieval objectives. The norm retrieval objective targets regulatory requirements, inspection clauses, protective measures, and prohibited behaviors. The case retrieval objective targets accident mechanisms, unsafe actions, direct causes, indirect causes, and consequences. This separation is necessary because regulations and accident reports use different language. A regulation may state that a protective device shall be installed, inspected, or maintained, whereas an accident report may describe a fall, collapse, electric shock, or object strike caused by missing or ineffective controls.

The query rewriter adapts planned queries to the target evidence path. For the norm path, it adds regulatory wording, standard-oriented expressions, inspection terms, and requirement-oriented terms. For the case path, it emphasizes accident type, unsafe action, causal factor, consequence, and site condition. When later arbitration identifies evidence insufficiency, the rewriter can reformulate the query according to the missing hazard, missing requirement, or missing case type. This makes retrieval improvement controlled and bounded rather than open-ended.

Both evidence paths use hybrid retrieval. BM25 is used to retrieve exact terms, standard numbers, article identifiers, and construction safety expressions [41]. Dense-vector retrieval is used to capture semantic paraphrase and informal site descriptions [40]. Tag-based retrieval is used to enforce scenario and hazard relevance. The ranked lists from these retrieval channels are fused by reciprocal rank fusion [42]:

$$
\mathrm{RRF}(c) = \sum_{r \in R} \frac{1}{k + \mathrm{rank}_r(c)}, \tag{1}
$$

where \(R\) is the set of retrieval channels, \(\mathrm{rank}_r(c)\) is the rank of chunk \(c\) in retrieval channel \(r\), and \(k\) is a smoothing constant. This fusion strategy is suitable for construction safety training because queries often combine formal terminology and site-level descriptions. A single retrieval channel may retrieve precise regulatory clauses but miss paraphrased hazards, or retrieve semantically similar accident reports but miss exact standard references.

After the case retriever returns accident chunks, the case-to-norm linker reads the `related_standards` field of the retrieved cases. Given a retrieved set of accident chunks \(A \subseteq \mathcal{C}_A\), the system collects article-level references as:

$$
\mathcal{R}(A) = \bigcup_{a \in A} a.\texttt{related\_standards}.
$$

Each reference is then resolved by exact match on \(\langle \mathrm{standard\_code}, \mathrm{article\_id} \rangle\) against the regulation corpus:

$$
\mathcal{L}(A) =
\{\, c \in \mathcal{C}_R \mid
\langle \mathrm{standard\_code}(c), \mathrm{article\_id}(c) \rangle
\in \mathcal{R}(A) \,\}. \tag{2}
$$

The linked norm chunks \(\mathcal{L}(A)\) are deduplicated by `chunk_id` and merged into the norm evidence set. Each linked chunk is marked with `linked_from_case`, which records the accident case from which the reference was resolved. This provenance tag allows the system to distinguish norm evidence retrieved through similarity-based search from norm evidence injected through a case-derived regulatory reference.

![Figure 3. Case-to-norm evidence linking and dual-path retrieval.](<3 Methodology/figures/fig3-2-case-norm-chain.png>)

**Figure 3. Case-to-norm evidence linking and dual-path retrieval.** The scenario is decomposed into norm-oriented and case-oriented queries. Norm and case chunks are retrieved through separate hybrid retrieval paths. Retrieved cases provide `related_standards`, which are resolved by exact lookup against the regulation corpus. The linked norm chunks are injected into the evidence package, producing a closed evidence chain from accident case to related clause, safety requirement, and consequence warning.

The output of this stage is a linked dual-evidence package:

```text
E = (E_R, E_A, E_L, IDs_R, IDs_A, IDs_L, D),
```

where \(E_R\) is the retrieved norm evidence, \(E_A\) is the retrieved accident evidence, \(E_L\) is the linked norm evidence, \(IDs_R\), \(IDs_A\), and \(IDs_L\) are the corresponding identifier sets, and \(D\) contains retrieval diagnostics. This package becomes the only valid evidence source for downstream generation and checking. The mechanism also exposes evaluation variables, including retrieval recall, link resolution rate, linked norm coverage, and citation validity. Therefore, the evidence link is not only a design feature but also a testable component of the proposed method.

### 3.4. LangGraph-based grounded deliberative generation and output control

Constructing a linked evidence package does not by itself guarantee reliable training material. If the evidence package is passed to a single unconstrained generation call, the language model may ignore linked clauses, fabricate citation identifiers, overstate accident consequences, or use accident-derived experience in a way that conflicts with formal regulation [43]. The proposed workflow therefore separates authoring, grounding, checking, and arbitration within a LangGraph `StateGraph`, following the broader idea that LLM systems can be made more reliable by combining generation with retrieval, acting, critique, and tool-use steps [46-49]. The language model is used to interpret scenarios, organize evidence, and select candidate citations, while deterministic procedures control citation validity, state transitions, and failure handling.

The graph begins with `scenario_agent`, which converts a broad topic into a searchable training scenario. A topic such as scaffold dismantling, temporary electricity, or lifting operation is expanded into a work activity, site condition, risk clues, and training objective. These fields are written into `TrainingState` as `training_scenario` and then used by downstream nodes. This step prevents retrieval from being driven only by the literal topic string. Its output is evaluated indirectly by whether the planned hazards and retrieved evidence cover the intended operation.

The `evidence_subgraph` then acquires evidence for one bounded round. It starts from the input fields `topic`, `training_scenario`, hazards, and retrieval feedback if arbitration has supplied an `evidence_request`. The risk-planning node writes `hazards_identified`, `norm_queries`, and `case_queries`. The query-rewriting node specializes the planned queries for the two evidence paths. The norm and case retrievers execute in parallel and write `norm_evidence`, `case_evidence`, `norm_evidence_ids`, and `case_evidence_ids`. The case-to-norm linker reads the retrieved cases' `related_standards`, resolves exact regulation chunks, appends linked norm evidence, and writes `linked_norm_evidence_ids`. The output is not prose but an auditable evidence state containing norm evidence, case evidence, linked norm evidence, evidence identifiers, and retrieval diagnostics.

The `authoring_subgraph` converts this evidence state into a draft training material. Its evidence-fusion node receives the scenario, identified hazards, norm evidence, case evidence, linked norm evidence, and diagnostics. It organizes the content into a pedagogical sequence: work scenario, risk-identification prompt, expected hazards, regulatory requirements, accident warnings, operational precautions, learner-response evaluation, remedial feedback, and follow-up quiz. This sequence supports a short training loop in which the learner first identifies risks and then receives evidence-supported correction and reinforcement. The node also produces structured evidence selections rather than free-form citation text.

A key design decision is to separate semantic evidence selection from factual citation reconstruction. During evidence fusion, the language model may select relevant evidence by emitting `chunk_id` values. It is not allowed to create citation text, article numbers, or accident source metadata from memory. The system reconstructs cited regulation text, accident metadata, source fields, and case-to-norm provenance from the retrieved evidence package. This design constrains generated citations to observed evidence and reduces the risk of fluent but unsupported safety claims.

Let \(\mathcal{E}\) be the set of valid evidence identifiers retrieved or linked in the current round, and let \(S\) be the set of identifiers selected by the authoring agent. The grounded citation set is defined as:

$$
\mathcal{G} = \{\, s \in S \mid s \in \mathcal{E} \,\}. \tag{3}
$$

Any selected identifier \(s \notin \mathcal{E}\) is rejected as an invalid citation. Valid identifiers are expanded into citation content through deterministic lookup. Because this rule depends only on set membership, it can be applied to both pre-task training generation and focused safety question answering.

The consistency checker combines deterministic grounding with semantic review. The deterministic check verifies whether every cited `chunk_id` belongs to the current evidence package and whether available norm evidence has been cited when regulatory claims are made. The semantic review checks whether the draft contains unsupported requirements, insufficient evidence, exaggerated accident warnings, or norm-case conflicts. These two checks address different failure modes. Deterministic grounding can precisely detect invalid citation identifiers, but it cannot judge whether a retrieved case has been overinterpreted. Semantic review can identify overstatement and conflict, but it must be constrained by deterministic citation evidence. The checker writes `consistency_passed`, `consistency_issues`, `retry_count`, and `retry_reason` into `TrainingState`.

The `arbitration_subgraph` replaces a generic "reflect and retry" prompt with explicit deliberation and route application. It reads the control fields in `TrainingState`, including consistency issues, retry reason, dialogue budget, case-index availability, and current retry count. The deliberation node writes an `arbitration_decision` and an `arbitration_route`. The apply-decision node performs deterministic side effects, such as demoting conflicting case warnings, setting `requires_human_review`, or creating a structured evidence request. When the checker reports a problem, the arbiter applies issue-specific rules:

```text
hallucination           -> authoring_subgraph
evidence_insufficient   -> evidence_subgraph
norm_case_conflict      -> apply norm-over-case policy and flag human review
passed                  -> training_agent
```

For hallucination, the route returns to `authoring_subgraph` and re-grounds the draft using the same evidence package because the failure lies in generation or citation selection. For evidence insufficiency, the arbiter emits a structured evidence request that identifies the missing hazard, requirement, or case type, and then routes to `evidence_subgraph` only if the dialogue budget allows another retrieval round and the case index is available. For norm-case conflict, the regulation is treated as authoritative. The conflicting case experience is retained only as supplementary warning evidence, its provenance is preserved, and the case is flagged for human review. This policy prevents accident-derived practice from overriding formal safety requirements.

The terminal `training_agent` is invoked only after the graph route converges. It receives the scenario, hazards, grounded fused evidence, draft output, consistency status, and arbitration diagnostics, and then produces the final structured training material. The final output retains the same citation discipline: selected final citations must be drawn from grounded norm requirements and case warnings already reconstructed from the evidence package. Thus, the terminal node formats and completes the training material but does not create a new evidence base.

All loops are bounded by `MAX_RETRIES` and `dialogue_budget`. This constraint is necessary because an Agentic RAG workflow should not rely on uncontrolled self-reflection or indefinite retrieval. The bounded state graph is also a methodological advantage over ordinary "reflect and retry" prompting: each retry has a typed reason, a fixed route, and a finite budget. The arbitration output records the decision type, route, evidence request, retry count, and human-review flag. These diagnostics allow the experimental section to evaluate both quality and cost, including hallucinated citation rate, evidence sufficiency, conflict handling, LLM calls, retrieval calls, node steps, and wall-clock time.

![Figure 4. LangGraph-based grounded deliberative generation and arbitration.](<3 Methodology/figures/fig3-3-dual-mode-orchestration.png>)

**Figure 4. LangGraph-based grounded deliberative generation and arbitration.** The training workflow is represented as a stateful graph over shared `TrainingState`. The evidence, authoring, and arbitration subgraphs write evidence fields and control fields into the same state. Conditional routes send hallucination back to authoring, evidence insufficiency back to evidence acquisition, norm-case conflict to a norm-over-case policy with human-review flag, and passed drafts to the training agent. `MAX_RETRIES` and `dialogue_budget` bound all loops.

The same evidence-control mechanism supports two operation modes. Mode A is full pre-task training generation. It invokes scenario interpretation, risk planning, dual retrieval, case-to-norm linking, grounded authoring, consistency checking, arbitration, and final training material generation. Mode B is lightweight safety question answering. It uses the same evidence substrate, linking mechanism, and grounding rule, but follows a shorter path and reports low confidence when evidence is insufficient rather than repeatedly searching. This dual-mode design allows the method to support both comprehensive training material and focused safety answers without abandoning traceable evidence control.

Overall, the proposed methodology converts high-risk work scenarios into linked norm-case evidence packages and constrains generation through deterministic grounding and bounded arbitration. The intended contribution is not a general construction chatbot, but a reproducible evidence-control pipeline for generating scenario-specific, regulation-aware, accident-informed, and traceable construction safety training material.

## 4. Experimental design

### 4.1. Evaluation objective and task construction

The evaluation was designed to test whether the proposed workflow improves evidence traceability and retrieval reliability for scenario-specific construction safety training. It was not designed to test whether workers trained with the generated material show improved field performance. The primary experimental question was therefore method-level: can explicit case-to-norm linking and deterministic grounding improve the availability, validity, and provenance of regulatory and accident evidence compared with LLM-only and RAG baselines?

The task set contains 46 high-risk construction safety training tasks derived from 76 accident cases. Each task describes a scenario summary, expected hazards, expected scenario tags, expected regulatory references, expected accident-case references, expected training points, source case identifier, source case title, accident type, and construction method metadata. The four themes are work at height (9 tasks), scaffolding (22 tasks), lifting operations (13 tasks), and temporary electricity (2 tasks). The theme distribution reflects the available accident corpus and the initial focus on high-risk work categories rather than a balanced benchmark across all construction hazards.

The tasks were divided into two evidence tiers. Tier-S contains 33 tasks with full article-level gold references resolved from accident-case standards. These tasks provide the strongest test of the case-to-norm linker because the expected regulation articles are available as exact references. Tier-W contains 13 tasks with weaker or proxy references, typically because the source case cited only a standard name or because a fallback article was used during task construction. Tier-W is retained because it reflects realistic accident-report incompleteness, but Tier-S is emphasized when interpreting article-level norm recall.

The regulation corpus contains 1,791 chunks from 23 Chinese construction safety standards. The chunking report shows 1,705 article chunks, 56 term chunks, 27 table chunks, and 3 figure chunks, with no duplicate chunk identifiers and no validation issues. The accident corpus contains 152 chunks from 76 cases, with one summary chunk and one cause-oriented chunk for each case. The case corpus includes fall from height, mechanical injury, collapse, lifting injury, object strike, electric shock, and other accident types. Four cases lack related-standard references, which creates a realistic but limited test of missing cross-document links.

The corpus was intentionally kept close to the evidence used by the system rather than converted into a fully normalized legal database. This preserves the actual conditions under which a RAG workflow must operate: standards contain tables, definitions, and article text; accident reports vary in how they describe causes and cite standards; and some references are incomplete. The evaluation therefore measures performance over a curated but still heterogeneous evidence base. This choice makes the task harder than testing only on hand-selected clauses and also makes the failure modes more informative for deployment.

After the main 46-task two-backend validation, the accident corpus was expanded to 88 cases and 176 accident-case chunks. The corresponding deterministic task builder produced 58 tasks: work at height (9), scaffolding (19), lifting operations (13), and temporary electricity (17). This expanded set is reported separately because it was generated after the original Qwen and DeepSeek two-backend comparison. It is used as a supplemental validation of whether the same mechanism-level trend holds after corpus growth, especially for temporary electricity, which increased from 2 diagnostic tasks to 17 tasks, including 13 Tier-S tasks.

### 4.2. System variants and fairness controls

Five variants were compared in the main benchmark. The LLM-only baseline generated training material without retrieval. The norm-only RAG baseline retrieved regulatory chunks only. The naive dual RAG baseline retrieved regulation and accident evidence in parallel but did not perform case-to-norm linking or deterministic evidence control. The optimized RAG baseline used stronger hybrid retrieval and ranking but still lacked the case-to-norm linker and bounded arbitration. The proposed method used dual evidence, case-to-norm linking, deterministic grounding, consistency checking, and bounded agentic orchestration.

The main benchmark contained 230 runs for each model backend, corresponding to 46 tasks multiplied by five variants. All variants used the same task set, regulation corpus, accident corpus where applicable, and evaluation scripts. Retrieval-enabled variants used the same Elasticsearch-backed evidence store. The original local-model experiment used Qwen3.5-9B-Q5_K_M through an OpenAI-compatible local server at `localhost:51000`. A second-backend replication used DeepSeek v4pro through the OpenAI-compatible DeepSeek API, with `LLM_MODEL=deepseek-v4-pro` and `OPENAI_BASE_URL=https://api.deepseek.com`. The two backends are reported separately rather than pooled.

The baseline design separates three possible explanations for performance. First, the LLM-only baseline tests whether model parameters alone can generate traceable safety material. Second, the norm-only and naive dual RAG baselines test whether retrieval of relevant text is sufficient. Third, the optimized RAG baseline tests whether improved retrieval and reranking alone can approach the proposed method without explicit cross-document linking. This structure is important because the core claim of the paper is not simply that "more context helps", but that a structured case-to-norm evidence chain changes the reliability of the evidence package.

Fairness was handled by keeping the evaluation inputs, corpora, and scoring scripts fixed across variants. The baselines were not given worker-profile data, expert annotations, or manually selected evidence that the proposed method did not receive. Conversely, the proposed method was not scored on outputs unavailable to the baselines; all variants were evaluated against the same expected norm references, case references, hazard labels, and citation-grounding rules. This setup favors a conservative interpretation of gains. If the proposed method improves, the improvement should arise from its evidence organization and control mechanisms rather than from privileged data.

### 4.3. Ablation design

The ablation suite isolates mechanism-level contributions within the proposed workflow. It contains 276 runs for each model backend, corresponding to the full proposed control plus five ablations over the same 46 tasks. Each ablation flips one environment switch before invoking the proposed system. The `no_case_evidence` ablation removes accident-case retrieval. The `no_case_norm_linker` ablation keeps accident retrieval but removes the case-to-norm linker. The `no_query_rewrite` ablation uses planner queries without the query-rewriting step. The `no_deterministic_ground` ablation disables deterministic chunk-id grounding. The `no_arbitration` ablation removes typed arbitration and proceeds without the bounded route layer.

This design distinguishes necessary data from mechanism. If removing accident evidence harms performance, cases are useful, but the result does not prove that linking is necessary. If removing the linker while retaining case evidence produces a similar decline, the result indicates that cases alone are insufficient and that the structured link is doing work. Likewise, query rewriting and arbitration are evaluated as supporting mechanisms rather than assumed contributions. This is important because agentic systems often contain many components; ablation prevents a paper from attributing gains to the whole architecture when only one component is responsible.

### 4.4. Metrics

The metrics were chosen to reflect evidence traceability rather than pedagogical effectiveness. Grounding rate measures the proportion of cited chunk identifiers that belong to the evidence package retrieved or linked in the current run. Hallucination rate measures invalid cited chunk identifiers. Norm citation validity measures the proportion of final cited norm references that match task gold references. Norm recall at k measures whether expected norm references were retrieved or linked before generation. Link-resolution rate measures the proportion of regulatory references resolved through case-to-norm links. Hazard coverage measures overlap between expected hazard labels and generated hazard labels. Case relevance measures overlap between cited or retrieved cases and expected case references. Case recall at k measures whether expected accident cases were retrieved. Elapsed time measures end-to-end runtime per task.

Several metrics are intentionally strict. Hazard coverage and case relevance use label overlap, which may undercount semantically correct paraphrases. Norm citation validity is also strict because article-level matches are required. These choices make the benchmark conservative for generated text quality but appropriate for a traceability method paper. A system that produces a fluent paraphrase without a correct article-level reference should not receive the same score as a system that retrieves and cites the expected clause.

The metrics also have different interpretive roles. Norm recall at k evaluates the evidence substrate before final authoring, while norm citation validity evaluates what the model ultimately cites. Grounding rate evaluates provenance, not relevance. Link-resolution rate evaluates whether the cross-document mechanism was actually used. For this reason, the Results section interprets the metrics jointly rather than treating a single score as a complete measure of training quality.

Runtime was recorded because agentic workflows can improve evidence control at the cost of latency. The elapsed-time metric includes retrieval, model calls, linking, checking, and graph orchestration. It is not a pure model-inference benchmark, and it should not be compared directly with low-latency chatbot settings. Its purpose is to determine whether the additional evidence-control steps remain plausible for pre-task training material preparation.

## 5. Results

### 5.1. Overall baseline comparison

Table 1 reports aggregate results over the 46 training tasks for Qwen3.5-9B-Q5_K_M and DeepSeek v4pro. Under both backends, the proposed method was the only variant with perfect grounding, non-zero case-to-norm link resolution, and meaningful article-level norm citation validity. With Qwen3.5-9B-Q5_K_M, it achieved a grounding rate of 1.000, norm citation validity of 0.152, hazard coverage of 0.268, case relevance of 0.328, norm recall at k of 0.674, and link-resolution rate of 0.393. With DeepSeek v4pro, it achieved grounding of 1.000, norm citation validity of 0.146, hazard coverage of 0.324, case relevance of 0.328, norm recall at k of 0.674, and link-resolution rate of 0.390. The optimized RAG baseline achieved non-zero case relevance and higher norm recall than the simpler RAG baselines, but its link-resolution rate remained 0.000 under both backends because it had no mechanism for resolving accident-case references into regulation chunks.

**Table 1. Aggregate baseline results over 46 construction safety training tasks under Qwen3.5-9B-Q5_K_M and DeepSeek v4pro. Higher is better except elapsed time.**

| Variant | Backend | Grounding | Norm validity | Hazard coverage | Case relevance | Norm recall at k | Link resolution | Elapsed (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LLM only | Qwen3.5-9B | 0.000 | 0.000 | 0.033 | 0.000 | 0.000 | 0.000 | 41.3 |
| LLM only | DeepSeek v4pro | 0.000 | 0.000 | 0.036 | 0.000 | 0.000 | 0.000 | 32.2 |
| Norm-only RAG | Qwen3.5-9B | 0.196 | 0.002 | 0.000 | 0.000 | 0.087 | 0.000 | 49.6 |
| Norm-only RAG | DeepSeek v4pro | 0.152 | 0.000 | 0.000 | 0.000 | 0.087 | 0.000 | 9.5 |
| Naive dual RAG | Qwen3.5-9B | 0.774 | 0.000 | 0.000 | 0.268 | 0.087 | 0.000 | 54.6 |
| Naive dual RAG | DeepSeek v4pro | 0.889 | 0.000 | 0.000 | 0.274 | 0.087 | 0.000 | 11.6 |
| Optimized RAG | Qwen3.5-9B | 0.770 | 0.000 | 0.000 | 0.319 | 0.128 | 0.000 | 58.6 |
| Optimized RAG | DeepSeek v4pro | 0.859 | 0.000 | 0.000 | 0.339 | 0.128 | 0.000 | 14.7 |
| Proposed | Qwen3.5-9B | 1.000 | 0.152 | 0.268 | 0.328 | 0.674 | 0.393 | 67.8 |
| Proposed | DeepSeek v4pro | 1.000 | 0.146 | 0.324 | 0.328 | 0.674 | 0.390 | 21.7 |

The most important improvement is norm recall. The proposed method increased norm recall at k from 0.128 for optimized RAG to 0.674 under both Qwen3.5-9B-Q5_K_M and DeepSeek v4pro, a 5.3-fold increase. This improvement occurred even though optimized RAG retrieved accident cases reasonably well. The difference is that optimized RAG relied on similarity retrieval alone to surface regulation articles, whereas the proposed method used retrieved accident cases to pull referenced articles directly into the norm evidence package. Thus, the improvement is best interpreted as evidence-substrate improvement rather than only better wording by a particular generation model.

Grounding results also distinguish the variants. Naive dual RAG and optimized RAG produced lower grounding than the proposed method under both backends, which means that some cited identifiers were not valid under the current evidence package. The proposed method achieved grounding rate 1.000 and hallucination rate 0.000 with both Qwen3.5-9B-Q5_K_M and DeepSeek v4pro because final citations were constrained by deterministic membership. This result does not mean every cited article was the ideal article; the norm citation validity of 0.152 for Qwen and 0.146 for DeepSeek v4pro shows that article selection remains difficult. It does mean that every cited identifier was auditable against the retrieved or linked evidence.

The LLM-only baseline had no retrieval and therefore no grounded citations, no norm recall, and no case relevance. This is expected, but it is still a useful negative control. It shows that model fluency alone is not a substitute for evidence traceability. The norm-only RAG baseline retrieved some relevant articles, but its citation validity remained near zero and it could not use accident cases. The naive dual baseline improved case relevance because it retrieved accident evidence, but it did not improve norm recall over norm-only RAG. This supports the central claim that simply adding accident cases to a prompt is not enough; the cases must be structurally connected to regulations.

### 5.2. Tier and theme analysis

Tier-level results clarify where the proposed method is strongest. On the 33 Tier-S tasks with full article-level gold references, the proposed method achieved norm recall at k of 0.939 under both Qwen3.5-9B-Q5_K_M and DeepSeek v4pro. These values indicate that when accident cases contain resolvable article-level references, the proposed workflow usually retrieves or links the expected norm articles. On the 13 Tier-W tasks, norm recall was 0.000 under both backends because the proxy references do not necessarily correspond to articles explicitly cited in the source case. However, link resolution remained non-zero, indicating that the linker still resolved case-derived regulatory articles even when they did not match the proxy gold labels.

**Table 2. Proposed-method performance by evidence tier under Qwen3.5-9B-Q5_K_M and DeepSeek v4pro.**

| Tier | Backend | n | Grounding | Norm validity | Hazard coverage | Case relevance | Norm recall at k | Link resolution | Elapsed (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Tier-S | Qwen3.5-9B | 33 | 1.000 | 0.211 | 0.318 | 0.326 | 0.939 | 0.414 | 68.8 |
| Tier-S | DeepSeek v4pro | 33 | 1.000 | 0.204 | 0.361 | 0.318 | 0.939 | 0.421 | 21.9 |
| Tier-W | Qwen3.5-9B | 13 | 1.000 | 0.000 | 0.141 | 0.333 | 0.000 | 0.341 | 65.3 |
| Tier-W | DeepSeek v4pro | 13 | 1.000 | 0.000 | 0.231 | 0.353 | 0.000 | 0.312 | 21.0 |

The Tier-S result is the strongest evidence for the case-to-norm mechanism because the gold articles are defined at the same level of granularity as the linker. The Tier-W result is better interpreted as a stress case for incomplete evidence rather than as a failure of retrieval. When accident reports cite only a standard name or when task construction uses proxy articles, exact article-level recall becomes less meaningful. For a deployable system, this distinction matters: the method can only resolve exact links when the source data contain or support exact references. When the source case provides weaker references, the system should report lower confidence or request human review rather than claim article-level certainty.

Theme-level results show similar variation across the two model backends. Work at height achieved the highest norm recall (0.889 under both backends), reflecting mature article-level evidence and repeated references to fall-protection standards. Scaffolding achieved norm recall of 0.636 under both backends and the highest hazard coverage, especially with DeepSeek v4pro. Lifting operations achieved norm recall of 0.692 under both backends, but hazard coverage remained lower, partly because lifting tasks contain diverse causal labels and stricter label matching undercounts semantically related hazards. Temporary electricity had only two tasks, with norm recall 0.000 under both backends, so it should not be overinterpreted.

**Table 3. Proposed-method performance by theme under Qwen3.5-9B-Q5_K_M and DeepSeek v4pro.**

| Theme | Backend | n | Grounding | Norm validity | Hazard coverage | Case relevance | Norm recall at k | Link resolution | Elapsed (s) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Work at height | Qwen3.5-9B | 9 | 1.000 | 0.195 | 0.259 | 0.509 | 0.889 | 0.525 | 67.1 |
| Work at height | DeepSeek v4pro | 9 | 1.000 | 0.169 | 0.296 | 0.509 | 0.889 | 0.486 | 21.2 |
| Scaffolding | Qwen3.5-9B | 22 | 1.000 | 0.162 | 0.424 | 0.273 | 0.636 | 0.326 | 68.1 |
| Scaffolding | DeepSeek v4pro | 22 | 1.000 | 0.149 | 0.504 | 0.273 | 0.636 | 0.313 | 21.4 |
| Lifting operations | Qwen3.5-9B | 13 | 1.000 | 0.127 | 0.051 | 0.269 | 0.692 | 0.447 | 68.2 |
| Lifting operations | DeepSeek v4pro | 13 | 1.000 | 0.148 | 0.051 | 0.269 | 0.692 | 0.476 | 22.8 |
| Temporary electricity | Qwen3.5-9B | 2 | 1.000 | 0.000 | 0.000 | 0.500 | 0.000 | 0.200 | 65.5 |
| Temporary electricity | DeepSeek v4pro | 2 | 1.000 | 0.000 | 0.250 | 0.500 | 0.000 | 0.250 | 20.0 |

These theme results should be read as diagnostic rather than definitive. The benchmark was not constructed as a balanced cross-hazard test set. It reflects the available accident cases and the initial scope of the evidence base. The results nevertheless show an important pattern: the proposed method performs best when accident reports contain explicit, article-level regulatory references and when the regulation corpus contains matching chunks. Weaknesses appear when the case data are sparse, when gold references are proxy-based, or when hazard labels are too strict for the generated wording.

### 5.3. Ablation analysis

The ablation results identify which components account for the improvement. Table 4 reports the full proposed control and five ablations under Qwen3.5-9B-Q5_K_M and DeepSeek v4pro. Removing accident evidence reduced norm recall at k from 0.674 to 0.073 and eliminated link resolution under both backends. Removing only the case-to-norm linker produced the same norm-recall drop and also eliminated link resolution, while case relevance remained non-zero because accident cases were still retrieved. This repeated pattern shows that the cross-document evidence structure, rather than a model-specific phrasing effect, accounts for the main recall gain.

**Table 4. Ablation results over 46 tasks under Qwen3.5-9B-Q5_K_M and DeepSeek v4pro.**

| Variant | Backend | Norm validity | Hazard coverage | Case relevance | Norm recall at k | Link resolution | Elapsed (s) |
|---|---|---:|---:|---:|---:|---:|---:|
| Full proposed | Qwen3.5-9B | 0.143 | 0.286 | 0.317 | 0.674 | 0.365 | 71.7 |
| Full proposed | DeepSeek v4pro | 0.147 | 0.355 | 0.323 | 0.674 | 0.374 | 19.7 |
| No query rewrite | Qwen3.5-9B | 0.150 | 0.281 | 0.333 | 0.674 | 0.380 | 62.8 |
| No query rewrite | DeepSeek v4pro | 0.147 | 0.357 | 0.312 | 0.674 | 0.373 | 20.0 |
| No case evidence | Qwen3.5-9B | 0.027 | 0.073 | 0.000 | 0.073 | 0.000 | 51.0 |
| No case evidence | DeepSeek v4pro | 0.029 | 0.172 | 0.000 | 0.073 | 0.000 | 17.9 |
| No case-to-norm linker | Qwen3.5-9B | 0.028 | 0.136 | 0.339 | 0.073 | 0.000 | 61.6 |
| No case-to-norm linker | DeepSeek v4pro | 0.026 | 0.261 | 0.323 | 0.073 | 0.000 | 19.0 |
| No deterministic grounding | Qwen3.5-9B | 0.147 | 0.163 | 0.328 | 0.674 | 0.386 | 62.3 |
| No deterministic grounding | DeepSeek v4pro | 0.152 | 0.313 | 0.312 | 0.674 | 0.378 | 19.1 |
| No arbitration | Qwen3.5-9B | 0.152 | 0.230 | 0.323 | 0.674 | 0.392 | 62.0 |
| No arbitration | DeepSeek v4pro | 0.148 | 0.323 | 0.317 | 0.674 | 0.383 | 19.8 |

The paired decline in `no_case_evidence` and `no_case_norm_linker` is the cleanest mechanism-level result. Accident evidence is necessary because it supplies case-specific causal information and related-standard references. The linker is also necessary because case evidence alone does not inject the referenced regulation chunks into the norm evidence package. In the `no_case_norm_linker` ablation, case relevance remains comparable to the full system, but norm recall collapses. This isolates the structural contribution of cross-document linking and shows that the result is reproduced with DeepSeek v4pro, not only with the local Qwen backend.

Query rewriting had little aggregate effect. Removing it did not reduce norm recall under either backend and changed link resolution only slightly. This suggests that the risk planner already generated adequate queries for the benchmark tasks. Query rewriting should therefore be framed as a deployment option for underspecified user inputs or retry cases, not as a primary source of the reported gains.

Deterministic grounding produced a more subtle result. The measured grounding rate remained 1.000 even when deterministic grounding was disabled, because the outputs in these runs happened to cite identifiers that were present in the retrieved set. However, the benchmark did not include a strong adversarial hallucination test, so this ablation should not be treated as a complete proof of grounding value. Grounding is best interpreted here as a safety-control mechanism that guarantees provenance membership in the reported output, while adversarial citation-pressure tests remain necessary.

Arbitration also had limited aggregate effect. Removing arbitration did not reduce norm recall or link resolution under either backend, and some metrics were slightly higher. The likely reason is that the benchmark corpus rarely triggered conflict or insufficiency routes. The arbitration layer is therefore not the main driver of average performance in this experiment. Its value lies in providing bounded behavior for harder deployments, especially when evidence is insufficient, retrieved cases conflict with current requirements, or human review is needed.

### 5.4. Expanded 58-task DeepSeek validation

After expanding the case corpus from 76 to 88 cases, the deterministic task set increased from 46 to 58 tasks. The expanded set is not pooled with the 46-task two-backend result because the task distribution changed, especially for temporary electricity. Instead, it is reported as a supplemental validation using DeepSeek v4pro over the expanded task set. The run generated 290 benchmark outputs and 348 ablation outputs, with metadata and metrics archived separately from the 46-task experiments.

Table 5 shows the expanded 58-task benchmark. The proposed method retained perfect grounding and remained the only variant with non-zero link resolution. Norm recall at k decreased from the 46-task DeepSeek value of 0.674 to 0.586, mainly because the added temporary-electricity tasks contain more heterogeneous accident mechanisms and weaker article-level recoverability. The relative pattern nevertheless remained the same: optimized RAG achieved norm recall of 0.106 and zero link resolution, whereas the proposed method achieved norm recall of 0.586 and link resolution of 0.349. Bootstrap analysis over task-level metrics gave a 95% confidence interval of 0.465 to 0.707 for proposed-method norm recall and 0.295 to 0.402 for link resolution. Paired Wilcoxon tests against optimized RAG were significant after Holm correction for norm recall, norm citation validity, and link resolution.

**Table 5. Expanded 58-task DeepSeek v4pro benchmark after accident-corpus growth. Higher is better except elapsed time.**

| Variant | n | Grounding | Norm validity | Hazard coverage | Case relevance | Norm recall at k | Link resolution | Elapsed (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LLM only | 58 | 0.000 | 0.000 | 0.042 | 0.000 | 0.000 | 0.000 | 30.8 |
| Norm-only RAG | 58 | 0.155 | 0.000 | 0.000 | 0.000 | 0.081 | 0.000 | 9.6 |
| Naive dual RAG | 58 | 0.860 | 0.000 | 0.000 | 0.273 | 0.081 | 0.000 | 10.3 |
| Optimized RAG | 58 | 0.921 | 0.000 | 0.000 | 0.364 | 0.106 | 0.000 | 12.0 |
| Proposed | 58 | 1.000 | 0.141 | 0.280 | 0.320 | 0.586 | 0.349 | 21.5 |

The expanded temporary-electricity subset is now large enough to be inspected as a theme-level diagnostic rather than as a two-task anecdote. Across all 17 temporary-electricity tasks, the proposed method achieved grounding of 1.000, norm citation validity of 0.122, hazard coverage of 0.147, case relevance of 0.338, norm recall at k of 0.235, and link resolution of 0.281. On the 13 Tier-S temporary-electricity tasks, the corresponding values were norm citation validity 0.160, hazard coverage 0.167, case relevance 0.308, norm recall at k 0.308, and link resolution 0.314. These scores are lower than work at height and lifting operations, but they provide a more defensible estimate than the original two-task subset and show that temporary-electricity performance is no longer being inferred from a negligible sample.

The expanded ablation suite further confirms that the main gain depends on case-to-norm structure. In the 58-task DeepSeek ablation, the full proposed control reached norm recall at k of 0.586 and link resolution of 0.377. Removing accident evidence reduced norm recall to 0.063 and link resolution to 0.000. Removing only the case-to-norm linker produced the same norm-recall collapse and also eliminated link resolution, while case relevance remained non-zero. Thus, even after adding the temporary-electricity cases, accident retrieval alone was not sufficient; the linker remained the mechanism that converted accident references into regulatory evidence.

**Table 6. Expanded 58-task DeepSeek v4pro ablation results.**

| Variant | n | Norm validity | Hazard coverage | Case relevance | Norm recall at k | Link resolution | Elapsed (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full proposed | 58 | 0.147 | 0.308 | 0.308 | 0.586 | 0.377 | 17.8 |
| No query rewrite | 58 | 0.143 | 0.297 | 0.333 | 0.586 | 0.380 | 17.6 |
| No case evidence | 58 | 0.027 | 0.171 | 0.000 | 0.063 | 0.000 | 15.5 |
| No case-to-norm linker | 58 | 0.028 | 0.154 | 0.329 | 0.063 | 0.000 | 17.3 |
| No deterministic grounding | 58 | 0.141 | 0.272 | 0.308 | 0.586 | 0.352 | 17.6 |
| No arbitration | 58 | 0.142 | 0.305 | 0.312 | 0.586 | 0.348 | 17.6 |

This expanded validation should be interpreted as single-backend evidence rather than a replacement for the original two-backend comparison. An attempted local Qwen run over the expanded task set was not used because the local backend produced repeated `TrainingOutput` truncation errors under the full benchmark configuration. Therefore, the 58-task numbers are reported only for DeepSeek v4pro and are used to strengthen the corpus-growth and temporary-electricity analysis, not to claim a new two-backend average.

### 5.5. Runtime and practical cost

The proposed method was slower than the non-agentic baselines within a given backend, but remained within an interactive range for pre-task material generation. With Qwen3.5-9B-Q5_K_M, the proposed workflow averaged 67.8 s per task, compared with 58.6 s for optimized RAG, 54.6 s for naive dual RAG, 49.6 s for norm-only RAG, and 41.3 s for LLM-only generation. With DeepSeek v4pro, the proposed workflow averaged 21.7 s per task, compared with 14.7 s for optimized RAG, 11.6 s for naive dual RAG, 9.5 s for norm-only RAG, and 32.2 s for LLM-only generation. In the ablation suite, the full proposed control averaged 71.7 s with Qwen3.5-9B and 19.7 s with DeepSeek v4pro. The additional time reflects scenario interpretation, risk planning, dual retrieval, case-to-norm linking, consistency checking, and graph orchestration.

For a toolbox briefing or pre-task training document, this overhead may be acceptable because the output is meant to be auditable and reusable rather than instantaneous. The cost would be less acceptable for rapid question answering at the workface, which is why the methodology includes a lightweight question-answering mode. The runtime results also indicate where optimization should focus. Query rewriting and arbitration contribute latency but limited average gains on this dataset. A deployment could conditionally invoke them only when the initial evidence package is weak, the user query is underspecified, or the checker detects a problem.

The proposed system's runtime should be interpreted in the context of the backend and infrastructure used in each experiment. The Qwen run used a local OpenAI-compatible server and Elasticsearch retrieval, whereas the DeepSeek v4pro run used the hosted DeepSeek API with the same local retrieval store. Absolute latency therefore reflects both model-serving conditions and workflow design. The relative result remains useful: explicit evidence linking adds measurable overhead within a backend, but the major quality gain comes from retrieving and injecting the right regulatory articles before generation.

### 5.6. Failure modes

The remaining weaknesses are informative. First, norm citation validity remains low in absolute terms. Even with norm recall at k of 0.674, final norm citation validity is 0.152 for the Qwen proposed benchmark and 0.146 for the DeepSeek v4pro proposed benchmark. The ablation controls show the same pattern, with values of 0.143 and 0.147, respectively. This gap means that the evidence substrate often contains the right article, but the authoring stage does not always select the expected article for final citation. Future work should improve article selection through evidence ranking, citation-aware decoding, or a separate citation verifier, building on the wider retrieval and self-critique literature [39,40,44,49].

Second, strict hazard-label overlap undercounts some useful outputs. For example, a generated phrase may describe missing fall protection or unsafe access without matching the exact gold label. The current metric is conservative and reproducible, but it does not fully represent semantic adequacy. Expert review or calibrated LLM-as-judge evaluation could complement the strict metric, provided that such evaluation is reported transparently and not substituted for article-level traceability.

Third, the method depends on the quality of case metadata. If accident reports lack related-standard references, or if references are only at the standard level, the linker cannot create exact article-level chains. The Tier-W results show this boundary clearly. Fourth, the expanded temporary-electricity subset remains difficult despite increasing from 2 to 17 tasks; its lower norm recall indicates that electrical accident cases require stronger article-level metadata and citation selection. Fifth, arbitration was not stress-tested on a corpus intentionally designed to contain norm-case conflicts or evidence insufficiency. These limitations define the next evaluation stage rather than invalidating the current method-level evidence.

## 6. Discussion

### 6.1. Why case-to-norm linking is more than dual RAG

The main finding is that explicit cross-document evidence linking outperforms implicit model inference. Naive dual RAG and optimized RAG both provide the model with regulation and accident evidence. They achieve non-zero case relevance, and optimized RAG retrieves expected cases reasonably well. However, their link-resolution rate remains zero because they do not create a structural relationship between retrieved accident cases and regulatory clauses. In these baselines, the model must infer the relationship in natural language. The proposed method resolves the relationship before generation and exposes it as part of the evidence package.

This distinction matters for safety training. In a conventional dual RAG prompt, an accident report and a regulation clause may appear in the same context window because they share a hazard term. The model may then write that the accident demonstrates the importance of that clause. Sometimes this will be correct, but the relationship is not guaranteed. In the proposed workflow, the case-to-norm linker follows article-level references from retrieved accident cases and resolves them against the regulation corpus. The generated material can therefore present an accident warning with a traceable path to the related requirement. This is a stronger evidentiary structure than topical co-retrieval.

The ablation results support this interpretation. Removing the linker while keeping accident retrieval reduced norm recall from 0.674 to 0.073 and link resolution to zero under both Qwen3.5-9B-Q5_K_M and DeepSeek v4pro, even though case relevance remained non-zero. Thus, the improvement cannot be explained by accident evidence alone. The case evidence supplies the reference, but the linker converts that reference into a regulatory chunk available for grounding and authoring. This also explains why optimized RAG did not match the proposed method under either backend: better retrieval over parallel corpora is useful, but it does not replace exact cross-document lookup when the data contain structured references.

### 6.2. Scenario personalization as a deployable unit

The study also argues for scenario-level personalization as a pragmatic alternative to worker-profile personalization. This does not diminish the value of worker-specific training. In many settings, worker experience, role, language, prior incidents, and cognitive state may help tailor instruction. However, a method that requires such data may be difficult to deploy across subcontractors or early-stage digital environments. Scenario-level personalization begins from information that is usually available: the task to be performed and the hazards associated with it.

This unit of personalization aligns with safety management practice. Toolbox meetings and pre-task briefings are commonly organized around planned work. A supervisor may not know every worker's detailed training history, but they know whether the crew will dismantle scaffolding, lift components, enter a temporary electrical area, or work near an unprotected edge. By using the scenario as the retrieval key, the system can generate material that is more specific than a generic safety lecture while avoiding sensitive personal data.

The results show that this approach is technically viable for traceable content generation. Work at height, scaffolding, and lifting operations all achieved non-zero link resolution and substantial norm recall where article-level case references were available. The method therefore provides a path for organizations that want more adaptive training material but do not yet have mature worker-level data infrastructure. Future systems could combine scenario-level retrieval with worker profiles, but the scenario-based evidence chain can stand on its own as a minimum auditable layer.

### 6.3. Grounding and auditability in safety-critical generation

The deterministic chunk-id grounding rule addresses a common weakness of LLM-based safety systems: a model can sound authoritative while citing a source that was not retrieved or does not exist. By requiring cited identifiers to be members of the current evidence package and reconstructing citation text by lookup, the method reduces the space in which unsupported citation claims can occur. This is particularly important for construction safety because generated text may be used to justify protective measures, inspection items, or prohibited actions.

Grounding should not be confused with correctness. A cited chunk can be validly retrieved but still be less relevant than another clause. The proposed method reached perfect grounding but only modest norm citation validity, which shows that provenance control and article selection are different problems. This distinction is useful because it prevents overclaiming. The method ensures that cited evidence is auditable; it does not guarantee that the best possible article was selected in every case. Improving article selection remains a priority.

The broader implication is that safety-critical LLM systems should treat domain evidence as structured objects, not only as text. Construction standards contain article numbers, chapter structures, definitions, tables, and source metadata. Accident reports contain case identifiers, causal fields, and related-standard references. Prior construction informatics work on safety knowledge graphs, NLP-based accident mining, and automated code compliance supports the same general direction [13-17,28,34-38]. A system that preserves these structures can apply deterministic checks before and after generation. This provides a level of auditability that cannot be achieved by prompt wording alone.

### 6.4. Interpreting the absolute scores

The proposed method substantially improved several metrics, but the absolute scores reveal remaining difficulty. Norm recall at k was high for Tier-S tasks, but final norm citation validity remained low under both backends: 0.152 for Qwen3.5-9B-Q5_K_M and 0.146 for DeepSeek v4pro in the proposed benchmark. This suggests that the retrieval and linking layer is ahead of the authoring layer. The right articles are often present, especially in Tier-S tasks, but the generated training material does not always cite the expected subset. In practical terms, the system is better viewed as an evidence-preparation and grounded drafting assistant than as a fully autonomous compliance author.

Hazard coverage and case relevance also require careful interpretation. The metrics use strict overlap with expected labels and case references. This makes them reproducible, but it may undercount acceptable paraphrases and alternative relevant cases. Conversely, a higher overlap score does not automatically mean better pedagogical quality. A generated training document could mention the correct hazard labels but still be unclear or poorly sequenced. Therefore, these automated metrics should be complemented by expert review before making claims about training usefulness or learning outcomes.

The Tier-W and temporary-electricity results show another boundary. When source accident reports do not contain exact article-level references, or when the gold references are proxy-based, exact norm recall becomes less informative. The expanded temporary-electricity validation reduced the sampling problem but did not remove the evidence-quality problem: several electrical tasks still had weak article-level recall or zero link resolution under the full method. The method depends on the available evidence. It can resolve references that exist, and it can retrieve semantically related evidence, but it should not be expected to create authoritative article-level links from weak source metadata without human validation.

### 6.5. Boundary conditions and deployment implications

The method is most suitable for organizations that have or can build a structured safety evidence base. The minimum requirements are stable regulation chunks, accident-case chunks, scenario and hazard tags, and related-standard references where available. If a contractor's accident database lacks source traceability or if standards are not chunked at article level, the method's main advantage will be reduced. Data preparation is therefore part of the engineering contribution, not a peripheral step.

The method is also designed for pre-task material generation rather than immediate emergency guidance. The runtime of approximately one minute per task is reasonable for preparing a briefing, but too slow for situations requiring instant response. The dual-mode design partially addresses this by supporting shorter question answering, but deployment should still distinguish between training preparation, supervisor review, and real-time field use. For high-stakes or ambiguous outputs, human safety professionals should remain in the loop.

Regulatory jurisdiction is another boundary. The present corpus is based on Chinese construction safety standards and Chinese accident reports. The architecture should transfer to other jurisdictions if standards and reports can be chunked and linked, but the actual tags, article formats, legal hierarchy, and accident-report conventions will differ. Cross-jurisdiction evaluation is needed before claiming general regulatory coverage.

Finally, arbitration remains under-tested. The current benchmark rarely triggered norm-case conflict or evidence insufficiency routes, and the same pattern appears under DeepSeek v4pro, so the aggregate results do not demonstrate strong arbitration benefits. This does not mean the layer is unnecessary. It means that the present dataset mainly tests retrieval, linking, and grounding. A future benchmark should include deliberately conflicting or incomplete evidence to evaluate whether typed arbitration improves safety behavior under stress.

### 6.6. Implications for construction automation research

The results contribute to construction automation by showing that LLM reliability can be improved through domain-specific evidence structure. Many construction documents contain latent structure: clause numbers, inspection items, defect categories, work phases, asset identifiers, and cross-references. Treating these structures as first-class data allows automation systems to perform deterministic operations that language models should not be trusted to perform from memory.

For construction safety, the case-to-norm chain is one example of this principle. Similar chains could link inspection defects to corrective actions, near-miss reports to control measures, method statements to checklist items, or BIM elements to regulatory requirements, extending ideas already visible in construction computer vision, safety data analytics, knowledge-graph, and compliance-checking research [29-38]. The broader lesson is that the most useful LLM systems in construction may not be those that generate the most fluent prose, but those that combine generation with explicit provenance, domain constraints, and auditable state transitions.

This perspective also changes how such systems should be evaluated. General answer quality is insufficient. A construction safety generation system should be tested on whether it retrieves the right evidence, cites valid sources, resolves cross-document references, reports insufficiency, and preserves the hierarchy between regulations and experience. The benchmark in this paper is a step in that direction, focusing on traceability and reliability before field effectiveness.

## 7. Conclusions

This paper proposed a scenario-personalized dual-evidence Agentic RAG workflow for traceable construction safety training. The method addresses a specific weakness in conventional RAG workflows for safety applications: retrieving regulations and accident cases in parallel does not guarantee that generated material correctly connects accident mechanisms with the regulatory requirements they illustrate. To address this, the proposed workflow structures regulations and accident reports as a dual-evidence knowledge base, resolves case-to-norm links before generation, constrains final citations through deterministic chunk-id grounding, and uses bounded graph routes for evidence insufficiency, hallucination, and norm-case conflict.

The main evaluation used 46 high-risk construction training tasks, 1,791 regulation chunks, and 152 accident-case chunks. Under Qwen3.5-9B-Q5_K_M, the proposed method achieved a grounding rate of 1.000, norm recall at k of 0.674, link-resolution rate of 0.393, and norm citation validity of 0.152. Under DeepSeek v4pro, the same workflow achieved grounding of 1.000, norm recall at k of 0.674, link-resolution rate of 0.390, and norm citation validity of 0.146. Compared with optimized RAG, norm recall increased from 0.128 to 0.674 under both model backends, while link resolution increased from 0.000 to approximately 0.39. On the 33 Tier-S tasks with full article-level gold references, norm recall reached 0.939 in the original Qwen run. Across the ablation suites, removing either accident evidence or the case-to-norm linker reduced norm recall to 0.073 and eliminated link resolution under both backends. These results show that the main gain comes from the interaction between accident evidence and explicit cross-document linking, not from simply adding more text to the prompt or switching to a different LLM backend.

After corpus growth, the expanded evidence base contained 88 accident cases and 176 accident-case chunks, producing 58 deterministic tasks. A DeepSeek v4pro expanded validation over this task set preserved the same mechanism-level trend: the proposed method achieved grounding of 1.000, norm recall at k of 0.586, norm citation validity of 0.141, and link resolution of 0.349, whereas optimized RAG remained at norm recall of 0.106 and zero link resolution. The 17-task temporary-electricity subset remained harder than the other themes, but it now provides a real theme-level estimate rather than a two-task diagnostic sample.

The study also clarifies the role of deterministic grounding. Grounding did not solve article selection by itself, and the absolute norm citation validity indicates that better citation selection remains necessary. Its value is that generated citations become auditable members of the retrieved or linked evidence package rather than free-form source claims produced from model memory. This makes the output more suitable for expert review, revision, and organizational record keeping. In safety applications, such provenance control is a necessary foundation for more ambitious claims about automated training support.

The contribution is therefore method-level traceability rather than proof of training effectiveness. The automated metrics show that the workflow can retrieve, link, and ground safety evidence more reliably than the tested baselines, and that the main recall/linking trend is reproduced with DeepSeek v4pro as a second model backend. However, they do not show that workers learn more, change behavior, or experience fewer incidents. Expert review and field studies are needed before making such claims. Other limitations include a corpus focused on Chinese standards and accident reports, strict label-overlap metrics, no repeated-run variance estimates, a local Qwen truncation issue on the expanded task set, and limited stress-testing of arbitration.

Within these boundaries, the paper demonstrates a practical design principle for construction safety AI: accident experience and regulatory requirements should be connected as structured evidence before generation, and generated citations should be constrained by deterministic provenance checks. This principle can support auditable pre-task training material, focused safety question answering, and future construction automation systems that need to combine domain documents, causal cases, and compliance requirements without relying on unconstrained model inference. Future work should improve article selection, harden local-model JSON generation for expanded tasks, test additional jurisdictions and repeated-run uncertainty, add conflict-focused benchmarks, and evaluate the usefulness of generated material with safety professionals and field users.

## Declarations

### Data availability

The experiments use local regulation chunks, accident-case chunks, training tasks, and evaluation outputs stored in the project repository under `data/chunks/` and `data/eval/`. Some source accident reports and standards may be subject to source-specific redistribution restrictions. A public release should therefore include derived metadata, task definitions, scripts, and allowable excerpts, while directing readers to original standards and accident-report sources where required.

### Generative AI use

Large language models were used as part of the evaluated system to generate and organize training material. The manuscript draft was prepared with AI assistance and should be checked by the authors for factual accuracy, citation completeness, and compliance with the target journal's author policies before submission.

### Declaration of competing interest

The authors declare no competing interests. This statement should be confirmed by all authors before submission.

### Funding and acknowledgements

Funding information, acknowledgements, author affiliations, and CRediT contribution roles should be completed by the authors before submission.

## References

[1] A. Sabir, R. Hussain, A. Pedro, C. Park, Personalized construction safety training system using conversational AI in virtual reality, Automation in Construction 175 (2025) 106207. https://doi.org/10.1016/j.autcon.2025.106207

[2] I. Jeelani, K. Han, A. Albert, Automating and scaling personalized safety training using eye-tracking data, Automation in Construction 93 (2018) 63-77. https://doi.org/10.1016/j.autcon.2018.05.006

[3] M. Zhang, L. Shu, X. Luo, M. Yuan, X. Zheng, Virtual reality technology in construction safety training: Extended technology acceptance model, Automation in Construction 135 (2022) 104113. https://doi.org/10.1016/j.autcon.2021.104113

[4] D. Choi, S. Seo, H. Park, T. Hong, C. Koo, Forecasting personal learning performance in virtual reality-based construction safety training using biometric responses, Automation in Construction 156 (2023) 105115. https://doi.org/10.1016/j.autcon.2023.105115

[5] Q. L. Bao, S. V. T. Tran, J. Yang, A. Pedro, H. C. Pham, C. Park, Token incentive framework for virtual-reality-based construction safety training, Automation in Construction 158 (2024) 105167. https://doi.org/10.1016/j.autcon.2023.105167

[6] B. E. Ozel, M. K. Pekericli, Construction site hazard recognition via mobile immersive virtual reality and eye tracking, Automation in Construction 173 (2025) 106080. https://doi.org/10.1016/j.autcon.2025.106080

[7] L. Liao, C. Gan, J. Yang, Y. Liang, Impacts of Safety Capacity and Personalized Safety Training on Construction Workers' Hazard Recognition Using Eye-Tracking Technology, Journal of Construction Engineering and Management 151(6) (2025) 04025050. https://doi.org/10.1061/jcemd4.coeng-15765

[8] Q. Xu, H. Y. Chong, P. C. Liao, Exploring eye-tracking searching strategies for construction hazard recognition in a laboratory scene, Safety Science 120 (2019) 824-832. https://doi.org/10.1016/j.ssci.2019.08.012

[9] S. Rokooei, A. Shojaei, A. Alvanchi, R. Azad, N. Didehvar, Virtual reality application for construction safety training, Safety Science 157 (2023) 105925. https://doi.org/10.1016/j.ssci.2022.105925

[10] X. Guo, Y. Liu, Y. Tan, Z. Xia, H. Fu, Hazard identification performance comparison between virtual reality and traditional construction safety training modes for different learning style individuals, Safety Science 180 (2024) 106644. https://doi.org/10.1016/j.ssci.2024.106644

[11] K. Dhalmahapatra, J. Maiti, O. Krishna, Assessment of virtual reality based safety training simulator for electric overhead crane operations, Safety Science 139 (2021) 105241. https://doi.org/10.1016/j.ssci.2021.105241

[12] A. Perlman, R. Sacks, R. Barak, Hazard recognition and risk perception in construction, Safety Science 64 (2014) 22-31. https://doi.org/10.1016/j.ssci.2013.11.019

[13] N. Xu, L. Ma, Q. Liu, L. Wang, Y. Deng, An improved text mining approach to extract safety risk factors from construction accident reports, Safety Science 138 (2021) 105216. https://doi.org/10.1016/j.ssci.2021.105216

[14] F. Zhang, H. Fleyeh, X. Wang, M. Lu, Construction site accident analysis using text mining and natural language processing techniques, Automation in Construction 99 (2019) 238-248. https://doi.org/10.1016/j.autcon.2018.12.016

[15] M. Y. Cheng, D. Kusoemo, R. A. Gosno, Text mining-based construction site accident classification using hybrid supervised machine learning, Automation in Construction 118 (2020) 103265. https://doi.org/10.1016/j.autcon.2020.103265

[16] Z. Ma, Z. S. Chen, Mining construction accident reports via unsupervised NLP and Accimap for systemic risk analysis, Automation in Construction 161 (2024) 105343. https://doi.org/10.1016/j.autcon.2024.105343

[17] Y. M. Goh, C. Ubeynarayana, Construction accident narrative classification: An evaluation of text mining techniques, Accident Analysis & Prevention 108 (2017) 122-130. https://doi.org/10.1016/j.aap.2017.08.026

[18] X. Luo, X. Li, Y. M. Goh, X. Song, Q. Liu, Application of machine learning technology for occupational accident severity prediction in the case of construction collapse accidents, Safety Science 163 (2023) 106138. https://doi.org/10.1016/j.ssci.2023.106138

[19] S. Sarkar, J. Maiti, Machine learning in occupational accident analysis: A review using science mapping approach with citation network analysis, Safety Science 131 (2020) 104900. https://doi.org/10.1016/j.ssci.2020.104900

[20] P. Manu, N. Ankrah, D. Proverbs, S. Suresh, An approach for determining the extent of contribution of construction project features to accident causation, Safety Science 48(6) (2010) 687-692. https://doi.org/10.1016/j.ssci.2010.03.001

[21] P. Katsakiori, G. Sakellaropoulos, E. Manatakis, Towards an evaluation of accident investigation methods in terms of their alignment with accident causation models, Safety Science 47(7) (2009) 1007-1015. https://doi.org/10.1016/j.ssci.2008.11.002

[22] W. Li, L. Zhang, W. Liang, An Accident Causation Analysis and Taxonomy (ACAT) model of complex industrial system from both system safety and control theory perspectives, Safety Science 92 (2017) 94-103. https://doi.org/10.1016/j.ssci.2016.10.001

[23] M. Uhm, J. Kim, S. Ahn, H. Jeong, H. Kim, Effectiveness of retrieval augmented generation-based large language models for generating construction safety information, Automation in Construction 170 (2025) 105926. https://doi.org/10.1016/j.autcon.2024.105926

[24] J. Lee, S. Ahn, D. Kim, D. Kim, Performance comparison of retrieval-augmented generation and fine-tuned large language models for construction safety management knowledge retrieval, Automation in Construction 168 (2024) 105846. https://doi.org/10.1016/j.autcon.2024.105846

[25] C. Wu, W. Ding, Q. Jin, J. Jiang, R. Jiang, Q. Xiao, et al., Retrieval augmented generation-driven information retrieval and question answering in construction management, Advanced Engineering Informatics 65 (2025) 103158. https://doi.org/10.1016/j.aei.2025.103158

[26] S. V. T. Tran, J. Yang, R. Hussain, N. Khan, E. C. Kimito, A. Pedro, et al., Leveraging large language models for enhanced construction safety regulation extraction, Journal of Information Technology in Construction 29 (2024) 1026-1038. https://doi.org/10.36680/j.itcon.2024.045

[27] Q. Chen, X. Yin, B. Yuan, Q. Chen, Personalized safety training for construction workers: A large language model-driven multi-agent framework integrated with knowledge graph reasoning, Computers in Industry 174 (2026) 104399. https://doi.org/10.1016/j.compind.2025.104399

[28] X. Wang, N. El-Gohary, Deep learning-based relation extraction and knowledge graph-based representation of construction safety requirements, Automation in Construction 147 (2023) 104696. https://doi.org/10.1016/j.autcon.2022.104696

[29] Y. Pan, L. Zhang, Roles of artificial intelligence in construction engineering and management: A critical review and future trends, Automation in Construction 122 (2021) 103517. https://doi.org/10.1016/j.autcon.2020.103517

[30] X. Hou, C. Li, Q. Fang, Computer vision-based safety risk computing and visualization on construction sites, Automation in Construction 156 (2023) 105129. https://doi.org/10.1016/j.autcon.2023.105129

[31] W. Fang, L. Ding, P. E. Love, H. Luo, H. Li, F. Pena-Mora, et al., Computer vision applications in construction safety assurance, Automation in Construction 110 (2020) 103013. https://doi.org/10.1016/j.autcon.2019.103013

[32] H. Lee, J. Jeon, D. Lee, C. Park, J. Kim, D. Lee, Game engine-driven synthetic data generation for computer vision-based safety monitoring of construction workers, Automation in Construction 155 (2023) 105060. https://doi.org/10.1016/j.autcon.2023.105060

[33] J. Liu, H. Luo, H. Liu, Deep learning-based data analytics for safety in construction, Automation in Construction 140 (2022) 104302. https://doi.org/10.1016/j.autcon.2022.104302

[34] S. Zhang, F. Boukamp, J. Teizer, Ontology-based semantic modeling of construction safety knowledge: Towards automated safety planning for job hazard analysis (JHA), Automation in Construction 52 (2015) 29-41. https://doi.org/10.1016/j.autcon.2015.02.005

[35] W. Fang, L. Ma, P. E. Love, H. Luo, L. Ding, A. Zhou, Knowledge graph for identifying hazards on construction sites: Integrating computer vision with ontology, Automation in Construction 119 (2020) 103310. https://doi.org/10.1016/j.autcon.2020.103310

[36] X. Xue, J. Zhang, Regulatory information transformation ruleset expansion to support automated building code compliance checking, Automation in Construction 138 (2022) 104230. https://doi.org/10.1016/j.autcon.2022.104230

[37] J. Wu, X. Xue, J. Zhang, Invariant Signature, Logic Reasoning, and Semantic Natural Language Processing (NLP)-Based Automated Building Code Compliance Checking (I-SNACC) Framework, Journal of Information Technology in Construction 28 (2023) 1-18. https://doi.org/10.36680/j.itcon.2023.001

[38] J. Zhang, N. M. El-Gohary, Automated Information Transformation for Automated Regulatory Compliance Checking in Construction, Journal of Computing in Civil Engineering 29(4) (2015) B4015001. https://doi.org/10.1061/(asce)cp.1943-5487.0000427

[39] P. Lewis, E. Perez, A. Piktus, F. Petroni, V. Karpukhin, N. Goyal, et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks, arXiv (2020). https://doi.org/10.48550/arXiv.2005.11401

[40] V. Karpukhin, B. Oguz, S. Min, P. Lewis, L. Wu, S. Edunov, et al., Dense Passage Retrieval for Open-Domain Question Answering, Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP) (2020) 6769-6781. https://doi.org/10.18653/v1/2020.emnlp-main.550

[41] S. Robertson, H. Zaragoza, The Probabilistic Relevance Framework: BM25 and Beyond, Foundations and Trends in Information Retrieval 4(1-2) (2009) 1-174. https://doi.org/10.1561/1500000019

[42] G. V. Cormack, C. L. A. Clarke, S. Buettcher, Reciprocal rank fusion outperforms Condorcet and individual rank learning methods, Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval (2009) 758-759. https://doi.org/10.1145/1571941.1572114

[43] Z. Ji, N. Lee, R. Frieske, T. Yu, D. Su, Y. Xu, et al., Survey of Hallucination in Natural Language Generation, ACM Computing Surveys 55(12) (2023) 1-38. https://doi.org/10.1145/3571730

[44] Y. Gao, Y. Xiong, X. Gao, K. Jia, J. Pan, Y. Bi, et al., Retrieval-Augmented Generation for Large Language Models: A Survey, arXiv (2023). https://doi.org/10.48550/arXiv.2312.10997

[45] W. X. Zhao, K. Zhou, J. Li, T. Tang, X. Wang, Y. Hou, et al., A Survey of Large Language Models, arXiv (2023). https://doi.org/10.48550/arXiv.2303.18223

[46] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, et al., ReAct: Synergizing Reasoning and Acting in Language Models, arXiv (2022). https://doi.org/10.48550/arXiv.2210.03629

[47] J. Wei, X. Wang, D. Schuurmans, M. Bosma, B. Ichter, F. Xia, et al., Chain-of-Thought Prompting Elicits Reasoning in Large Language Models, arXiv (2022). https://doi.org/10.48550/arXiv.2201.11903

[48] T. Schick, J. Dwivedi-Yu, R. Dessi, R. Raileanu, M. Lomeli, L. Zettlemoyer, et al., Toolformer: Language Models Can Teach Themselves to Use Tools, arXiv (2023). https://doi.org/10.48550/arXiv.2302.04761

[49] A. Asai, Z. Wu, Y. Wang, A. Sil, H. Hajishirzi, Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection, arXiv (2023). https://doi.org/10.48550/arXiv.2310.11511

[50] A. Vaswani, N. Shazeer, N. Parmar, J. Uszkoreit, L. Jones, A. N. Gomez, et al., Attention Is All You Need, arXiv (2017). https://doi.org/10.48550/arXiv.1706.03762
