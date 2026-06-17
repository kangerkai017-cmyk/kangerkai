#!/usr/bin/env python3
"""Mode B: 安全问答入口。

用法：
    python scripts/run_qa.py "脚手架拆除前为什么要设置警戒区？"
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents.qa_graph import get_compiled_qa_graph

DEFAULT_QUESTION = "脚手架拆除前为什么要设置警戒区？"


def print_separator(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_qa_output(output: dict):
    if not output:
        print("(No output generated)")
        return

    print_separator("回答")
    print(output.get("answer_text", "(未生成)"))

    confidence = output.get("confidence", "low")
    evidence_gap = output.get("evidence_gap", "")
    print(f"\n[置信度: {confidence}]", end="")
    if evidence_gap:
        print(f"  {evidence_gap}", end="")
    print()

    norms = output.get("cited_norms", [])
    if norms:
        print_separator("规范依据")
        for n in norms:
            print(f"  [{n.get('article_id', '-')}] {n.get('content', '')}")
            print(
                f"  chunk_id: {n.get('chunk_id', '-')}  |  "
                f"来源: {n.get('source', '-')}"
            )
            if n.get("linked_from_case"):
                print(f"  (案例链接自: {', '.join(n['linked_from_case'])})")

    cases = output.get("cited_cases", [])
    if cases:
        print_separator("事故案例")
        for c in cases:
            print(f"  ■ {c.get('case_title', '-')}")
            print(f"  经过: {c.get('summary', '')}")
            print(f"  后果: {c.get('consequence', '')}")
            print(f"  教训: {c.get('lesson', '')}")
            print(f"  chunk_id: {c.get('chunk_id', '-')}  |  来源: {c.get('source', '-')}")

    print_separator("DONE")


def main():
    question = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUESTION
    print(f"问题: {question}\n")

    graph = get_compiled_qa_graph()

    initial_state = {
        "question": question,
        "step_count": 0,
        "llm_calls": 0,
        "retrieval_calls": 0,
        "norm_queries": [],
        "case_queries": [],
        "norm_evidence": [],
        "case_evidence": [],
        "norm_evidence_ids": [],
        "case_evidence_ids": [],
        "linked_norm_evidence_ids": [],
        "case_index_available": False,
        "evidence_diagnostics": {},
        "final_qa_output": None,
    }

    print("Running Safety Q&A pipeline...\n")
    result = graph.invoke(initial_state)

    # Show diagnostics
    diag = result.get("evidence_diagnostics", {})
    if diag:
        print(f"检索诊断: norm={diag.get('norm_count', 0)} 条, "
              f"case={diag.get('case_count', 0)} 条, "
              f"case→norm 链接={diag.get('linked_norm_count', 0)} 条")

    print_qa_output(result.get("final_qa_output", {}))

    # Save full result
    output_path = os.path.join(os.path.dirname(__file__), "..", "data", "qa_output.json")
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
