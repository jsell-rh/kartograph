# Schema-Guided Extraction Error Analysis

## Summary

The schema-guided extraction produced **20,181 entities** but had **multiple critical errors** that prevented successful ingestion into Dgraph. This document analyzes what went wrong and how to prevent these errors.

---

## Critical Errors Found

### Error 1: Relationship Entities Instead of Predicates

**What happened:**

- Extraction created **16,156 "Relationship" entities**
- These were separate entities with structure: `{@type: "Relationship", from: urn1, to: urn2, relationshipType: "predicate"}`
- This is **fundamentally wrong** for JSON-LD and graph databases

**What should have happened:**

- Relationships should be **predicates on source entities**, not separate entities
- Example: Instead of a Relationship entity, `urn:service:foo` should have predicate `repoUrl: {"@id": "urn:repo:bar"}`

**Impact:**

- Original entity count: 36,338 (inflated)
- Actual entities after removing Relationships: 20,181
- Lost 16,156 relationships that had to be reconstructed

**Root cause:**

- Agent likely misunderstood Pass 2 instructions
- Created relationship metadata instead of actually linking entities
- PROCESS.md was ambiguous about the distinction

---

### Error 2: Missing `name` Field (82% of entities)

**What happened:**

- **16,638 out of 20,181 entities (82%)** had no `name` field
- Breakdown:
  - 16,156 Relationship entities (no name - expected since they shouldn't exist)
  - 481 EmailAddress entities (no name - CRITICAL BUG)
  - 1 ExtractionMetadata entity (no name - metadata artifact)

**What should have happened:**

- **ALL entities MUST have `name` field** (per PROCESS.md line 1103-1140)
- EmailAddress entities should use `email` field as `name`

**Impact:**

- App server skips entities without `name` in relationship traversal
- Entities appear as hex UIDs in visualizations
- Queries by name fail completely

**Root cause:**

- Agent didn't follow validate_entity_before_extraction() requirement
- No enforcement of fallback naming strategies
- Validation was not run during extraction

---

### Error 3: Invalid Entity Type Names

**What happened:**

- Generated entity types with **illegal characters**: `/`, `[`, `]`
- Examples:
  - `rhdh/backstage.io/techdocs-ref/clowder`
  - `rhdh/backstage.io/techdocs-ref/provisioning-backend`
  - `Acceptancecriteria[0]`, `Acceptancecriteria[10]`, `Acceptancecriteria[11]`

**What should have happened:**

- Entity type names must match `^[A-Za-z][A-Za-z0-9]*$`
- Array elements should have generic type (e.g., `AcceptanceCriterion`), not indexed types
- Tech docs refs are **values**, not types (should be predicates on entities)

**Impact:**

- Dgraph schema generation failed with parse errors
- Data could not be loaded via `dgraph live` command
- HTTP API fallback also failed (unreliable for large datasets)

**Root cause:**

- Agent used field values as `@type` (techdocs URLs)
- Agent created indexed types for array elements instead of generic types
- No type name validation during extraction

---

### Error 4: Over-extraction to Nested Entities

**What happened:**

- Created 866 distinct entity types (EXCESSIVE)
- Many types represent array indices: `Items[0]`, `Parameters[1]`, `Codecomponents[2]`
- Indicates over-application of nested entity extraction

**What should have happened:**

- Nested entities should have **generic, reusable types**
- Array elements of same type should share type name (e.g., all items → `Item`, not `Items[0]`, `Items[1]`)
- Many nested objects should be **properties**, not separate entities

**Impact:**

- Schema bloat (866 types vs expected ~50-100)
- Dgraph schema too large and complex
- Many entities lack meaningful identity

**Root cause:**

- Agent didn't apply "queryability" test (Iteration 4)
- Extracted every nested object regardless of independence
- Type naming based on field path instead of semantic meaning

---

## Prevention Strategy

### 1. Explicit Prohibition in PROCESS.md

Add these **CRITICAL: DO NOT** rules to PROCESS.md:

```markdown
## CRITICAL: What NOT to Do

### ❌ DO NOT Create Relationship Entities

NEVER create entities with @type="Relationship". Relationships are predicates, not entities.

❌ WRONG:
{
  "@type": "Relationship",
  "from": "urn:service:foo",
  "to": "urn:repo:bar",
  "relationshipType": "repoUrl"
}

✅ CORRECT:
{
  "@id": "urn:service:foo",
  "@type": "Service",
  "name": "foo",
  "repoUrl": {"@id": "urn:repo:bar"}
}

### ❌ DO NOT Use Invalid Type Names

Entity type names MUST match: ^[A-Za-z][A-Za-z0-9]*$

Invalid characters: / [ ] . : - space

❌ WRONG: "rhdh/backstage.io/techdocs-ref/clowder"
❌ WRONG: "Parameters[0]"
❌ WRONG: "acceptance-criteria"

✅ CORRECT: "TechDocsRef" (if it's truly an entity type)
✅ CORRECT: "Parameter" (generic, reusable)
✅ CORRECT: "AcceptanceCriterion"

### ❌ DO NOT Skip Name Fields

ALL entities MUST have a `name` field before extraction.

Use fallback strategies (PROCESS.md lines 1142-1186):
1. Extract from primary field (e.g., `email` for EmailAddress)
2. Extract from URN last segment
3. Use `@type` + unique identifier

### ❌ DO NOT Create Entities from Array Indices

Array elements of the same type should share a generic type name.

❌ WRONG:
- Items[0], Items[1], Items[2] (indexed types)
- Parameters[0], Parameters[1] (indexed types)

✅ CORRECT:
- Item (generic, reusable for all array items)
- Parameter (generic, reusable)
```

---

### 2. Validation Standards to Enforce

Add to Phase 3.5 validation:

```markdown
**Standard 7: No Relationship Entities**

Agent: "Checking for Relationship entities..."
✓ No entities with @type='Relationship'
❌ Found 123 Relationship entities → FAIL

**Standard 8: Valid Type Names**

Agent: "Validating entity type names..."
✓ All type names match ^[A-Za-z][A-Za-z0-9]*$
❌ Found types with invalid characters: /[].:-

**Standard 9: Name Field Coverage**

Agent: "Checking name field presence..."
✓ Has name: 286/286 (100%)
❌ Has name: 212/286 (74.1%) → FAIL
```

---

### 3. Pre-Extraction Validation Function

Enhance the validation function in PROCESS.md:

```python
def validate_entity_before_extraction(entity, filepath):
    """Validate entity BEFORE adding to graph."""

    # Check @id
    if "@id" not in entity or not entity["@id"]:
        raise ValueError(f"Missing @id in {filepath}")

    # Check @type
    if "@type" not in entity or not entity["@type"]:
        raise ValueError(f"Missing @type in {filepath}: {entity.get('@id')}")

    # CRITICAL: Reject Relationship entities
    if entity["@type"] == "Relationship":
        raise ValueError(
            f"ILLEGAL: Relationship entities not allowed. "
            f"Add as predicate instead: {entity}"
        )

    # CRITICAL: Validate type name format
    type_name = entity["@type"]
    if not re.match(r'^[A-Za-z][A-Za-z0-9]*$', type_name):
        raise ValueError(
            f"Invalid @type name: '{type_name}'. "
            f"Must match ^[A-Za-z][A-Za-z0-9]*$ (no /, [, ], ., :, -, spaces)"
        )

    # Check name with fallback
    if "name" not in entity or not entity["name"]:
        entity["name"] = generate_fallback_name(entity, filepath)
        if not entity["name"]:
            raise ValueError(f"Cannot generate name for {entity['@id']}")

    return entity
```

---

### 4. Clearer Pass 2 Instructions

Update Pass 2 relationship resolution instructions:

```markdown
## Pass 2: Relationship Resolution

**CRITICAL UNDERSTANDING**: Relationships are PREDICATES on entities, not separate entities.

### How to Resolve a Relationship

When you find a reference like `$ref: /path/to/file.yml`:

1. **Determine the target entity URN** (extract if needed)
2. **Add a predicate to the source entity** pointing to target URN
3. **DO NOT create a Relationship entity**

Example:

Source data:
{
  "name": "my-service",
  "repoUrl": {"$ref": "/repos/my-repo.yml"}
}

✅ CORRECT approach:
1. Extract target: urn:coderepository:my-repo
2. Add predicate to source entity:
   {
     "@id": "urn:service:my-service",
     "@type": "Service",
     "name": "my-service",
     "repoUrl": {"@id": "urn:coderepository:my-repo"}  ← predicate, not entity
   }

❌ WRONG approach:
1. Create Relationship entity:
   {
     "@type": "Relationship",  ← NO! This is forbidden!
     "from": "urn:service:my-service",
     "to": "urn:coderepository:my-repo",
     "relationshipType": "repoUrl"
   }
```

---

## Testing Requirements

Before declaring extraction complete, agent MUST:

1. **Run all validation standards** (including new Standards 7-9)
2. **Check entity type name validity** with regex
3. **Verify 100% name field coverage**
4. **Confirm zero Relationship entities**
5. **Test JSON-LD loads into Dgraph** (not just generates valid JSON)

---

## Lessons Learned

### For PROCESS.md Updates

1. **Explicit prohibitions > implicit expectations**
   - Don't assume agents know what's wrong
   - State "DO NOT do X" clearly

2. **Validate early and often**
   - Run validation DURING extraction, not just after
   - Fail fast on critical errors

3. **Show examples of wrong patterns**
   - "What not to do" examples prevent mistakes
   - Side-by-side ❌/✅ comparisons are effective

4. **Enforce standards with code**
   - Validation functions should REJECT invalid entities
   - Don't just warn - actually block bad data

### For Future Extractions

1. **Start with small sample** (10-20 files)
   - Validate thoroughly before scaling
   - Catch structural issues early

2. **Check entity type diversity**
   - 866 types from 10K files = RED FLAG
   - Expected: ~50-100 types for infrastructure domain

3. **Manual spot-check required**
   - Agent self-validation isn't sufficient
   - Review sample of extracted entities manually

---

## Recommended Next Steps

1. ✅ **Update PROCESS.md** with prohibitions and enhanced validation
2. **Re-run extraction** on app-interface with updated PROCESS.md
3. **Test on 20-file sample first** to validate fixes
4. **Full-scale extraction** only after sample passes all standards
5. **Dgraph load test** as part of validation (not separate step)

---

## Data Quality Metrics

### Original Extraction (Before Fixes)

- Total entities: 36,338
- Relationship entities: 16,156 (44.4%) ❌
- Entities missing name: 16,638 (45.8%) ❌
- Invalid entity types: ~60 types with special chars ❌
- Dgraph load: FAILED ❌

### After Manual Fixes

- Total entities: 20,181
- Relationship entities: 0 (converted to predicates) ✓
- Entities missing name: 0 (added fallback names) ✓
- Invalid entity types: Still ~60 (not fixable with script) ❌
- Dgraph load: STILL FAILED (due to invalid type names) ❌

### Required for Success

- All entities: Must have @id, @type, name
- Zero Relationship entities
- All type names match `^[A-Za-z][A-Za-z0-9]*$`
- Entity types: 50-150 (reasonable diversity)
- Dgraph live load: SUCCESS
