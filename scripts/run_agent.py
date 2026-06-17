#!/usr/bin/env python3
"""统一入口：双模态施工安全 agent。

一个图、一个交互入口，自动判断输入是"培训主题"还是"安全问题"并分流。

用法：
    python scripts/run_agent.py                       # 交互式 REPL
    python scripts/run_agent.py "你的问题或培训主题"    # 单次模式
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import metrics
from src.agents.unified_graph import get_compiled_unified_graph
from src.config import AGENT_INTERACTIVE_FAST, DIALOGUE_BUDGET


def print_separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def initial_unified_state(user_input: str) -> dict:
    return {
        "user_input": user_input,
        "mode": "",
        "intent_reason": "",
        "step_count": 0,
        "llm_calls": 0,
        "retrieval_calls": 0,
        # training (Mode A) fields
        "topic": "",
        "training_scenario": None,
        "hazards_identified": [],
        "fused_evidence": None,
        "draft_training_output": None,
        "consistency_passed": False,
        "consistency_issues": [],
        "retry_count": 0,
        "retry_reason": "",
        "dialogue_budget": DIALOGUE_BUDGET,
        "evidence_request": None,
        "arbitration_decision": {},
        "requires_human_review": False,
        "arbitration_route": "",
        "final_training_output": None,
        # qa (Mode B) fields
        "question": "",
        "final_qa_output": None,
        # shared evidence substrate
        "norm_queries": [],
        "case_queries": [],
        "norm_evidence": [],
        "case_evidence": [],
        "retrieval_mode": "",
        "norm_evidence_ids": [],
        "case_evidence_ids": [],
        "linked_norm_evidence_ids": [],
        "case_index_available": False,
        "evidence_diagnostics": {},
    }


def print_qa_output(output: dict):
    if not output:
        print("(未生成回答)")
        return

    print_separator("回答")
    print(output.get("answer_text", "(未生成)"))

    confidence = output.get("confidence", "low")
    evidence_gap = output.get("evidence_gap", "")
    line = f"\n[置信度: {confidence}]"
    if evidence_gap:
        line += f"  {evidence_gap}"
    print(line)

    norms = output.get("cited_norms", [])
    if norms:
        print_separator("规范依据")
        for n in norms:
            print(f"  [{n.get('article_id', '-')}] {n.get('content', '')}")
            print(f"  chunk_id: {n.get('chunk_id', '-')}  |  来源: {n.get('source', '-')}")
            if n.get("linked_from_case"):
                print(f"  (案例链接自: {', '.join(n['linked_from_case'])})")

    cases = output.get("cited_cases", [])
    if cases:
        print_separator("事故案例")
        for c in cases:
            print(f"  ■ {c.get('case_title', '-')}")
            print(f"  经过: {c.get('summary', '')}")
            print(f"  后果: {c.get('consequence', '')}")
            print(f"  chunk_id: {c.get('chunk_id', '-')}  |  来源: {c.get('source', '-')}")


def print_training_output(output: dict):
    if not output:
        print("(未生成培训材料)")
        return

    print_separator("1. 作业情境")
    print(output.get("scenario_description", "(未生成)"))

    print_separator("2. 风险识别问题")
    print(output.get("hazard_identification_question", "(未生成)"))
    print("\n期望识别的危险源：")
    for h in output.get("expected_hazards", []):
        print(f"  - {h}")

    print_separator("3. 规范要求")
    for n in output.get("norm_requirements", []):
        print(f"  [{n.get('article_id', '-')}] {n.get('content', '')}")
        print(
            f"  chunk_id: {n.get('chunk_id', '-')}  |  "
            f"来源: {n.get('source', '-')}  |  类型: {n.get('requirement_type', '-')}"
        )

    print_separator("4. 事故警示")
    for c in output.get("accident_warnings", []):
        print(f"  ■ {c.get('case_title', '-')}")
        print(f"  经过: {c.get('summary', '')}")
        print(f"  后果: {c.get('consequence', '')}")
        print(f"  chunk_id: {c.get('chunk_id', '-')}  |  来源: {c.get('source', '-')}")

    print_separator("5. 操作要点")
    for i, op in enumerate(output.get("operation_points", []), 1):
        print(f"  {i}. {op}")

    print_separator("6. 学习者评价指南")
    print(output.get("learner_evaluation_guide", "(未生成)"))

    print_separator("7. 补训反馈指南")
    print(output.get("remedial_feedback_guide", "(未生成)"))

    print_separator("8. 小测题")
    for i, q in enumerate(output.get("quiz_questions", []), 1):
        print(f"\n  Q{i} [{q.get('type', 'unknown')}] {q.get('question', '')}")
        for opt in q.get("options", []):
            print(f"      {opt}")
        print(f"  答案: {q.get('answer', '')}")
        if q.get("explanation"):
            print(f"  解析: {q['explanation']}")


def run_once(graph, user_input: str):
    metrics.reset()
    t0 = time.perf_counter()
    result = graph.invoke(initial_unified_state(user_input))
    wall_seconds = round(time.perf_counter() - t0, 2)
    metrics.attach(result, wall_seconds, "fast" if AGENT_INTERACTIVE_FAST else "full")

    mode = result.get("mode", "qa")
    reason = result.get("intent_reason", "")
    print(f"\n[意图路由 → {mode}]  {reason}")

    snap = metrics.snapshot()
    profile = "fast" if AGENT_INTERACTIVE_FAST else "full"
    print(
        f"运行指标: 拓扑={profile}, 耗时={wall_seconds}s, "
        f"LLM 调用={snap['llm_calls']} 次, 检索={snap['retrieval_calls']} 次, "
        f"节点={snap['node_steps']} 个"
    )

    diag = result.get("evidence_diagnostics", {})
    if diag:
        print(
            f"检索诊断: norm={diag.get('norm_count', 0)} 条, "
            f"case={diag.get('case_count', 0)} 条, "
            f"case→norm 链接={diag.get('linked_norm_count', 0)} 条"
        )

    if mode == "training":
        print_training_output(result.get("final_training_output", {}))
    else:
        print_qa_output(result.get("final_qa_output", {}))
    print_separator("DONE")
    return result


def main():
    graph = get_compiled_unified_graph()

    if len(sys.argv) > 1:
        user_input = sys.argv[1]
        print(f"输入: {user_input}")
        run_once(graph, user_input)
        return

    print("施工安全 Agent（统一入口）。输入培训主题或安全问题；输入 exit / quit 退出。\n")
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("再见。")
            break
        run_once(graph, user_input)
        print()


if __name__ == "__main__":
    main()
