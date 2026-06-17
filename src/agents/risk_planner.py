import json
from src import config
from src.config import LLM_QUERY_TEMPERATURE
from src.llm_utils import call_llm_json
from src.schema.training import RiskPlanOutput
from src.prompts import risk_planner as prompts


def run_risk_planner(state: dict) -> dict:
    topic = state["topic"]
    scenario = state["training_scenario"]
    retry_count = state.get("retry_count", 0)
    consistency_issues = state.get("consistency_issues", [])
    evidence_request = state.get("evidence_request")
    if config.AGENT_INTERACTIVE_FAST:
        return _fallback_plan(topic, scenario)

    # Re-planning round: triggered by a consistency retry or by an arbiter
    # evidence_request (Part B). Fold the structured request into the issue list
    # so the planner targets exactly the hazards/requirements that came back
    # unsupported, and produces queries that differ from the previous round.
    if (retry_count > 0 and consistency_issues) or evidence_request:
        issues_payload = list(consistency_issues or [])
        if evidence_request:
            issues_payload.append({"type": "evidence_request", **evidence_request})
        previous = (state.get("norm_queries", []) or []) + (state.get("case_queries", []) or [])
        prompt = prompts.USER_RETRY.format(
            topic=topic,
            scenario=scenario,
            consistency_issues=json.dumps(issues_payload, ensure_ascii=False),
            previous_queries=json.dumps(previous, ensure_ascii=False),
            query_guide=prompts.QUERY_GUIDE,
        )
    else:
        prompt = prompts.USER.format(
            topic=topic, scenario=scenario, query_guide=prompts.QUERY_GUIDE
        )

    try:
        result = call_llm_json(
            prompt,
            prompts.SYSTEM,
            response_model=RiskPlanOutput,
            temperature=LLM_QUERY_TEMPERATURE,
        )
    except ValueError:
        return _fallback_plan(topic, scenario)

    return {
        "hazards_identified": result.hazards_identified,
        "norm_queries": result.norm_queries,
        "case_queries": result.case_queries,
    }


def _fallback_plan(topic: str, scenario: str) -> dict:
    text = f"{topic} {scenario}".strip()
    hazards = []
    if any(key in text for key in ("脚手架", "高处", "临边", "洞口", "吊篮")):
        hazards.extend(["高处坠落", "物体打击"])
    if any(key in text for key in ("脚手架", "支架", "模板", "坍塌")):
        hazards.append("坍塌")
    if any(key in text for key in ("临时用电", "电", "电焊")):
        hazards.append("触电")
    if not hazards:
        hazards = ["违章作业", "防护不到位", "人员误入危险区域"]

    base = text.replace("安全培训", "").strip() or topic
    return {
        "hazards_identified": list(dict.fromkeys(hazards))[:5],
        "norm_queries": [
            base,
            f"{base} 规范 要求 安全 防护",
            f"{base} 作业前 交底 检查",
        ],
        "case_queries": [
            f"{base} 事故 案例",
            f"{base} 高处坠落 物体打击",
        ],
    }
