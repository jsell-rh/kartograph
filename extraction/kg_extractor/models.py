"""Core data models for knowledge graph extraction.

All models use Pydantic for validation and serialization.
"""

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Entity(BaseModel):
    """
    Represents a single entity in the knowledge graph.

    Entities are the core units of extracted knowledge, each with:
    - Unique URN identifier (urn:type:identifier)
    - Type classification (e.g., Service, APIEndpoint, Team)
    - Human-readable name
    - Optional description and custom properties
    """

    id: str = Field(
        description="Unique URN identifier (urn:type:identifier)",
    )
    type: str = Field(
        description="Entity type (must be alphanumeric, start with capital)",
    )
    name: str = Field(
        description="Human-readable name",
    )
    description: str | None = Field(
        default=None,
        description="Optional description",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional entity properties",
    )

    @field_validator("id")
    @classmethod
    def validate_urn_format(cls, v: str) -> str:
        """Validate URN format: urn:type:identifier."""
        if not v.startswith("urn:"):
            raise ValueError("URN must start with 'urn:'")

        parts = v.split(":")
        if len(parts) < 3:
            raise ValueError(
                "URN must have format 'urn:type:identifier' (at least 3 parts)"
            )

        return v

    @field_validator("type")
    @classmethod
    def validate_type_name(cls, v: str) -> str:
        """Validate type name is alphanumeric and starts with capital letter."""
        if not v:
            raise ValueError("Type name cannot be empty")

        if not v[0].isupper():
            raise ValueError("Type name must start with capital letter")

        if not v.replace("_", "").isalnum():
            raise ValueError("Type name must be alphanumeric (or contain underscores)")

        return v

    def _normalize_property_value(self, value: Any) -> Any:
        """
        Normalize property values to valid JSON-LD format.

        Converts entity references to proper {"@id": "urn:..."} format.
        Flattens nested lists and ensures consistent formatting.

        Args:
            value: Property value to normalize

        Returns:
            Normalized value
        """
        # Handle None
        if value is None:
            return None

        # Handle lists - flatten and normalize each item
        if isinstance(value, list):
            normalized_items = []
            for item in value:
                # Recursively normalize nested lists
                if isinstance(item, list):
                    # Flatten nested list
                    for nested_item in item:
                        norm = self._normalize_property_value(nested_item)
                        if norm is not None:
                            normalized_items.append(norm)
                else:
                    norm = self._normalize_property_value(item)
                    if norm is not None:
                        normalized_items.append(norm)
            return normalized_items if normalized_items else None

        # Handle entity references (dicts with @id)
        if isinstance(value, dict):
            if "@id" in value:
                # Already in correct format
                return value
            else:
                # Pass through non-reference dicts
                return value

        # Handle plain string URNs - convert to {"@id": "urn:..."}
        if isinstance(value, str) and value.startswith("urn:"):
            return {"@id": value}

        # Pass through other scalar values (strings, numbers, booleans)
        return value

    def to_jsonld(self) -> dict[str, Any]:
        """
        Convert entity to JSON-LD format.

        Returns a dictionary with @id, @type, and all properties.
        Normalizes all entity references to proper {"@id": "urn:..."} format.
        """
        jsonld: dict[str, Any] = {
            "@id": self.id,
            "@type": self.type,
            "name": self.name,
        }

        if self.description:
            jsonld["description"] = self.description

        # Add custom properties with normalization
        for key, value in self.properties.items():
            normalized = self._normalize_property_value(value)
            if normalized is not None:  # Skip None values
                jsonld[key] = normalized

        return jsonld

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        """
        Create Entity from dictionary (typically from JSON-LD).

        Expected keys: @id, @type, name, description (optional), and any custom properties.
        """
        # Extract known fields
        entity_id = data.get("@id")
        entity_type = data.get("@type")
        name = data.get("name")
        description = data.get("description")

        # Remaining fields become properties
        reserved_keys = {"@id", "@type", "name", "description", "@context"}
        properties = {k: v for k, v in data.items() if k not in reserved_keys}

        return cls(
            id=entity_id,
            type=entity_type,
            name=name,
            description=description,
            properties=properties,
        )


class ValidationError(BaseModel):
    """
    Represents a validation error encountered during extraction.

    Used to track issues with extracted entities without failing the entire extraction.
    """

    entity_id: str = Field(
        description="URN of the entity with validation error",
    )
    field: str = Field(
        description="Field name that failed validation",
    )
    message: str = Field(
        description="Human-readable error message",
    )
    severity: Literal["error", "warning", "info"] = Field(
        description="Error severity level",
    )


class ExtractionResult(BaseModel):
    """
    Result of extracting entities from a single chunk.

    Contains extracted entities, validation errors, and metadata about the extraction.
    """

    entities: list[Entity] = Field(
        description="Entities extracted from this chunk",
    )
    chunk_id: str = Field(
        description="Identifier for the chunk that was processed",
    )
    validation_errors: list[ValidationError] = Field(
        default_factory=list,
        description="Validation errors encountered",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (files processed, duration, etc.)",
    )

    def to_jsonld(self) -> dict[str, Any]:
        """
        Convert extraction result to JSON-LD graph format.

        Returns a JSON-LD document with @context and @graph containing all entities.
        """
        return {
            "@context": {
                "@vocab": "https://schema.org/",
            },
            "@graph": [entity.to_jsonld() for entity in self.entities],
        }


class ExtractionMetrics(BaseModel):
    """
    Metrics tracking extraction progress and performance.

    Used for monitoring, logging, and reporting extraction status.
    """

    total_chunks: int = Field(
        ge=0,
        description="Total number of chunks to process",
    )
    chunks_processed: int = Field(
        ge=0,
        description="Number of chunks successfully processed",
    )
    chunks_failed: int = Field(
        default=0,
        ge=0,
        description="Number of chunks that failed during processing",
    )
    chunks_skipped: int = Field(
        default=0,
        ge=0,
        description="Number of chunks skipped (from checkpoint resume)",
    )
    entities_extracted: int = Field(
        ge=0,
        description="Total entities extracted across all chunks",
    )
    validation_errors: int = Field(
        ge=0,
        description="Total validation errors encountered",
    )

    @property
    def chunks_attempted(self) -> int:
        """Total chunks attempted (successful + failed)."""
        return self.chunks_processed + self.chunks_failed

    @property
    def success_rate(self) -> float:
        """Chunk success rate (0.0 to 1.0)."""
        if self.chunks_attempted == 0:
            return 0.0
        return self.chunks_processed / self.chunks_attempted

    @property
    def failure_rate(self) -> float:
        """Chunk failure rate (0.0 to 1.0)."""
        return 1.0 - self.success_rate

    duration_seconds: float = Field(
        ge=0.0,
        description="Total extraction duration in seconds",
    )
    # Actual usage stats from LLM API
    actual_input_tokens: int = Field(
        default=0,
        ge=0,
        description="Actual input tokens consumed (from API)",
    )
    actual_output_tokens: int = Field(
        default=0,
        ge=0,
        description="Actual output tokens generated (from API)",
    )
    actual_cost_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Actual cost in USD (from API)",
    )

    @property
    def progress_percentage(self) -> float:
        """Calculate progress as percentage of chunks processed."""
        if self.total_chunks == 0:
            return 0.0
        return (self.chunks_processed / self.total_chunks) * 100.0

    @property
    def entities_per_second(self) -> float:
        """Calculate extraction rate (entities per second)."""
        if self.duration_seconds == 0.0:
            return 0.0
        return self.entities_extracted / self.duration_seconds
