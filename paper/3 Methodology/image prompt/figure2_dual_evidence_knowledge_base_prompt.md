# Figure 2 Prompt: Scenario-oriented dual-evidence knowledge base

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

Title inside figure: "Scenario-oriented dual-evidence knowledge base"

Use a two-column layout.

Left column title, green: "Regulation evidence"
Show a top-to-bottom pipeline:
"Safety standards"
-> "OCR / text cleaning"
-> "Article-level segmentation"
-> "Norm chunk schema"
-> "Regulation evidence base"

Inside or beside "Norm chunk schema", show compact field labels:
"chunk_id"
"standard_code"
"article_id"
"text"
"requirement_type"

Right column title, orange: "Accident-case evidence"
Show a top-to-bottom pipeline:
"Accident reports"
-> "Case structuring"
-> "Summary and cause chunks"
-> "Case chunk schema"
-> "Accident-case evidence base"

Inside or beside "Case chunk schema", show compact field labels:
"case_id"
"accident_type"
"process"
"causes"
"consequences"
"related_standards"

At the bottom, draw a shared gray metadata layer spanning both columns:
"Shared metadata and indexes"
Inside it, include:
"scenario_tags"
"hazard_tags"
"source metadata"
"stable identifiers"
"lexical index"
"vector embeddings"

Draw arrows from both evidence bases into the shared metadata and indexes layer.
Add a small purple arrow from "related_standards" in the case schema pointing toward a label: "used for case-to-norm linking in Fig. 3".

Do not include generation, arbitration, LLM, or final output in this figure.
Keep the figure focused on evidence construction and representation.
Use readable English labels and enough whitespace.
```

Suggested filename after export:

```text
paper/3 Methodology/figures/fig3-2-dual-evidence-knowledge-base.png
```
