"""Agent-based deduplication using LLM for consistency checking."""

import logging
from pathlib import Path

from anthropic import Anthropic
from pydantic import ValidationError

from kg_extractor.config import AuthConfig, DeduplicationConfig
from kg_extractor.deduplication.models import (
    DeduplicationAnalysis,
    DeduplicationMetrics,
    DeduplicationResult,
)
from kg_extractor.models import Entity
from kg_extractor.prompts.loader import DiskPromptLoader

logger = logging.getLogger(__name__)


class AgentBasedDeduplicator:
    """
    LLM-powered deduplication with type normalization.

    Uses Claude with structured outputs to:
    - Normalize entity type names
    - Detect semantic duplicates
    - Fix relationship inconsistencies
    """

    def __init__(
        self,
        config: DeduplicationConfig,
        auth_config: AuthConfig,
        prompt_loader: DiskPromptLoader | None = None,
    ):
        """
        Initialize agent-based deduplicator.

        Args:
            config: Deduplication configuration
            auth_config: Authentication configuration
            prompt_loader: Optional prompt loader (created if not provided)
        """
        self.config = config
        self.auth_config = auth_config

        # Create prompt loader if not provided
        if prompt_loader is None:
            prompt_loader = DiskPromptLoader(
                template_dir=Path(__file__).parent.parent / "prompts" / "templates"
            )
        self.prompt_loader = prompt_loader

        # Create Anthropic client
        if auth_config.auth_method == "api_key":
            self.client = Anthropic(api_key=auth_config.api_key)
        else:
            # Vertex AI
            try:
                from anthropic.vertex import AnthropicVertex
            except ImportError as e:
                raise ImportError(
                    "Vertex AI support requires the anthropic[vertex] extra. "
                    "Install with: pip install 'anthropic[vertex]' google-cloud-aiplatform\n"
                    "Or use API key auth with: --auth-method=api_key --api-key=<your-key>"
                ) from e

            self.client = AnthropicVertex(
                project_id=auth_config.vertex_project_id,
                region=auth_config.vertex_region,
            )

    def deduplicate(self, entities: list[Entity]) -> DeduplicationResult:
        """
        Deduplicate entities using LLM analysis.

        Args:
            entities: List of entities to deduplicate

        Returns:
            DeduplicationResult with deduplicated entities and metrics
        """
        if not entities:
            return DeduplicationResult(
                entities=[],
                metrics=DeduplicationMetrics(
                    total_input_entities=0,
                    total_output_entities=0,
                    duplicates_found=0,
                    duplicates_merged=0,
                    merge_operations=0,
                ),
            )

        logger.info(f"Starting agent-based deduplication of {len(entities)} entities")

        # 1. Analyze type variations
        type_summary = self._build_type_summary(entities)
        logger.info(f"Detected {len(type_summary)} base types with variations")

        # 2. Load and render prompt
        template = self.prompt_loader.load("deduplication")
        system_prompt, user_prompt = template.render(
            entity_count=len(entities),
            type_summary=type_summary,
        )

        # 3. Call LLM with structured output
        logger.info("Calling LLM for deduplication analysis...")
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-5@20250929",
                max_tokens=8000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                # Use JSON mode for structured output
                # Note: Anthropic's structured output feature might have different API
                # For now, we'll rely on the prompt to return valid JSON
            )

            # Parse response content
            response_text = response.content[0].text

            # 4. Parse structured response
            try:
                analysis = DeduplicationAnalysis.model_validate_json(response_text)
            except ValidationError as e:
                logger.error(f"Failed to parse deduplication analysis: {e}")
                # Fall back to no changes
                analysis = DeduplicationAnalysis(
                    type_normalizations=[],
                    duplicate_groups=[],
                    urn_corrections=[],
                    summary="Failed to parse LLM response, no changes applied",
                )

            logger.info(f"Analysis summary: {analysis.summary}")
            logger.info(f"  - {len(analysis.type_normalizations)} type normalizations")
            logger.info(f"  - {len(analysis.duplicate_groups)} duplicate groups")
            logger.info(f"  - {len(analysis.urn_corrections)} URN corrections")

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Fall back to no changes
            analysis = DeduplicationAnalysis(
                type_normalizations=[],
                duplicate_groups=[],
                urn_corrections=[],
                summary=f"LLM call failed: {e}",
            )

        # 5. Apply normalizations and merges
        normalized_entities = self._apply_normalizations(entities, analysis)
        deduplicated_entities = self._apply_merges(normalized_entities, analysis)
        corrected_entities = self._apply_corrections(deduplicated_entities, analysis)

        # 6. Build metrics
        metrics = DeduplicationMetrics(
            total_input_entities=len(entities),
            total_output_entities=len(corrected_entities),
            duplicates_found=sum(
                len(g.duplicate_urns) for g in analysis.duplicate_groups
            ),
            duplicates_merged=sum(
                len(g.duplicate_urns) for g in analysis.duplicate_groups
            ),
            merge_operations=len(analysis.duplicate_groups),
        )

        logger.info(
            f"Deduplication complete: {metrics.total_input_entities} → "
            f"{metrics.total_output_entities} entities"
        )

        return DeduplicationResult(
            entities=corrected_entities,
            metrics=metrics,
        )

    def _build_type_summary(self, entities: list[Entity]) -> dict[str, list[str]]:
        """Build summary of type variations."""
        type_variations: dict[str, set[str]] = {}
        for entity in entities:
            base_type = entity.type.lower()
            if base_type not in type_variations:
                type_variations[base_type] = set()
            type_variations[base_type].add(entity.type)

        # Convert sets to sorted lists
        return {
            base: sorted(variations) for base, variations in type_variations.items()
        }

    def _apply_normalizations(
        self, entities: list[Entity], analysis: DeduplicationAnalysis
    ) -> list[Entity]:
        """Apply type normalizations."""
        # Build normalization map
        norm_map = {
            n.original_type: n.canonical_type for n in analysis.type_normalizations
        }

        if norm_map:
            logger.info(f"Applying {len(norm_map)} type normalizations")

            # Show first 5 normalizations with example entity names
            normalizations_shown = 0
            for orig, canonical in norm_map.items():
                if normalizations_shown >= 5:
                    break
                # Find an example entity with this type
                example_entity = next((e for e in entities if e.type == orig), None)
                if example_entity:
                    logger.debug(
                        f"  {orig} → {canonical} (e.g., '{example_entity.name}')"
                    )
                else:
                    logger.debug(f"  {orig} → {canonical}")
                normalizations_shown += 1

            if len(norm_map) > 5:
                logger.debug(f"  ... and {len(norm_map) - 5} more normalizations")

        normalized = []
        for entity in entities:
            if entity.type in norm_map:
                canonical = norm_map[entity.type]
                # Create new entity with normalized type and URN
                new_urn = entity.id.replace(f"urn:{entity.type}:", f"urn:{canonical}:")
                normalized.append(
                    Entity(
                        id=new_urn,
                        type=canonical,
                        name=entity.name,
                        description=entity.description,
                        properties=entity.properties,
                    )
                )
            else:
                normalized.append(entity)

        return normalized

    def _apply_merges(
        self, entities: list[Entity], analysis: DeduplicationAnalysis
    ) -> list[Entity]:
        """Apply duplicate merges."""
        # Build entity lookup for detailed logging
        entity_lookup = {e.id: e for e in entities}

        # Build URN mapping (duplicate -> primary)
        urn_map = {}
        for group in analysis.duplicate_groups:
            if group.confidence >= self.config.agent_similarity_threshold:
                for dup_urn in group.duplicate_urns:
                    urn_map[dup_urn] = group.primary_urn
            else:
                logger.debug(
                    f"Skipping duplicate group (confidence {group.confidence} "
                    f"< threshold {self.config.agent_similarity_threshold}): "
                    f"{group.primary_urn}"
                )

        if urn_map:
            logger.info(f"Merging {len(urn_map)} duplicate entities")
            # Show first few merges with entity names
            for dup_urn, primary_urn in list(urn_map.items())[:3]:
                dup_entity = entity_lookup.get(dup_urn)
                primary_entity = entity_lookup.get(primary_urn)
                dup_name = dup_entity.name if dup_entity else "unknown"
                primary_name = primary_entity.name if primary_entity else "unknown"
                logger.debug(
                    f"  Merging: {dup_entity.type if dup_entity else '?'}:'{dup_name}' ({dup_urn}) "
                    f"→ {primary_entity.type if primary_entity else '?'}:'{primary_name}' ({primary_urn})"
                )
            if len(urn_map) > 3:
                logger.debug(f"  ... and {len(urn_map) - 3} more merges")

        # Group entities by resolved URN
        entity_groups: dict[str, list[Entity]] = {}
        for entity in entities:
            resolved_urn = urn_map.get(entity.id, entity.id)
            if resolved_urn not in entity_groups:
                entity_groups[resolved_urn] = []
            entity_groups[resolved_urn].append(entity)

        # Merge each group
        merged = []
        for urn, group in entity_groups.items():
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Merge properties from all entities in group
                merged.append(self._merge_entities(group))

        return merged

    def _merge_entities(self, entities: list[Entity]) -> Entity:
        """Merge multiple entities (same logic as URN deduplicator)."""
        # Use first entity as base
        base = entities[0]
        merged_props = dict(base.properties)

        for entity in entities[1:]:
            for key, value in entity.properties.items():
                if key not in merged_props:
                    merged_props[key] = value
                elif merged_props[key] != value:
                    # Conflict - collect into list
                    if isinstance(merged_props[key], list):
                        if value not in merged_props[key]:
                            merged_props[key].append(value)
                    else:
                        merged_props[key] = [merged_props[key], value]

        return Entity(
            id=base.id,
            type=base.type,
            name=base.name,
            description=base.description,
            properties=merged_props,
        )

    def _apply_corrections(
        self, entities: list[Entity], analysis: DeduplicationAnalysis
    ) -> list[Entity]:
        """Apply URN reference corrections."""
        # Build correction map
        corrections = {}
        for corr in analysis.urn_corrections:
            key = (corr.entity_urn, corr.predicate, corr.old_reference)
            corrections[key] = corr.new_reference

        if corrections:
            logger.info(f"Applying {len(corrections)} URN corrections")
            # Show first few corrections
            for (entity_urn, pred, old_ref), new_ref in list(corrections.items())[:3]:
                logger.debug(f"  {entity_urn}.{pred}: {old_ref} → {new_ref}")
            if len(corrections) > 3:
                logger.debug(f"  ... and {len(corrections) - 3} more corrections")

        # Apply corrections
        corrected = []
        for entity in entities:
            corrected_props = dict(entity.properties)

            for pred_name, pred_value in entity.properties.items():
                # Handle single reference
                if isinstance(pred_value, dict) and "@id" in pred_value:
                    key = (entity.id, pred_name, pred_value["@id"])
                    if key in corrections:
                        corrected_props[pred_name] = {"@id": corrections[key]}

                # Handle array of references
                elif isinstance(pred_value, list):
                    corrected_list = []
                    for item in pred_value:
                        if isinstance(item, dict) and "@id" in item:
                            key = (entity.id, pred_name, item["@id"])
                            if key in corrections:
                                corrected_list.append({"@id": corrections[key]})
                            else:
                                corrected_list.append(item)
                        else:
                            corrected_list.append(item)
                    corrected_props[pred_name] = corrected_list

            corrected.append(
                Entity(
                    id=entity.id,
                    type=entity.type,
                    name=entity.name,
                    description=entity.description,
                    properties=corrected_props,
                )
            )

        return corrected
