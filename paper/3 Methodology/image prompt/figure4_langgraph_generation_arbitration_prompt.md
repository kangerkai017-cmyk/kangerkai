# Figure 4 Prompt: LangGraph-based grounded deliberative generation and arbitration

Use this prompt in GPT image2. Generate a clean academic vector-style diagram for an English journal article. After generation, check all text manually and redraw in PowerPoint, Figma, Illustrator, or BioRender if any labels are distorted.

General style:

- White background.
- Academic journal style, suitable for Automation in Construction or Computers in Industry.
- Clean vector diagram, not photorealistic.
- Use consistent colors:
  - dark blue for scenario/input and control modules;
  - green for regulation/norm evidence;
  - orange for accident-case evidence;
  - purple for case-to-norm linking;
  - gray for diagnostics and metadata.
- Use thin lines, rounded rectangles with small radius, and clear arrows.
- Use readable English labels.
- Avoid decorative icons, 3D effects, gradients, shadows, and dense text.
- Leave enough whitespace for later editing.
- Make the diagram landscape, 16:9 aspect ratio.

```text
Create a clean academic vector diagram, landscape 16:9, white background, for a journal paper methodology figure.

Title inside figure: "State-transition control for grounded deliberative generation"

Draw the figure as a LangGraph-style state-transition diagram, not as a module pipeline.
The purpose is to show how `TrainingState` changes and how arbitration routes the graph.
Do not repeat the detailed acquisition-authoring workflow already shown in Fig. 1c.

Place a large central gray object labeled:
"Shared TrainingState"
Divide it into three compact field groups:
1. "Input and scenario fields"
   "topic"
   "training_scenario"
   "hazards_identified"
   "norm_queries / case_queries"
2. "Evidence and draft fields"
   "norm_evidence_ids"
   "case_evidence_ids"
   "linked_norm_evidence_ids"
   "draft_training_output"
3. "Control fields"
   "consistency_issues"
   "retry_reason"
   "retry_count"
   "dialogue_budget"
   "arbitration_decision"
   "requires_human_review"

Around the central state object, draw graph nodes as small rounded rectangles:
"scenario_agent"
"evidence_subgraph"
"authoring_subgraph"
"arbitration_subgraph"
"training_agent"
"END"

Use solid dark-blue arrows for the normal forward transition:
"scenario_agent" -> "evidence_subgraph" -> "authoring_subgraph" -> "arbitration_subgraph" -> "training_agent" -> "END"

Use dashed conditional arrows from "arbitration_subgraph":
1. Red dashed loop:
"hallucination"
-> "authoring_subgraph"
Label: "re-ground same evidence"
2. Orange dashed loop:
"evidence_insufficient"
-> "evidence_subgraph"
Label: "targeted retrieval if dialogue_budget > 0"
3. Purple terminal route:
"norm_case_conflict"
-> "training_agent"
Label: "norm-over-case + human-review flag"
4. Green terminal route:
"passed"
-> "training_agent"
Label: "release"

Show boundedness explicitly:
Place two gray guard boxes near the dashed loops:
"MAX_RETRIES"
"dialogue_budget"
Connect them to the red and orange dashed routes with thin gray lines.
Add a small note:
"only hallucination and evidence insufficiency form loops"

Show state updates with thin gray arrows from graph nodes to "Shared TrainingState":
"scenario_agent writes scenario"
"evidence_subgraph writes evidence IDs"
"authoring_subgraph writes draft and consistency issues"
"arbitration_subgraph writes decision and route"
"training_agent writes final output"

On the right side, add a small diagnostics strip:
"Logged diagnostics"
"LLM calls"
"retrieval calls"
"node steps"
"retry trace"

Keep the diagram sparse and more abstract than Fig. 1.
Avoid drawing internal modules such as risk planning, query rewriting, norm retrieval, case retrieval, evidence fusion, or consistency-checker internals.
Do not include evidence base construction in this figure.
Do not include mobile app, UI, knowledge graph, or worker profile.
Use a clean academic style with readable English labels, consistent colors, and enough whitespace.
```

Suggested filename after export:

```text
paper/3 Methodology/figures/fig3-4-grounded-generation-arbitration.png
```
