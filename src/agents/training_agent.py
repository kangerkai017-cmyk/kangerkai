import json
from src import config
from src.llm_utils import call_llm_json
from src.schema.training import TrainingCompactOutput, TrainingOutput
from src.prompts import training as prompts
from src.agents.evidence_formatter import compact_draft_for_prompt


def run_training_agent(state: dict) -> dict:
    topic = state["topic"]
    scenario = state.get("training_scenario", "")
    hazards = state.get("hazards_identified", [])
    fused = state.get("fused_evidence", {})
    draft = state.get("draft_training_output", {})
    consistency_passed = state.get("consistency_passed", False)
    consistency_issues = state.get("consistency_issues", [])

    if config.AGENT_INTERACTIVE_FAST and draft:
        final = TrainingOutput.model_validate(draft).model_dump()
        _fill_fast_training_defaults(final, topic, scenario, hazards)
        if not final.get("norm_requirements") and fused.get("norm_requirements"):
            final["norm_requirements"] = fused["norm_requirements"]
        if not final.get("accident_warnings") and fused.get("case_warnings"):
            final["accident_warnings"] = fused["case_warnings"]
        return {"final_training_output": final}

    # fused_evidence already carries the grounded, chunk-level citations (norm
    # requirements + case warnings); don't re-stuff the full evidence indexes on
    # top of it — that was the biggest prompt-size offender.
    prompt = prompts.USER.format(
        topic=topic,
        scenario=scenario,
        hazards=json.dumps(hazards, ensure_ascii=False),
        fused_evidence=json.dumps(fused, ensure_ascii=False, separators=(",", ":")),
        evidence_diagnostics=json.dumps(
            state.get("evidence_diagnostics", {}),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        draft=json.dumps(compact_draft_for_prompt(draft), ensure_ascii=False, separators=(",", ":")),
        consistency_passed="是" if consistency_passed else "否",
        consistency_issues=json.dumps(consistency_issues, ensure_ascii=False, separators=(",", ":")),
    )

    try:
        result = call_llm_json(prompt, prompts.SYSTEM, response_model=TrainingCompactOutput)
    except ValueError:
        # Terminal node: never crash the whole run. Fall back to the validated
        # draft if present, otherwise a minimal scenario-only output.
        if draft:
            final = TrainingOutput.model_validate(draft).model_dump()
            if not final.get("norm_requirements") and fused.get("norm_requirements"):
                final["norm_requirements"] = fused["norm_requirements"]
            if not final.get("accident_warnings") and fused.get("case_warnings"):
                final["accident_warnings"] = fused["case_warnings"]
            return {"final_training_output": final}
        else:
            return {
                "final_training_output": TrainingOutput(
                    scenario_description=scenario,
                    learner_evaluation_guide="（本次培训材料生成失败，请以现场安全交底为准）",
                ).model_dump()
            }

    final = result.model_dump()
    valid_norm = {item.get("chunk_id"): item for item in fused.get("norm_requirements", []) or []}
    valid_case = {item.get("chunk_id"): item for item in fused.get("case_warnings", []) or []}
    selected_norm = [
        valid_norm[item.get("chunk_id")]
        for item in final.get("norm_requirements", []) or []
        if isinstance(item, dict) and item.get("chunk_id") in valid_norm
    ]
    selected_case = [
        valid_case[item.get("chunk_id")]
        for item in final.get("accident_warnings", []) or []
        if isinstance(item, dict) and item.get("chunk_id") in valid_case
    ]
    final["norm_requirements"] = selected_norm or fused.get("norm_requirements", [])
    final["accident_warnings"] = selected_case or fused.get("case_warnings", [])
    return {"final_training_output": final}


def _fill_fast_training_defaults(final: dict, topic: str, scenario: str, hazards: list) -> None:
    clean_topic = topic.strip() or "本次作业"
    if not final.get("scenario_description"):
        final["scenario_description"] = scenario or f"{clean_topic}作业前，班组应完成安全交底和现场检查。"
    if not final.get("hazard_identification_question"):
        final["hazard_identification_question"] = f"请识别{clean_topic}中的主要危险源，并说明应采取哪些控制措施。"
    if not final.get("expected_hazards"):
        final["expected_hazards"] = [str(h)[:30] for h in hazards[:5]] or ["高处坠落", "物体打击", "违章作业"]
    if not final.get("operation_points"):
        final["operation_points"] = [
            f"作业前：核对{clean_topic}专项方案和安全技术交底，确认作业人员已理解危险点和控制措施。",
            "作业前：检查作业环境、设备工具和个人防护用品，设置必要的警戒隔离和专人监护。",
            "作业中：严格按操作规程和审批的方案作业，不违章指挥、不违章操作、不冒险蛮干。",
            "作业中：正确佩戴和使用劳动防护用品，发现隐患立即停止作业并报告处理。",
            "作业后：清理现场、恢复安全状态，确认无遗留隐患后方可撤离。",
        ]
    if not final.get("learner_evaluation_guide"):
        final["learner_evaluation_guide"] = (
            f"能说出{clean_topic}的主要危险源、相应的规范要求和个人防护要求，即为合格。"
        )
    if not final.get("remedial_feedback_guide"):
        final["remedial_feedback_guide"] = (
            "若漏答关键危险源或防护要求，应结合对应规范条文和事故案例重新讲解后再考核。"
        )
    if not final.get("quiz_questions"):
        final["quiz_questions"] = [
            {
                "type": "true_false",
                "question": f"进行{clean_topic}时，只要赶进度，可以简化安全交底和防护措施。",
                "options": [],
                "answer": "错误",
                "explanation": "任何作业都必须落实安全交底和防护措施，不得因赶进度而简化。",
            }
        ]
