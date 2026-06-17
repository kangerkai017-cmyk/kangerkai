# Ablation Switches (Paper §4)

> 与 `paper/Manuscript_Architecture.md` §4 "Ablation experiments" 5 项列表对齐。
>
> 设计原则：**每个开关精确剔除 proposed 系统的一项机制**，其它一切相同。
> 差异（full − ablation）= 该机制的净贡献。

## 5 项消融

| Ablation | Env flag (default=true) | 剔除机制 | 主线条款 |
|---|---|---|---|
| A1 `no_case_evidence` | `ABLATION_CASE_EVIDENCE=false` | 不检索事故案例（norm 路单独跑）| 案例证据的必要性 |
| A2 `no_case_norm_linker` | `ABLATION_CASE_NORM_LINKER=false` | 案例 + 规范并行检索，但**不**用案例引用反向拉规范 | §5.2 跨文档证据链 |
| A3 `no_query_rewrite` | `QUERY_REWRITE_ENABLED=false` | risk_planner 出的原查询直接喂检索器 | §7.2.5 query rewriter |
| A4 `no_deterministic_ground` | `ABLATION_DETERMINISTIC_GROUND=false` | consistency_checker 不做 chunk_id 接地，仅靠 LLM 自查 | §5.3 反幻觉保证 |
| A5 `no_arbitration` | `ABLATION_ARBITRATION=false` | 撰写后直接终稿；无 norm_case_conflict 裁决 / 不足再检索 / 幻觉重接地 | §5.4 三层审议 + §7.6.5 仲裁层 |

## 实现位置

| Ablation | 钩子位置 |
|---|---|
| A1 | `src/agents/subgraphs/evidence.py::_retrieve_cases` |
| A2 | `src/agents/subgraphs/evidence.py::_link_case_norms` |
| A3 | `src/agents/query_rewriter.py::run_query_rewriter`（项目原有，本轮未动）|
| A4 | `src/agents/consistency_checker.py::run_consistency_checker` |
| A5 | `src/agents/graph.py::build_graph`（条件边路由）|

## 跑法

```bash
# 单任务 6 套（full + 5 ablations）
python scripts/run_ablation.py --task-id task-起重吊装-009

# 完整批跑
python scripts/run_ablation.py --output data/eval/ablation_full/

# 仅特定消融（如只跑 §5.2 + §5.3 两项）
python scripts/run_ablation.py --ablations full no_case_norm_linker no_deterministic_ground \
    --output data/eval/ablation_525_53/
```

驱动会自动 reload `src.config` + 相关 graph 模块，所以 env switch 实时生效，不需要重启 Python。

## 与 §9.3 指标的对应

| 指标 | 预期受影响最大的消融 |
|---|---|
| 规范引用合法率（grounding rate）| A4（去接地）显著降；A5（去仲裁）次之 |
| 幻觉率 | A4 显著升 |
| 案例相关性 | A1 降到 0 |
| 链接解析率（§5.2 头条）| A2 降到 0；A1 间接降到 0（无案例则无链接源）|
| 危险源覆盖率 | A3（去 rewriter）轻微降 |
| 时延 / LLM 调用次数 | A5 显著降（不再循环）|

## 与 baselines 对照实验的关系

| 实验 | 隔离的贡献 | 与 baseline 关系 |
|---|---|---|
| B5 vs B4 | 三大主线机制联合 | 跨架构对照 |
| A4 vs full | 仅 §5.3 接地 | proposed 内部消融 |
| A2 vs full | 仅 §5.2 链接 | proposed 内部消融 |
| A5 vs full | 仅 §5.4 仲裁 | proposed 内部消融 |

baselines 提供跨架构上限（**"我能做到多好"**），ablations 提供内部归因（**"哪一块在贡献"**）。
