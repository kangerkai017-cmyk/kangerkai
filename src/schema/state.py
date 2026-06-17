from typing import TypedDict, Optional


class TrainingState(TypedDict):
    # Input
    topic: str
    step_count: int
    llm_calls: int
    retrieval_calls: int

    # ScenarioAgent output
    training_scenario: Optional[str]

    # RiskPlanner output
    hazards_identified: list[str]
    norm_queries: list[str]
    case_queries: list[str]

    # Retrievers output (serialized chunk dicts)
    norm_evidence: list[dict]
    case_evidence: list[dict]
    retrieval_mode: str
    norm_evidence_ids: list[str]
    case_evidence_ids: list[str]
    linked_norm_evidence_ids: list[str]
    case_index_available: bool
    evidence_diagnostics: dict

    # EvidenceFusionAgent output (model_dump dicts)
    fused_evidence: Optional[dict]
    draft_training_output: Optional[dict]

    # ConsistencyChecker output
    consistency_passed: bool
    consistency_issues: list[dict]
    retry_count: int
    retry_reason: str

    # Arbitration subgraph (Part B): deliberation + controlled communication
    dialogue_budget: int          # remaining targeted re-retrieval rounds
    evidence_request: Optional[dict]  # what the next retrieval round must cover
    arbitration_decision: dict    # how a conflict/insufficiency was resolved
    requires_human_review: bool   # norm_case_conflict flagged for human audit
    arbitration_route: str        # next hop chosen by arbitration

    # TrainingAgent output (model_dump dict)
    final_training_output: Optional[dict]
