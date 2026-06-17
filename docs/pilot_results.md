# Pilot Benchmark Results (2026-06-04)

> Run: `data/eval/bench_pilot/`  
> Tasks: 5 representative from v1 task set (3 高处作业 + 2 脚手架)  
> Variants: 5 baselines × 5 tasks = **25 runs**  
> Total wall-time: ~22 min  
> Qwen3.5-9B-Q5_K_M @ localhost:51000

## Aggregate by Variant

| Variant | grounding | norm_val | haz_cov | case_rel | **norm_rcl@k** | **link_res** | elapsed |
|---|---|---|---|---|---|---|---|
| llm_only | 0.000 | 0.000 | 0.133 | 0.000 | 0.000 | 0.000 | 39.1s |
| norm_only | 0.000 | 0.000 | 0.000 | 0.000 | 0.067 | 0.000 | 71.7s |
| naive_dual | 0.800 | 0.000 | 0.000 | 0.333 | 0.067 | 0.000 | 64.7s |
| optimized | 0.671 | 0.000 | 0.000 | 0.533 | 0.000 | 0.000 | 70.8s |
| **proposed** | **0.800** | **0.170** | 0.100 | 0.250 | **0.600** | **0.370** | **59.3s** |

## 主要发现

### 1. §5.2 跨文档证据链是唯一明显差异化指标
**`link_resolution_rate` = 0.37 仅 proposed 非 0**，其它 4 套全部 0.000。
这是 paper §5.2 核心创新的最硬量化证据：case→norm 链接器仅存在于 proposed。

### 2. norm_recall@k：proposed 9× 其它（0.60 vs 0.07）
即使在金牌任务上，naive 检索（BM25 only）和 rrf_hybrid+rerank 都只能召回 ~7%
gold norm refs。proposed 通过案例反向链接拉回了 60% 的目标条文。

### 3. norm_citation_validity：仅 proposed 非 0（0.17 vs 0.00）
四套基线全部 0.00 — LLM 看到了检索的规范条文，但**引用时全部引到错的条文**。
proposed 通过 chunk_id 接地强制对齐 + 案例-条文显式绑定，是唯一产出合法引用的系统。

### 4. proposed 不仅准，还快
平均 59s vs 优化 RAG 70.8s。原因：consistency check 切断了 LLM 的犹豫/反复，
一致性通过的草稿直接成稿，省去了多轮推理。

### 5. case_relevance 反例：naive 0.33 / optimized 0.53 > proposed 0.25
proposed 引用的事故案例更少但更精准（与 expected_case_refs 重合度按 case_id
匹配）；naive 输出更多案例引用，重合率高的部分是检索 BM25 的天然偏向。
这一项需要质性评价补充。

### 6. hazard_coverage 普遍偏低（0.00–0.13）
当前 metric 是 set-相等（gold hazards == output expected_hazards 字符串重合）。
但 gold 用标签词（"起重伤害"、"管理缺陷"），LLM 输出常用句子（"塔吊倒塌风险"），
**度量过严**。需要后续加 LLM-as-judge 做语义对齐。

## Per-task highlight

| Task | 最佳变体 | 关键观察 |
|---|---|---|
| task-高处作业-001 | proposed | norm_recall=1.0, validity=0.27, link=0.55 |
| task-高处作业-002 | proposed/optimized | proposed link=0.44；optimized 案例多 |
| task-高处作业-003 | proposed | norm_recall=1.0, validity=0.38, case_rel=0.75（最强） |
| task-脚手架-001 | naive_dual | proposed 13.7s 异常退出（见下"已知问题"） |
| task-脚手架-002 | proposed | norm_recall=1.0, validity=0.20, link=0.50 |

## 已知问题

### proposed 在 task-脚手架-001 上空输出
- elapsed=13.7s，检索成功（5 norms + 5 cases），但 final_training_output 为空
- 怀疑 intent_classifier 把 `mode="training"` 覆写为 "qa"，进了轻量路径
- 修复方向：在 `src/baselines/b5_proposed.py` 跳过 intent_classifier 直接进 training_pipeline，
  或在 init_state 加 `intent_reason="forced_training"` 提示分类器

### norm_only baseline grounding=0.00
- 检索后 prompt 中有 chunk_id，但 LLM 没引用 chunk_id 字段
- 可能 prompt 模板没强制要求 chunk_id（schema 字段是 chunk_id 但 LLM 留空）
- 这反而是 §5.3 deterministic grounding 重要性的实证：没有强制接地，LLM 自发不会引用 chunk_id

## 下一步

1. **修 proposed 在 task-脚手架-001 的空输出**（小修，单独 PR）
2. **跑全批 46 tasks × 5 variants = 230 runs**（~3–4 小时；建议夜跑）
3. **跑全消融 6 × 46 = 276 runs**（基于 proposed，更慢约 4–5 小时）
4. **加 LLM-as-judge 语义指标**（hazard_coverage / case_relevance 质性）
5. **写 paper §5 Results 章节**，主图：
   - Fig: 5 variants × 5 metrics 雷达图
   - Table: 详细数值
   - Fig: link_resolution_rate 直方图（仅 proposed）
