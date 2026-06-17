from src.agents.consistency_checker import _ground_against_evidence
from src.data_pipeline.norm_chunker import validate_norm_chunks
from src.retrieval.es_store import rrf_fuse
from src.schema import NormChunk
from src.tags import hazard_tags_for_text, scenario_tags_for_text


def test_norm_chunk_validation_rejects_mock_ids():
    chunk = NormChunk(
        chunk_id="norm_001",
        standard_name="测试规范",
        text="正文",
        chunk_kind="article",
        standard_code="TEST-1",
        source_path="tests/fixtures/test.pdf",
        scenario_tags=["高处作业"],
        hazard_tags=["高处坠落"],
        content_hash="hash",
        pipeline_version="norm_chunker_v2",
    )

    issues = validate_norm_chunks([chunk])

    assert any("mock id is not allowed" in issue for issue in issues)


def test_taxonomy_infers_shared_scenario_and_hazard_tags():
    text = "脚手架拆除 高处坠落 连墙件"

    scenario_tags = scenario_tags_for_text(text)
    hazard_tags = hazard_tags_for_text(text, scenario_tags)

    assert "脚手架拆除" in scenario_tags
    assert "脚手架使用" in scenario_tags
    assert "高处坠落" in hazard_tags
    assert "坍塌" in hazard_tags


def test_rrf_fuse_deduplicates_by_chunk_id_and_prefers_multi_route_hits():
    hit_a_1 = {"_source": {"chunk_id": "a", "hazard_tags": ["高处坠落"], "scenario_tags": ["脚手架拆除"]}}
    hit_b = {"_source": {"chunk_id": "b", "hazard_tags": [], "scenario_tags": []}}
    hit_a_2 = {"_source": {"chunk_id": "a", "hazard_tags": ["高处坠落"], "scenario_tags": ["脚手架拆除"]}}

    fused = rrf_fuse(
        [[hit_a_1, hit_b], [hit_a_2]],
        hazard_tags=["高处坠落"],
        scenario_tags=["脚手架拆除"],
        rrf_k=60,
    )

    assert [item["hit"]["_source"]["chunk_id"] for item in fused] == ["a", "b"]
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]


def test_checker_grounding_flags_fabricated_and_missing_norm_citations():
    state = {
        "draft_training_output": {
            "norm_requirements": [{"chunk_id": "fake"}],
            "accident_warnings": [],
        },
        "norm_evidence_ids": ["real"],
        "case_evidence_ids": [],
        "norm_evidence": [{"chunk_id": "real"}],
    }

    issues = _ground_against_evidence(state)

    assert any(issue["type"] == "hallucination" for issue in issues)
    assert any(issue["type"] == "evidence_insufficient" for issue in issues)


def test_checker_grounding_accepts_valid_norm_citations():
    state = {
        "draft_training_output": {
            "norm_requirements": [{"chunk_id": "real"}],
            "accident_warnings": [],
        },
        "norm_evidence_ids": ["real"],
        "case_evidence_ids": [],
        "norm_evidence": [{"chunk_id": "real"}],
    }

    assert _ground_against_evidence(state) == []
