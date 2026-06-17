from typing import Literal
from pydantic import BaseModel, Field, model_validator

from src.schema.state import TrainingState
from src.schema.qa import QAState


class UnifiedState(TrainingState, QAState):
    """Superset state for the top-level intent-routed graph.

    Inherits every field of the training (Mode A) and Q&A (Mode B) pipelines —
    they share evidence keys with identical types, so each nested subgraph reads
    and writes only its own schema's keys while these routing fields ride along
    at the parent level.
    """

    user_input: str
    mode: str            # "training" | "qa", set by intent_classifier
    intent_reason: str   # why the classifier chose this mode (transparency)


class IntentOutput(BaseModel):
    mode: Literal["training", "qa"] = "qa"
    topic: str = ""      # normalized training topic (only when mode=="training")
    reason: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_mode(cls, data: dict) -> dict:
        if isinstance(data, dict):
            raw = str(data.get("mode", "")).strip().lower()
            data["mode"] = raw if raw in {"training", "qa"} else "qa"
        return data
