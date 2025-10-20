# Iteration 1: Mandatory Name/Type Enforcement - Detailed Changes

**Date**: 2025-10-20
**Focus**: Eliminate missing names and types from extracted entities
**Target**: Reduce missing names from 48.6% to < 5%, eliminate missing types (0%)

---

## Overview

This iteration addresses the critical issue where 48.6% of entities lack names and 46.6% lack types, causing them to appear as hex IDs (e.g., `0x29948fa`) in graph visualizations. We've enhanced PROCESS.md with mandatory validation, fallback naming strategies, and type inference patterns.

---

## Section 1: Naming Requirements (Enhanced)

**Location**: Phase 2: Entity Extraction → Naming Requirements

### What Changed

Added three major subsections:

1. Mandatory Name/Type Validation
2. Fallback Naming Strategies (4 strategies)
3. Type Inference Patterns (4 patterns)

### BEFORE

```markdown
### Naming Requirements

**CRITICAL**: ALL entities MUST have these predicates:

{
  "@id": "urn:entity:unique-id",
  "@type": "EntityType",
  "name": "Human Readable Name"
}

Entities without names will appear as hex IDs in graph visualizations.
```

**Issue**: No guidance on HOW to ensure entities have names when source data lacks them.

### AFTER

Added **269 lines** of detailed implementation guidance:

#### 1. Mandatory Name/Type Validation (NEW)

```python
def validate_entity_before_extraction(entity, filepath):
    """Validate entity has required fields BEFORE adding to graph."""

    # Mandatory field check
    if "@id" not in entity:
        raise ValueError(f"Entity missing @id in {filepath}")

    if "@type" not in entity or not entity["@type"]:
        # Attempt type inference before failing
        entity["@type"] = infer_type_from_context(entity, filepath)
        if not entity["@type"]:
            raise ValueError(f"Entity missing @type in {filepath}")

    if "name" not in entity or not entity["name"]:
        # Attempt name fallback before failing
        entity["name"] = generate_fallback_name(entity, filepath)
        if not entity["name"]:
            raise ValueError(f"Entity missing name in {filepath}")

    return entity
```

**Rationale**: Enforce validation BEFORE entities enter the graph, not after batch completion. Prevents unnamed entities from ever being added.

#### 2. Fallback Naming Strategies (NEW)

Four strategies applied in order when `name` field is missing:

**Strategy 1: Extract from URN**

```python
def extract_name_from_urn(urn):
    # urn:service:my-service → "My Service"
    # urn:namespace:prod:app-sre → "App Sre"
    segments = urn.split(':')
    last_segment = segments[-1]
    name = last_segment.replace('-', ' ').replace('_', ' ').title()
    return name
```

**Rationale**: URNs are guaranteed to exist (required field) and contain meaningful identifiers. Converting kebab-case to Title Case produces human-readable names.

**Strategy 2: Use Schema Entity Type**

```python
def name_from_type_and_identifier(entity_type, identifier):
    # urn:k8s-configmap:namespace:config-name → "Config Name (ConfigMap)"
    clean_id = identifier.replace('-', ' ').title()
    return f"{clean_id} ({entity_type})"
```

**Rationale**: For generic resource types (ConfigMap, Secret), combining identifier with type provides context.

**Strategy 3: Extract from File Path**

```python
def extract_name_from_filepath(filepath):
    # /services/cincinnati/app.yml → "Cincinnati"
    # /namespaces/production/config.yml → "Production"

    path_parts = filepath.split('/')

    if '/services/' in filepath:
        service_idx = path_parts.index('services') + 1
        return path_parts[service_idx].replace('-', ' ').title()

    # Generic: use parent directory name
    parent_dir = path_parts[-2] if len(path_parts) > 1 else path_parts[-1]
    return parent_dir.replace('-', ' ').title()
```

**Rationale**: Repository structure often encodes entity identity. Service defined at `/services/foo/app.yml` is named "Foo".

**Strategy 4: Composite Field Name**

```python
def generate_composite_name(entity, data):
    # Kubernetes: namespace + kind + resource_name
    if 'namespace' in data and 'kind' in data:
        ns = data['namespace']
        kind = data['kind']
        resource_name = data.get('metadata', {}).get('name', 'unknown')
        return f"{resource_name} ({kind} in {ns})"

    # Endpoints: host + path
    if 'host' in data and 'path' in data:
        return f"{data['host']}{data['path']}"

    # Ownership: owner + resource type
    if 'owner' in data and '@type' in entity:
        return f"{data['owner']}'s {entity['@type']}"
```

**Rationale**: When single `name` field absent, combine multiple descriptive fields to create unique, readable name.

#### 3. Type Inference Patterns (NEW)

Four patterns for inferring `@type` when missing:

**Pattern 1: URN-Based Inference**

```python
def infer_type_from_urn(urn):
    # urn:service:X → "Service"
    # urn:namespace:Y → "Namespace"
    type_segment = urn.split(':')[1]

    type_mapping = {
        'service': 'Service',
        'namespace': 'Namespace',
        'dependency': 'Dependency',
        'k8s-service': 'K8sService',
        'k8s-deployment': 'Deployment',
        # ... (10+ mappings)
    }

    return type_mapping.get(type_segment.lower())
```

**Rationale**: URN structure encodes type information. Extract and normalize to entity type.

**Pattern 2: Schema Field Inference**

```python
def infer_type_from_schema_field(data):
    # $schema: /dependencies/dependency-1.yml → "Dependency"
    schema_ref = data.get('$schema', '')

    schema_mapping = {
        '/app/': 'Service',
        '/dependencies/': 'Dependency',
        '/namespace/': 'Namespace',
        # ...
    }
```

**Rationale**: qontract-schema repositories use `$schema` field to reference schema files. Path contains entity type.

**Pattern 3: File Path Inference**

```python
def infer_type_from_filepath(filepath):
    # /services/foo/app.yml → "Service"
    path_mapping = {
        '/services/': 'Service',
        '/namespaces/': 'Namespace',
        # ...
    }
```

**Rationale**: Directory structure indicates entity type.

**Pattern 4: Kubernetes Kind Field**

```python
def infer_type_from_kubernetes_kind(data):
    # kind: Deployment → @type: "Deployment"
    if 'kind' not in data:
        return None

    kind = data['kind']
    # Avoid conflicts
    if kind == 'Service':
        return 'K8sService'

    return kind
```

**Rationale**: Kubernetes manifests have explicit `kind` field. Use it, but rename conflicting types.

### Impact

**Before**: No guidance → extraction scripts did not ensure names/types
**After**: 4 fallback naming strategies + 4 type inference patterns → entities can ALWAYS be named and typed

**Expected Improvement**:

- Missing names: 48.6% → < 5% (90% reduction)
- Missing types: 46.6% → 0% (100% elimination)

---

## Section 2: Validation Checkpoints (Enhanced)

**Location**: Phase 2: Entity Extraction → Validation Checkpoints

### What Changed

Complete rewrite of `validate_batch()` function with:

- Mandatory field validation with fail-fast
- Completeness metrics (% with names/types)
- Added `validate_entity_quality()` function for advanced metrics

### BEFORE

```python
def validate_batch(entities):
    """Validate extracted entities before continuing."""

    # Check all entities have required fields
    for entity in entities:
        assert "@id" in entity, f"Entity missing @id: {entity}"
        assert "@type" in entity, f"Entity missing @type: {entity}"
        assert "name" in entity, f"Entity missing name: {entity['@id']}"

    # Check URN uniqueness
    urns = [e["@id"] for e in entities]
    assert len(urns) == len(set(urns)), "Duplicate URNs found"

    # Count by type
    type_counts = {}
    for entity in entities:
        entity_type = entity["@type"]
        type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

    print(f"Batch extracted {len(entities)} entities:")
    for entity_type, count in sorted(type_counts.items()):
        print(f"  {entity_type}: {count}")

    return True
```

**Issues**:

1. Used assertions (wrong for data validation)
2. No detailed error reporting
3. No completeness metrics
4. Validated AFTER batch completion (too late)

### AFTER

```python
def validate_batch(entities):
    """Validate extracted entities before continuing."""

    errors = []
    warnings = []

    # MANDATORY: Check all entities have required fields
    for entity in entities:
        entity_id = entity.get("@id", "<no-id>")

        # Check @id
        if "@id" not in entity:
            errors.append(f"Entity missing @id: {entity}")
            continue

        # Check @type (MANDATORY)
        if "@type" not in entity or not entity["@type"]:
            errors.append(f"Entity missing @type: {entity_id}")

        # Check name (MANDATORY)
        if "name" not in entity or not entity["name"]:
            errors.append(f"Entity missing name: {entity_id}")

        # Check name is not just whitespace
        if "name" in entity and isinstance(entity["name"], str):
            if not entity["name"].strip():
                errors.append(f"Entity has empty/whitespace name: {entity_id}")

    # Check URN uniqueness
    urns = [e["@id"] for e in entities]
    if len(urns) != len(set(urns)):
        duplicates = [urn for urn in urns if urns.count(urn) > 1]
        errors.append(f"Duplicate URNs found: {set(duplicates)}")

    # FAIL FAST if critical errors found
    if errors:
        print(f"❌ VALIDATION FAILED: {len(errors)} critical errors")
        for error in errors[:20]:  # Show first 20 errors
            print(f"  - {error}")
        raise ValueError(f"Batch validation failed with {len(errors)} errors")

    # Count by type
    type_counts = {}
    for entity in entities:
        entity_type = entity["@type"]
        type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

    # Calculate completeness metrics (NEW)
    total = len(entities)
    with_names = sum(1 for e in entities if e.get("name"))
    with_types = sum(1 for e in entities if e.get("@type"))

    print(f"✅ Batch extracted {total} entities:")
    for entity_type, count in sorted(type_counts.items()):
        print(f"  {entity_type}: {count}")

    print(f"\nCompleteness:")
    print(f"  Entities with names: {with_names}/{total} ({100*with_names/total:.1f}%)")
    print(f"  Entities with types: {with_types}/{total} ({100*with_types/total:.1f}%)")

    # Warnings for low completeness (should be 100%)
    if with_names < total:
        warnings.append(f"{total - with_names} entities lack names")
    if with_types < total:
        warnings.append(f"{total - with_types} entities lack types")

    if warnings:
        print(f"\n⚠️  WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")

    return True
```

### Added: validate_entity_quality() (NEW)

```python
def validate_entity_quality(entities):
    """Additional quality checks beyond mandatory fields."""

    quality_report = {
        'entities_with_descriptions': 0,
        'entities_with_relationships': 0,
        'total_relationships': 0,
        'orphaned_entities': [],
        'sparse_entities': []  # Entities with < 3 fields
    }

    # ... (detailed implementation in PROCESS.md)

    print(f"\n📊 Quality Metrics:")
    print(f"  With descriptions: {quality_report['entities_with_descriptions']}/{total}")
    print(f"  With relationships: {quality_report['entities_with_relationships']}/{total}")
    print(f"  Total relationships: {quality_report['total_relationships']}")
    print(f"  Orphaned entities: {len(quality_report['orphaned_entities'])}")
    print(f"  Sparse entities (< 3 fields): {len(quality_report['sparse_entities'])}")

    return quality_report
```

**Rationale**:

1. Error list instead of assertions allows collecting ALL errors before failing
2. Completeness metrics track name/type coverage
3. Quality metrics identify entities needing improvement
4. Fail-fast with detailed reporting helps debugging

### Impact

**Before**: Basic validation, no metrics, assertions failed on first error
**After**: Comprehensive validation, completeness/quality metrics, detailed error reporting

**Expected Improvement**:

- Identify ALL validation issues in one run (not just first error)
- Track name/type completeness per batch
- Measure graph quality (relationships, descriptions)

---

## Section 3: Best Practices (No Changes)

**Location**: Best Practices → 1. Entity Naming

**Decision**: Did not modify this section. It already emphasizes the CRITICAL requirement for name/@type. The new "Naming Requirements" section in Phase 2 provides the implementation details.

**Rationale**: Best Practices is high-level guidance. Detailed implementation belongs in Phase 2 where extraction happens.

---

## Summary of Changes

### Files Modified

1. **PROCESS.md**
   - Section "Naming Requirements" expanded from 12 lines to 281 lines
   - Section "Validation Checkpoints" expanded from 28 lines to 131 lines
   - **Total additions**: ~372 lines of implementation guidance

2. **ITERATIONS.md**
   - Updated Iteration 0 with baseline metrics
   - Added Iteration 1 entry with hypothesis, changes, expected improvements

3. **ITERATION_1_CHANGES.md** (this file)
   - Created detailed before/after comparison
   - Documented rationale for each change

### Key Improvements

| Area | Before | After | Impact |
|------|--------|-------|--------|
| **Name Fallback** | None | 4 strategies | Can name entities from URN, filepath, composite fields |
| **Type Inference** | None | 4 patterns | Can type entities from URN, schema, filepath, k8s kind |
| **Pre-validation** | No | Yes | Entities validated BEFORE adding to graph |
| **Error Reporting** | First error only | All errors | Complete picture of validation issues |
| **Metrics** | Entity counts | Completeness + quality | Track name/type coverage, relationships |

### Expected Metric Improvements

| Metric | Baseline | Target | Improvement |
|--------|----------|--------|-------------|
| Missing names | 48.6% | < 5% | 90% reduction |
| Missing types | 46.6% | 0% | 100% elimination |
| Hex ID visualizations | ~3,000 | < 50 | 98% reduction |
| Validation errors caught | After batch | Before entity added | Immediate feedback |

---

## Implementation Checklist

To realize these improvements in practice:

- [x] Document changes to PROCESS.md
- [x] Update ITERATIONS.md with baseline and Iteration 1
- [x] Create ITERATION_1_CHANGES.md
- [ ] Update extraction scripts to implement:
  - [ ] `validate_entity_before_extraction()`
  - [ ] `extract_name_from_urn()`
  - [ ] `extract_name_from_filepath()`
  - [ ] `name_from_type_and_identifier()`
  - [ ] `generate_composite_name()`
  - [ ] `infer_type_from_urn()`
  - [ ] `infer_type_from_schema_field()`
  - [ ] `infer_type_from_filepath()`
  - [ ] `infer_type_from_kubernetes_kind()`
  - [ ] `infer_type_from_context()`
  - [ ] Enhanced `validate_batch()`
  - [ ] New `validate_entity_quality()`
- [ ] Re-run extraction on app-interface
- [ ] Measure actual improvements vs. targets
- [ ] Document results in ITERATIONS.md

---

## Next Iteration Focus Areas

After achieving < 5% missing names and 0% missing types, focus on:

1. **Relationship Inference**: Increase graph connectedness
   - Infer relationships from file paths
   - Label matching patterns
   - Name similarity detection

2. **Free-Text Extraction**: Mine description fields
   - Extract team names, tool references
   - Create relationships from mentions
   - NLP-based entity extraction

3. **Nested Structure Handling**: Create more sub-entities
   - Code components
   - Alert rules
   - Endpoint definitions
   - Owner details
