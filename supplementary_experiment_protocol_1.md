# 补充实验协议 (Supplementary Experiment Protocol)

**论文**：Scenario-personalized dual-evidence Agentic RAG for traceable construction safety training
**目标期刊**：Automation in Construction（一区 top）
**本协议目的**：补齐审稿人最可能攻击的三大证据缺口（单一弱模型 / 无统计严谨性 / 无专家评估），并把两个"看起来没用"的 agentic 组件（arbitration、deterministic grounding 消融）转化为正向贡献。

> **重要原则**：本协议只产出**真实测量数据**。所有结果表格留空并标注"[待填：真实结果]"。任何数字都必须来自实际跑出/评出的观测，不得用公式推断填充。可用公式合法计算的，仅限基于真实测量的派生统计量（均值、标准差、置信区间、检验统计量）。

---

## 0. 实验包总览与优先级

按"审稿影响 ÷ 投入成本"排序，建议的执行顺序：

| 顺序 | 实验包 | 解决的审稿质疑 | 是否需新跑 | 预估工作量 |
|---|---|---|---|---|
| 1 | **B-主**：已有数据的 Bootstrap 置信区间 | "无统计严谨性、无误差棒" | 否（用现有 per-task 分数） | 0.5–1 天 |
| 2 | **C**：专家评估 | "纯自动指标、0.152 太低、无人验证" | 是（人工评分） | 招募+评分，2–4 周（提前启动） |
| 3 | **A**：多模型泛化 | "单个 9B 量化模型、结论是否泛化、强模型是否让 linking 失效" | 是 | 2–4 天机时 |
| 4 | **D**：arbitration / grounding 压力测试集 | "agentic 组件无贡献、grounding 消融无效" | 是（先建集再跑） | 1 周 |
| 5 | **B-辅**：重复跑求 run-level 方差 | "单次跑、无随机性刻画" | 是 | 2–3 天机时 |
| 6 | **E**：任务集扩充与平衡 | "46 太小、临时用电 n=2 不可解释" | 视语料 | 1–2 周 |

最低限度要进 top：**1 + 2 + 3**。能再加 4 会把 limitation 变贡献。

---

## 实验包 A：多模型泛化实验

### A.1 目的
证明"case-to-norm linking 优于 optimized RAG"这一核心结论**不是单个弱模型的产物**，并直面最危险的一个反驳：*"换成强模型后，模型自己就能在 prompt 里推断出 case 与 norm 的关系，你的结构化机制是否就多余了？"*

### A.2 控制原则（公平性）
只替换 LLM backend，其余**完全冻结**：
- 同一任务集、同一规范语料（1,791 chunks）、同一事故语料（152 chunks）、同一 Elasticsearch 检索索引、同一 BM25+dense+tag 混合检索与 RRF 参数、同一评估脚本。
- 同一 prompt 模板、同一 `max_tokens`、**固定 temperature**（建议 0.0；若模型不支持 0 则取 0.1 并固定 seed）。
- 同一证据包（即让不同模型在**相同的检索/链接结果**上做 authoring 与 citation 选择），这样指标差异只来自"生成与引用选择"能力，归因干净。

### A.3 模型选择（按类别，不按具体型号锁死——选你当前能稳定部署的）
| 角色 | 选择标准 | 示例（用你跑实验时可得的当前强模型替换） |
|---|---|---|
| M0 原始基线 | 已有数据，保留 | Qwen 系列 9B 量化（即现稿模型，**先核对版本字符串**，见 §F） |
| M1 同族更大 | 测"是否是模型规模/量化导致 0.152" | 同族 32B/72B，非量化或 Q8 |
| M2 异族开源 | 测跨架构泛化 | 另一开源家族的 70B 级模型 |
| M3 前沿 API | 上界 + 关键对照 | 一个前沿商用 API 模型 |

### A.4 跑哪些组合（控成本）
核心科学问题只需两支变体跨模型对比：**Proposed** vs **Optimized RAG**。
- 全模型 × {Proposed, Optimized RAG} × Tier-S（33 任务）为**必跑**：4×2×33 = **264 runs**。
- 若机时允许，扩到全 46 任务：4×2×46 = **368 runs**。
- 关键判读：若在 M3（强模型）上 Proposed 的 norm recall / link resolution 仍显著高于 Optimized RAG → 直接驳倒"强模型让 linking 失效"的质疑，这是本实验包最重要的一句结论。

### A.5 产出
**新表 A**：模型 × 变体 的 norm recall@k / norm validity / link resolution / hazard coverage / case relevance。

| Model | Variant | Grounding | Norm validity | Hazard cov. | Case rel. | Norm recall@k | Link res. |
|---|---|---|---|---|---|---|---|
| M0 | Optimized RAG | [待填] | [待填] | [待填] | [待填] | [待填] | [待填] |
| M0 | Proposed | [待填] | … | | | | |
| M1 | Optimized RAG | | | | | | |
| M1 | Proposed | | | | | | |
| … | … | | | | | | |

**正文结论模板（用真实结果填）**："Across N=4 backends spanning 9B–70B+ and one frontier API, the proposed method's link-resolution rate remained [X–Y] while all optimized-RAG variants stayed at 0.000, indicating the cross-document mechanism is not substitutable by stronger parametric inference."（**仅在真实数据支持时才能这么写**。）

---

## 实验包 B：统计严谨性

### B-主（**今天就能做，零新跑**）：跨任务 Bootstrap 置信区间

#### 目的
给每个 headline 指标加 95% CI，给核心对比加显著性与效应量。前提：你有 `data/eval/` 里每个变体每个任务的 **per-task 分数**。

#### 方法（对真实测量的合法统计，可直接用）
对每个 (变体, 指标)：
1. 设 46 个任务（或 33 个 Tier-S）的 per-task 分数为 \(x_1,\dots,x_n\)。
2. **Bootstrap CI**：有放回重采样 B=10,000 次，每次重算均值，取 2.5/97.5 百分位作为 95% CI。
3. **配对显著性检验**：因为同一任务在不同变体下成对，用 **Wilcoxon signed-rank test**（非参数，适合 0–1 有界、非正态指标）。核心对比：Proposed vs Optimized RAG 的 norm recall；Full vs no_case_norm_linker 的 norm recall。
4. **效应量**：报 **Cliff's delta**（或 rank-biserial r），别只报 p。
5. **多重比较校正**：同一指标族内用 **Holm–Bonferroni** 校正 p 值。

#### 可直接套用的脚本骨架（Python，对你的真实分数运行）
```python
import numpy as np
from scipy.stats import wilcoxon

def bootstrap_ci(x, B=10000, alpha=0.05, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    means = x[rng.integers(0, len(x), size=(B, len(x)))].mean(axis=1)
    lo, hi = np.percentile(means, [100*alpha/2, 100*(1-alpha/2)])
    return x.mean(), lo, hi

def cliffs_delta(a, b):           # a, b: per-task scores of two variants
    a, b = np.asarray(a), np.asarray(b)
    gt = sum((ai > bj) for ai in a for bj in b)
    lt = sum((ai < bj) for ai in a for bj in b)
    return (gt - lt) / (len(a) * len(b))

# 示例：proposed vs optimized 的 norm recall（替换成你的真实 per-task 数组）
# m, lo, hi = bootstrap_ci(recall_proposed)
# stat, p = wilcoxon(recall_proposed, recall_optimized)   # 配对
# d = cliffs_delta(recall_proposed, recall_optimized)
```

#### 产出
把所有主表（Table 1–4）的每个单元格改为 `mean [95% CI]`；核心对比补一行 `p = [待填], Cliff's δ = [待填]`。**这一步几乎零成本，却补上了审稿人最常提的"无误差棒/无显著性"。**

### B-辅（需新跑）：run-level 随机性

#### 目的
刻画 LLM 采样带来的跑间方差（B-主刻画的是任务间方差，二者不同）。

#### 设计
- 对 **Proposed、Optimized RAG、no_case_norm_linker** 三支关键变体，固定 temperature>0（如 0.3）+ 不同 seed，**重复 R=3 次** × 46 任务 = 3×3×46 = **414 runs**。
- 报每个指标的"跨重复 mean ± SD"，确认结论在采样噪声下稳定。
- 若你 §A 已用 temperature=0 做了确定性跑，可在正文说明"主结果为确定性配置；B-辅单独刻画采样方差"。

---

## 实验包 C：专家评估（**最高杠杆**）

### C.1 目的
用领域专家验证生成材料/证据包的真实可用性，回应"严格 label-overlap 低估语义正确""0.152 看着吓人""纯自动指标"三连击。

### C.2 评分员
- **≥3 名**合格施工安全专业人员（注册安全工程师，或 ≥5 年现场安全管理经验）。3 名是能算一致性的实务下限；有条件上 4–5 名更稳。
- 评分前做 **校准轮**：用 3–5 份不在测试集中的样例共同评分、讨论分歧、固化评分细则（rubric anchoring）。报告这一步。

### C.3 样本
- 分层随机抽样：覆盖 4 个主题 × 2 个 tier。建议 **20–30 个任务 × {Proposed, Optimized RAG} = 40–60 份文档**。
- **单盲**：去掉系统标识、随机化呈现顺序，评分员不知道哪份来自哪个系统。

### C.4 评分维度（1–5 Likert，每档写明锚点描述）
| 维度 | 含义 |
|---|---|
| 法规引用正确性 | 引用条款是否确为治理该场景的条款 |
| 危险源覆盖完整性 | 是否覆盖该作业关键危险源 |
| 事故警示恰当性 | 警示是否真实、无夸大、无误导 |
| 现场可用性 | 能否直接用于班前/工具箱交底 |
| 可追溯性 | 关键论断能否核到来源证据 |
| 总体适用性 | 综合是否可用 |

**额外两项（比 Likert 更有说服力）**：
- 二元："是否经少量编辑即可投用？(Y/N)" → 给出"可用率"。
- 计数：每份文档标出的**事实性错误条数** → 给出"每文档错误率"，这是比 0.152 更能打动审稿人的硬指标。

### C.5 一致性与分析
- **评分员间信度**：序数 Likert 用 **Krippendorff's α (ordinal)** 或 **ICC(2,k)**；目标 α ≥ 0.667（可接受），低于则需重新校准。
- **系统对比**：Proposed vs Optimized RAG 各维度用配对 Wilcoxon；报均值±SD、p、效应量。
- **定性**：归纳评分员评论中的反复出现主题（如"条款对但顺序乱""警示偏弱"），写入 Discussion。

### C.6 伦理
确认本机构对"专家评估系统输出"是否需 IRB/伦理审批（多数情况下豁免，但正文需一句声明）。

### C.7 产出
**新表 C**：各维度 系统 × (mean±SD) + α/ICC + 可用率 + 每文档错误率。这是单项性价比最高的加分。

---

## 实验包 D：arbitration / grounding 压力测试集

### D.1 目的
现 benchmark 几乎不触发 arbitration，导致两个 agentic 组件"看起来没用"，且 `no_deterministic_grounding` 消融因没诱发幻觉而无效。构造针对性子集，让它们真正被激活，把 limitation 变贡献。

### D.2 三个受控子集
1. **norm_case_conflict 集（~15–20 任务）**
   故意构造"事故经验做法 ↔ 现行规范"冲突的任务（如旧做法 vs 更新后的标准）。检验 norm-over-case 策略与 human-review flag 是否正确触发。
   - 指标：冲突检出率、norm-over-case 正确裁决率、human-review flag 的 precision/recall。
2. **evidence_insufficient 集（~15–20 任务）**
   故意让治理条款在语料中缺失或稀疏（移除关键 article，或查询无匹配 chunk 的危险源）。检验系统是**请求补证据/报低置信**还是**强行幻觉**。
   - 指标：insufficiency 上报率 vs "证据不足下的幻觉率"。
3. **adversarial_hallucination 集（~15–20 任务）——修复无效消融**
   注入近义干扰条款、或诱导引用包外条款，构造易诱发"引用包外 chunk-id"的条件。然后 **grounding ON vs OFF** 对比。此时 `no_deterministic_grounding` 才会真正显出差异。
   - 指标：幻觉引用率 (ON vs OFF)、grounding 拦截率。

### D.3 产出
**新表 D**：三子集上的 arbitration/grounding 专属指标。正文里把现稿"arbitration under-tested""grounding 消融无效"两条 limitation，改写成"在专门压力集上验证了 arbitration/grounding 的作用边界"。

---

## 实验包 E：任务集扩充与平衡（可选但推荐）

### E.1 目的
46 偏小、临时用电 n=2 不可解释。

### E.2 方案（二选一，依语料而定）
- **能扩**：你有 76 个事故案例但只派生 46 任务 → 补派生任务，优先把临时用电及欠采样主题补到每主题 n≥8–10，总数 ≥60。
- **难平衡**：明确把临时用电从 headline claim 中**降级**，仅作为有文档记录的 edge case (n=2) 呈现，并在 limitation 写明。

---

## F. 可复现性清单（投稿前必须落实）

- [ ] **核对并锁定模型版本字符串**：现稿写的 "Qwen3.5-9B-Q5_K_M" 请对照实际服务的模型确认无误（通义官方系列命名需核实），写成可追溯的精确标识（含 quantization、context length、推理后端）。版本写错是可复现性审查的硬伤。
- [ ] 固定并报告 temperature / seed / top-p / max_tokens。
- [ ] 固定并报告 Elasticsearch 索引版本、RRF 的 k、各通道权重。
- [ ] 公开评估脚本、任务定义、chunk schema、（在版权允许范围内的）派生元数据。
- [ ] 报告每个实验的 run 数与硬件，给出机时。
- [ ] 多模型/多重复实验的随机性控制方式逐一写清。

---

## G. 实验—审稿质疑—正文落点 映射表

| 实验包 | 回应的审稿质疑 | 写入正文的位置 | 产出 |
|---|---|---|---|
| A | 单弱模型 / 强模型是否让 linking 失效 | 新增 5.x「Cross-model generalization」 | 表 A |
| B-主 | 无误差棒 / 无显著性 | 改造 Table 1–4 为 mean[CI] + 检验 | CI、p、效应量 |
| B-辅 | 单次跑、无随机性刻画 | 5.x 或附录 | mean±SD |
| C | 纯自动指标 / 0.152 / 无人验证 | 新增 5.x「Expert evaluation」 | 表 C + 一致性 |
| D | agentic 组件无贡献 / grounding 消融无效 | 改写 5.5 与 6.5，新增压力测试 | 表 D |
| E | 任务集小且不均衡 | 4.1 与 limitation | 扩充后任务分布 |

---

## H. 数据回填约定（给我/合作者）

跑完任一实验包后，把**真实结果**（最好是 per-task 级别的 CSV/JSON）回填到对应空表。届时我可以帮你：
- 用 §B 的方法对你的真实分数算 CI、做配对检验、算效应量；
- 把真实数字写成符合期刊语气的 Results 段落；
- 据真实结果调整 Abstract / Conclusion 的 claim 强度。

**再次强调**：空表里的任何数字都必须来自真实跑出/评出的观测，不得以任何"推断"方式填入。
