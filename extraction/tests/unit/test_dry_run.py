"""Tests for dry-run mode and cost estimation."""

from pathlib import Path

import pytest

from kg_extractor.chunking.models import Chunk
from kg_extractor.config import LLMConfig
from kg_extractor.cost_estimator import CostEstimate, CostEstimator


def test_cost_estimator_basic():
    """Test basic cost estimation."""
    llm_config = LLMConfig(model="claude-3-5-sonnet-20241022")
    estimator = CostEstimator(llm_config)

    # Create a simple test chunk
    chunk = Chunk(
        chunk_id="test-chunk",
        files=[Path(__file__)],  # Use this test file as example
        total_size_bytes=1000,
    )

    # Estimate tokens for chunk
    input_tokens, output_tokens = estimator.estimate_chunk(chunk)

    # Should have input tokens (file + prompt overhead)
    assert input_tokens > 2000  # At least the prompt overhead
    assert output_tokens > 0  # Should estimate some output
    assert output_tokens < input_tokens  # Output should be less than input


def test_cost_estimator_chunks():
    """Test cost estimation for multiple chunks."""
    llm_config = LLMConfig(model="claude-3-5-sonnet-20241022")
    estimator = CostEstimator(llm_config)

    # Create test chunks
    chunks = []
    for i in range(3):
        chunk = Chunk(
            chunk_id=f"chunk-{i}",
            files=[Path(__file__)],
            total_size_bytes=1000,
        )
        chunks.append(chunk)

    # Estimate cost
    estimate = estimator.estimate_chunks(chunks)

    # Verify estimate
    assert isinstance(estimate, CostEstimate)
    assert estimate.total_files == 3
    assert estimate.total_chunks == 3
    assert estimate.total_size_bytes == 3000
    assert estimate.estimated_input_tokens > 0
    assert estimate.estimated_output_tokens > 0
    assert estimate.estimated_cost_usd > 0
    assert estimate.estimated_duration_seconds > 0
    assert estimate.model == "claude-3-5-sonnet-20241022"


def test_cost_estimator_with_larger_files():
    """Test cost estimation with larger files."""
    llm_config = LLMConfig(model="claude-3-5-sonnet-latest")
    estimator = CostEstimator(llm_config)

    # Create chunk with larger file
    chunk = Chunk(
        chunk_id="large-chunk",
        files=[Path(__file__)],
        total_size_bytes=100_000,  # 100KB
    )

    estimate = estimator.estimate_chunks([chunk])

    # Should have some cost (actual file is used, so it's smaller than 100KB)
    assert estimate.estimated_input_tokens > 2000  # At least prompt overhead
    assert estimate.estimated_cost_usd > 0.01  # At least some cost


def test_cost_estimate_string_representation():
    """Test CostEstimate string representation."""
    estimate = CostEstimate(
        total_files=10,
        total_chunks=5,
        total_size_bytes=1_000_000,
        estimated_input_tokens=100_000,
        estimated_output_tokens=10_000,
        estimated_cost_usd=0.50,
        estimated_duration_seconds=120.0,
        model="claude-3-5-sonnet-20241022",
    )

    # Convert to string
    str_repr = str(estimate)

    # Verify key info is present
    assert "10" in str_repr  # files
    assert "5" in str_repr  # chunks
    assert "$0.50" in str_repr  # cost
    assert "2.0 minutes" in str_repr  # duration
    assert "claude-3-5-sonnet-20241022" in str_repr  # model


def test_cost_estimator_token_estimation(tmp_path):
    """Test token estimation from text and files."""
    llm_config = LLMConfig()
    estimator = CostEstimator(llm_config)

    # Test text estimation
    text = "Hello world " * 100  # ~1200 characters
    tokens = estimator.estimate_tokens_from_text(text)
    assert tokens > 200  # Should be around 300 tokens (1200/4)
    assert tokens < 500

    # Test file estimation
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content " * 100)
    tokens = estimator.estimate_tokens_from_file(test_file)
    assert tokens > 200


def test_cost_estimator_model_pricing():
    """Test that different models use correct pricing."""
    llm_config = LLMConfig(model="claude-3-5-sonnet-20241022")
    estimator = CostEstimator(llm_config)

    # Check pricing is available
    assert "claude-3-5-sonnet-20241022" in CostEstimator.MODEL_PRICING
    pricing = CostEstimator.MODEL_PRICING["claude-3-5-sonnet-20241022"]
    assert pricing["input"] == 3.00  # $3 per million input tokens
    assert pricing["output"] == 15.00  # $15 per million output tokens


def test_cost_estimator_zero_files():
    """Test cost estimation with no files."""
    llm_config = LLMConfig()
    estimator = CostEstimator(llm_config)

    # Empty chunks list
    estimate = estimator.estimate_chunks([])

    assert estimate.total_files == 0
    assert estimate.total_chunks == 0
    assert estimate.total_size_bytes == 0
    assert estimate.estimated_input_tokens == 0
    assert estimate.estimated_output_tokens == 0
    assert estimate.estimated_cost_usd == 0
    assert estimate.estimated_duration_seconds == 0
