"""Entity extraction agent using Agent SDK."""

from pathlib import Path
from typing import Any

from kg_extractor.exceptions import ExtractionError, PromptTooLongError
from kg_extractor.models import Entity, ExtractionResult, ValidationError
from kg_extractor.prompts.protocol import PromptLoader
from kg_extractor.validation.entity_validator import EntityValidator


class ExtractionAgent:
    """
    Entity extraction agent.

    Coordinates extraction workflow:
    1. Load and render prompt template
    2. Call LLM via Agent SDK
    3. Parse JSON response
    4. Validate entities
    5. Return extraction result
    """

    def __init__(
        self,
        llm_client: Any,  # LLMClient protocol
        prompt_loader: PromptLoader,
        validator: EntityValidator,
        prompt_name: str = "entity_extraction",
    ):
        """
        Initialize extraction agent.

        Args:
            llm_client: LLM client implementing LLMClient protocol
            prompt_loader: Prompt template loader
            validator: Entity validator
            prompt_name: Name of prompt template to use (default: entity_extraction)
        """
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.validator = validator
        self.prompt_name = prompt_name

    async def extract(
        self,
        files: list[Path],
        chunk_id: str = "chunk-001",
        schema_dir: Path | None = None,
        **kwargs: Any,
    ) -> ExtractionResult:
        """
        Extract entities from files.

        Args:
            files: List of files to extract from
            chunk_id: Identifier for the chunk being processed
            schema_dir: Optional schema directory for reference
            **kwargs: Additional variables for prompt rendering

        Returns:
            Extraction result with entities and validation errors

        Raises:
            ExtractionError: If extraction fails
        """
        # Load and render prompt template
        try:
            template = self.prompt_loader.load(self.prompt_name)
        except Exception as e:
            raise ExtractionError(f"Failed to load prompt template: {e}") from e

        # Prepare prompt variables
        prompt_vars = {
            "file_paths": files,
            "schema_dir": schema_dir,
        }

        # Render template
        try:
            system_prompt, user_prompt = template.render(**prompt_vars)
        except Exception as e:
            raise ExtractionError(f"Failed to render prompt template: {e}") from e

        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Extract event_callback if provided (for verbose mode)
        event_callback = kwargs.get("event_callback")

        # Call LLM with rendered prompt
        try:
            response = await self.llm_client.extract_entities(
                prompt=full_prompt,
                event_callback=event_callback,
            )
        except Exception as e:
            raise ExtractionError(f"LLM extraction failed: {e}") from e

        # Parse response
        entities, metadata = self._parse_response(response)

        # Validate entities
        validation_errors = self._validate_entities(entities)

        # Build result
        return ExtractionResult(
            entities=entities,
            chunk_id=chunk_id,
            validation_errors=validation_errors,
            metadata=metadata,
        )

    def _parse_response(
        self, response: dict[str, Any]
    ) -> tuple[list[Entity], dict[str, Any]]:
        """
        Parse LLM response into entities.

        Args:
            response: LLM response dict

        Returns:
            Tuple of (entities, metadata)

        Raises:
            ExtractionError: If response is invalid
        """
        if "entities" not in response:
            raise ExtractionError(
                f"Missing 'entities' field in LLM response: {response.keys()}"
            )

        entities_data = response["entities"]
        metadata = response.get("metadata", {})

        # Parse entities
        entities: list[Entity] = []
        for entity_dict in entities_data:
            try:
                # Try to create entity - validation happens here
                entity = Entity.from_dict(entity_dict)
                entities.append(entity)
            except Exception:
                # If Pydantic validation fails, try to create entity with model_construct
                # This allows us to create the entity for validation reporting
                try:
                    entity_id = entity_dict.get("@id", "unknown")
                    entity_type = entity_dict.get("@type", "Unknown")
                    name = entity_dict.get("name", "Unknown")
                    description = entity_dict.get("description")

                    reserved_keys = {"@id", "@type", "name", "description", "@context"}
                    properties = {
                        k: v for k, v in entity_dict.items() if k not in reserved_keys
                    }

                    # Use model_construct to bypass validation
                    entity = Entity.model_construct(
                        id=entity_id,
                        type=entity_type,
                        name=name,
                        description=description,
                        properties=properties,
                    )
                    entities.append(entity)
                except Exception:
                    # If even that fails, skip this entity
                    continue

        return entities, metadata

    def _validate_entities(self, entities: list[Entity]) -> list[ValidationError]:
        """
        Validate extracted entities.

        Args:
            entities: List of entities to validate

        Returns:
            List of validation errors
        """
        all_errors: list[ValidationError] = []

        for entity in entities:
            errors = self.validator.validate(entity)
            all_errors.extend(errors)

        return all_errors
