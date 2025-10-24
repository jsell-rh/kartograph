"""Entity validation implementation."""

import re
from typing import Any

from kg_extractor.config import ValidationConfig
from kg_extractor.models import Entity, ValidationError


def extract_urn_references(value: Any) -> set[str]:
    """
    Extract URN references from a value (could be dict, list, string, etc.).

    Args:
        value: Value to extract URNs from

    Returns:
        Set of URN strings found
    """
    urns = set()

    if isinstance(value, dict):
        # Check if this is a reference object {"@id": "urn:..."}
        if "@id" in value and isinstance(value["@id"], str):
            if value["@id"].startswith("urn:"):
                urns.add(value["@id"])
        # Recursively check all values
        for v in value.values():
            urns.update(extract_urn_references(v))
    elif isinstance(value, list):
        # Recursively check all list items
        for item in value:
            urns.update(extract_urn_references(item))
    elif isinstance(value, str):
        # Direct URN string
        if value.startswith("urn:"):
            urns.add(value)

    return urns


class EntityValidator:
    """
    Entity validator for knowledge graph extraction.

    Validates entities against configured rules:
    - Required fields (@id, @type, name, etc.)
    - URN format (urn:type:identifier)
    - Type name format (alphanumeric, starts with capital)
    """

    def __init__(self, config: ValidationConfig):
        """
        Initialize entity validator.

        Args:
            config: Validation configuration
        """
        self.config = config

    def validate(self, entity: Entity) -> list[ValidationError]:
        """
        Validate an Entity object.

        Args:
            entity: Entity to validate

        Returns:
            List of validation errors (empty if valid)
        """
        # Convert entity to dict for validation
        entity_dict = {
            "@id": entity.id,
            "@type": entity.type,
            "name": entity.name,
        }

        if entity.description:
            entity_dict["description"] = entity.description

        # Add properties
        entity_dict.update(entity.properties)

        return self.validate_dict(entity_dict)

    def validate_dict(self, entity_dict: dict[str, Any]) -> list[ValidationError]:
        """
        Validate an entity dictionary.

        Args:
            entity_dict: Entity as dictionary (with @id, @type, etc.)

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Get entity ID for error reporting
        entity_id = entity_dict.get("@id", "unknown")

        # Validate required fields
        errors.extend(self._validate_required_fields(entity_dict, entity_id))

        # Validate URN format
        if "@id" in entity_dict:
            errors.extend(self._validate_urn_format(entity_dict["@id"], entity_id))

        # Validate type name format
        if "@type" in entity_dict:
            errors.extend(self._validate_type_name(entity_dict["@type"], entity_id))

        return errors

    def _validate_required_fields(
        self, entity_dict: dict[str, Any], entity_id: str
    ) -> list[ValidationError]:
        """
        Validate required fields are present.

        Args:
            entity_dict: Entity dictionary
            entity_id: Entity ID for error reporting

        Returns:
            List of validation errors
        """
        errors = []

        for field in self.config.required_fields:
            if field not in entity_dict:
                # Special handling for name field
                if field == "name" and self.config.allow_missing_name:
                    # Allow missing name, but maybe warn
                    errors.append(
                        ValidationError(
                            entity_id=entity_id,
                            field=field,
                            message=f"Missing optional field: {field}",
                            severity="warning",
                        )
                    )
                else:
                    errors.append(
                        ValidationError(
                            entity_id=entity_id,
                            field=field,
                            message=f"Missing required field: {field}",
                            severity="error",
                        )
                    )

        return errors

    def _validate_urn_format(self, urn: str, entity_id: str) -> list[ValidationError]:
        """
        Validate URN format.

        Expected format: urn:type:identifier

        Args:
            urn: URN to validate
            entity_id: Entity ID for error reporting

        Returns:
            List of validation errors
        """
        errors = []

        if self.config.strict_urn_format:
            # Strict validation: must start with "urn:" and have at least 3 parts
            if not urn.startswith("urn:"):
                errors.append(
                    ValidationError(
                        entity_id=entity_id,
                        field="@id",
                        message="URN must start with 'urn:'",
                        severity="error",
                    )
                )

            parts = urn.split(":")
            if len(parts) < 3:
                errors.append(
                    ValidationError(
                        entity_id=entity_id,
                        field="@id",
                        message="URN must have format 'urn:type:identifier' (at least 3 parts)",
                        severity="error",
                    )
                )
        else:
            # Non-strict: just warn if it doesn't look like a URN
            if not urn.startswith("urn:") and ":" in urn:
                errors.append(
                    ValidationError(
                        entity_id=entity_id,
                        field="@id",
                        message="URN should preferably start with 'urn:'",
                        severity="warning",
                    )
                )

        return errors

    def _validate_type_name(
        self, type_name: str, entity_id: str
    ) -> list[ValidationError]:
        """
        Validate type name format.

        Type names should:
        - Start with capital letter
        - Be alphanumeric (or contain underscores)

        Args:
            type_name: Type name to validate
            entity_id: Entity ID for error reporting

        Returns:
            List of validation errors
        """
        errors = []

        if not type_name:
            errors.append(
                ValidationError(
                    entity_id=entity_id,
                    field="@type",
                    message="Type name cannot be empty",
                    severity="error",
                )
            )
            return errors

        # Check if starts with capital letter
        if not type_name[0].isupper():
            errors.append(
                ValidationError(
                    entity_id=entity_id,
                    field="@type",
                    message="Type name must start with capital letter",
                    severity="error",
                )
            )

        # Check if alphanumeric (allowing underscores)
        if not type_name.replace("_", "").isalnum():
            errors.append(
                ValidationError(
                    entity_id=entity_id,
                    field="@type",
                    message="Type name must be alphanumeric (or contain underscores)",
                    severity="error",
                )
            )

        return errors

    def validate_graph(self, entities: list[Entity]) -> list[ValidationError]:
        """
        Validate a complete graph of entities.

        Checks for:
        - Orphaned entities (no relationships to/from other entities)
        - Broken references (URNs that don't exist in graph)

        Args:
            entities: List of all entities in the graph

        Returns:
            List of validation errors
        """
        errors = []

        # Build entity ID set for reference checking
        entity_ids = {entity.id for entity in entities}

        # Check each entity
        for entity in entities:
            # Check for orphaned entities
            if self.config.detect_orphans:
                errors.extend(self._detect_orphaned_entity(entity, entity_ids))

            # Check for broken references
            if self.config.detect_broken_refs:
                errors.extend(self._detect_broken_references(entity, entity_ids))

        return errors

    def _detect_orphaned_entity(
        self, entity: Entity, all_entity_ids: set[str]
    ) -> list[ValidationError]:
        """
        Detect if entity has no relationships (orphaned).

        An entity is orphaned if:
        - It has no properties that reference other entities
        - No other entities reference it

        Args:
            entity: Entity to check
            all_entity_ids: Set of all entity IDs in graph

        Returns:
            List of validation errors
        """
        errors = []

        # Check if entity has any outgoing references
        entity_dict = entity.to_jsonld()
        referenced_urns = extract_urn_references(entity_dict)

        # Remove self-reference
        referenced_urns.discard(entity.id)

        # Filter to only URNs that exist in the graph
        outgoing_refs = referenced_urns & all_entity_ids

        # For now, just check outgoing references
        # Checking incoming would require scanning all entities which is expensive
        # We could add that as an optional check later
        if not outgoing_refs:
            errors.append(
                ValidationError(
                    entity_id=entity.id,
                    field="relationships",
                    message="Entity has no relationships to other entities (orphaned)",
                    severity="warning",
                )
            )

        return errors

    def _detect_broken_references(
        self, entity: Entity, all_entity_ids: set[str]
    ) -> list[ValidationError]:
        """
        Detect broken references (URNs that don't exist in graph).

        Args:
            entity: Entity to check
            all_entity_ids: Set of all entity IDs in graph

        Returns:
            List of validation errors
        """
        errors = []

        # Extract all URN references from entity
        entity_dict = entity.to_jsonld()
        referenced_urns = extract_urn_references(entity_dict)

        # Remove self-reference
        referenced_urns.discard(entity.id)

        # Find broken references (URNs that don't exist in graph)
        broken_refs = referenced_urns - all_entity_ids

        for broken_ref in broken_refs:
            errors.append(
                ValidationError(
                    entity_id=entity.id,
                    field="reference",
                    message=f"References non-existent entity: {broken_ref}",
                    severity="error",
                )
            )

        return errors
