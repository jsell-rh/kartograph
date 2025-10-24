"""Metrics export functionality."""

import csv
import json
from pathlib import Path
from typing import Any

from kg_extractor.models import ExtractionMetrics, Entity


class MetricsExporter:
    """
    Export extraction metrics to various formats.

    Supports:
    - JSON: Structured data for programmatic analysis
    - CSV: Tabular format for spreadsheets
    - Markdown: Human-readable summary
    """

    def __init__(
        self, metrics: ExtractionMetrics, entities: list[Entity] | None = None
    ):
        """
        Initialize metrics exporter.

        Args:
            metrics: Extraction metrics
            entities: Optional list of entities for additional stats
        """
        self.metrics = metrics
        self.entities = entities or []
        self._compute_stats()

    def _compute_stats(self) -> None:
        """Compute additional statistics from entities."""
        if self.entities:
            # Count entities by type
            self.entities_by_type: dict[str, int] = {}
            self.total_relationships = 0

            for entity in self.entities:
                # Count by type
                entity_type = entity.type
                self.entities_by_type[entity_type] = (
                    self.entities_by_type.get(entity_type, 0) + 1
                )

                # Count relationships (properties that reference other entities)
                entity_dict = entity.to_jsonld()
                for key, value in entity_dict.items():
                    if key.startswith("@"):
                        continue
                    if isinstance(value, dict) and "@id" in value:
                        self.total_relationships += 1
                    elif isinstance(value, list):
                        self.total_relationships += sum(
                            1
                            for item in value
                            if isinstance(item, dict) and "@id" in item
                        )
        else:
            self.entities_by_type = {}
            self.total_relationships = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Export metrics as dictionary.

        Returns:
            Metrics data as dict
        """
        result = {
            "extraction": {
                "total_chunks": self.metrics.total_chunks,
                "chunks_processed": self.metrics.chunks_processed,
                "entities_extracted": self.metrics.entities_extracted,
                "validation_errors": self.metrics.validation_errors,
                "duration_seconds": self.metrics.duration_seconds,
            },
            "performance": {
                "chunks_per_second": (
                    self.metrics.chunks_processed / self.metrics.duration_seconds
                    if self.metrics.duration_seconds > 0
                    else 0
                ),
                "entities_per_second": (
                    self.metrics.entities_extracted / self.metrics.duration_seconds
                    if self.metrics.duration_seconds > 0
                    else 0
                ),
            },
            "quality": {
                "validation_pass_rate": (
                    1.0
                    - (self.metrics.validation_errors / self.metrics.entities_extracted)
                    if self.metrics.entities_extracted > 0
                    else 1.0
                ),
                "relationships_per_entity": (
                    self.total_relationships / len(self.entities)
                    if len(self.entities) > 0
                    else 0
                ),
            },
        }

        if self.entities_by_type:
            result["entities_by_type"] = self.entities_by_type

        return result

    def to_json(self, indent: int = 2) -> str:
        """
        Export metrics as JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent)

    def to_csv(self) -> str:
        """
        Export metrics as CSV string.

        Returns:
            CSV string with metrics
        """
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Metric", "Value"])

        # Extraction metrics
        writer.writerow(["Total Chunks", self.metrics.total_chunks])
        writer.writerow(["Chunks Processed", self.metrics.chunks_processed])
        writer.writerow(["Entities Extracted", self.metrics.entities_extracted])
        writer.writerow(["Validation Errors", self.metrics.validation_errors])
        writer.writerow(["Duration (seconds)", f"{self.metrics.duration_seconds:.2f}"])

        # Performance metrics
        data = self.to_dict()
        writer.writerow(
            [
                "Chunks per Second",
                f"{data['performance']['chunks_per_second']:.2f}",
            ]
        )
        writer.writerow(
            [
                "Entities per Second",
                f"{data['performance']['entities_per_second']:.2f}",
            ]
        )

        # Quality metrics
        writer.writerow(
            [
                "Validation Pass Rate",
                f"{data['quality']['validation_pass_rate']:.2%}",
            ]
        )
        writer.writerow(
            [
                "Relationships per Entity",
                f"{data['quality']['relationships_per_entity']:.2f}",
            ]
        )

        # Entities by type
        if self.entities_by_type:
            writer.writerow([])  # Empty row
            writer.writerow(["Entity Type", "Count"])
            for entity_type, count in sorted(
                self.entities_by_type.items(), key=lambda x: -x[1]
            ):
                writer.writerow([entity_type, count])

        # Strip carriage returns for consistent cross-platform output
        return output.getvalue().replace("\r\n", "\n").replace("\r", "\n")

    def to_markdown(self) -> str:
        """
        Export metrics as Markdown.

        Returns:
            Markdown string
        """
        lines = []

        # Header
        lines.append("# Extraction Metrics")
        lines.append("")

        # Extraction Summary
        lines.append("## Extraction Summary")
        lines.append("")
        lines.append(f"- **Total Chunks**: {self.metrics.total_chunks}")
        lines.append(f"- **Chunks Processed**: {self.metrics.chunks_processed}")
        lines.append(f"- **Entities Extracted**: {self.metrics.entities_extracted}")
        lines.append(f"- **Validation Errors**: {self.metrics.validation_errors}")
        lines.append(
            f"- **Duration**: {self.metrics.duration_seconds:.2f}s ({self.metrics.duration_seconds / 60:.1f}m)"
        )
        lines.append("")

        # Performance
        data = self.to_dict()
        lines.append("## Performance")
        lines.append("")
        lines.append(
            f"- **Chunks/sec**: {data['performance']['chunks_per_second']:.2f}"
        )
        lines.append(
            f"- **Entities/sec**: {data['performance']['entities_per_second']:.2f}"
        )
        lines.append("")

        # Quality
        lines.append("## Quality")
        lines.append("")
        lines.append(
            f"- **Validation Pass Rate**: {data['quality']['validation_pass_rate']:.1%}"
        )
        lines.append(
            f"- **Relationships per Entity**: {data['quality']['relationships_per_entity']:.2f}"
        )
        lines.append("")

        # Entities by Type
        if self.entities_by_type:
            lines.append("## Entities by Type")
            lines.append("")
            lines.append("| Type | Count | Percentage |")
            lines.append("|------|-------|------------|")
            total = sum(self.entities_by_type.values())
            for entity_type, count in sorted(
                self.entities_by_type.items(), key=lambda x: -x[1]
            ):
                percentage = (count / total * 100) if total > 0 else 0
                lines.append(f"| `{entity_type}` | {count} | {percentage:.1f}% |")
            lines.append("")

        return "\n".join(lines)

    def save(self, path: Path, format: str = "json") -> None:
        """
        Save metrics to file.

        Args:
            path: Output file path
            format: Output format ('json', 'csv', 'markdown')

        Raises:
            ValueError: If format is unknown
        """
        if format == "json":
            content = self.to_json()
        elif format == "csv":
            content = self.to_csv()
        elif format == "markdown":
            content = self.to_markdown()
        else:
            raise ValueError(f"Unknown format: {format}")

        path.write_text(content, encoding="utf-8")

    def print_summary(self) -> None:
        """Print summary to console."""
        print("=" * 60)
        print("EXTRACTION METRICS")
        print("=" * 60)
        print(f"Entities Extracted: {self.metrics.entities_extracted}")
        print(f"Chunks Processed: {self.metrics.chunks_processed}")
        print(f"Duration: {self.metrics.duration_seconds:.2f}s")
        print(f"Validation Errors: {self.metrics.validation_errors}")

        data = self.to_dict()
        print(f"Validation Pass Rate: {data['quality']['validation_pass_rate']:.1%}")
        print(
            f"Relationships/Entity: {data['quality']['relationships_per_entity']:.2f}"
        )
        print("=" * 60)
