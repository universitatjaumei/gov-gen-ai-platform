"""Tests unitarios para recommend_retrieval_mode."""

from server.app.modules.agents_hub.services.corpus_recommender import recommend_retrieval_mode

def test_recommends_long_context_for_small_corpus() -> None:
    mode, reason = recommend_retrieval_mode(total_tokens=10_000, context_window=128_000)
    assert mode == "MD_LONG_CONTEXT"
    assert "MD_LONG_CONTEXT" in reason

def test_recommends_agentic_for_medium_corpus() -> None:
    mode, reason = recommend_retrieval_mode(total_tokens=200_000, context_window=128_000)
    assert mode == "MD_AGENT_SELECTOR"
    assert "MD_AGENT_SELECTOR" in reason

def test_recommends_vector_for_huge_corpus() -> None:
    mode, reason = recommend_retrieval_mode(total_tokens=3_000_000, context_window=128_000)
    assert mode == "RAG"
    assert "RAG" in reason

def test_recommendation_reason_includes_token_count() -> None:
    total_tokens = 123_456
    _, reason = recommend_retrieval_mode(total_tokens=total_tokens, context_window=128_000)
    assert "123,456" in reason