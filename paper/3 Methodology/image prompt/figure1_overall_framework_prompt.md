# Figure 1 Prompt: Overall framework

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

Title inside figure: "Scenario-personalized dual-evidence Agentic RAG framework"

Draw the framework as four horizontal bands from top to bottom:

Band 1: "Scenario-personalized input"
Place two boxes:
1. "High-risk work topic / scenario"
2. "Hazards and training objective"
Use dark blue.

Band 2: "Dual-evidence substrate"
Place two large parallel boxes:
Left green box: "Regulation evidence base"
Inside it, small labels: "article-level chunks", "scenario tags", "hazard tags", "stable chunk_id".
Right orange box: "Accident-case evidence base"
Inside it, small labels: "case process", "causes", "consequences", "related_standards".
Between them, add a purple bridge label: "case-to-norm bridge".

Band 3: "Evidence linking and retrieval"
Place five connected modules from left to right:
"Risk planner" -> "Query rewriter" -> two parallel paths:
green path: "Norm retriever"
orange path: "Case retriever"
then both flow into purple module: "Case-to-norm linker".
The output of this band is a box: "Linked dual-evidence package".

Band 4: "Grounded generation and outputs"
Place three connected modules:
"Evidence-grounded authoring" -> "Consistency checker" -> "Arbitration"
Then split into two output boxes:
1. "Pre-task training material"
2. "In-situ safety Q&A"
Add a small gray box under outputs: "Citations and diagnostics".

Use arrows to show left-to-right flow within each band and vertical flow between bands.
Highlight the purple arrow from accident-case evidence to case-to-norm linker and then to linked dual-evidence package.
Do not include code names, LangGraph, UI, mobile application, or knowledge graph.
Keep all text short and readable.
```

Suggested filename after export:

```text
paper/3 Methodology/figures/fig3-1-system-architecture.png
```
