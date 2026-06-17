# 方法（Methodology）· 中英文对照阅读件

**Source file:** `paper/3 Methodology/Methodology.md`（作者自撰英文 Methods 章）
**Type:** methods/algorithm section（自有正文，非出版商 PDF）
**Mode:** 段落级中英对照；公式、章节编号、术语、图引用均保留
**Note:** 源文件无内嵌图片，仅含 Fig. 1–4 文内引用；图见 `paper/3 Methodology/figures/`，本件不伪造图裁剪。

## 章节索引

- §3 方法（总览）— S001
- §3.1 施工安全规范证据库 — S002–S003（含式 1）
- §3.2 事故案例证据库与案例—规范链接 — S004–S005（含式 2）
- §3.3 三层审议式生成 — S006；§3.3.1 取证层 — S007；§3.3.2 撰写层与确定性 chunk_id 接地 — S008（含式 3）；§3.3.3 仲裁层与有界受控通信 — S009
- §3.4 双模态意图自适应编排 — S010

---

# 3. Methodology ｜ 方法

<a id="S001"></a>
**Source:** §3 intro · S001

**Original:** The proposed framework is a dual-evidence, consistency-constrained agentic Retrieval-Augmented Generation (RAG) method for pre-job construction-safety training. Rather than treating retrieval as a one-shot prelude to generation, it organizes the task as a grounded, auditable pipeline in which every externally presented claim is traceable to a retrieved source. The overall framework is shown in Fig. 1 and comprises four components: (i) a construction-safety **regulation evidence base** that supplies normative requirements (what must be done); (ii) an **accident-case evidence base** that supplies cautionary evidence (why it must be done), together with a *case-to-regulation cross-document link* that binds the two; (iii) a **three-tier deliberative generation** process (evidence acquisition, authoring, and arbitration) that prevents the language model from breaking the evidence chain during generation; and (iv) a **dual-modal intent-adaptive orchestration** layer that serves both proactive training-material generation and reactive safety question answering over the same grounded substrate. The following subsections describe each component in turn.

**中文:** 本文提出的框架是一种面向施工作业前安全培训的、双证据一致性约束的智能体检索增强生成（RAG）方法。它不将检索视为生成前的一次性前置步骤，而是把任务组织为一条可接地、可审计的流水线，使对外呈现的每一条主张都可追溯到检索到的来源。总体框架如图 1 所示，由四个部分构成：(i) 提供规范性要求（应该怎么做）的施工安全**规范证据库**；(ii) 提供警示性证据（为什么必须这样做）的**事故案例证据库**，以及将二者绑定的*案例—规范跨文档链接*；(iii) 在生成阶段防止语言模型破坏证据链的**三层审议式生成**过程（取证、撰写、仲裁）；(iv) 在同一接地基座之上同时服务于主动式培训材料生成与响应式安全问答的**双模态意图自适应编排**层。以下各小节依次介绍各部分。

---

## 3.1. Construction-safety regulation evidence base ｜ 施工安全规范证据库

<a id="S002"></a>
**Source:** §3.1 · S002

**Original:** The regulation evidence base provides the normative backbone of the framework. Construction-safety standards are first acquired in document form and, where their text layer is unreliable, converted to plain text through optical character recognition before processing. Each standard is then segmented at the **article level**, so that a chunk corresponds to a single normative clause rather than an arbitrary text window; this preserves the regulatory unit at which compliance is later asserted. Every chunk $c_i$ is assigned a globally unique identifier $\mathrm{chunk\_id}$ that encodes its provenance as $\langle \mathrm{standard\_code} : \mathrm{article\_id}\rangle$ (e.g., `JGJ-80-2016:3.0.5`); this identifier is the anchor on which all later grounding and cross-document linking depend.

**中文:** 规范证据库为框架提供规范性骨架。施工安全标准首先以文档形式获取；当其文本层不可靠时，先经光学字符识别（OCR）转为纯文本再行处理。随后将每部标准按**条文级**切分，使一个 chunk 对应单一规范条款，而非任意文本窗口；这保留了后续断言合规性所依据的规范单元。每个 chunk $c_i$ 被赋予一个全局唯一标识 $\mathrm{chunk\_id}$，以 $\langle \mathrm{standard\_code} : \mathrm{article\_id}\rangle$ 的形式编码其来源（例如 `JGJ-80-2016:3.0.5`）；该标识是后续一切接地与跨文档链接所依赖的锚点。

<a id="S003"></a>
**Source:** §3.1 · S003（含式 1）

**Original:** On this basis, each chunk is encoded into a dense vector with a pre-trained Chinese text-representation model [embedding model, ref] and simultaneously indexed for lexical search, yielding a regulation corpus $\mathcal{C}_R = \{c_1, c_2, \ldots, c_n\}$ stored in a single retrieval back-end. To accommodate both terminological precision (standard numbers, technical terms) and semantic paraphrase, retrieval is performed as a hybrid of three channels—lexical (BM25), dense-vector, and tag-based—whose ranked lists are combined by Reciprocal Rank Fusion (RRF) [RRF, ref]. For a chunk $c$ retrieved by channel set $R$, its fused score is

$$\mathrm{RRF}(c) = \sum_{r \in R} \frac{1}{k + \mathrm{rank}_r(c)}, \tag{1}$$

where $\mathrm{rank}_r(c)$ is the rank of $c$ in channel $r$ and $k$ is a smoothing constant. The fused ranking provides high-quality normative evidence for subsequent stages while remaining agnostic to which single channel surfaced a given clause.

**中文:** 在此基础上，每个 chunk 通过预训练中文文本表示模型 [embedding model, ref] 编码为稠密向量，并同时建立词法检索索引，得到存储于单一检索后端的规范语料库 $\mathcal{C}_R = \{c_1, c_2, \ldots, c_n\}$。为兼顾术语精确性（标准号、技术术语）与语义改写，检索采用词法（BM25）、稠密向量与标签三路混合，并以倒数排名融合（RRF）[RRF, ref] 合并各路排序列表。对由通道集合 $R$ 检索到的 chunk $c$，其融合得分为：

$$\mathrm{RRF}(c) = \sum_{r \in R} \frac{1}{k + \mathrm{rank}_r(c)}, \tag{1}$$

其中 $\mathrm{rank}_r(c)$ 为 $c$ 在通道 $r$ 中的排名，$k$ 为平滑常数。该融合排序为后续阶段提供高质量的规范证据，同时不依赖于究竟由哪一路单独通道召回某一条款。

---

## 3.2. Accident-case evidence base and case-to-regulation linking ｜ 事故案例证据库与案例—规范链接

<a id="S004"></a>
**Source:** §3.2 · S004

**Original:** Accident cases are critical to safety training because they convey the consequences of non-compliance, yet their value is realized only when each case can be connected to the specific clause it violated. To this end, accident-investigation reports are structured into a uniform schema—incident description, direct and indirect causes, casualties and losses, and *violated standards*—and each case is parsed for its `related_standards`, a set of article-level references to the regulation corpus (e.g., `JGJ-276-2012:3.0.23`). Each structured case yields one or more chunks that are embedded and indexed alongside the regulation corpus, forming the case corpus $\mathcal{C}_A$ on the same retrieval substrate as $\mathcal{C}_R$.

**中文:** 事故案例对安全培训至关重要，因为它们传达了不合规的后果；然而，只有当每起案例都能与其所违反的具体条款相连接时，其价值才能实现。为此，事故调查报告被结构化为统一模式——事故描述、直接与间接原因、伤亡与损失、以及*违反规范*——并从每起案例中解析出其 `related_standards`，即指向规范语料库的条文级引用集合（例如 `JGJ-276-2012:3.0.23`）。每起结构化案例产生一个或多个 chunk，与规范语料库一同嵌入并索引，构成与 $\mathcal{C}_R$ 处于同一检索基座上的案例语料库 $\mathcal{C}_A$。

<a id="S005"></a>
**Source:** §3.2 · S005（含式 2）

**Original:** The central mechanism of this subsection is the **case-to-regulation cross-document link**, illustrated in Fig. 2. Conventional RAG retrieves regulation and case evidence in parallel and never joins them, leaving the relation "which clause did this accident violate" to be inferred by the language model at generation time. In contrast, the proposed link makes this relation a deterministic retrieval-time fact. Given a set of retrieved cases $A \subseteq \mathcal{C}_A$, the system collects their references $\mathcal{R} = \bigcup_{a \in A} \mathrm{related\_standards}(a)$, resolves each reference by exact match on $\langle \mathrm{standard\_code}, \mathrm{article\_id}\rangle$, and retrieves the corresponding regulation chunks:

$$\mathcal{L}(A) = \{\, c \in \mathcal{C}_R \mid \langle \mathrm{standard\_code}(c), \mathrm{article\_id}(c)\rangle \in \mathcal{R} \,\}. \tag{2}$$

The linked chunks $\mathcal{L}(A)$ are merged into the regulation evidence with a `linked_from_case` provenance tag, so that the framework can distinguish evidence obtained by similarity recall from evidence obtained by causal linkage. As a result, each retrieved accident is accompanied by the precise clauses it violated, and the generated material can present a closed evidence chain—*accident (what happened) → violated clause (which rule) → training requirement (what to do) → consequence (why it matters)*—rather than two unconnected pools of text.

**中文:** 本小节的核心机制是**案例—规范跨文档链接**，如图 2 所示。传统 RAG 并行检索规范与案例证据却从不将二者连接，把"某起事故违反了哪条条款"这一关系留给语言模型在生成时推断。与之相反，所提出的链接使该关系成为检索时的确定性事实。给定检索到的案例集合 $A \subseteq \mathcal{C}_A$，系统汇集其引用 $\mathcal{R} = \bigcup_{a \in A} \mathrm{related\_standards}(a)$，按 $\langle \mathrm{standard\_code}, \mathrm{article\_id}\rangle$ 精确匹配解析每条引用，并检索对应的规范 chunk：

$$\mathcal{L}(A) = \{\, c \in \mathcal{C}_R \mid \langle \mathrm{standard\_code}(c), \mathrm{article\_id}(c)\rangle \in \mathcal{R} \,\}. \tag{2}$$

链接得到的 chunk $\mathcal{L}(A)$ 以 `linked_from_case` 来源标记并入规范证据，使框架能够区分由相似度召回得到的证据与由因果链接得到的证据。由此，每起检索到的事故都伴随其所违反的精确条款，生成的材料得以呈现一条闭合的证据链——*事故（发生了什么）→ 违反的条款（违反了哪条规则）→ 培训要求（该怎么做）→ 后果（为什么重要）*——而非两堆互不关联的文本。

---

## 3.3. Three-tier deliberative generation ｜ 三层审议式生成

<a id="S006"></a>
**Source:** §3.3 intro · S006

**Original:** Constructing the evidence chain at retrieval time is necessary but not sufficient: if the chain is then handed to a single unconstrained generation call, the language model may ignore the linked clauses, fabricate provisions when evidence is thin, or produce statements inconsistent with the retrieved sources. To prevent this, training-material generation is organized as three cooperating tiers—evidence acquisition, authoring, and arbitration—shown in Fig. 4. The design principle is that decisions affecting the integrity of the evidence chain are removed from free generation and delegated to reproducible, deterministic mechanisms, leaving the language model responsible only for organizing language.

**中文:** 在检索时构建证据链是必要的，但并不充分：若随后把证据链交给单次无约束的生成调用，语言模型可能忽略链接到的条款、在证据稀薄时编造条文，或产生与检索来源不一致的陈述。为防止这一点，培训材料生成被组织为三个协作的层——取证、撰写、仲裁——如图 4 所示。其设计原则是：将影响证据链完整性的决策从自由生成中剥离，交由可复现的确定性机制承担，使语言模型只负责组织语言。

### 3.3.1. Evidence acquisition tier ｜ 取证层

<a id="S007"></a>
**Source:** §3.3.1 · S007

**Original:** The evidence acquisition tier assembles the grounded evidence for one round. Given a high-risk work topic, the agent proceeds in three steps: in the first step it generates a training scenario and identifies the hazards the scenario should cover; in the second step it decomposes the task into regulation-oriented and case-oriented queries and reformulates them through path-specialized query rewriting and terminology expansion; in the third step the two corpora are retrieved in parallel and the case-to-regulation link of Eq. (2) is applied. The tier exposes a single artifact—the linked, dual-evidence set—as the sole evidence source for all downstream generation.

**中文:** 取证层为单轮组装接地证据。给定一个高危作业主题，智能体分三步进行：第一步生成培训情境并识别该情境应覆盖的危险源；第二步将任务分解为面向规范与面向案例的查询，并通过路径特化的查询改写与术语扩展加以重构；第三步并行检索两个语料库，并应用式 (2) 的案例—规范链接。该层对外暴露单一产物——已链接的双证据集合——作为后续所有生成的唯一证据来源。

### 3.3.2. Authoring tier and deterministic chunk_id grounding ｜ 撰写层与确定性 chunk_id 接地

<a id="S008"></a>
**Source:** §3.3.2 · S008（含式 3）

**Original:** The authoring tier turns evidence into an audited draft. Evidence fusion first organizes the scenario, hazards, normative requirements, and cautionary cases into a draft training material. Crucially, the language model is not asked to reproduce the text of any citation; instead it selects citations by emitting only their identifiers, and the system back-fills the cited content verbatim from the retrieval set. Formally, let $\mathcal{E}$ be the set of $\mathrm{chunk\_id}$s actually retrieved in the current round and $S$ the set selected by the agent; the grounded citation set is

$$\mathcal{G} = \{\, s \in S \mid s \in \mathcal{E} \,\}, \tag{3}$$

and any selected identifier $s \notin \mathcal{E}$—a hallucinated reference—is discarded. A consistency audit then pairs a semantic review by the language model (whether a citation is exaggerated, whether a case description matches the retrieved source, whether a regulation and a case conflict) with this deterministic grounding check. When the two disagree, grounding is authoritative: an unsupported "hallucination" flag that the grounding check cannot confirm is dropped, which eliminates spurious regeneration, whereas genuine conflicts and evidence gaps are passed to the arbitration tier. Because Eq. (3) depends only on set membership and not on the generation task, the same anti-hallucination guarantee holds wherever it is applied.

**中文:** 撰写层将证据转化为经审计的草稿。证据融合首先将情境、危险源、规范性要求与警示性案例组织为培训材料草稿。关键在于，语言模型并不被要求复述任何引用的正文；它只通过输出标识来选择引用，再由系统从检索集合中逐字回填被引内容。形式化地，设 $\mathcal{E}$ 为本轮实际检索到的 $\mathrm{chunk\_id}$ 集合、$S$ 为智能体所选集合，则接地后的引用集合为：

$$\mathcal{G} = \{\, s \in S \mid s \in \mathcal{E} \,\}, \tag{3}$$

任何被选中却 $s \notin \mathcal{E}$ 的标识——即幻觉引用——都被丢弃。随后的一致性审计将语言模型的语义审查（引用是否被夸大、案例描述是否与检索来源一致、规范与案例是否冲突）与这一确定性接地校验配对。当二者不一致时，以接地为权威：接地校验无法证实的"幻觉"标记被丢弃，从而消除无意义的重新生成；而真正的冲突与证据缺口则交由仲裁层处理。由于式 (3) 只依赖集合成员关系，而与具体生成任务无关，同一反幻觉保证在其被应用的任何场合都成立。

### 3.3.3. Arbitration tier and bounded controlled communication ｜ 仲裁层与有界受控通信

<a id="S009"></a>
**Source:** §3.3.3 · S009

**Original:** The arbitration tier deliberates over the audit outcome and decides the next action, replacing the ad-hoc "re-fuse and retry" heuristic of conventional pipelines with a principled, type-specific policy. A **regulation–case conflict** is resolved by a deterministic *regulation-over-case* rule: the normative requirement prevails, the conflicting case experience is demoted to a supplementary warning with its provenance retained, and the case is flagged for human review; the rationale is templated and therefore reproducible and testable. **Insufficient evidence** triggers a structured re-retrieval request that returns control to the evidence tier for one targeted round, realizing a controlled bidirectional communication rather than forcing the model to generate from inadequate evidence. A **hallucination** verdict returns the draft to the authoring tier for re-grounding without further retrieval, because the fault lies in generation rather than in evidence. To guarantee termination, every loop is bounded by two budgets—a maximum number of authoring retries and a dialogue budget on evidence re-negotiation—so that the pipeline always converges to a final material. In this way, each manner in which the evidence chain could be broken during generation is intercepted and corrected by a corresponding, auditable branch.

**中文:** 仲裁层就审计结果进行审议并决定下一步动作，以一套有原则、按类型区分的策略取代传统流水线中临时性的"重新融合并重试"启发式。**规范—案例冲突**由确定性的*规范优先于案例*规则裁决：规范性要求为准，与之冲突的案例经验被降级为补充警示并保留其来源，同时该案例被标记为需人工复核；裁决理由为模板化，因而可复现、可测试。**证据不足**触发一个结构化的再检索请求，将控制权交回取证层进行一轮定向检索，实现受控的双向通信，而非迫使模型在证据不足时生成。**幻觉**判定将草稿退回撰写层重新接地而不再检索，因为问题出在生成而非证据。为保证终止性，每个回环都受两个预算约束——撰写重试次数上限与证据再协商的对话预算——使流水线总能收敛到最终材料。如此，证据链在生成阶段可能被破坏的每一种方式，都由一个对应的、可审计的分支加以拦截与纠正。

---

## 3.4. Dual-modal intent-adaptive orchestration ｜ 双模态意图自适应编排

<a id="S010"></a>
**Source:** §3.4 · S010

**Original:** The mechanisms above depend only on the retrieval set and the $\mathrm{chunk\_id}$ anchor, and are therefore independent of the particular product being generated. To exploit this generality, a top-level intent classifier routes each user input to one of two pipelines over the same grounded substrate, as shown in Fig. 1. The **training modality** (proactive) accepts a high-risk work topic and produces a complete pre-job training material through the full three-tier deliberation of Section 3.3. The **question-answering modality** (reactive) accepts a free-text query and produces a concise answer through a lightweight linear path—query planning, parallel regulation/case retrieval, cross-document linking, and answer generation—without an arbitration loop; when evidence is insufficient it answers with an explicit low-confidence note and an evidence gap rather than re-retrieving or fabricating. Both modalities share the identical retrieval, linking, and deterministic grounding substrate, so the anti-hallucination guarantee of Eq. (3) holds across modalities. This arrangement also realizes intent-adaptive computation: orchestration complexity scales with task risk, with the high-stakes, fully traceable training material invoking the complete deliberation and the latency-sensitive query answering taking the lightweight path. The intent classifier uses the language model with a deterministic keyword heuristic as fallback, ensuring robust routing even when model-based classification fails.

**中文:** 上述机制只依赖检索集合与 $\mathrm{chunk\_id}$ 锚点，因而与所生成的具体产物无关。为利用这一普适性，一个顶层意图分类器将每个用户输入路由到同一接地基座之上的两条流水线之一，如图 1 所示。**培训模态**（主动式）接受高危作业主题，通过第 3.3 节完整的三层审议产出一份完整的作业前培训材料。**问答模态**（响应式）接受自由文本查询，通过一条轻量线性路径——查询规划、规范/案例并行检索、跨文档链接与答案生成——产出简洁回答，且不含仲裁回环；当证据不足时，它以明确的低置信标注与证据缺口作答，而非再检索或编造。两种模态共享完全相同的检索、链接与确定性接地基座，因此式 (3) 的反幻觉保证跨模态成立。该安排同时实现了意图自适应算力分配：编排复杂度随任务风险伸缩——高风险、需全面可追溯的培训材料调用完整审议，而对时延敏感的问答走轻量路径。意图分类器以语言模型为主、以确定性关键词启发式为兜底，确保即使模型分类失败仍能稳健路由。

---

## 术语对照表（Terminology）

| English | 中文 | 说明 |
| --- | --- | --- |
| chunk / chunk_id | chunk / chunk_id（块标识） | 保留英文，标识形如 `standard_code:article_id` |
| regulation evidence base | 规范证据库 | 规范条文一侧 |
| accident-case evidence base | 事故案例证据库 | 事故案例一侧 |
| case-to-regulation (case→norm) cross-document link | 案例—规范跨文档链接 | 论文核心机制 |
| `related_standards` | 违反/相关规范引用 | 案例字段，保留英文键名 |
| `linked_from_case` | 案例链接来源标记 | 来源标记，保留英文键名 |
| deterministic chunk_id grounding | 确定性 chunk_id 接地 | 反幻觉机制 |
| three-tier deliberative generation | 三层审议式生成 | 取证 / 撰写 / 仲裁 |
| evidence acquisition / authoring / arbitration tier | 取证层 / 撰写层 / 仲裁层 | 三层 |
| regulation-over-case | 规范优先于案例 | 冲突裁决规则 |
| dialogue budget | 对话预算 | 再检索回合上限 |
| dual-modal intent-adaptive orchestration | 双模态意图自适应编排 | 顶层路由 |
| RRF (Reciprocal Rank Fusion) | 倒数排名融合 | 保留英文缩写 RRF |
| BM25 | BM25 | 保留英文 |

## 阅读提示（Reading notes）

- 全章为单一因果主线：普通 RAG 证据断链（S001、S005、S006）→ 在检索层补链（S004–S005）→ 接地与三层审议护链（S008–S009）→ 同一机制跨模态复用（S010）。
- 三个编号公式：式 (1) RRF 融合、式 (2) 案例—规范链接算子、式 (3) chunk_id 接地过滤，对应方法的形式化骨架。
- 图引用：Fig. 1（总体架构）、Fig. 2（案例—规范链）、Fig. 4（三层编排）见 `paper/3 Methodology/figures/`；源文未内嵌图片。
- `[ref]` 为引用占位（embedding 模型、RRF、BM25/Elasticsearch、基础 LLM），需以核实文献替换。
