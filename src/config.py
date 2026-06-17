import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-v4-pro")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))
LLM_MAX_TOKENS_BY_MODEL = {
    "ScenarioOutput": int(os.getenv("LLM_MAX_TOKENS_SCENARIO", "512")),
    "RiskPlanOutput": int(os.getenv("LLM_MAX_TOKENS_RISK_PLAN", "768")),
    "FusionResult": int(os.getenv("LLM_MAX_TOKENS_FUSION", "2500")),
    "FusionCompactResult": int(os.getenv("LLM_MAX_TOKENS_FUSION_COMPACT", "1400")),
    "ConsistencyCheckOutput": int(os.getenv("LLM_MAX_TOKENS_CONSISTENCY", "768")),
    "TrainingOutput": int(os.getenv("LLM_MAX_TOKENS_TRAINING", "3500")),
    "TrainingCompactOutput": int(os.getenv("LLM_MAX_TOKENS_TRAINING_COMPACT", "1400")),
    "QAPlanOutput": int(os.getenv("LLM_MAX_TOKENS_QA_PLAN", "256")),
    "QAOutput": int(os.getenv("LLM_MAX_TOKENS_QA", "1024")),
    "QACompactOutput": int(os.getenv("LLM_MAX_TOKENS_QA_COMPACT", "900")),
    "IntentOutput": int(os.getenv("LLM_MAX_TOKENS_INTENT", "256")),
}
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.9"))
LLM_DISABLE_THINKING = os.getenv("LLM_DISABLE_THINKING", "true").lower() in {"1", "true", "yes"}
# Higher temperature for query/scenario generation so retries actually explore
# different angles instead of re-emitting the same low-entropy output.
LLM_QUERY_TEMPERATURE = float(os.getenv("LLM_QUERY_TEMPERATURE", "0.7"))
LLM_USE_JSON_MODE = os.getenv("LLM_USE_JSON_MODE", "false").lower() in {"1", "true", "yes"}
LLM_STRUCTURED_MODE = os.getenv("LLM_STRUCTURED_MODE", "json_object").lower()
LLM_JSON_SCHEMA_MODELS = {
    name.strip()
    for name in os.getenv(
        "LLM_JSON_SCHEMA_MODELS",
        "ScenarioOutput,RiskPlanOutput,QueryRewriteOutput,FusionResult,FusionCompactResult,ConsistencyCheckOutput,TrainingOutput,TrainingCompactOutput,QAPlanOutput,QAOutput,QACompactOutput,IntentOutput",
    ).split(",")
    if name.strip()
}
AGENT_TRACE = os.getenv("AGENT_TRACE", "false").lower() in {"1", "true", "yes"}
# Interactive runs prefer bounded latency. Set AGENT_INTERACTIVE_FAST=false for
# the full paper/ablation graph with the extra rewrite step.
AGENT_INTERACTIVE_FAST = os.getenv("AGENT_INTERACTIVE_FAST", "true").lower() in {"1", "true", "yes"}
QA_MAX_LLM_CALLS = int(os.getenv("QA_MAX_LLM_CALLS", "2"))
TRAINING_MAX_LLM_CALLS = int(os.getenv("TRAINING_MAX_LLM_CALLS", "5"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5")
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
RETRIEVAL_BACKEND = os.getenv("RETRIEVAL_BACKEND", "elasticsearch")
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "rrf_hybrid")
ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ES_USERNAME = os.getenv("ES_USERNAME", "")
ES_PASSWORD = os.getenv("ES_PASSWORD", "")
ES_NORM_INDEX = os.getenv("ES_NORM_INDEX", "safety_norm_chunks")
ES_CASE_INDEX = os.getenv("ES_CASE_INDEX", "safety_case_chunks")
RRF_K = int(os.getenv("RRF_K", "60"))
BM25_TOP_K = int(os.getenv("BM25_TOP_K", "20"))
VECTOR_TOP_K = int(os.getenv("VECTOR_TOP_K", "20"))
TAG_TOP_K = int(os.getenv("TAG_TOP_K", "20"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
# Part B arbitration: max targeted re-retrieval rounds the arbiter may request
# before it must converge to the training agent (bounds the evidence dialogue).
DIALOGUE_BUDGET = int(os.getenv("DIALOGUE_BUDGET", "1"))
# Tier-aware query rewriting inside the evidence subgraph (path-optimized +
# feedback-steered). One small extra LLM call; toggle off to skip it.
QUERY_REWRITE_ENABLED = os.getenv("QUERY_REWRITE_ENABLED", "true").lower() in {"1", "true", "yes"}

# Retrieval result cache: query→fused-chunks LRU so repeated queries (across
# training/qa runs and the UI) skip the ES round-trip. Deterministic for a fixed
# index; clear it after rebuilding the index (clear_retrieval_cache()).
RETRIEVAL_CACHE_ENABLED = os.getenv("RETRIEVAL_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}
RETRIEVAL_CACHE_SIZE = int(os.getenv("RETRIEVAL_CACHE_SIZE", "256"))

# Cross-encoder reranking on top of RRF (off by default; needs the model present).
RERANK_ENABLED = os.getenv("RERANK_ENABLED", "false").lower() in {"1", "true", "yes"}
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
RERANK_POOL = int(os.getenv("RERANK_POOL", "30"))

# === Paper §4 ablation switches ===
# Each switch removes ONE mechanism from the proposed pipeline to isolate its
# contribution. All default ON; turn OFF to ablate.
#
#   ABLATION_CASE_EVIDENCE=false       → skip case retrieval entirely
#   ABLATION_CASE_NORM_LINKER=false    → skip §5.2 case→norm linker (cases
#                                         retrieved but not used to pull norms)
#   ABLATION_DETERMINISTIC_GROUND=false → consistency_checker ignores chunk_id
#                                         grounding (LLM-side checks only)
#   ABLATION_ARBITRATION=false         → skip arbitration node; treat consistency
#                                         check result as final
#   ABLATION_QUERY_REWRITE controlled by QUERY_REWRITE_ENABLED already.
ABLATION_CASE_EVIDENCE = os.getenv("ABLATION_CASE_EVIDENCE", "true").lower() in {"1", "true", "yes"}
ABLATION_CASE_NORM_LINKER = os.getenv("ABLATION_CASE_NORM_LINKER", "true").lower() in {"1", "true", "yes"}
ABLATION_DETERMINISTIC_GROUND = os.getenv("ABLATION_DETERMINISTIC_GROUND", "true").lower() in {"1", "true", "yes"}
ABLATION_ARBITRATION = os.getenv("ABLATION_ARBITRATION", "true").lower() in {"1", "true", "yes"}

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
