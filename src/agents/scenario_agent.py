from src import config
from src.config import LLM_QUERY_TEMPERATURE
from src.llm_utils import call_llm_json
from src.schema.training import ScenarioOutput
from src.prompts import scenario as prompts


def run_scenario_agent(state: dict) -> dict:
    topic = state["topic"]
    if config.AGENT_INTERACTIVE_FAST:
        return {
            "training_scenario": (
                f"{topic}作业前，班组准备开展安全交底。现场应核查作业区域、"
                "防护设施、警戒隔离、人员资质和应急处置要求。"
            )
        }
    prompt = prompts.USER.format(topic=topic)
    try:
        result = call_llm_json(
            prompt,
            prompts.SYSTEM,
            response_model=ScenarioOutput,
            temperature=LLM_QUERY_TEMPERATURE,
        )
        return {"training_scenario": result.training_scenario}
    except ValueError:
        # Degrade to the raw topic so the pipeline can still proceed.
        return {"training_scenario": topic}
