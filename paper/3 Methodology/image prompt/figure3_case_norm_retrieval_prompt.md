# Figure 3 Prompt: Case-to-norm linking and dual-path retrieval

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

Title inside figure: "Case-to-norm linking and dual-path retrieval"

This is the core mechanism figure. Make the case-to-norm link visually prominent.

Layout:
Start on the left with a dark blue input box:
"Input scenario"

Then connect to:
"Scenario interpretation"
-> "Risk planner"
-> "Query rewriter"

After "Query rewriter", split into two parallel retrieval paths:

Upper green path:
"Norm-oriented queries"
-> "Hybrid norm retrieval"
Inside or below this module, small labels: "BM25", "dense vector", "tags", "RRF"
-> "Retrieved norm chunks"

Lower orange path:
"Case-oriented queries"
-> "Hybrid case retrieval"
Inside or below this module, small labels: "BM25", "dense vector", "tags", "RRF"
-> "Retrieved accident chunks"

From "Retrieved accident chunks", draw a thick purple arrow to:
"related_standards"
-> "Exact norm lookup"
Add small label under exact lookup:
"standard_code : article_id"
-> "Linked norm chunks"

Merge "Retrieved norm chunks", "Retrieved accident chunks", and "Linked norm chunks" into a large box on the right:
"Linked dual-evidence package"
Inside it, show:
"norm evidence"
"case evidence"
"linked norm evidence"
"evidence IDs"
"retrieval diagnostics"

At the bottom, add a purple callout strip labeled:
"Closed evidence chain"
with the sequence:
"accident case -> related clause -> safety requirement -> consequence warning"

Add small gray evaluation labels near the final package:
"link resolution rate"
"linked norm coverage"
"citation validity"

Use green for norm path, orange for case path, purple for deterministic case-to-norm lookup, dark blue for planning modules, gray for evaluation labels.
Clearly distinguish similarity retrieval from exact lookup.
Do not include generation or arbitration in this figure.
Keep all text short, readable, and aligned.
```

Suggested filename after export:

```text
paper/3 Methodology/figures/fig3-3-case-norm-retrieval.png
```
