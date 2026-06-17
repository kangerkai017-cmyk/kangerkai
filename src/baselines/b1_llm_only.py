"""B1: LLM-only baseline. No retrieval — just the LLM seeing the task scenario.

Operationalizes the §4 claim "普通 LLM 不使用外部知识库" (research_plan §9.1).
"""

import json

from src.llm_utils import call_llm_json
from src.schema.training import TrainingOutput
from src.baselines.base import BaselineResult, OUTPUT_BUDGET, register


SYSTEM = (
    "你是建筑施工安全培训助手。根据提供的高危作业场景，直接生成一份作业前安全"
    "培训材料。仅输出 JSON，结构匹配 TrainingOutput。"
)

USER_TEMPLATE = (
    "作业主题：{theme}\n"
    "作业场景：{scenario}\n\n"
    "请输出 JSON，字段包括：scenario_description、hazard_identification_question、"
    "expected_hazards（数组）、norm_requirements（数组，每项含 standard_code、article_id、"
    "content）、accident_warnings（数组，每项含 case_title、summary、lesson）、"
    "operation_points（数组）、learner_evaluation_guide、remedial_feedback_guide、"
    "quiz_questions（数组，每项含 type/question/answer）。"
)


@register("llm_only")
def run(task: dict, opts: dict) -> BaselineResult:
    prompt = USER_TEMPLATE.format(
        theme=task.get("theme", ""),
        scenario=task.get("scenario_summary", ""),
    ) + OUTPUT_BUDGET
    result = BaselineResult(
        variant="llm_only",
        task_id=task.get("task_id", ""),
        training_output={},
        prompt_chars=len(prompt),
        grounded=False,  # no chunk evidence → no grounding possible
    )
    if opts.get("dry_run"):
        result.training_output = {
            "scenario_description": task.get("scenario_summary", ""),
            "expected_hazards": [],
            "norm_requirements": [],
            "accident_warnings": [],
        }
        return result
    try:
        out = call_llm_json(prompt, SYSTEM, response_model=TrainingOutput)
        result.training_output = out.model_dump()
        result.llm_calls = 1
    except Exception as e:
        result.training_output = {"_error": str(e), "scenario_description": task.get("scenario_summary", "")}
    return result
