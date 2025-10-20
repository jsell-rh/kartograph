# Iteration 2: Two-Pass Reference Resolution - Changes Summary

## Overview

**Date**: 2025-10-20
**Status**: Complete
**Focus**: Reducing broken references from 18% to < 2%

This iteration implements a two-pass extraction strategy with proactive reference validation to dramatically reduce broken references in the knowledge graph.

## Problem Statement

Baseline analysis revealed 18% of entity references (2,036 broken references) pointed to entities that didn't exist in the graph. Root causes:

1. Relationships created before validating target entities exist
2. $ref links in YAML files point to unextracted files
3. URN construction doesn't match actual extracted entity URNs
4. No validation before relationship creation

## Solution: Two-Pass Extraction with Validation

### Core Pattern

**Pass 1**: Extract ALL entities, build URN index

- Extract entities with scalar fields only
- Store reference fields as `_pending_refs` (defer relationship creation)
- Build global entity index (URN → entity mapping)
- Validate entity structure (name, type, URN format)

**Pass 2**: Resolve relationships with validation

- For each pending reference, resolve to target URN
- Validate target URN exists in entity index
- Create relationship only if validation passes
- Log broken references for analysis

### Expected Impact

- Broken references: 18% → < 2% (90% reduction)
- Unnamed nodes: ~3,000 → < 250 (92% reduction)
- Proactive detection of missing entity types
- Clear broken reference reports for debugging

## Changes to PROCESS.md

### 1. Phase 2: Entity Extraction

#### Added: Two-Pass Extraction Strategy (New Section)

**Location**: After "Type Inference Patterns" section

**Content Summary**:

- Problem statement: 18% broken references from baseline
- Solution: Two-pass extraction pattern
- Pass 1: Entity Extraction & Index Building
- Pass 2: Relationship Resolution with Validation
- Enhanced Reference Resolution with $ref Following
- URN Standardization & Validation
- Integration: Complete Two-Pass Extraction Flow

**Code Functions Added**:

```python
extract_entities_pass1(files, schema_config)
is_reference_field(value)
extract_relationships_pass2(entities, entity_index, schema_config)
resolve_reference(ref_value, target_type, entity_index)
find_urn_by_source_file(entity_index, file_path)
extract_referenced_entity(file_path, expected_type)
generate_urn(urn_pattern, data)
normalize_urn_component(value)
validate_urn(urn)
extract_entity_with_urn_validation(data, filepath, schema_config)
extract_all_entities_two_pass(schema_catalog, output_file)
```

**Key Features**:

- Defer relationship creation to Pass 2
- Build complete URN index before validation
- Follow $ref links to extract missing entities on-demand
- Standardize URN generation (lowercase, hyphens, URL-encoding)
- Report broken references with source, predicate, target, reason

### 2. Phase 3: Relationship Resolution

#### Enhanced: Proactive Validation Patterns (New Sections)

**Sections Added**:

1. **Proactive Reference Validation Pattern** - Validate BEFORE creating relationships
2. **Reference Validation Before Creation** - Bad vs. good patterns with examples
3. **URN Matching Validation** - Fuzzy matching for URN construction mismatches
4. **$ref Resolution Enhancement** - Dependency graph building and topological sort

**Code Functions Added**:

```python
create_relationship_with_validation(source_entity, predicate, target_urn, entity_index)
validate_and_create_relationships(entities, entity_index)
validate_urn_construction(expected_urn, entity_index, entity_type)
generate_alternative_urns(urn, entity_type)
resolve_ref_with_extraction(ref_value, entity_index, base_path)
build_dependency_graph(files, base_dir)
topological_sort_files(dependency_graph)
```

**Key Patterns**:

- Check-then-create instead of create-then-validate
- Fuzzy matching for common URN mismatches (casing, separators)
- On-demand extraction when following $ref links
- Optimal extraction order via topological sort

#### Updated: Step 2 Title

**Before**: "Step 2: Validate References"
**After**: "Step 2: Validate References (Post-Extraction)"

**Reason**: Clarify this is post-extraction validation, not the preferred proactive approach

### 3. Phase 3.5: Graph Validation & Repair

#### Updated: Opening Note

**Added**: Best practice note emphasizing proactive prevention over reactive repair

#### Enhanced: Best Practices for Preventing Issues

**Section Title**: "Best Practices for Preventing Issues (Iteration 2 Improvements)"

**New Structure** (5 Priority Levels):

- **Priority 1**: Use Two-Pass Extraction (90% reduction expected)
- **Priority 2**: Proactive Reference Validation (check before create)
- **Priority 3**: URN Standardization (consistent generation)
- **Priority 4**: $ref Following (extract referenced entities)
- **Priority 5**: Build Entity Index First (foundation)

Each priority includes:

- Problem statement
- Code example (bad vs. good)
- Expected impact
- Implementation notes

### 4. Best Practices Section

#### Updated: Section 6 - Relationship Resolution Order

**Added**: Note about two-pass extraction eliminating manual dependency ordering

**Content**:

- Two-pass extraction handles circular dependencies gracefully
- No need to manually determine extraction order
- Pass 1 extracts all, Pass 2 resolves all

#### Added: Section 6.5 - Two-Pass Extraction for Broken Reference Prevention (NEW)

**Content**:

- Problem: 18% broken references from baseline
- Solution: Two-pass extraction with validation
- Expected impact: 18% → < 2%
- When to use (should be default)
- Code example

#### Added: Section 6.6 - URN Validation and Standardization (NEW)

**Content**:

- Problem: Inconsistent URN construction
- Solution: Centralized `generate_urn()` function
- URN normalization rules
- Benefits for relationship validation
- Code example (bad vs. good)

## Files Modified

### /home/jsell/code/kartograph-kg-iteration/extraction/PROCESS.md

**Sections Modified**:

1. Phase 2: Entity Extraction - Added "Two-Pass Extraction Strategy" (495 lines)
2. Phase 3: Relationship Resolution - Enhanced with proactive validation (368 lines)
3. Phase 3.5: Graph Validation & Repair - Updated best practices (88 lines)
4. Best Practices - Added sections 6.5 and 6.6 (69 lines)

**Total Lines Added**: ~1,020 lines
**New Code Functions**: 17 functions with complete implementations

### /home/jsell/code/kartograph-kg-iteration/extraction/ITERATIONS.md

**Section Added**: Iteration 2 entry (153 lines)

**Content**:

- Hypothesis
- Changes to PROCESS.md (detailed breakdown)
- Code examples added (17 functions)
- Expected improvements (metrics table)
- Implementation details (4 subsections)
- Implementation status
- Next steps
- Success criteria
- Metrics to track

## Key Patterns Introduced

### 1. Two-Pass Extraction Pattern

```python
# Pass 1: Extract entities
entities, entity_index = extract_entities_pass1(files, schema_config)

# Pass 2: Resolve relationships
resolved, broken = extract_relationships_pass2(entities, entity_index, schema_config)
```

### 2. Proactive Validation Pattern

```python
# Before creating relationship
if target_urn in entity_index:
    entity[predicate] = {"@id": target_urn}
else:
    log_warning(f"Target {target_urn} not found, skipping relationship")
```

### 3. URN Standardization Pattern

```python
# Centralized generation with normalization
urn = generate_urn(schema_config['urn_pattern'], data)
# Handles: lowercase, hyphens, URL-encoding, validation
```

### 4. $ref Following Pattern

```python
# Extract referenced entity on-demand
target_urn = resolve_reference(ref_value, target_type, entity_index)
# If not in index, follows $ref and extracts
```

## Expected Metrics Improvements

| Metric | Baseline | Target | Improvement |
|--------|----------|--------|-------------|
| Broken references | 2,036 (18%) | < 226 (2%) | 90% reduction |
| Entities with broken refs | ~1,800 | < 200 | 89% reduction |
| Unnamed nodes | ~3,000 | < 250 | 92% reduction |
| URN mismatch errors | Unknown | Near zero | Standardization |

## Implementation Checklist

- [x] Document two-pass extraction strategy
- [x] Document proactive validation patterns
- [x] Document URN standardization
- [x] Document $ref following
- [x] Update best practices
- [x] Add code examples (17 functions)
- [x] Document iteration in ITERATIONS.md
- [ ] Update extraction scripts to implement patterns
- [ ] Re-run extraction on app-interface
- [ ] Measure actual improvements
- [ ] Compare against targets

## Next Steps

1. **Update extraction scripts** to implement two-pass extraction
2. **Implement URN standardization** via `generate_urn()` function
3. **Implement reference validation** with entity index
4. **Re-run extraction** on app-interface repository
5. **Measure results**:
   - Total relationships created
   - Broken references (count and %)
   - $ref links followed
   - URN validation failures
   - Alternative URN matches
6. **Compare against baseline** (18%) and target (< 2%)
7. **Analyze remaining broken references** to identify root causes
8. **Plan Iteration 3** (likely relationship inference or free-text extraction)

## Success Criteria

- ✅ Two-pass extraction pattern fully documented
- ✅ Reference validation code examples provided
- ✅ URN standardization guidelines added
- ⏳ Expected to reduce broken references from 18% → < 2%
- ⏳ Broken reference reports generated for debugging
- ⏳ All cross-entity relationships validated before creation

## References

- Baseline metrics: `/home/jsell/code/kartograph-kg-iteration/extraction/ITERATIONS.md` (Iteration 0)
- Process documentation: `/home/jsell/code/kartograph-kg-iteration/extraction/PROCESS.md`
- Iteration log: `/home/jsell/code/kartograph-kg-iteration/extraction/ITERATIONS.md`
