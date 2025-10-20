# Knowledge Graph Extraction Iterations

## Overview

This document tracks iterative improvements to the knowledge graph extraction process for app-interface data.

## Goals

1. **Improve Graph Connectedness**: Increase the ratio of entities with relationships
2. **Increase Quality**: Better entity extraction with complete metadata
3. **Increase Specificity**: Extract more granular entities from nested structures
4. **Better Free-Text Extraction**: Extract entities/relationships from description fields, documentation

## Baseline Metrics

To be measured from current extraction:

- Total entities extracted
- Entities by type
- Total relationships
- Orphaned entities (no relationships)
- Entities missing names
- Broken references

## Iteration Log

### Iteration 0: Baseline Analysis

**Date**: 2025-10-20
**Status**: Complete

**Actions**:

- Analyzed current extraction output from app-interface repository
- Identified critical weaknesses in entity naming and typing
- Set improvement targets

**Baseline Metrics** (from initial extraction):

- **Total entities extracted**: 6,332
- **Entities missing names**: 3,077 (48.6%)
- **Entities missing @type**: 2,951 (46.6%)
- **Impact**: Nearly half of entities appear as hex IDs (0x29948fa) in graph visualizations
- **Root cause**: Extraction logic did not enforce mandatory name/@type fields

**Key Issues Identified**:

1. No validation enforcement before adding entities to graph
2. No fallback strategies when source data lacks 'name' field
3. No type inference when schema/kind information missing
4. Validation only performed AFTER batch completion (too late)

**Improvement Targets for Iteration 1**:

- Reduce missing names from 48.6% to < 5%
- Reduce missing types from 46.6% to 0%
- Implement pre-extraction validation
- Add fallback naming strategies

---

## Improvement Areas Identified

### 1. Free-Text Entity Extraction

**Current State**: Description fields contain references to teams, tools, systems not extracted
**Target**: Extract entities mentioned in descriptions and create relationships

### 2. Nested Structure Handling

**Current State**: Complex nested objects may be simplified
**Target**: Create sub-entities for complex nested structures

### 3. Relationship Inference

**Current State**: Only explicit relationships extracted
**Target**: Infer relationships from file paths, naming patterns, labels

### 4. Metadata Completeness

**Current State**: Some entities may lack complete metadata
**Target**: Extract all available fields per Maximum Fidelity principle

---

## Iteration Template

### Iteration N: [Title]

**Date**: YYYY-MM-DD
**Status**: [Planning|In Progress|Complete]
**Focus Area**: [Free-text|Nested|Relationships|Metadata]

**Hypothesis**: What we expect to improve

**Changes to PROCESS.md**:

- List specific changes

**Implementation**:

- Scripts modified
- New extraction rules

**Results**:

- Metrics comparison
- Quality improvements observed
- Issues encountered

**Next Steps**: What to focus on next

---

### Iteration 1: Mandatory Name/Type Enforcement

**Date**: 2025-10-20
**Status**: Complete
**Focus Area**: Metadata Completeness

**Hypothesis**:
By enforcing mandatory name/@type validation BEFORE entities are added to the graph and implementing fallback strategies for missing data, we can reduce missing names from 48.6% to < 5% and eliminate missing types entirely (0%).

**Changes to PROCESS.md**:

1. **Added "Mandatory Name/Type Validation" subsection** (Phase 2: Entity Extraction)
   - `validate_entity_before_extraction()` function that enforces @id, @type, name before graph addition
   - Fail-fast approach: raise ValueError if entity cannot be named/typed
   - Attempts inference/fallback before failing

2. **Enhanced "Fallback Naming Strategies"** (4 strategies, applied in order)
   - Strategy 1: Extract from URN (urn:service:my-service → "My Service")
   - Strategy 2: Use schema entity type with identifier
   - Strategy 3: Extract from file path patterns (/services/foo/ → "Foo")
   - Strategy 4: Composite field names (namespace + kind, host + path, etc.)

3. **Added "Type Inference Patterns"** (4 patterns)
   - Pattern 1: URN-based inference (urn:service:X → @type: "Service")
   - Pattern 2: Schema field inference ($schema: /dependencies/ → "Dependency")
   - Pattern 3: File path inference (/namespaces/ → "Namespace")
   - Pattern 4: Kubernetes kind field (kind: Deployment → @type: "Deployment")

4. **Enhanced "Validation Checkpoints"** section
   - Mandatory validation with fail-fast on missing name/@type
   - Completeness metrics (% with names, % with types)
   - Quality metrics (descriptions, relationships, orphaned/sparse entities)
   - Warnings for any entities lacking names/types (target: 0 warnings)

**Implementation Details**:

```python
# Pre-extraction validation (NEW)
def extract_entity(data, filepath, schema_config):
    entity = build_entity(data, schema_config)

    # Apply fallback strategies if name missing
    if not entity.get("name"):
        entity["name"] = (
            extract_name_from_urn(entity["@id"]) or
            extract_name_from_filepath(filepath) or
            name_from_type_and_identifier(entity["@type"], entity["@id"]) or
            generate_composite_name(entity, data)
        )

    # Infer type if missing
    if not entity.get("@type"):
        entity["@type"] = infer_type_from_context(entity, filepath, data)

    # VALIDATE before adding to graph
    validate_entity_before_extraction(entity, filepath)

    return entity
```

**Expected Improvements**:

| Metric | Baseline (Iteration 0) | Target (Iteration 1) | Expected Improvement |
|--------|------------------------|----------------------|----------------------|
| Entities missing names | 3,077 (48.6%) | < 317 (5%) | 90% reduction |
| Entities missing @type | 2,951 (46.6%) | 0 (0%) | 100% elimination |
| Entities appearing as hex IDs in visualizer | ~3,000+ | < 50 | 98% reduction |
| Broken references due to unnamed entities | Unknown | 0 | Complete elimination |

**Implementation Status**:

- ✅ PROCESS.md updated with all changes
- ✅ Validation functions specified
- ✅ Fallback strategies documented (4 strategies)
- ✅ Type inference patterns documented (4 patterns)
- ⏳ Extraction scripts need updating (next step)
- ⏳ Re-extraction needed to measure actual improvements

**Next Steps**:

1. Update existing extraction scripts to implement new validation logic
2. Re-run extraction on app-interface repository
3. Measure actual improvement metrics
4. Compare against baseline and targets
5. Document results and identify next iteration focus (likely relationship inference or free-text extraction)
