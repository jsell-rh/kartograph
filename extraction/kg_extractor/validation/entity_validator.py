"""Entity validation implementation."""

import re
from typing import Any

from kg_extractor.config import ValidationConfig
from kg_extractor.models import Entity, ValidationError


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
