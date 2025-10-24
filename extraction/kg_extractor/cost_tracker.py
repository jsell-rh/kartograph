"""Track actual costs and improve estimates over time."""

from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime


@dataclass
class ActualCost:
    """Actual costs from an extraction run."""

    timestamp: str
    total_files: int
    total_chunks: int
    total_size_bytes: int
    actual_input_tokens: int
    actual_output_tokens: int
    actual_cost_usd: float
    actual_duration_seconds: float
    model: str

    # Estimated values (for comparison)
    estimated_input_tokens: int | None = None
    estimated_output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    estimated_duration_seconds: float | None = None

    @property
    def token_estimation_error(self) -> float | None:
        """Calculate % error in token estimation."""
        if self.estimated_input_tokens is None:
            return None
        if self.actual_input_tokens == 0:
            return None
        return (
            abs(self.estimated_input_tokens - self.actual_input_tokens)
            / self.actual_input_tokens
            * 100
        )

    @property
    def cost_estimation_error(self) -> float | None:
        """Calculate % error in cost estimation."""
        if self.estimated_cost_usd is None:
            return None
        if self.actual_cost_usd == 0:
            return None
        return (
            abs(self.estimated_cost_usd - self.actual_cost_usd)
            / self.actual_cost_usd
            * 100
        )

    @property
    def duration_estimation_error(self) -> float | None:
        """Calculate % error in duration estimation."""
        if self.estimated_duration_seconds is None:
            return None
        if self.actual_duration_seconds == 0:
            return None
        return (
            abs(self.estimated_duration_seconds - self.actual_duration_seconds)
            / self.actual_duration_seconds
            * 100
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "files": self.total_files,
            "chunks": self.total_chunks,
            "size_bytes": self.total_size_bytes,
            "model": self.model,
            "actual": {
                "input_tokens": self.actual_input_tokens,
                "output_tokens": self.actual_output_tokens,
                "cost_usd": self.actual_cost_usd,
                "duration_seconds": self.actual_duration_seconds,
            },
            "estimated": {
                "input_tokens": self.estimated_input_tokens,
                "output_tokens": self.estimated_output_tokens,
                "cost_usd": self.estimated_cost_usd,
                "duration_seconds": self.estimated_duration_seconds,
            },
            "error_percent": {
                "tokens": self.token_estimation_error,
                "cost": self.cost_estimation_error,
                "duration": self.duration_estimation_error,
            },
        }


class CostTracker:
    """Track and analyze actual costs over time."""

    def __init__(self, history_file: Path | None = None):
        """
        Initialize cost tracker.

        Args:
            history_file: Path to JSON file storing cost history
        """
        self.history_file = history_file or Path.home() / ".kg_extractor_costs.json"
        self.history: list[ActualCost] = []
        self._load_history()

    def _load_history(self) -> None:
        """Load cost history from file."""
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text())
                # Simple loading for now - could add proper deserialization
                self.history = data.get("runs", [])
            except Exception:
                # Corrupted file, start fresh
                self.history = []

    def record_run(self, actual: ActualCost) -> None:
        """Record an extraction run."""
        self.history.append(actual)
        self._save_history()

    def _save_history(self) -> None:
        """Save cost history to file."""
        try:
            data = {
                "runs": [
                    run.to_dict() if hasattr(run, "to_dict") else run
                    for run in self.history
                ],
                "last_updated": datetime.now().isoformat(),
            }
            self.history_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            # Don't fail extraction if we can't save history
            import logging

            logging.getLogger(__name__).warning(f"Failed to save cost history: {e}")

    def get_average_metrics(self, model: str | None = None) -> dict:
        """
        Get average metrics from history.

        Args:
            model: Filter by model (None = all models)

        Returns:
            Dictionary with average chars_per_token, output_ratio, etc.
        """
        if not self.history:
            return {}

        runs = self.history
        if model:
            runs = [r for r in runs if r.get("model") == model]

        if not runs:
            return {}

        # Calculate averages
        total_runs = len(runs)
        avg_chars_per_token = (
            sum(
                r.get("size_bytes", 0) / max(r["actual"].get("input_tokens", 1), 1)
                for r in runs
            )
            / total_runs
        )

        avg_output_ratio = (
            sum(
                r["actual"].get("output_tokens", 0)
                / max(r["actual"].get("input_tokens", 1), 1)
                for r in runs
            )
            / total_runs
        )

        avg_tokens_per_second = (
            sum(
                (
                    r["actual"].get("input_tokens", 0)
                    + r["actual"].get("output_tokens", 0)
                )
                / max(r["actual"].get("duration_seconds", 1), 1)
                for r in runs
            )
            / total_runs
        )

        return {
            "avg_chars_per_token": avg_chars_per_token,
            "avg_output_ratio": avg_output_ratio,
            "avg_tokens_per_second": avg_tokens_per_second,
            "sample_size": total_runs,
        }

    def print_comparison(self, actual: ActualCost) -> None:
        """Print estimated vs actual comparison."""
        print("\n" + "=" * 70)
        print("COST ESTIMATION ACCURACY")
        print("=" * 70)

        print(f"\n{'Metric':<25} {'Estimated':>15} {'Actual':>15} {'Error':>10}")
        print("-" * 70)

        # Tokens
        if actual.estimated_input_tokens:
            error = actual.token_estimation_error or 0
            print(
                f"{'Input Tokens':<25} {actual.estimated_input_tokens:>15,} "
                f"{actual.actual_input_tokens:>15,} {error:>9.1f}%"
            )

        if actual.estimated_output_tokens:
            print(
                f"{'Output Tokens':<25} {actual.estimated_output_tokens:>15,} "
                f"{actual.actual_output_tokens:>15,}"
            )

        # Cost
        if actual.estimated_cost_usd:
            error = actual.cost_estimation_error or 0
            print(
                f"{'Cost (USD)':<25} ${actual.estimated_cost_usd:>14.2f} "
                f"${actual.actual_cost_usd:>14.2f} {error:>9.1f}%"
            )

        # Duration
        if actual.estimated_duration_seconds:
            error = actual.duration_estimation_error or 0
            est_min = actual.estimated_duration_seconds / 60
            act_min = actual.actual_duration_seconds / 60
            print(
                f"{'Duration (minutes)':<25} {est_min:>15.1f} "
                f"{act_min:>15.1f} {error:>9.1f}%"
            )

        print("=" * 70)

        # Show improvement suggestions
        if actual.token_estimation_error and actual.token_estimation_error > 20:
            print(
                "\n⚠️  Token estimation is >20% off. Consider updating CHARS_PER_TOKEN constant."
            )

        if actual.cost_estimation_error and actual.cost_estimation_error > 15:
            print(
                "\n⚠️  Cost estimation is >15% off. Check model pricing or estimation logic."
            )
