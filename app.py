#!/usr/bin/env python3
"""Streamlit UI for the construction-safety unified agent."""

import json
import os
import sys
import time
from html import escape
from typing import Any

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from src import config as cfg
from src import metrics
from src.agents.unified_graph import get_compiled_unified_graph
from src.config import (
    DIALOGUE_BUDGET,
    ES_CASE_INDEX,
    ES_NORM_INDEX,
    ES_URL,
    OPENAI_BASE_URL,
)


MODE_LABELS = {"training": "培训生成", "qa": "安全问答"}
QUIZ_TYPE_LABELS = {
    "choice": "单选题",
    "true_false": "判断题",
    "short_answer": "简答题",
}
CONFIDENCE_META = {
    "high": ("高", "conf-high"),
    "medium": ("中", "conf-medium"),
    "low": ("低", "conf-low"),
}


EXAMPLES = [
    "脚手架拆除作业前安全培训",
    "脚手架拆除前为什么要设置警戒区？",
    "高处作业吊篮作业人员安全带使用培训",
    "施工现场临时用电触电事故预防培训",
    "临边洞口作业防坠落安全培训",
    "模板支架安装拆除安全培训",
]


def initial_unified_state(user_input: str) -> dict[str, Any]:
    return {
        "user_input": user_input,
        "mode": "",
        "intent_reason": "",
        "step_count": 0,
        "llm_calls": 0,
        "retrieval_calls": 0,
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
        "question": "",
        "final_qa_output": None,
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


@st.cache_resource(show_spinner=False)
def load_graph(profile: str):
    """Compile the unified graph for the given topology. The fast/full split is
    decided at build time by AGENT_INTERACTIVE_FAST, so build under the matching
    flag and restore it; one compiled graph is cached per profile."""
    prev = cfg.AGENT_INTERACTIVE_FAST
    cfg.AGENT_INTERACTIVE_FAST = profile == "fast"
    try:
        return get_compiled_unified_graph()
    finally:
        cfg.AGENT_INTERACTIVE_FAST = prev


def inject_css() -> None:
    st.markdown(
        """
<style>
:root {
  --app-bg: #f5f7fb;
  --panel: #ffffff;
  --text: #172033;
  --muted: #667085;
  --primary: #2563eb;
  --accent: #0f766e;
  --border: #d9e1ec;
  --soft: #eef4ff;
}

.stApp {
  background: var(--app-bg);
  color: var(--text);
}

[data-testid="stSidebar"] {
  background: #ffffff;
  border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: var(--text);
}

.main-title {
  font-size: 28px;
  line-height: 1.25;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 4px 0;
}

.subtle {
  color: var(--muted);
  font-size: 14px;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin: 14px 0 18px 0;
}

.metric-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
}

.metric-label {
  color: var(--muted);
  font-size: 12px;
}

.metric-value {
  color: var(--text);
  font-size: 20px;
  font-weight: 700;
  margin-top: 4px;
}

.answer-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 18px;
  margin: 10px 0 14px 0;
}

.section-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.pill {
  display: inline-block;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--soft);
  color: #1e3a8a;
  font-size: 12px;
  padding: 3px 8px;
  margin: 2px 5px 2px 0;
}

.source-line {
  color: var(--muted);
  font-size: 12px;
  margin-top: 6px;
}

.conf-badge {
  display: inline-block;
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 600;
}

.conf-high {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #86efac;
}

.conf-medium {
  background: #fef9c3;
  color: #854d0e;
  border: 1px solid #fde047;
}

.conf-low {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}

div.stButton > button {
  border-radius: 8px;
  border: 1px solid var(--border);
  background: #ffffff;
  color: var(--text);
  width: 100%;
}

div.stButton > button:hover {
  border-color: var(--primary);
  color: var(--primary);
}

[data-testid="stChatMessage"] {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
}

@media (max-width: 900px) {
  .metric-strip {
    grid-template-columns: 1fr;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_metric_strip(result: dict[str, Any]) -> None:
    diag = result.get("evidence_diagnostics") or {}
    mode = result.get("mode") or "-"
    mode_label = MODE_LABELS.get(mode, mode)
    st.markdown(
        f"""
<div class="metric-strip">
  <div class="metric-card">
    <div class="metric-label">意图路由</div>
    <div class="metric-value">{_safe_html(mode_label)}</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">规范证据</div>
    <div class="metric-value">{diag.get("norm_count", 0)}</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">事故案例</div>
    <div class="metric-value">{diag.get("case_count", 0)}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    reason = result.get("intent_reason")
    if reason:
        st.caption(f"路由说明：{reason}")
    if "wall_seconds" in diag:
        st.caption(
            f"运行指标：拓扑 {diag.get('agent_profile', '-')} · "
            f"耗时 {diag.get('wall_seconds', '-')}s · "
            f"LLM {diag.get('llm_calls', 0)} 次 · "
            f"检索 {diag.get('retrieval_calls', 0)} 次 · "
            f"节点 {diag.get('node_steps', 0)} 个"
        )


def _safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _safe_html(value: Any, fallback: str = "") -> str:
    return escape(_safe_text(value, fallback))


def _norm_code(item: dict[str, Any]) -> str:
    """规范编号：优先 standard_code，否则从 chunk_id 前缀（CODE:article）解析。"""
    code = _safe_text(item.get("standard_code"))
    if code:
        return code
    chunk_id = _safe_text(item.get("chunk_id"))
    if ":" in chunk_id:
        return chunk_id.split(":", 1)[0]
    return _safe_text(item.get("source"), "未知来源")


def render_norms(norms: list[dict[str, Any]]) -> None:
    if not norms:
        st.info("本次没有返回可展示的规范依据。")
        return
    for item in norms:
        title = _safe_text(item.get("article_id"), "-")
        with st.expander(f"{title} · {_norm_code(item)}"):
            st.write(_safe_text(item.get("content"), ""))
            st.markdown(
                f"""
<div class="source-line">
chunk_id: {_safe_html(item.get("chunk_id"), "-")} · 类型: {_safe_html(item.get("requirement_type"), "-")}
</div>
""",
                unsafe_allow_html=True,
            )
            linked_from = item.get("linked_from_case") or []
            if linked_from:
                st.caption("案例链接自：" + "，".join(linked_from))


def render_cases(cases: list[dict[str, Any]]) -> None:
    if not cases:
        st.info("本次没有返回可展示的事故案例。")
        return
    for item in cases:
        with st.expander(_safe_text(item.get("case_title"), "事故案例")):
            if item.get("summary"):
                st.write("经过：" + _safe_text(item.get("summary")))
            if item.get("consequence"):
                st.write("后果：" + _safe_text(item.get("consequence")))
            if item.get("lesson"):
                st.write("教训：" + _safe_text(item.get("lesson")))
            st.markdown(
                f"""
<div class="source-line">
chunk_id: {_safe_html(item.get("chunk_id"), "-")} · 来源: {_safe_html(item.get("source"), "-")}
</div>
""",
                unsafe_allow_html=True,
            )


def render_qa(result: dict[str, Any]) -> None:
    output = result.get("final_qa_output") or {}
    answer = _safe_text(output.get("answer_text"), "未生成回答。")
    confidence = _safe_text(output.get("confidence"), "low").lower()
    conf_label, conf_class = CONFIDENCE_META.get(confidence, (confidence or "-", "conf-low"))
    evidence_gap = _safe_text(output.get("evidence_gap"))
    gap_html = (
        f'<span class="source-line">{_safe_html(evidence_gap)}</span>' if evidence_gap else ""
    )

    st.markdown(
        f"""
<div class="answer-card">
  <div class="section-title">回答</div>
  <div>{_safe_html(answer)}</div>
  <div class="source-line">置信度：<span class="conf-badge {conf_class}">{_safe_html(conf_label)}</span> {gap_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    tab_norms, tab_cases, tab_raw = st.tabs(["规范依据", "事故案例", "原始结果"])
    with tab_norms:
        render_norms(output.get("cited_norms") or [])
    with tab_cases:
        render_cases(output.get("cited_cases") or [])
    with tab_raw:
        st.json(result)


ARBITRATION_TYPE_LABELS = {
    "passed": "无冲突，通过",
    "norm_case_conflict": "规范-案例冲突",
    "evidence_insufficient": "证据不足",
    "hallucination": "幻觉/未接地",
    "exhausted": "重试预算用尽",
    "unknown": "其他",
}
ARBITRATION_ACTION_LABELS = {
    "proceed": "放行至撰写终稿",
    "resolved": "已裁决（规范 > 案例）",
    "request_more_evidence": "退回取证层定向再检索",
    "re_ground": "退回撰写层重新接地",
}


def render_deliberation(result: dict[str, Any]) -> None:
    """三层审议过程：取证 → 撰写 → 仲裁。完整模式有实质内容，快速模式诚实标注。"""
    diag = result.get("evidence_diagnostics") or {}
    profile = diag.get("agent_profile", "fast")

    with st.expander("审议过程（取证 → 撰写 → 仲裁）", expanded=(profile == "full")):
        # 取证层
        st.markdown("**① 取证层**　检索 + case→norm 跨文档链接")
        st.write(
            f"规范证据 {diag.get('norm_count', 0)} 条 · 事故案例 {diag.get('case_count', 0)} 条 · "
            f"案例→规范链接 {diag.get('linked_norm_count', 0)} 条"
        )

        if profile != "full":
            st.divider()
            st.info("当前为**快速模式**：仅取证→融合直接成稿，未运行撰写层一致性审计与仲裁层冲突裁决。切到「完整三层」可查看审议全过程。")
            return

        # 撰写层
        st.divider()
        passed = result.get("consistency_passed")
        status = "通过" if passed else "未通过 / 需关注"
        st.markdown("**② 撰写层**　融合成稿 + 一致性审计（确定性 chunk_id 接地）")
        st.write(f"一致性检查：{status} · 重试次数：{result.get('retry_count', 0)}")
        issues = result.get("consistency_issues") or []
        if issues:
            for issue in issues:
                st.write(f"　- [{issue.get('type', '-')}] {issue.get('description', '')}")

        # 仲裁层
        st.divider()
        decision = result.get("arbitration_decision") or {}
        st.markdown("**③ 仲裁层**　按冲突类型审议 + 受控再检索")
        if decision:
            dtype = ARBITRATION_TYPE_LABELS.get(decision.get("type"), decision.get("type", "-"))
            action = ARBITRATION_ACTION_LABELS.get(decision.get("action"), decision.get("action", "-"))
            st.write(f"裁决：{dtype} → {action}")
            if decision.get("policy"):
                st.write(f"　优先级策略：{decision['policy']}")
            if decision.get("rationale"):
                st.write(f"　裁决理由：{decision['rationale']}")
            if decision.get("note"):
                st.write(f"　备注：{decision['note']}")
        else:
            st.write("（本次未触发仲裁）")
        if result.get("requires_human_review"):
            st.warning("⚠ 该结果存在规范-案例冲突，已标记需人工复核（规范要求为准，冲突案例降级为补充警示）。")


def render_training(result: dict[str, Any]) -> None:
    output = result.get("final_training_output") or {}

    render_deliberation(result)

    st.markdown(
        f"""
<div class="section-card">
  <div class="section-title">作业情境</div>
  <div>{_safe_html(output.get("scenario_description"), "未生成作业情境。")}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="section-card">
  <div class="section-title">风险识别问题</div>
  <div>{_safe_html(output.get("hazard_identification_question"), "未生成风险识别问题。")}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    hazards = output.get("expected_hazards") or []
    if hazards:
        st.markdown(
            "".join(f'<span class="pill">{_safe_html(h)}</span>' for h in hazards),
            unsafe_allow_html=True,
        )

    tab_norms, tab_cases, tab_ops, tab_quiz, tab_raw = st.tabs(
        ["规范要求", "事故警示", "操作与评价", "小测题", "原始结果"]
    )
    with tab_norms:
        render_norms(output.get("norm_requirements") or [])
    with tab_cases:
        render_cases(output.get("accident_warnings") or [])
    with tab_ops:
        points = output.get("operation_points") or []
        if points:
            for idx, point in enumerate(points, 1):
                st.write(f"{idx}. {point}")
        st.divider()
        st.markdown("**学习者评价指南**")
        st.write(_safe_text(output.get("learner_evaluation_guide"), "未生成。"))
        st.markdown("**补训反馈指南**")
        st.write(_safe_text(output.get("remedial_feedback_guide"), "未生成。"))
    with tab_quiz:
        for idx, question in enumerate(output.get("quiz_questions") or [], 1):
            q_type = question.get("type", "")
            type_label = QUIZ_TYPE_LABELS.get(q_type, q_type or "题目")
            with st.expander(f"Q{idx} · {type_label}"):
                st.write(question.get("question", ""))
                for option in question.get("options") or []:
                    st.write(option)
                st.caption(f"答案：{question.get('answer', '')}")
                if question.get("explanation"):
                    st.write("解析：" + question["explanation"])
    with tab_raw:
        st.json(result)


def render_result(result: dict[str, Any]) -> None:
    render_metric_strip(result)
    if result.get("mode") == "training":
        render_training(result)
    else:
        render_qa(result)


@st.cache_data(show_spinner=False)
def run_agent(user_input: str, profile: str) -> dict[str, Any]:
    graph = load_graph(profile)
    # Node behavior (fast bypasses) reads the live flag at call time; set it to
    # match the topology we're about to invoke. Runs are sequential per session.
    cfg.AGENT_INTERACTIVE_FAST = profile == "fast"
    metrics.reset()
    t0 = time.perf_counter()
    result = graph.invoke(initial_unified_state(user_input))
    wall_seconds = round(time.perf_counter() - t0, 2)
    metrics.attach(result, wall_seconds, profile)
    return result


def main() -> None:
    st.set_page_config(page_title="施工安全 Agent", page_icon="🦺", layout="wide")
    inject_css()

    if "runs" not in st.session_state:
        st.session_state.runs = []
    if "pending_input" not in st.session_state:
        st.session_state.pending_input = ""

    with st.sidebar:
        st.markdown("## 施工安全 Agent")
        st.caption("Agentic RAG · 规范条文 · 事故案例 · 培训生成")
        st.divider()
        st.markdown("**运行模式**")
        mode_label = st.radio(
            "运行模式",
            ["快速问答", "完整三层（可追溯）"],
            index=0,
            label_visibility="collapsed",
            help="快速：单次 LLM 调用、低延迟。完整三层：取证→撰写→仲裁，含一致性审计与冲突仲裁，可追溯但较慢。",
        )
        profile = "fast" if mode_label.startswith("快速") else "full"
        st.divider()
        st.markdown("**服务配置**")
        st.caption(f"Qwen: {OPENAI_BASE_URL}")
        st.caption(f"ES: {ES_URL}")
        st.caption(f"规范索引: {ES_NORM_INDEX}")
        st.caption(f"案例索引: {ES_CASE_INDEX}")
        st.divider()
        st.markdown("**示例输入**")
        for i, example in enumerate(EXAMPLES):
            if st.button(example, key=f"example-{i}"):
                st.session_state.pending_input = example
        st.divider()
        if st.button("清空会话"):
            st.session_state.runs = []
            st.session_state.pending_input = ""
            run_agent.clear()
            st.rerun()

    st.markdown('<div class="main-title">施工安全智能培训与问答</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtle">输入安全问题或培训主题，系统会自动分流到问答或培训生成流程，并展示可追溯证据。</div>',
        unsafe_allow_html=True,
    )

    for run in st.session_state.runs:
        with st.chat_message("user"):
            st.write(run["input"])
        with st.chat_message("assistant"):
            if run.get("error"):
                st.error(run["error"])
            else:
                render_result(run["result"])

    prompt = st.chat_input("输入安全问题或培训主题")
    user_input = st.session_state.pending_input or prompt
    st.session_state.pending_input = ""

    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("正在调用 agent 检索规范和案例..."):
                try:
                    result = run_agent(user_input, profile)
                    render_result(result)
                    st.session_state.runs.append({"input": user_input, "result": result})
                    st.download_button(
                        "下载本次 JSON",
                        data=json.dumps(result, ensure_ascii=False, indent=2),
                        file_name="agent_result.json",
                        mime="application/json",
                    )
                except Exception as exc:  # pragma: no cover - UI safety net
                    message = f"{type(exc).__name__}: {exc}"
                    st.error(message)
                    st.session_state.runs.append({"input": user_input, "error": message})


if __name__ == "__main__":
    main()
