"""JSON-LD graph output for knowledge graph extraction."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from kg_extractor.models import Entity


class JSONLDContext(BaseModel):
    """
    JSON-LD context for namespace definitions.

    Provides vocabulary and namespace mappings for the graph.
    """

    context: dict[str, str] = Field(
        default={"@vocab": "http://schema.org/", "urn": "@id"},
        description="Context mappings for JSON-LD",
    )

    model_config = {"populate_by_name": True}


class JSONLDGraph(BaseModel):
    """
    Complete JSON-LD graph for output.

    Compatible with graph databases (Neo4j, Dgraph) and JSON-LD processors.
    Provides methods for building, saving, and loading knowledge graphs.
    """

    context: JSONLDContext = Field(
        default_factory=JSONLDContext,
        description="JSON-LD context",
    )
    graph: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Graph entities",
    )

    model_config = {"populate_by_name": True}

    def add_entity(self, entity: Entity) -> None:
        """
        Add single entity to graph.

        Args:
            entity: Entity to add
        """
        self.graph.append(entity.to_jsonld())

    def add_entities(self, entities: list[Entity]) -> None:
        """
        Add multiple entities to graph.

        Args:
            entities: List of entities to add
        """
        for entity in entities:
            self.add_entity(entity)

    def to_jsonld_string(self, indent: int = 2) -> str:
        """
        Export graph as JSON-LD string.

        Args:
            indent: Indentation level (0 for compact)

        Returns:
            JSON-LD string representation
        """
        data = {
            "@context": self.context.context,
            "@graph": self.graph,
        }
        return json.dumps(
            data, indent=indent if indent > 0 else None, ensure_ascii=False
        )

    def save(self, path: Path) -> None:
        """
        Save graph to file.

        Args:
            path: Output file path
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON-LD to file
        path.write_text(self.to_jsonld_string())

    @classmethod
    def load(cls, path: Path) -> "JSONLDGraph":
        """
        Load graph from file.

        Args:
            path: Input file path

        Returns:
            Loaded JSONLDGraph instance

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        data = json.loads(path.read_text())

        return cls(
            context=JSONLDContext(context=data.get("@context", {})),
            graph=data.get("@graph", []),
        )

    @property
    def entity_count(self) -> int:
        """Get number of entities in graph."""
        return len(self.graph)

    @property
    def types(self) -> set[str]:
        """
        Get all unique entity types in graph.

        Returns:
            Set of entity type names
        """
        return {e.get("@type", "Unknown") for e in self.graph}
