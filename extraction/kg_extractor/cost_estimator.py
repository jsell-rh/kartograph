"""Cost estimation for LLM-based extraction."""

from dataclasses import dataclass
from pathlib import Path

from kg_extractor.chunking.models import Chunk
from kg_extractor.config import LLMConfig


@dataclass
class CostEstimate:
    """
    Cost estimate for extraction run.

    Provides detailed breakdown of expected costs and processing time.
    """

    total_files: int
    total_chunks: int
    total_size_bytes: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    estimated_duration_seconds: float
    model: str

    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"Cost Estimate Summary:\n"
            f"\n"
            f"⚠️  WARNING: These are ROUGH ESTIMATES based on heuristics.\n"
            f"    Actual costs may vary by 2-3x depending on:\n"
            f"    - File content and structure\n"
            f"    - Complexity of extraction\n"
            f"    - Number of relationships found\n"
            f"    - Tool calls and retries\n"
            f"\n"
            f"  Files: {self.total_files}\n"
            f"  Chunks: {self.total_chunks}\n"
            f"  Total Size: {self.total_size_bytes / (1024 * 1024):.2f} MB\n"
            f"  Estimated Input Tokens: {self.estimated_input_tokens:,}\n"
            f"  Estimated Output Tokens: {self.estimated_output_tokens:,}\n"
            f"  Estimated Cost: ${self.estimated_cost_usd:.2f}\n"
            f"  Estimated Duration: {self.estimated_duration_seconds / 60:.1f} minutes\n"
            f"  Model: {self.model}\n"
            f"\n"
            f"💡 Run with actual extraction to see real costs and improve estimates."
        )


class CostEstimator:
    """
    Estimate costs for LLM-based extraction.

    Provides token and cost estimates before running extraction.
    """

    # Token estimation constants
    # Average characters per token (rough estimate for English text)
    CHARS_PER_TOKEN = 4

    # Model pricing (per million tokens) - updated for Claude 3.5 Sonnet (2024-10-22)
    MODEL_PRICING = {
        "claude-3-5-sonnet-20241022": {
            "input": 3.00,  # $3 per million input tokens
            "output": 15.00,  # $15 per million output tokens
        },
        "claude-3-5-sonnet-latest": {
            "input": 3.00,
            "output": 15.00,
        },
        # Fallback for other models
        "default": {
            "input": 3.00,
            "output": 15.00,
        },
    }

    # Processing speed estimates (tokens per second)
    # Based on typical API throughput
    PROCESSING_SPEED = {
        "input_tokens_per_second": 1000,
        "output_tokens_per_second": 100,  # Output generation is slower
    }

    def __init__(self, llm_config: LLMConfig):
        """
        Initialize cost estimator.

        Args:
            llm_config: LLM configuration with model info
        """
        self.llm_config = llm_config
        self.model = llm_config.model

    def estimate_tokens_from_text(self, text: str) -> int:
        """
        Estimate token count from text.

        Uses character-based heuristic (4 chars per token for English).

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        return len(text) // self.CHARS_PER_TOKEN

    def estimate_tokens_from_file(self, file_path: Path) -> int:
        """
        Estimate token count from file.

        Args:
            file_path: Path to file

        Returns:
            Estimated token count
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return self.estimate_tokens_from_text(content)
        except Exception:
            # Fallback: estimate from file size (1 token per 4 bytes)
            return file_path.stat().st_size // self.CHARS_PER_TOKEN

    def estimate_chunk(self, chunk: Chunk) -> tuple[int, int]:
        """
        Estimate input and output tokens for a chunk.

        Args:
            chunk: Chunk to estimate

        Returns:
            Tuple of (input_tokens, output_tokens)
        """
        # Estimate input tokens from chunk files
        input_tokens = sum(self.estimate_tokens_from_file(file) for file in chunk.files)

        # Add overhead for prompt template (estimated ~2000 tokens)
        input_tokens += 2000

        # Estimate output tokens based on input size
        # Typical extraction produces ~10% of input as entities
        output_tokens = int(input_tokens * 0.1)

        return input_tokens, output_tokens

    def estimate_chunks(self, chunks: list[Chunk]) -> CostEstimate:
        """
        Estimate cost for processing chunks.

        Args:
            chunks: List of chunks to process

        Returns:
            CostEstimate with detailed breakdown
        """
        total_input_tokens = 0
        total_output_tokens = 0
        total_files = 0
        total_size = 0

        for chunk in chunks:
            input_tokens, output_tokens = self.estimate_chunk(chunk)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            total_files += len(chunk.files)
            total_size += chunk.total_size_bytes

        # Calculate cost
        pricing = self.MODEL_PRICING.get(self.model, self.MODEL_PRICING["default"])

        input_cost = (total_input_tokens / 1_000_000) * pricing["input"]
        output_cost = (total_output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        # Estimate duration (includes API latency, retries, etc.)
        # Conservative estimate: add 50% overhead for API latency
        input_time = (
            total_input_tokens / self.PROCESSING_SPEED["input_tokens_per_second"]
        )
        output_time = (
            total_output_tokens / self.PROCESSING_SPEED["output_tokens_per_second"]
        )
        estimated_duration = (input_time + output_time) * 1.5

        return CostEstimate(
            total_files=total_files,
            total_chunks=len(chunks),
            total_size_bytes=total_size,
            estimated_input_tokens=total_input_tokens,
            estimated_output_tokens=total_output_tokens,
            estimated_cost_usd=total_cost,
            estimated_duration_seconds=estimated_duration,
            model=self.model,
        )
