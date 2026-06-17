# 翻译说明（translation_notes）

## 模式
- 全文对照（en→zh），段落级 Original/中文 配对，覆盖 §3 全部 10 个正文块（S001–S010），无跳过。
- 非草稿模式：源文为作者自撰英文 Methods，文本可完整提取，无 OCR/版面不确定性。

## 术语处理
- 保留英文/符号：`chunk_id`、`related_standards`、`linked_from_case`、`RRF`、`BM25`、`Elasticsearch`、`Fig.`、各标准号（如 `JGJ-80-2016:3.0.5`）、集合与公式符号（$\mathcal{C}_R$、$\mathcal{C}_A$、$\mathcal{L}(A)$、$\mathcal{E}$、$\mathcal{G}$ 等）。
- 统一译名：evidence base→证据库；grounding→接地；deliberative→审议式；arbitration→仲裁；dual-modal→双模态；intent-adaptive→意图自适应；orchestration→编排。详见 paper.md 末术语表。
- 三处编号公式（式 1 RRF、式 2 链接算子、式 3 接地过滤）原样保留，中英块内一致。

## 未决/占位
- `[ref]` 引用占位（embedding 模型、RRF、BM25/Elasticsearch、基础 LLM）未翻译为具体文献，需作者以核实文献替换；本件未臆造任何引用。
- 系统名沿用 “the proposed framework / 本文提出的框架”，未起专有简称。
- 图：源文无内嵌图片，仅 Fig. 1/2/4 文内引用；`assets/` 为空；实际图位于 `paper/3 Methodology/figures/`（codex 生成版，命名与编号可能与正文不一致，排版定稿时需对齐）。

## 低置信/可调整项
- “authoring tier”译“撰写层”、“evidence acquisition tier”译“取证层”、“arbitration tier”译“仲裁层”，与项目既有中文叙述一致；如论文统一用其他译名可全局替换。
- 闭环要素中文化（事故→违反条款→培训要求→后果）与英文括注一一对应，便于读者对照。
