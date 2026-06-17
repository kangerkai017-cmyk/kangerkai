from src import config
from src.config import LLM_QUERY_TEMPERATURE
from src.llm_utils import call_llm_json
from src.schema.qa import QAPlanOutput
from src.prompts import qa_planner as prompts


def run_qa_planner(state: dict) -> dict:
    question = state["question"]
    if config.AGENT_INTERACTIVE_FAST:
        clean = question.strip()
        base = clean.rstrip("？?")
        return {
            "norm_queries": [
                base,
                f"{base} 规范 要求 安全 防护",
                f"{base} 施工 安全 措施",
            ],
            "case_queries": [
                base,
                f"{base} 事故 案例",
            ],
        }

    prompt = prompts.USER.format(question=question)

    try:
        result = call_llm_json(
            prompt,
            prompts.SYSTEM,
            response_model=QAPlanOutput,
            temperature=LLM_QUERY_TEMPERATURE,
        )
    except ValueError:
        return {"norm_queries": [], "case_queries": []}

    return {
        "norm_queries": result.norm_queries,
        "case_queries": result.case_queries,
    }
