# Contract: Deduplication Strategy Interface

## Purpose

Defines the boundary around entity deduplication to enable:

- **Swappable strategies** (URN-based, agent-based, hybrid)
- **Testing** with mock implementations
- **Performance comparison** between strategies
- **Incremental improvements** without breaking existing code
- **Clear separation** between deduplication logic and orchestration

## Interface Definition

### Core Protocol

```python
from typing import Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class DeduplicationResult:
    """Result of deduplication operation."""
    entities: list[dict]  # Deduplicated entities
    duplicates_found: int  # Number of duplicates detected
    duplicates_merged: int  # Number of duplicates merged
    unique_entities: int  # Number of unique entities

    @property
    def deduplication_rate(self) -> float:
        """Calculate deduplication rate."""
        total = self.unique_entities + self.duplicates_found
        if total == 0:
            return 0.0
        return self.duplicates_found / total


class DeduplicationStrategy(Protocol):
    """
    Abstract interface for deduplication strategies.

    This protocol defines the boundary around deduplication logic, enabling:
    - Swapping between different strategies
    - Testing with mock implementations
    - Performance benchmarking
    - Incremental improvements
    """

    async def deduplicate(
        self,
        new_entities: list[dict],
        existing_entities: list[dict],
    ) -> DeduplicationResult:
        """
        Deduplicate new entities against existing ones.

        Args:
            new_entities: Entities from current extraction
            existing_entities: Entities from previous extractions

        Returns:
            Deduplication result with merged entities

        Raises:
            DeduplicationError: Failed to deduplicate
        """
        ...

    def get_metrics(self) -> dict:
        """
        Get strategy-specific metrics.

        Returns:
            Dictionary of metrics (e.g., comparisons_made, llm_calls)
        """
        ...

    def reset_metrics(self) -> None:
        """Reset metrics to zero."""
        ...


class DeduplicationError(Exception):
    """Base class for deduplication errors."""
    pass
```

## Implementations

### URN-Based Deduplication

```python
from typing import Literal

class URNBasedDeduplication:
    """
    Simple URN-based deduplication with configurable merge strategy.

    Fast, deterministic deduplication based on @id field.
    """

    def __init__(
        self,
        merge_strategy: Literal["first", "last", "merge_predicates"] = "merge_predicates",
    ):
        """
        Args:
            merge_strategy:
                - "first": Keep first entity encountered
                - "last": Keep last entity encountered (overwrite)
                - "merge_predicates": Merge fields from both entities
        """
        self.merge_strategy = merge_strategy
        self._comparisons_made = 0
        self._duplicates_found = 0

    async def deduplicate(
        self,
        new_entities: list[dict],
        existing_entities: list[dict],
    ) -> DeduplicationResult:
        """Deduplicate based on URN (@id field)."""
        # Build URN index from existing entities
        by_urn: dict[str, dict] = {
            e["@id"]: e for e in existing_entities
        }

        duplicates_found = 0
        duplicates_merged = 0

        for entity in new_entities:
            self._comparisons_made += 1
            urn = entity["@id"]

            if urn not in by_urn:
                # New unique entity
                by_urn[urn] = entity
            else:
                # Duplicate found
                duplicates_found += 1
                self._duplicates_found += 1

                # Merge according to strategy
                if self.merge_strategy == "first":
                    # Keep existing, ignore new
                    pass
                elif self.merge_strategy == "last":
                    # Replace with new
                    by_urn[urn] = entity
                    duplicates_merged += 1
                elif self.merge_strategy == "merge_predicates":
                    # Merge predicates from both
                    by_urn[urn] = self._merge_predicates(by_urn[urn], entity)
                    duplicates_merged += 1

        entities = list(by_urn.values())

        return DeduplicationResult(
            entities=entities,
            duplicates_found=duplicates_found,
            duplicates_merged=duplicates_merged,
            unique_entities=len(entities),
        )

    def _merge_predicates(self, existing: dict, new: dict) -> dict:
        """
        Merge predicates from both entities.

        Strategy:
        - Keep @id and @type from existing (identity fields)
        - For scalars: prefer new value (more recent)
        - For arrays: merge and deduplicate
        - For objects: prefer new value
        """
        merged = existing.copy()

        for key, value in new.items():
            # Don't merge identity fields
            if key in ["@id", "@type"]:
                continue

            if key not in merged:
                # New field
                merged[key] = value
            elif isinstance(value, list):
                # Merge arrays
                existing_values = merged[key] if isinstance(merged[key], list) else [merged[key]]
                # Deduplicate based on value equality
                for v in value:
                    if v not in existing_values:
                        existing_values.append(v)
                merged[key] = existing_values
            else:
                # For scalars/objects, prefer new value (more recent)
                merged[key] = value

        return merged

    def get_metrics(self) -> dict:
        """Get metrics."""
        return {
            "strategy": "urn_based",
            "merge_strategy": self.merge_strategy,
            "comparisons_made": self._comparisons_made,
            "duplicates_found": self._duplicates_found,
        }

    def reset_metrics(self) -> None:
        """Reset metrics."""
        self._comparisons_made = 0
        self._duplicates_found = 0
```

### Agent-Based Semantic Deduplication

```python
from kg_extractor.llm import LLMClient, LLMRequest
from pydantic import BaseModel

class SimilarityMatch(BaseModel):
    """Result of semantic similarity comparison."""
    is_duplicate: bool
    confidence: float  # 0.0-1.0
    reason: str

class AgentBasedDeduplication:
    """
    Agent-powered semantic deduplication.

    Uses LLM to detect semantic duplicates that have different URNs.
    Slower but more accurate for ambiguous cases.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        similarity_threshold: float = 0.85,
        batch_size: int = 10,
    ):
        """
        Args:
            llm_client: LLM client for semantic comparison
            similarity_threshold: Minimum confidence to merge (0.0-1.0)
            batch_size: Number of comparisons per LLM call
        """
        self.llm = llm_client
        self.threshold = similarity_threshold
        self.batch_size = batch_size
        self._llm_calls = 0
        self._comparisons_made = 0

    async def deduplicate(
        self,
        new_entities: list[dict],
        existing_entities: list[dict],
    ) -> DeduplicationResult:
        """Deduplicate using semantic similarity."""
        # First pass: URN-based deduplication (fast path)
        urn_dedup = URNBasedDeduplication(merge_strategy="merge_predicates")
        urn_result = await urn_dedup.deduplicate(new_entities, existing_entities)

        # Second pass: semantic comparison for potential duplicates
        # Compare entities with different URNs but similar types
        by_type: dict[str, list[dict]] = {}
        for entity in urn_result.entities:
            entity_type = entity.get("@type", "Unknown")
            by_type.setdefault(entity_type, []).append(entity)

        # Compare entities within same type
        semantic_duplicates = 0
        final_entities = []

        for entity_type, entities in by_type.items():
            if len(entities) <= 1:
                final_entities.extend(entities)
                continue

            # Compare pairs
            merged_urns = set()
            entity_map = {e["@id"]: e for e in entities}

            for i, entity1 in enumerate(entities):
                if entity1["@id"] in merged_urns:
                    continue

                for entity2 in entities[i+1:]:
                    if entity2["@id"] in merged_urns:
                        continue

                    # Compare semantically
                    match = await self._compare_entities(entity1, entity2)
                    self._comparisons_made += 1

                    if match.is_duplicate and match.confidence >= self.threshold:
                        # Merge entity2 into entity1
                        entity_map[entity1["@id"]] = self._merge_entities(
                            entity1, entity2
                        )
                        merged_urns.add(entity2["@id"])
                        semantic_duplicates += 1

            # Add non-merged entities
            for urn, entity in entity_map.items():
                if urn not in merged_urns:
                    final_entities.append(entity)

        return DeduplicationResult(
            entities=final_entities,
            duplicates_found=urn_result.duplicates_found + semantic_duplicates,
            duplicates_merged=urn_result.duplicates_merged + semantic_duplicates,
            unique_entities=len(final_entities),
        )

    async def _compare_entities(
        self,
        entity1: dict,
        entity2: dict,
    ) -> SimilarityMatch:
        """Compare two entities for semantic similarity."""
        self._llm_calls += 1

        request = LLMRequest(
            system_prompt="""You are an expert at determining if two entities represent the same real-world thing.

Compare the entities and determine if they are duplicates (same entity with different representations).

Return JSON:
{
  "is_duplicate": true/false,
  "confidence": 0.0-1.0,
  "reason": "explanation"
}""",
            user_prompt=f"""Entity 1:
{json.dumps(entity1, indent=2)}

Entity 2:
{json.dumps(entity2, indent=2)}

Are these the same entity?""",
            temperature=0.0,  # Deterministic
        )

        parsed, _ = await self.llm.query_structured(request, SimilarityMatch)
        return parsed

    def _merge_entities(self, entity1: dict, entity2: dict) -> dict:
        """Merge two semantically duplicate entities."""
        # Use same merge logic as URN-based
        urn_dedup = URNBasedDeduplication()
        return urn_dedup._merge_predicates(entity1, entity2)

    def get_metrics(self) -> dict:
        """Get metrics."""
        return {
            "strategy": "agent_based",
            "similarity_threshold": self.threshold,
            "llm_calls": self._llm_calls,
            "comparisons_made": self._comparisons_made,
        }

    def reset_metrics(self) -> None:
        """Reset metrics."""
        self._llm_calls = 0
        self._comparisons_made = 0
```

### Hybrid Deduplication

```python
class HybridDeduplication:
    """
    Hybrid strategy: URN-based for obvious cases, agent-based for ambiguous.

    Combines speed of URN-based with accuracy of agent-based.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        similarity_threshold: float = 0.85,
        use_agent_for_same_type: bool = True,
    ):
        """
        Args:
            llm_client: LLM client for semantic comparison
            similarity_threshold: Minimum confidence to merge
            use_agent_for_same_type: Use agent for entities of same type
        """
        self.urn_strategy = URNBasedDeduplication(merge_strategy="merge_predicates")
        self.agent_strategy = AgentBasedDeduplication(
            llm_client=llm_client,
            similarity_threshold=similarity_threshold,
        )
        self.use_agent_for_same_type = use_agent_for_same_type

    async def deduplicate(
        self,
        new_entities: list[dict],
        existing_entities: list[dict],
    ) -> DeduplicationResult:
        """Deduplicate using hybrid approach."""
        # Fast path: URN-based
        urn_result = await self.urn_strategy.deduplicate(
            new_entities, existing_entities
        )

        # Slow path: Agent-based for same-type entities
        if self.use_agent_for_same_type:
            agent_result = await self.agent_strategy.deduplicate(
                urn_result.entities, []
            )
            return agent_result
        else:
            return urn_result

    def get_metrics(self) -> dict:
        """Get combined metrics."""
        return {
            "strategy": "hybrid",
            "urn_metrics": self.urn_strategy.get_metrics(),
            "agent_metrics": self.agent_strategy.get_metrics(),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.urn_strategy.reset_metrics()
        self.agent_strategy.reset_metrics()
```

### No-Op Deduplication (Testing)

```python
class NoOpDeduplication:
    """
    No-op deduplication for testing.

    Simply concatenates entities without any deduplication.
    """

    async def deduplicate(
        self,
        new_entities: list[dict],
        existing_entities: list[dict],
    ) -> DeduplicationResult:
        """Return all entities without deduplication."""
        all_entities = existing_entities + new_entities

        return DeduplicationResult(
            entities=all_entities,
            duplicates_found=0,
            duplicates_merged=0,
            unique_entities=len(all_entities),
        )

    def get_metrics(self) -> dict:
        """Get metrics."""
        return {"strategy": "noop"}

    def reset_metrics(self) -> None:
        """Reset metrics."""
        pass
```

## Usage Examples

### Basic Usage

```python
from kg_extractor.deduplication import URNBasedDeduplication

# Create strategy
dedup = URNBasedDeduplication(merge_strategy="merge_predicates")

# Deduplicate
result = await dedup.deduplicate(
    new_entities=[
        {"@id": "urn:service:foo", "@type": "Service", "name": "Foo", "version": "2.0"},
    ],
    existing_entities=[
        {"@id": "urn:service:foo", "@type": "Service", "name": "Foo", "version": "1.0"},
    ],
)

# Check results
assert result.duplicates_found == 1
assert result.unique_entities == 1
assert result.entities[0]["version"] == "2.0"  # Newer value
```

### Dependency Injection

```python
class ExtractionOrchestrator:
    """Orchestrator with injected deduplication strategy."""

    def __init__(
        self,
        deduplication_strategy: DeduplicationStrategy,
        ...
    ):
        self.dedup = deduplication_strategy

    async def extract_chunk(self, chunk: Chunk) -> list[dict]:
        """Extract and deduplicate chunk."""
        # Extract entities
        new_entities = await self.extract_entities(chunk)

        # Deduplicate against existing
        result = await self.dedup.deduplicate(new_entities, self.all_entities)

        self.all_entities = result.entities
        return result.entities
```

### Strategy Selection

```python
from kg_extractor.config import ExtractionConfig
from kg_extractor.deduplication import (
    URNBasedDeduplication,
    AgentBasedDeduplication,
    HybridDeduplication,
)

def create_deduplication_strategy(
    config: ExtractionConfig,
    llm_client: LLMClient,
) -> DeduplicationStrategy:
    """Factory function to create deduplication strategy."""
    if config.deduplication.strategy == "urn":
        return URNBasedDeduplication(
            merge_strategy=config.deduplication.urn_merge_strategy,
        )
    elif config.deduplication.strategy == "agent":
        return AgentBasedDeduplication(
            llm_client=llm_client,
            similarity_threshold=config.deduplication.agent_similarity_threshold,
        )
    elif config.deduplication.strategy == "hybrid":
        return HybridDeduplication(
            llm_client=llm_client,
            similarity_threshold=config.deduplication.agent_similarity_threshold,
        )
    else:
        raise ValueError(f"Unknown strategy: {config.deduplication.strategy}")
```

## Design Rationale

### Why Async Interface?

**Future-Proofing**:

- Agent-based deduplication requires async LLM calls
- URN-based can be sync, but async is compatible
- Consistent interface across all strategies
- Enables parallel deduplication in future

### Why DeduplicationResult?

**Structured Return**:

- Clear contract for return value
- Metrics embedded in result
- Type-safe
- Easy to test

### Why Separate get_metrics()?

**Observability**:

- Track performance of different strategies
- Compare strategies empirically
- Debug slow deduplication
- Production monitoring

### Why Strategy Pattern?

**Flexibility**:

- Swap strategies without changing orchestrator
- Test different strategies easily
- Incremental improvements
- User choice via config

## Performance Comparison

| Strategy | Time Complexity | Space Complexity | Accuracy | LLM Calls |
|----------|----------------|------------------|----------|-----------|
| URN-Based | O(n) | O(n) | Exact URN match | 0 |
| Agent-Based | O(n²) | O(n) | Semantic match | ~n²/2 |
| Hybrid | O(n²) worst | O(n) | Best of both | ~n²/4 |
| No-Op | O(n) | O(n) | None | 0 |

## Testing Contract

All implementations of `DeduplicationStrategy` MUST pass this test suite:

```python
# tests/contracts/test_deduplication_contract.py
import pytest
from typing import Type

@pytest.mark.parametrize("strategy_class", [
    URNBasedDeduplication,
    AgentBasedDeduplication,
    HybridDeduplication,
    NoOpDeduplication,
])
async def test_deduplication_contract(strategy_class: Type[DeduplicationStrategy]):
    """All deduplication strategies must satisfy this contract."""
    strategy = create_strategy(strategy_class)

    # Test deduplication
    result = await strategy.deduplicate(
        new_entities=[
            {"@id": "urn:test:1", "@type": "Test", "name": "One"},
            {"@id": "urn:test:2", "@type": "Test", "name": "Two"},
        ],
        existing_entities=[
            {"@id": "urn:test:1", "@type": "Test", "name": "One (old)"},
        ],
    )

    # Contract assertions
    assert isinstance(result, DeduplicationResult)
    assert isinstance(result.entities, list)
    assert result.unique_entities > 0
    assert result.duplicates_found >= 0
    assert result.duplicates_merged >= 0

    # Get metrics
    metrics = strategy.get_metrics()
    assert isinstance(metrics, dict)
    assert "strategy" in metrics
```

## Migration Path

**Phase 1 (Skateboard)**: URN-based only

- Fast, deterministic
- Good for 95% of cases
- No LLM costs

**Phase 2 (Scooter)**: Agent-based implementation

- Slower, but more accurate
- Handles edge cases
- Optional (config-based)

**Phase 3 (Bicycle)**: Hybrid strategy

- Best of both worlds
- Intelligent fallback
- Performance tuning

**Phase 4 (Car)**: Advanced deduplication

- ML-based similarity (embeddings)
- Fuzzy matching
- Graph-based entity resolution

## References

- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy)
- [Entity Resolution](https://en.wikipedia.org/wiki/Record_linkage)
- [Semantic Similarity](https://en.wikipedia.org/wiki/Semantic_similarity)
