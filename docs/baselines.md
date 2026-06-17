# Baseline Architecture (Paper §4)

> 与 `paper/Manuscript_Architecture.md` §4 第 3 节"Training material generation baselines"对齐。
> 与 `research_plan.md` §9.1 五系统对照对齐。

## 5 套对照系统

| ID | 变体 | 检索 | 案例 | 一致性检查 | 仲裁 | 接地 |
|---|---|---|---|---|---|---|
| B1 | `llm_only` | 无 | 无 | 无 | 无 | 无 |
| B2 | `norm_only` | norm 单路 BM25+RRF | 无 | 无 | 无 | 无 |
| B3 | `naive_dual` | norm+case 双路 BM25+RRF | 有 | 无 | 无 | 无 |
| B4 | `optimized` | 混合 BM25+向量+RRF + 交叉编码器重排 | 有 | 无 | 无 | 无 |
| B5 | `proposed` | 同 B4 + case→norm 链接 | 有 | 有 | 有（取证/撰写/仲裁三层）| **chunk_id 确定性接地** |

## 实现位置

```
src/baselines/
  __init__.py              # 入口 + 注册
  base.py                  # BaselineResult / 调度器 / 自动注册
  b1_llm_only.py
  b2_norm_only_rag.py
  b3_naive_dual_rag.py
  b4_optimized_rag.py
  b5_proposed.py           # 复用 unified_graph(mode=training)

scripts/run_baseline.py    # CLI 驱动
tests/test_baselines.py    # 8 条契约测试
```

## 接口

每个 baseline 输入一个 `task`（v1 任务集 JSONL 的一行），输出 `BaselineResult`：

```python
BaselineResult(
    variant: str
    task_id: str
    training_output: dict      # TrainingOutput schema
    retrieved_norm_ids: list   # 检索命中
    retrieved_case_ids: list
    llm_calls: int
    retrieval_calls: int
    elapsed_seconds: float
    prompt_chars: int
    grounded: bool             # 仅 B5 为 True
    raw_evidence: dict
)
```

## 论文逻辑

每两个相邻变体之间的差异**精确定位一项贡献**：

| 比较 | 隔离的贡献 |
|---|---|
| B2 - B1 | 检索（规范条文）的价值 |
| B3 - B2 | 加入事故案例 evidence 的价值 |
| B4 - B3 | 混合检索 + 重排序的价值（优化但非 agentic）|
| **B5 - B4** | **§5.2 case→norm 链接 + §5.3 确定性接地 + §5.4 三层仲裁** 的联合贡献 |

`grounded` 字段是 §5.3 反幻觉保证的唯一布尔标记——只有 B5 在 LLM 输出后做 chunk_id 接地校验。

## 跑法

```bash
# 单变体单任务
python scripts/run_baseline.py --variant proposed --task-id task-起重吊装-009

# 全 5 变体跑一个任务
python scripts/run_baseline.py --task-id task-起重吊装-009

# 全 5 变体 × 全 46 任务（230 runs，Qwen 必须在线）
python scripts/run_baseline.py --tasks data/eval/training_tasks_v1.jsonl \
    --output data/eval/baseline_runs/

# 不依赖 LLM 的脚手架验证
python scripts/run_baseline.py --task-id task-起重吊装-009 --dry-run
```

## 状态

- ✓ 5 个变体已注册并通过 dry-run 契约测试
- ✓ 67 测试全过（含 8 baseline 契约 + 6 消融契约）
- ✓ Qwen 在线，pilot 25 runs（5 task × 5 variant）跑通
- ✓ §9.3 自动指标（7 项）已实现，详见 `src/evaluation/baseline_metrics.py`
- ✓ 端到端 benchmark runner：`scripts/run_benchmark.py`
- ✓ 5 项消融开关 + driver：`scripts/run_ablation.py`，详见 [ablations.md](ablations.md)
- ✓ Pilot 结果分析：[pilot_results.md](pilot_results.md)
- ⏭ 下一步：跑全 46 tasks × 5 variants 批 + 加 LLM-as-judge 语义指标

## 与 §9.3 评价指标的对接

每个 `BaselineResult` 字段直接喂给指标：

| 指标 | 数据源 |
|---|---|
| 规范依据准确率 | `training_output.norm_requirements` × `expected_norm_refs` |
| 危险源覆盖率 | `training_output.expected_hazards` × `task.expected_hazards` |
| 案例相关性 | `retrieved_case_ids` × `task.expected_case_refs` |
| 幻觉率（仅 B5 关注）| `grounded=True` 时 = 0；其余依赖 post-hoc LLM-as-judge |
| 时延/成本 | `elapsed_seconds` / `llm_calls` / `retrieval_calls` |
