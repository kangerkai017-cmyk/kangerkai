from src.config import LLM_QUERY_TEMPERATURE
from src.llm_utils import call_llm_json
from src.schema.unified import IntentOutput
from src.prompts import intent as prompts

_QUESTION_MARKERS = (
    "？", "?", "为什么", "为何", "如何", "怎么", "怎样", "是什么",
    "能不能", "可不可以", "要不要", "是否", "多少", "哪些", "哪个",
    "什么时候", "有没有", "该不该",
)
_TRAINING_MARKERS = ("培训", "交底", "班前", "安全教育", "培训材料")


def _heuristic_mode(text: str) -> str:
    """Deterministic fallback when the LLM classifier is unavailable.

    Training markers win first (an explicit training request may also phrase a
    question); otherwise a question marker routes to qa; a bare work-activity
    topic defaults to training (the comprehensive product)."""
    if any(m in text for m in _TRAINING_MARKERS):
        return "training"
    if any(m in text for m in _QUESTION_MARKERS):
        return "qa"
    return "training"


def run_intent_classifier(state: dict) -> dict:
    user_input = state.get("user_input", "") or ""
    heuristic = _heuristic_mode(user_input)
    if heuristic == "training" and any(m in user_input for m in _TRAINING_MARKERS):
        return {
            "mode": "training",
            "topic": user_input.strip(),
            "intent_reason": "启发式规则：检测到培训/交底/班前教育关键词",
        }
    if heuristic == "qa":
        return {
            "mode": "qa",
            "question": user_input.strip(),
            "intent_reason": "启发式规则：检测到疑问词或问号",
        }

    prompt = prompts.USER.format(user_input=user_input)

    try:
        result = call_llm_json(
            prompt,
            prompts.SYSTEM,
            response_model=IntentOutput,
            temperature=LLM_QUERY_TEMPERATURE,
        )
        mode = result.mode
        topic = result.topic
        reason = result.reason
    except ValueError:
        mode = heuristic
        topic = ""
        reason = "LLM 分类失败，启发式兜底判定"

    if mode == "training":
        return {
            "mode": "training",
            "topic": (topic or user_input).strip(),
            "intent_reason": reason,
        }
    return {
        "mode": "qa",
        "question": user_input.strip(),
        "intent_reason": reason,
    }
