# Iteration 3: Orphan Detection & Linking - Changes to PROCESS.md

**Date**: 2025-10-20
**Status**: Complete
**Focus**: Relationships - Orphan Linking

## Overview

This iteration adds orphan detection and linking capabilities to reduce the orphan entity rate from 3% (341 entities) to < 0.5% by inferring relationships from file paths, naming patterns, and metadata.

## Summary of Changes

### Sections Modified

1. Phase 2: Entity Extraction - Enhanced two-pass extraction flow
2. Phase 2: Entity Extraction - Added orphan detection subsection
3. Phase 3: Relationship Resolution - Expanded relationship inference patterns
4. Best Practices - Added Section 6.7 on orphan detection & prevention

### New Functions Added

- `detect_orphans()` - Identify entities with no relationships
- `count_entity_relationships()` - Count relationships per entity
- `infer_file_path_relationships()` - 4 file path inference patterns
- `infer_naming_relationships()` - 3 naming inference patterns
- `infer_metadata_relationships()` - 3 metadata inference patterns
- `infer_relationships()` - Unified inference with deduplication
- `link_orphans()` - Apply inferred links by confidence level

### Inference Patterns Added

10 total patterns across 3 categories:

#### File-Path-Based (4 patterns, HIGH confidence)

1. Services own namespaces in their directory
2. Teams own services in their directory
3. Products contain services in their directory
4. AWS accounts contain namespaces in their directory

#### Naming-Based (3 patterns, MEDIUM-HIGH confidence)

5. Team names match service names (with "-team" suffix)
6. GitHub org names match service names
7. Namespace names follow service-{env} pattern

#### Metadata-Based (3 patterns, LOW-HIGH confidence)

8. Service/team labels link to entities
9. Owner annotations link to teams/users
10. Description mentions link to entities (low confidence)

## Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Orphan rate | 3.0% (341 entities) | < 0.5% (< 32 entities) | 83% reduction |
| Teams linked | Unknown | 100% | Complete linkage |
| Products linked | Unknown | 100% | Complete linkage |
| GitHub orgs linked | Unknown | 90%+ | Near-complete linkage |
| AWS accounts linked | Unknown | 100% | Complete linkage |

---

## Detailed Changes

### 1. Phase 2: Enhanced Two-Pass Extraction Flow

**Location**: Phase 2: Entity Extraction > Two-Pass Extraction Strategy > Integration: Two-Pass Extraction Flow

**Change**: Added orphan detection and linking after Pass 2

**Before**:

```python
# PASS 2: Resolve all relationships
print(f"\n--- Pass 2: Relationship Resolution ---")
# ... relationship resolution code ...

# Write to output
append_jsonld(output_file, all_entities)

return all_entities, global_entity_index, all_broken_refs
```

**After**:

```python
# PASS 2: Resolve all relationships
print(f"\n--- Pass 2: Relationship Resolution ---")
# ... relationship resolution code ...

# ORPHAN DETECTION & LINKING
print(f"\n--- Orphan Detection & Linking ---")
orphan_report = detect_orphans(all_entities, global_entity_index)

if orphan_report['orphan_count'] > 0:
    print(f"⚠️  Found {orphan_report['orphan_count']} orphaned entities ({orphan_report['orphan_rate']:.1f}%)")

    # Attempt to link orphans using inference patterns
    linked_count = link_orphans(all_entities, global_entity_index, orphan_report)

    print(f"✅ Linked {linked_count} orphaned entities via inference")

    # Re-detect orphans after linking
    final_orphan_report = detect_orphans(all_entities, global_entity_index)
    print(f"📊 Final orphan rate: {final_orphan_report['orphan_rate']:.1f}% (target: < 0.5%)")

# Write to output
append_jsonld(output_file, all_entities)

return all_entities, global_entity_index, all_broken_refs
```

**Impact**:

- Updated expected impact section to include orphan reduction metric
- Added orphan detection as step 4 in workflow
- Integrated orphan linking into extraction pipeline

---

### 2. Phase 2: New Subsection - Orphan Detection & Prevention

**Location**: Phase 2: Entity Extraction > (new subsection after two-pass extraction)

**Change**: Added comprehensive orphan detection subsection

**Content Added**:

#### Orphan Detection

```python
def detect_orphans(entities, entity_index):
    """
    Detect entities with no relationships.

    An entity is orphaned if it has:
    - No outbound relationships (doesn't reference other entities)
    - No inbound relationships (not referenced by other entities)

    Returns orphan report with entity types and potential linking opportunities.
    """
    orphans = []
    orphans_by_type = {}

    # Build reverse index (which entities reference each entity)
    referenced_by = {}

    for entity in entities:
        has_outbound = False

        # Check for outbound relationships
        for key, value in entity.items():
            if key.startswith('_'):
                continue

            # Check for reference
            if isinstance(value, dict) and "@id" in value:
                has_outbound = True
                target_urn = value["@id"]
                referenced_by.setdefault(target_urn, []).append(entity["@id"])

            # Check for array of references
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "@id" in item:
                        has_outbound = True
                        target_urn = item["@id"]
                        referenced_by.setdefault(target_urn, []).append(entity["@id"])

        # Check if entity has inbound or outbound relationships
        has_inbound = entity["@id"] in referenced_by

        if not has_outbound and not has_inbound:
            orphans.append(entity)
            entity_type = entity.get("@type", "Unknown")
            orphans_by_type.setdefault(entity_type, []).append(entity)

    total_entities = len(entities)
    orphan_count = len(orphans)
    orphan_rate = (100.0 * orphan_count / total_entities) if total_entities > 0 else 0.0

    report = {
        'orphan_count': orphan_count,
        'orphan_rate': orphan_rate,
        'orphans_by_type': orphans_by_type,
        'orphans': orphans,
        'referenced_by': referenced_by
    }

    # Log orphans by type
    print(f"\n📊 Orphan entities by type:")
    for entity_type, type_orphans in sorted(orphans_by_type.items(), key=lambda x: -len(x[1])):
        print(f"   {entity_type}: {len(type_orphans)}")
        # Show first few examples
        for orphan in type_orphans[:3]:
            print(f"      - {orphan.get('name', orphan['@id'])}")

    return report


def count_entity_relationships(entity):
    """Count total relationships for an entity."""
    relationship_count = 0

    for key, value in entity.items():
        if key.startswith('_') or key in ['@id', '@type', 'name']:
            continue

        # Check for reference
        if isinstance(value, dict) and "@id" in value:
            relationship_count += 1

        # Check for array of references
        elif isinstance(value, list):
            refs = [v for v in value if isinstance(v, dict) and "@id" in v]
            relationship_count += len(refs)

    return relationship_count
```

**Impact**:

- Provides systematic orphan detection after relationship resolution
- Identifies orphans by entity type for targeted analysis
- Builds reverse relationship index for inbound relationship tracking
- Returns structured report for use in orphan linking

---

### 3. Phase 3: Expanded Inferred Relationship Patterns

**Location**: Phase 3: Relationship Resolution > Step 4: Infer Implicit Relationships

**Change**: Replaced simple inference function with comprehensive pattern-based system

**Before**:

```python
def infer_relationships(entities):
    """Infer relationships from patterns."""

    inferred = []

    # Pattern 1: File path implies namespace
    # Pattern 2: Label matching
    # Pattern 3: Name similarity (fuzzy matching)

    print(f"✅ Inferred {len(inferred)} implicit relationships")
    return inferred
```

**After**:
Added detailed subsections with 10 specific patterns:

#### Pattern 1: File-Path-Based Relationship Inference

4 patterns with HIGH confidence:

**Pattern 1a**: Services own namespaces in their directory

```python
# /services/cincinnati/namespaces/prod.yaml → cincinnati hasNamespace prod
if entity_type == "Namespace":
    service_match = re.search(r'/services/([^/]+)/', source_file)
    if service_match:
        service_name = service_match.group(1)
        service_urn = f"urn:service:{normalize_urn_component(service_name)}"

        if service_urn in entity_index:
            inferred.append({
                'source': service_urn,
                'predicate': 'hasNamespace',
                'target': entity["@id"],
                'reason': 'file_path_structure',
                'confidence': 'high'
            })
```

**Pattern 1b**: Teams own services in their directory

```python
# /teams/platform-team/services/api.yml → platform-team owns api
elif entity_type == "Service":
    team_match = re.search(r'/teams/([^/]+)/', source_file)
    if team_match:
        team_name = team_match.group(1)
        team_urn = f"urn:team:{normalize_urn_component(team_name)}"

        if team_urn in entity_index:
            inferred.append({
                'source': team_urn,
                'predicate': 'owns',
                'target': entity["@id"],
                'reason': 'file_path_structure',
                'confidence': 'high'
            })
```

**Pattern 1c**: Products contain services

```python
# /products/openshift/services/console.yml → openshift contains console
elif entity_type == "Service":
    product_match = re.search(r'/products/([^/]+)/', source_file)
    if product_match:
        product_name = product_match.group(1)
        product_urn = f"urn:product:{normalize_urn_component(product_name)}"

        if product_urn in entity_index:
            inferred.append({
                'source': entity["@id"],
                'predicate': 'partOf',
                'target': product_urn,
                'reason': 'file_path_structure',
                'confidence': 'high'
            })
```

**Pattern 1d**: AWS accounts contain namespaces

```python
# /aws/account-123/namespaces/prod.yml → account-123 contains prod namespace
elif entity_type == "Namespace":
    aws_match = re.search(r'/aws/([^/]+)/', source_file)
    if aws_match:
        account_name = aws_match.group(1)
        account_urn = f"urn:aws-account:{normalize_urn_component(account_name)}"

        if account_urn in entity_index:
            inferred.append({
                'source': account_urn,
                'predicate': 'contains',
                'target': entity["@id"],
                'reason': 'file_path_structure',
                'confidence': 'high'
            })
```

#### Pattern 2: Naming-Based Relationship Inference

3 patterns with MEDIUM-HIGH confidence:

**Pattern 2a**: Team names match service names (with "-team" suffix)

```python
# Team "cincinnati-team" owns Service "cincinnati"
if "Team" in entities_by_type and "Service" in entities_by_type:
    for team in entities_by_type["Team"]:
        team_name = team.get("name", "").lower()

        # Try removing "-team" suffix
        if team_name.endswith("-team"):
            service_name = team_name[:-5]  # Remove "-team"

            # Find matching service
            for service in entities_by_type["Service"]:
                svc_name = service.get("name", "").lower()
                if svc_name == service_name or service_name in svc_name:
                    inferred.append({
                        'source': team["@id"],
                        'predicate': 'owns',
                        'target': service["@id"],
                        'reason': 'name_pattern_team_service',
                        'confidence': 'high'
                    })
```

**Pattern 2b**: GitHub org names match service names

```python
# GitHub org "app-sre" manages repos for services in app-sre
if "GitHubOrg" in entities_by_type and "Service" in entities_by_type:
    for org in entities_by_type["GitHubOrg"]:
        org_name = org.get("name", "").lower()

        for service in entities_by_type["Service"]:
            svc_name = service.get("name", "").lower()

            # Exact match or org name in service name
            if org_name == svc_name or org_name in svc_name:
                inferred.append({
                    'source': org["@id"],
                    'predicate': 'hostsCodeFor',
                    'target': service["@id"],
                    'reason': 'name_pattern_org_service',
                    'confidence': 'medium'
                })
```

**Pattern 2c**: Namespace names contain service names with env suffix

```python
# Namespace "cincinnati-prod" belongs to Service "cincinnati"
if "Namespace" in entities_by_type and "Service" in entities_by_type:
    for namespace in entities_by_type["Namespace"]:
        ns_name = namespace.get("name", "").lower()

        for service in entities_by_type["Service"]:
            svc_name = service.get("name", "").lower()

            # Check if namespace is service-{env} pattern
            for env in ["prod", "stage", "staging", "dev", "development", "test"]:
                if ns_name == f"{svc_name}-{env}" or ns_name.startswith(f"{svc_name}-{env}"):
                    inferred.append({
                        'source': service["@id"],
                        'predicate': 'hasNamespace',
                        'target': namespace["@id"],
                        'reason': 'name_pattern_namespace_service',
                        'confidence': 'medium'
                    })
                    break
```

#### Pattern 3: Metadata-Based Relationship Inference

3 patterns with LOW-HIGH confidence:

**Pattern 3a**: Label-based relationships

```python
# metadata.labels.service = "foo" → links to urn:service:foo
if entity_type in ["Route", "Deployment", "Service", "ConfigMap"]:
    # Check for service label
    service_label = (
        entity.get("serviceLabel") or
        entity.get("label_service") or
        entity.get("labels", {}).get("service")
    )

    if service_label:
        service_urn = f"urn:service:{normalize_urn_component(service_label)}"
        if service_urn in entity_index:
            inferred.append({
                'source': service_urn,
                'predicate': 'manages',
                'target': entity["@id"],
                'reason': 'metadata_label_service',
                'confidence': 'high'
            })
```

**Pattern 3b**: Annotation-based relationships

```python
# annotations.owner: "team-name" → links to Team "team-name"
annotations = entity.get("annotations", {})
for key, value in annotations.items():
    if "owner" in key.lower() and isinstance(value, str):
        # owner annotation might reference team or user
        owner_urn_team = f"urn:team:{normalize_urn_component(value)}"
        owner_urn_user = f"urn:user:{normalize_urn_component(value)}"

        if owner_urn_team in entity_index:
            inferred.append({
                'source': owner_urn_team,
                'predicate': 'owns',
                'target': entity["@id"],
                'reason': 'metadata_annotation_owner',
                'confidence': 'medium'
            })
```

**Pattern 3c**: Description field entity mentions

```python
# "managed by platform-team" → links to Team "platform-team"
description = entity.get("description", "")
if description and isinstance(description, str):
    # Look for entity name mentions in description
    for other_entity in entities:
        other_name = other_entity.get("name", "")
        if not other_name or len(other_name) < 4:  # Skip short names
            continue

        if other_name.lower() in description.lower():
            other_type = other_entity.get("@type")

            # Infer relationship based on type and context
            if other_type == "Team" and any(word in description.lower() for word in ["owned by", "managed by", "maintained by"]):
                inferred.append({
                    'source': other_entity["@id"],
                    'predicate': 'owns',
                    'target': entity["@id"],
                    'reason': 'description_mention_team',
                    'confidence': 'low'
                })
```

#### Unified Inference Function

Added comprehensive `infer_relationships()` function:

```python
def infer_relationships(entities, entity_index):
    """
    Infer implicit relationships from patterns.

    Combines all inference patterns:
    1. File path structure
    2. Naming conventions
    3. Metadata (labels, annotations, descriptions)

    Returns list of inferred relationships with confidence scores.
    """
    print(f"\n🔍 Inferring implicit relationships...")

    all_inferred = []

    # Apply all inference patterns
    all_inferred.extend(infer_file_path_relationships(entities, entity_index))
    all_inferred.extend(infer_naming_relationships(entities, entity_index))
    all_inferred.extend(infer_metadata_relationships(entities, entity_index))

    # Deduplicate (same source/predicate/target)
    unique_inferred = {}
    for rel in all_inferred:
        key = (rel['source'], rel['predicate'], rel['target'])
        if key not in unique_inferred:
            unique_inferred[key] = rel
        else:
            # Keep higher confidence
            if rel['confidence'] == 'high' and unique_inferred[key]['confidence'] != 'high':
                unique_inferred[key] = rel

    inferred_list = list(unique_inferred.values())

    # Report by confidence level
    high_conf = [r for r in inferred_list if r['confidence'] == 'high']
    medium_conf = [r for r in inferred_list if r['confidence'] == 'medium']
    low_conf = [r for r in inferred_list if r['confidence'] == 'low']

    print(f"\n✅ Inferred {len(inferred_list)} implicit relationships:")
    print(f"   High confidence: {len(high_conf)}")
    print(f"   Medium confidence: {len(medium_conf)}")
    print(f"   Low confidence: {len(low_conf)}")

    return inferred_list
```

#### Orphan Linking Strategy

Added `link_orphans()` function:

```python
def link_orphans(entities, entity_index, orphan_report):
    """
    Attempt to link orphaned entities using inference patterns.

    Strategy:
    1. Run all inference patterns on the full entity set
    2. Filter inferred relationships to only include orphans
    3. Apply high-confidence links immediately
    4. Log medium-confidence links for manual review
    5. Skip low-confidence links (too risky)

    Returns count of orphans successfully linked.
    """
    orphan_urns = {orphan["@id"] for orphan in orphan_report['orphans']}

    # Infer all relationships
    inferred_relationships = infer_relationships(entities, entity_index)

    # Filter to relationships involving orphans
    orphan_links = [
        rel for rel in inferred_relationships
        if rel['source'] in orphan_urns or rel['target'] in orphan_urns
    ]

    print(f"\n🔗 Found {len(orphan_links)} potential links for orphaned entities")

    # Apply by confidence level
    high_conf_links = [r for r in orphan_links if r['confidence'] == 'high']
    medium_conf_links = [r for r in orphan_links if r['confidence'] == 'medium']
    low_conf_links = [r for r in orphan_links if r['confidence'] == 'low']

    applied_count = 0

    # Apply high-confidence links
    for rel in high_conf_links:
        source_entity = entity_index.get(rel['source'])
        target_entity = entity_index.get(rel['target'])

        if source_entity and target_entity:
            # Add relationship to source entity
            predicate = rel['predicate']

            if predicate not in source_entity:
                source_entity[predicate] = []

            if isinstance(source_entity[predicate], list):
                source_entity[predicate].append({"@id": rel['target']})
            else:
                source_entity[predicate] = {"@id": rel['target']}

            applied_count += 1

    print(f"   Applied {applied_count} high-confidence links")

    # Log medium-confidence for manual review
    if medium_conf_links:
        print(f"   ⚠️  {len(medium_conf_links)} medium-confidence links need review:")
        for rel in medium_conf_links[:10]:  # Show first 10
            print(f"      {rel['source']} --{rel['predicate']}--> {rel['target']} ({rel['reason']})")

    # Skip low-confidence links
    if low_conf_links:
        print(f"   ⏭  Skipped {len(low_conf_links)} low-confidence links")

    return applied_count
```

**Impact**:

- Comprehensive inference pattern library covering common app-interface structures
- Confidence-based application prevents false positive relationships
- Systematic approach to orphan linking with validation
- Extensible pattern framework for future additions

---

### 4. Best Practices: New Section 6.7 - Orphan Detection & Prevention

**Location**: Best Practices > (new section after 6.6 URN Validation)

**Change**: Added comprehensive guidance on orphan detection and prevention

**Content Added**:

```markdown
### 6.7 Orphan Detection & Prevention

**New Best Practice (Iteration 3)**: Proactively detect and link orphaned entities.

**Problem**: 3% of entities (341 entities in baseline) have no relationships to other entities. These orphaned entities:
- Appear isolated in graph visualizations
- Cannot be discovered through relationship traversal
- Reduce queryability and graph usefulness
- Often indicate missing extraction or relationship logic

**Common Orphan Types**:
- Teams not linked to services/users they own
- Products not linked to services they contain
- GitHub orgs not linked to repositories
- AWS accounts not linked to namespaces/clusters
- Resources without service/namespace relationships

**Solution**: Two-phase orphan handling (see Phase 2)

**Phase 1: Detection**

Run orphan detection after Pass 2 of two-pass extraction:

```python
# After relationship resolution
orphan_report = detect_orphans(all_entities, global_entity_index)

# Identifies entities with:
# - No outbound relationships (doesn't reference others)
# - No inbound relationships (not referenced by others)
```

**Phase 2: Linking**

Attempt to link orphans using inference patterns (see Phase 3):

```python
linked_count = link_orphans(all_entities, global_entity_index, orphan_report)

# Uses inference patterns:
# - File path structure (high confidence)
# - Naming conventions (medium confidence)
# - Metadata labels/annotations (medium/high confidence)
# - Description mentions (low confidence - skipped)
```

**Orphan Prevention Strategies**:

1. **Extract All Entity Types**: Ensure extraction covers all referenced entity types
   - If Services reference Teams, extract Team entities
   - If Namespaces reference Clusters, extract Cluster entities
   - Check broken reference reports for missing types

2. **Use File Path Inference**: Structure extraction to capture implicit relationships
   - Files in `/services/foo/namespaces/` belong to service "foo"
   - Files in `/teams/bar/` are owned by team "bar"
   - Files in `/products/acme/services/` are part of product "acme"

3. **Extract Metadata Relationships**: Don't skip labels and annotations
   - `metadata.labels.team: "platform"` → links to Team "platform"
   - `metadata.labels.service: "api"` → links to Service "api"
   - `annotations.owner: "team-name"` → links to Team "team-name"

4. **Validate Against Orphan Target**: After extraction, check orphan rate
   - Target: < 0.5% orphaned entities
   - If > 0.5%: Review inference patterns, extract missing types
   - High orphan rate indicates missing extraction logic

**Expected Impact** (Iteration 3):

- Orphaned entities: 3% → < 0.5% (83% reduction)
- Improved graph connectivity and queryability
- Better entity discovery through relationship traversal
- Reduced need for manual linking

**Metrics to Track**:

- Total orphan count before/after linking
- Orphan rate (orphans / total entities)
- Orphans by entity type (identify problem types)
- Inference pattern effectiveness (links created per pattern)
- Confidence distribution (high/medium/low links)

```

**Impact**:
- Provides clear guidance on orphan detection and prevention
- Documents prevention strategies for proactive approach
- Sets clear target (< 0.5%) for validation
- Includes metrics for tracking success

---

## Summary

### Lines Added
- Approximately 800 lines of new code and documentation
- 7 new functions
- 10 inference patterns with examples
- 1 new best practices section

### Key Features
1. **Orphan Detection**: Systematic identification of unconnected entities
2. **Confidence-Based Linking**: Apply only high-confidence inferred relationships
3. **Pattern Library**: 10 patterns covering common structures
4. **Prevention Strategies**: Proactive approaches to avoid orphans
5. **Validation**: Target-based validation (< 0.5% orphan rate)

### Next Steps for Implementation
1. Update extraction scripts to implement new functions
2. Test inference patterns on sample data
3. Validate confidence levels (adjust thresholds as needed)
4. Measure actual orphan reduction
5. Analyze remaining orphans for additional patterns
