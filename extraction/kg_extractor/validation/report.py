"""Validation report generation."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from kg_extractor.models import ValidationError


class ValidationReport:
    """
    Validation report aggregating and formatting validation errors.

    Provides multiple export formats:
    - JSON: Structured data for programmatic analysis
    - Markdown: Human-readable summary
    - Text: Simple console output
    """

    def __init__(self, errors: list[ValidationError]):
        """
        Initialize validation report.

        Args:
            errors: List of validation errors to report
        """
        self.errors = errors
        self._analyze()

    def _analyze(self) -> None:
        """Analyze errors to compute statistics."""
        # Group by severity
        self.by_severity: dict[str, list[ValidationError]] = defaultdict(list)
        for error in self.errors:
            self.by_severity[error.severity].append(error)

        # Group by field
        self.by_field: dict[str, list[ValidationError]] = defaultdict(list)
        for error in self.errors:
            self.by_field[error.field].append(error)

        # Count unique entities with errors
        self.entity_ids_with_errors = {error.entity_id for error in self.errors}

        # Compute totals
        self.total_errors = len(self.errors)
        self.total_error_severity = len(self.by_severity.get("error", []))
        self.total_warning_severity = len(self.by_severity.get("warning", []))
        self.total_entities_with_errors = len(self.entity_ids_with_errors)

    def to_dict(self) -> dict[str, Any]:
        """
        Export report as dictionary.

        Returns:
            Report data as dict
        """
        return {
            "summary": {
                "total_issues": self.total_errors,
                "errors": self.total_error_severity,
                "warnings": self.total_warning_severity,
                "entities_affected": self.total_entities_with_errors,
            },
            "by_severity": {
                severity: [
                    {
                        "entity_id": e.entity_id,
                        "field": e.field,
                        "message": e.message,
                    }
                    for e in errors
                ]
                for severity, errors in self.by_severity.items()
            },
            "by_field": {field: len(errors) for field, errors in self.by_field.items()},
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Export report as JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """
        Export report as Markdown.

        Returns:
            Markdown string
        """
        lines = []

        # Header
        lines.append("# Validation Report")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Issues**: {self.total_errors}")
        lines.append(f"- **Errors**: {self.total_error_severity}")
        lines.append(f"- **Warnings**: {self.total_warning_severity}")
        lines.append(f"- **Entities Affected**: {self.total_entities_with_errors}")
        lines.append("")

        # By Severity
        if self.by_severity:
            lines.append("## Issues by Severity")
            lines.append("")

            for severity in ["error", "warning"]:
                if severity in self.by_severity:
                    errors = self.by_severity[severity]
                    lines.append(f"### {severity.upper()} ({len(errors)})")
                    lines.append("")

                    # Group by message for readability
                    by_message: dict[str, list[ValidationError]] = defaultdict(list)
                    for error in errors:
                        by_message[error.message].append(error)

                    for message, message_errors in sorted(by_message.items()):
                        lines.append(
                            f"**{message}** ({len(message_errors)} occurrences)"
                        )
                        lines.append("")
                        # Show first 5 entities
                        for error in message_errors[:5]:
                            lines.append(
                                f"- `{error.entity_id}` (field: `{error.field}`)"
                            )
                        if len(message_errors) > 5:
                            lines.append(f"- ... and {len(message_errors) - 5} more")
                        lines.append("")

        # By Field
        if self.by_field:
            lines.append("## Issues by Field")
            lines.append("")
            lines.append("| Field | Count |")
            lines.append("|-------|-------|")
            for field, errors in sorted(
                self.by_field.items(), key=lambda x: -len(x[1])
            ):
                lines.append(f"| `{field}` | {len(errors)} |")
            lines.append("")

        return "\n".join(lines)

    def to_text(self) -> str:
        """
        Export report as plain text.

        Returns:
            Text string for console output
        """
        lines = []

        lines.append("=" * 60)
        lines.append("VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append(f"Total Issues: {self.total_errors}")
        lines.append(f"  Errors: {self.total_error_severity}")
        lines.append(f"  Warnings: {self.total_warning_severity}")
        lines.append(f"Entities Affected: {self.total_entities_with_errors}")
        lines.append("=" * 60)

        if self.by_severity:
            for severity in ["error", "warning"]:
                if severity in self.by_severity:
                    errors = self.by_severity[severity]
                    lines.append(f"\n{severity.upper()}S ({len(errors)}):")
                    # Show first 10
                    for error in errors[:10]:
                        lines.append(
                            f"  {error.entity_id} [{error.field}]: {error.message}"
                        )
                    if len(errors) > 10:
                        lines.append(f"  ... and {len(errors) - 10} more")

        return "\n".join(lines)

    def save(self, path: Path, format: str = "json") -> None:
        """
        Save report to file.

        Args:
            path: Output file path
            format: Output format ('json', 'markdown', 'text')

        Raises:
            ValueError: If format is unknown
        """
        if format == "json":
            content = self.to_json()
        elif format == "markdown":
            content = self.to_markdown()
        elif format == "text":
            content = self.to_text()
        else:
            raise ValueError(f"Unknown format: {format}")

        path.write_text(content, encoding="utf-8")

    def print_summary(self) -> None:
        """Print summary to console."""
        print(self.to_text())
