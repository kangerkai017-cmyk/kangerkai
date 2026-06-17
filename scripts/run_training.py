#!/usr/bin/env python3
"""Run a single training flow and print the output."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.graph import get_compiled_graph
from src.config import DIALOGUE_BUDGET

DEFAULT_TOPIC = "脚手架拆除作业前安全培训"


def print_separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_training_output(output: dict):
    if not output:
        print("(No output generated)")
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
        qtype = q.get("type", "unknown")
        print(f"\n  Q{i} [{qtype}] {q.get('question', '')}")
        if q.get("options"):
            for opt in q["options"]:
                print(f"      {opt}")
        print(f"  答案: {q.get('answer', '')}")
        if q.get("explanation"):
            print(f"  解析: {q['explanation']}")

    print_separator("DONE")


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TOPIC
    print(f"Topic: {topic}\n")

    graph = get_compiled_graph()

    initial_state = {
        "topic": topic,
        "step_count": 0,
        "llm_calls": 0,
        "retrieval_calls": 0,
        "training_scenario": None,
        "hazards_identified": [],
        "norm_queries": [],
        "case_queries": [],
        "norm_evidence": [],
        "case_evidence": [],
        "retrieval_mode": "",
        "norm_evidence_ids": [],
        "case_evidence_ids": [],
        "case_index_available": False,
        "evidence_diagnostics": {},
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
    }

    print("Running Agentic RAG training pipeline...\n")
    result = graph.invoke(initial_state)

    # Print consistency check result
    print(f"Consistency passed: {result.get('consistency_passed', 'N/A')}")
    issues = result.get("consistency_issues", [])
    if issues:
        print(f"Issues ({len(issues)}):")
        for issue in issues:
            print(f"  [{issue.get('type', '-')}] {issue.get('description', '')}")
    print(f"Retries used: {result.get('retry_count', 0)}")

    print_training_output(result.get("final_training_output", {}))

    # Optionally save full result
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "output.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        safe = {}
        for k, v in result.items():
            try:
                json.dumps(v)
                safe[k] = v
            except (TypeError, ValueError):
                safe[k] = str(v)
        json.dump(safe, f, ensure_ascii=False, indent=2)
    print(f"\nFull output saved to: {output_path}")


if __name__ == "__main__":
    main()
