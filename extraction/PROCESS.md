# Knowledge Graph Extraction Framework

A repository-agnostic methodology for extracting knowledge graphs from configuration repositories, codebases, and structured data sources.

**Audience**: This guide is written for Claude (AI assistant) to follow when extracting knowledge graphs from repositories. Claude will generate repository-specific extraction scripts based on these patterns.

**Output Format**: JSON-LD (compatible with Dgraph, Neo4j, and any RDF-compliant graph database)

**Philosophy**: Completeness over shortcuts, systematic over ad-hoc, queryable over storage.

---

## Table of Contents

1. [Overview](#overview)
2. [Phase 0: Repository Discovery](#phase-0-repository-discovery)
3. [Phase 1: Schema Analysis](#phase-1-schema-analysis)
4. [Phase 2: Entity Extraction](#phase-2-entity-extraction)
5. [Phase 3: Relationship Resolution](#phase-3-relationship-resolution)
6. [Phase 3.5: Graph Validation & Repair](#phase-35-graph-validation--repair)
7. [Phase 4: Graph Export](#phase-4-graph-export)
8. [Best Practices](#best-practices)
9. [Case Studies](#case-studies)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What This Framework Does

Transforms any structured repository (YAML configs, Kubernetes manifests, Terraform, API definitions, etc.) into a queryable knowledge graph that answers questions like:

- "Who owns service X?"
- "What resources does namespace Y use?"
- "Which services depend on database Z?"
- "Show me all endpoints exposed on domain example.com"
- "What's the blast radius if component A fails?"

### Key Principles

1. **Schema-Driven When Possible**: Use existing schemas (JSON Schema, OpenAPI, Kubernetes CRDs) to guide extraction
2. **Heuristic When Necessary**: Extract meaningful entities even without schemas
3. **Maximum Fidelity**: Capture ALL meaningful fields, not just obvious ones
4. **Relationship-Rich**: Create explicit AND inferred relationships
5. **Validation-First**: Validate at every step, fail fast on errors

### Prerequisites

- Python 3.8+
- Access to target repository (local clone or API)
- Target graph database (Dgraph, Neo4j, or compatible)

### Instructions for Claude

When a user asks you to extract a knowledge graph from a repository:

1. **Follow this process systematically** - Do not skip phases
2. **Generate extraction scripts** - Create repository-specific Python scripts based on these patterns
3. **Use absolute paths from arguments** - Never hardcode paths; use argparse for all inputs
4. **Validate at each step** - Run validation after each extraction batch
5. **Report progress** - Show what entities were extracted and validation results
6. **Ask clarifying questions** - If repository structure is unclear, ask before proceeding

---

## Phase 0: Repository Discovery

**Goal**: Understand the repository structure, file types, and potential entities before writing any extraction code.

### Step 1: Initial Scan

```bash
# Count files by type
find . -type f | sed 's/.*\.//' | sort | uniq -c | sort -rn

# Identify directory structure
tree -L 3 -d

# Look for schema files
find . -name "*schema*" -o -name "*.json" -o -name "*.graphql" -o -name "openapi*"
```

**Output**: Inventory of file types, directory patterns, and potential schema sources.

### Step 2: Schema Detection

Automatically detect schema types:

| Schema Type      | Indicators                      | Common Locations                        |
| ---------------- | ------------------------------- | --------------------------------------- |
| JSON Schema      | `$schema` key, `*.schema.json`  | `/schemas`, `/definitions`              |
| OpenAPI          | `openapi: 3.x`, `swagger: 2.0`  | `openapi.yaml`, `/api`                  |
| Kubernetes CRD   | `apiVersion`, `kind`            | Any `.yaml` with standard k8s structure |
| qontract-schemas | `$ref` patterns, `/schemas` dir | App-interface style repos               |
| GraphQL          | `*.graphql`, type definitions   | `/schema`, `/graphql`                   |
| Terraform        | `*.tf`, resource blocks         | Root or `/modules`                      |
| Ansible          | `*.yml` with tasks/roles        | `/playbooks`, `/roles`                  |

**Decision Tree**:

```
Schemas found?
  YES → Proceed to Phase 1 (Schema Analysis)
  NO → Use heuristic extraction (Phase 2, Option B)
```

### Step 3: Sample Analysis

**Claude: Read 5-10 representative files from each major directory:**

```python
# Claude should implement this analysis
for directory in major_directories:
    sample_files = random.sample(files_in(directory), min(10, count))
    for file in sample_files:
        analyze_structure(file)
        identify_entity_candidates(file)
        detect_relationship_patterns(file)
```

**Output**:

- List of potential entity types (e.g., "Service", "Namespace", "User", "Database")
- Common field patterns (e.g., "name", "owner", "cluster", "dependencies")
- Reference patterns (e.g., `$ref`, `serviceRef`, YAML anchors)

### Step 4: Create Extraction Plan

Based on discovery, create a structured plan:

```markdown
## Extraction Plan for [Repository Name]

### Repository Type

[e.g., Kubernetes Config Repository, API Definition, Infrastructure as Code]

### Schema Approach

- [ ] JSON Schema files found: [count]
- [ ] Use schema-driven extraction
- [ ] Use heuristic extraction
- [ ] Hybrid approach needed

### Entity Types Identified

1. **Service** (~250 files) - `/services/**/*.yaml`
2. **Namespace** (~150 files) - `/namespaces/**/*.yaml`
3. **Database** (~50 files) - `/infrastructure/databases/*.yaml`
   ...

### Relationship Patterns

- Services → Namespaces (via `namespace` field)
- Services → Databases (via `dependencies[].$ref`)
- Users → Roles (via `roles[]`)
  ...

### Extraction Batch Plan

Batch 1: Core entities (Services, Namespaces)
Batch 2: Infrastructure (Databases, Caches, Storage)
Batch 3: Access control (Users, Roles, Permissions)
...
```

**Claude: Generate extraction scripts based on this plan.**

---

## Phase 1: Schema Analysis

**Goal**: Build a comprehensive catalog of entity types and their properties from schemas.

### When to Use This Phase

- ✅ Repository has JSON Schema, OpenAPI, or other formal schemas
- ✅ Schemas are up-to-date and representative
- ❌ Skip if no schemas or schemas are stale/incomplete

### Step 1: Parse Schema Files

**Claude: For each schema file, analyze its structure:**

```python
# Claude should implement this function
def analyze_schema(schema_file):
    schema = load_json_or_yaml(schema_file)

    entity_type = infer_entity_type(schema)  # e.g., "Service", "Namespace"
    required_fields = schema.get('required', [])
    optional_fields = [k for k in schema['properties'].keys() if k not in required_fields]

    # Extract relationship patterns
    references = find_ref_patterns(schema)  # $ref, foreignKey patterns

    # Extract validation rules
    enums = find_enum_fields(schema)
    formats = find_format_constraints(schema)

    return {
        'entity_type': entity_type,
        'required': required_fields,
        'optional': optional_fields,
        'references': references,
        'enums': enums,
        'formats': formats
    }
```

### Step 2: Build Schema Catalog

Create a mapping of schema types to extraction rules:

```json
{
  "schemas": [
    {
      "schema_file": "/schemas/service.schema.json",
      "entity_type": "Service",
      "urn_pattern": "urn:service:{name}",
      "required_predicates": ["name", "description", "owner"],
      "optional_predicates": ["grafanaUrl", "slackChannel"],
      "relationships": [
        {
          "field": "namespace",
          "target_type": "Namespace",
          "predicate": "belongsTo"
        },
        {
          "field": "dependencies[]",
          "target_type": "Dependency",
          "predicate": "dependsOn"
        }
      ],
      "file_pattern": "/services/**/*.yaml"
    }
  ]
}
```

**Output**: `schema_catalog.json` - Complete extraction blueprint.

### Step 3: Validate Schema Catalog

```python
# Check that all referenced entity types are defined
for schema in catalog['schemas']:
    for rel in schema['relationships']:
        assert rel['target_type'] in known_entity_types, \
            f"Unknown target type: {rel['target_type']}"

# Check file patterns match actual files
for schema in catalog['schemas']:
    matched_files = glob(schema['file_pattern'])
    assert len(matched_files) > 0, \
        f"No files match pattern: {schema['file_pattern']}"
```

---

## Phase 2: Entity Extraction

**Goal**: Extract ALL entities with maximum fidelity from repository files.

**Claude Instructions**:

- Generate a Python extraction script with argparse for all input/output paths
- Process files in batches and validate after each batch
- Use the patterns below as templates, adapting to the repository structure
- Never hardcode paths - all paths must come from command-line arguments

### Option A: Schema-Driven Extraction

Use the schema catalog from Phase 1.

#### Batch Strategy

Group schemas by dependency order (extract referenced entities first):

```python
# Pseudo-code
batches = [
    # Batch 1: No dependencies (leaf nodes)
    ['Cluster', 'AWSAccount', 'Product'],

    # Batch 2: Depend on Batch 1
    ['Namespace', 'Environment'],

    # Batch 3: Depend on Batch 1 & 2
    ['Service', 'Database'],

    # Batch 4: Everything else
    ['User', 'Role', 'Alert']
]
```

#### Extraction Pattern

For each entity type in the batch:

```python
def extract_entity_type(schema_config, output_file):
    """
    Extract entities of a single type.

    Args:
        schema_config: Entry from schema_catalog.json
        output_file: Path to append JSON-LD output
    """
    entities = []

    # Find all files matching the pattern
    files = glob(schema_config['file_pattern'])

    for filepath in files:
        data = load_yaml_or_json(filepath)

        # Create entity with URN
        urn = generate_urn(schema_config['urn_pattern'], data)

        entity = {
            "@id": urn,
            "@type": schema_config['entity_type']
        }

        # Extract ALL required fields
        for field in schema_config['required_predicates']:
            value = get_nested_field(data, field)
            if value is None:
                log_error(f"Missing required field '{field}' in {filepath}")
            entity[field] = value

        # Extract ALL optional fields that exist
        for field in schema_config['optional_predicates']:
            value = get_nested_field(data, field)
            if value is not None:
                entity[field] = value

        # Extract relationships
        for rel in schema_config['relationships']:
            ref_value = get_nested_field(data, rel['field'])
            if ref_value:
                # Convert $ref to URN
                target_urn = resolve_reference(ref_value, rel['target_type'])
                entity[rel['predicate']] = {"@id": target_urn}

        entities.append(entity)

    # Write to JSON-LD file
    append_jsonld(output_file, entities)

    return len(entities)
```

#### Maximum Fidelity Rule

**CRITICAL**: Extract EVERY meaningful field, even if it seems unimportant.

❌ **Wrong** (minimal extraction):

```json
{
  "@id": "urn:service:cincinnati",
  "@type": "Service",
  "name": "Cincinnati"
}
```

✅ **Right** (maximum detail):

```json
{
  "@id": "urn:service:cincinnati",
  "@type": "Service",
  "name": "Cincinnati",
  "description": "OpenShift Update Service that provides...",
  "onboardingStatus": "OnBoarded",
  "serviceOwner": [
    { "name": "John Doe", "email": "jdoe@example.com" },
    { "name": "Jane Smith", "email": "jsmith@example.com" }
  ],
  "grafanaUrl": "https://grafana.example.com/d/cincinnati",
  "slackChannel": "#cincinnati-team",
  "sopsUrl": "https://github.com/org/cincinnati/docs/sops",
  "architectureDocument": "https://docs.example.com/arch/cincinnati",
  "appCode": "CINC-001",
  "costCenter": "Engineering"
}
```

**Why?** You can't predict future queries. Extract everything now, filter later.

### Option B: Heuristic Extraction

When no schemas exist, use pattern matching and inference.

#### Entity Detection Heuristics

```python
def detect_entity_type(filepath, data):
    """Infer entity type from file structure and content."""

    # Check file path patterns
    if '/services/' in filepath:
        return 'Service'
    elif '/namespaces/' in filepath:
        return 'Namespace'
    elif '/users/' in filepath:
        return 'User'

    # Check Kubernetes-style resources
    if 'apiVersion' in data and 'kind' in data:
        return data['kind']  # Deployment, Service, ConfigMap, etc.

    # Check common field combinations
    if 'name' in data and 'owner' in data and 'endpoints' in data:
        return 'Service'
    elif 'name' in data and 'cluster' in data and 'namespace' in data:
        return 'Namespace'

    # Default: use directory name
    return os.path.basename(os.path.dirname(filepath)).capitalize()
```

#### Field Extraction Strategy

```python
def extract_all_fields(data, urn, entity_type):
    """Extract every field recursively."""
    entity = {
        "@id": urn,
        "@type": entity_type
    }

    for key, value in data.items():
        # Skip metadata fields
        if key in ['$schema', 'apiVersion', 'kind']:
            continue

        # Handle nested objects (create sub-entities)
        if isinstance(value, dict) and has_identity(value):
            sub_entity = extract_sub_entity(value, urn, key)
            entity[key] = {"@id": sub_entity["@id"]}

        # Handle arrays
        elif isinstance(value, list):
            entity[key] = extract_array(value, urn, key)

        # Simple values
        else:
            entity[key] = value

    return entity
```

### Naming Requirements

**CRITICAL**: ALL entities MUST have these predicates:

```json
{
  "@id": "urn:entity:unique-id",
  "@type": "EntityType",
  "name": "Human Readable Name"
}
```

Entities without names will appear as hex IDs in graph visualizations.

#### Mandatory Name/Type Validation

**ENFORCE BEFORE EXTRACTION**: Every entity MUST be validated before being added to the graph.

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
            raise ValueError(f"Entity {entity.get('@id', 'unknown')} missing @type in {filepath}")

    if "name" not in entity or not entity["name"]:
        # Attempt name fallback before failing
        entity["name"] = generate_fallback_name(entity, filepath)
        if not entity["name"]:
            raise ValueError(f"Entity {entity['@id']} missing name in {filepath}")

    return entity
```

#### Fallback Naming Strategies

When `name` field is missing or empty in source data, use these fallback strategies **in order**:

**Strategy 1: Extract from URN**

```python
def extract_name_from_urn(urn):
    """Extract human-readable name from URN last segment."""
    # urn:service:my-service → "my-service"
    # urn:namespace:prod:app-sre → "app-sre"
    segments = urn.split(':')
    last_segment = segments[-1]

    # Convert kebab-case/snake_case to Title Case
    name = last_segment.replace('-', ' ').replace('_', ' ').title()
    return name
```

**Strategy 2: Use Schema Entity Type**

```python
def name_from_type_and_identifier(entity_type, identifier):
    """Generate name from type and unique identifier."""
    # For entities like ConfigMap, Secret where URN contains meaningful info
    # urn:k8s-configmap:namespace:config-name → "Config Name (ConfigMap)"
    clean_id = identifier.replace('-', ' ').title()
    return f"{clean_id} ({entity_type})"
```

**Strategy 3: Extract from File Path**

```python
def extract_name_from_filepath(filepath):
    """Derive name from file location patterns."""
    # /services/cincinnati/app.yml → "Cincinnati"
    # /namespaces/production/config.yml → "Production"

    path_parts = filepath.split('/')

    # Check common patterns
    if '/services/' in filepath:
        # Get service name from directory
        service_idx = path_parts.index('services') + 1
        if service_idx < len(path_parts):
            return path_parts[service_idx].replace('-', ' ').title()

    # Generic: use parent directory name
    parent_dir = path_parts[-2] if len(path_parts) > 1 else path_parts[-1]
    return parent_dir.replace('-', ' ').title()
```

**Strategy 4: Composite Field Name**

```python
def generate_composite_name(entity, data):
    """Build name from multiple fields when single 'name' field absent."""

    # Pattern: namespace + kind (Kubernetes resources)
    if 'namespace' in data and 'kind' in data:
        ns = data['namespace']
        kind = data['kind']
        resource_name = data.get('metadata', {}).get('name', 'unknown')
        return f"{resource_name} ({kind} in {ns})"

    # Pattern: host + path (Endpoints)
    if 'host' in data and 'path' in data:
        return f"{data['host']}{data['path']}"

    # Pattern: owner + resource type
    if 'owner' in data and '@type' in entity:
        return f"{data['owner']}'s {entity['@type']}"

    return None
```

**Implementation in Extraction**:

```python
def extract_entity(data, filepath, schema_config):
    """Extract entity with guaranteed name field."""

    # Normal extraction
    entity = {
        "@id": generate_urn(schema_config['urn_pattern'], data),
        "@type": schema_config['entity_type']
    }

    # Try to get name from data
    name = get_nested_field(data, 'name')

    # Apply fallback strategies if name missing
    if not name:
        name = (
            extract_name_from_urn(entity["@id"]) or
            extract_name_from_filepath(filepath) or
            name_from_type_and_identifier(entity["@type"], entity["@id"]) or
            generate_composite_name(entity, data)
        )

    if not name:
        # FAIL EXTRACTION - do not add entity without name
        log_error(f"Cannot generate name for entity in {filepath}")
        return None

    entity["name"] = name

    # Extract remaining fields...
    return entity
```

#### Type Inference Patterns

When `@type` is missing, infer from context:

**Pattern 1: URN-Based Inference**

```python
def infer_type_from_urn(urn):
    """Infer entity type from URN structure."""
    # urn:service:X → "Service"
    # urn:namespace:Y → "Namespace"
    # urn:k8s-deployment:Z → "Deployment"

    if not urn.startswith('urn:'):
        return None

    type_segment = urn.split(':')[1]

    # Convert URN prefix to entity type
    type_mapping = {
        'service': 'Service',
        'namespace': 'Namespace',
        'dependency': 'Dependency',
        'k8s-service': 'K8sService',
        'k8s-deployment': 'Deployment',
        'k8s-configmap': 'ConfigMap',
        'k8s-route': 'Route',
        'cluster': 'Cluster',
        'user': 'User',
        'role': 'Role',
        'aws-account': 'AWSAccount'
    }

    return type_mapping.get(type_segment.lower())
```

**Pattern 2: Schema Field Inference**

```python
def infer_type_from_schema_field(data):
    """Extract type from $schema field in YAML."""
    # $schema: /dependencies/dependency-1.yml → "Dependency"
    # $schema: /app/app-1.yml → "Service"

    schema_ref = data.get('$schema', '')
    if not schema_ref:
        return None

    schema_mapping = {
        '/app/': 'Service',
        '/dependencies/': 'Dependency',
        '/namespace/': 'Namespace',
        '/cluster/': 'Cluster',
        '/aws/': 'AWSAccount',
        '/user/': 'User',
        '/role/': 'Role'
    }

    for pattern, entity_type in schema_mapping.items():
        if pattern in schema_ref:
            return entity_type

    return None
```

**Pattern 3: File Path Inference**

```python
def infer_type_from_filepath(filepath):
    """Infer entity type from file location."""
    # /services/foo/app.yml → "Service"
    # /namespaces/bar.yml → "Namespace"

    path_mapping = {
        '/services/': 'Service',
        '/namespaces/': 'Namespace',
        '/dependencies/': 'Dependency',
        '/clusters/': 'Cluster',
        '/aws/': 'AWSAccount',
        '/users/': 'User',
        '/roles/': 'Role'
    }

    for pattern, entity_type in path_mapping.items():
        if pattern in filepath:
            return entity_type

    return None
```

**Pattern 4: Kubernetes Kind Field**

```python
def infer_type_from_kubernetes_kind(data):
    """Use Kubernetes 'kind' field as entity type."""
    # kind: Deployment → @type: "Deployment"
    # kind: Service → @type: "K8sService" (to avoid conflict with app Service)

    if 'kind' not in data:
        return None

    kind = data['kind']

    # Avoid conflicts with business entity types
    if kind == 'Service':
        return 'K8sService'

    return kind
```

**Consolidated Type Inference**:

```python
def infer_type_from_context(entity, filepath, data=None):
    """Try all type inference strategies."""

    inferred_type = (
        infer_type_from_urn(entity.get("@id", "")) or
        (infer_type_from_schema_field(data) if data else None) or
        (infer_type_from_kubernetes_kind(data) if data else None) or
        infer_type_from_filepath(filepath)
    )

    if inferred_type:
        log_info(f"Inferred type '{inferred_type}' for {entity.get('@id', filepath)}")

    return inferred_type
```

### Sub-Entity Pattern

For complex nested structures, create separate entities:

```json
// Before (nested)
{
  "@id": "urn:service:foo",
  "codeComponents": [
    {"name": "api", "url": "https://github.com/org/api", "language": "Go"},
    {"name": "ui", "url": "https://github.com/org/ui", "language": "React"}
  ]
}

// After (sub-entities)
{
  "@id": "urn:service:foo",
  "hasCodeComponent": [
    {"@id": "urn:code-component:foo:api"},
    {"@id": "urn:code-component:foo:ui"}
  ]
}

{
  "@id": "urn:code-component:foo:api",
  "@type": "CodeComponent",
  "name": "api",
  "url": "https://github.com/org/api",
  "language": "Go",
  "parentService": {"@id": "urn:service:foo"}
}

{
  "@id": "urn:code-component:foo:ui",
  "@type": "CodeComponent",
  "name": "ui",
  "url": "https://github.com/org/ui",
  "language": "React",
  "parentService": {"@id": "urn:service:foo"}
}
```

**When to create sub-entities:**

- Multiple properties per item (3+)
- Items need independent queries ("find all Go code components")
- Items have relationships to other entities

**When to use simple arrays:**

- Simple key-value pairs
- Purely descriptive data
- No additional relationships

### URN Design

URNs uniquely identify entities. Follow these patterns:

| Pattern                 | Example                                   | Use Case                          |
| ----------------------- | ----------------------------------------- | --------------------------------- |
| `urn:type:name`         | `urn:service:cincinnati`                  | Simple entities with unique names |
| `urn:type:parent:name`  | `urn:namespace:prod:app-sre`              | Entities scoped to parent         |
| `urn:type:compound-key` | `urn:endpoint:api.example.com/v1/metrics` | Composite unique identifier       |
| `urn:type:path-based`   | `urn:resource:services/foo/config.yaml`   | File-based entities               |

**Requirements:**

- Globally unique across all entity types
- Stable (doesn't change when non-key fields update)
- Human-readable (can infer entity from URN)
- URL-encoded if containing special characters

### Validation Checkpoints

After each batch:

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

    # Calculate completeness metrics
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


def validate_entity_quality(entities):
    """Additional quality checks beyond mandatory fields."""

    quality_report = {
        'entities_with_descriptions': 0,
        'entities_with_relationships': 0,
        'total_relationships': 0,
        'orphaned_entities': [],
        'sparse_entities': []  # Entities with < 3 fields
    }

    for entity in entities:
        # Check description presence
        if 'description' in entity:
            quality_report['entities_with_descriptions'] += 1

        # Count relationships
        relationship_count = 0
        for key, value in entity.items():
            if isinstance(value, dict) and "@id" in value:
                relationship_count += 1
            elif isinstance(value, list):
                refs = [v for v in value if isinstance(v, dict) and "@id" in v]
                relationship_count += len(refs)

        if relationship_count > 0:
            quality_report['entities_with_relationships'] += 1
            quality_report['total_relationships'] += relationship_count
        else:
            quality_report['orphaned_entities'].append(entity["@id"])

        # Check field count (excluding @id, @type, name)
        field_count = len([k for k in entity.keys() if k not in ['@id', '@type', 'name']])
        if field_count < 3:
            quality_report['sparse_entities'].append({
                'id': entity["@id"],
                'field_count': field_count
            })

    total = len(entities)
    print(f"\n📊 Quality Metrics:")
    print(f"  With descriptions: {quality_report['entities_with_descriptions']}/{total} " +
          f"({100*quality_report['entities_with_descriptions']/total:.1f}%)")
    print(f"  With relationships: {quality_report['entities_with_relationships']}/{total} " +
          f"({100*quality_report['entities_with_relationships']/total:.1f}%)")
    print(f"  Total relationships: {quality_report['total_relationships']}")
    print(f"  Orphaned entities: {len(quality_report['orphaned_entities'])}")
    print(f"  Sparse entities (< 3 fields): {len(quality_report['sparse_entities'])}")

    return quality_report
```

---

## Phase 3: Relationship Resolution

**Goal**: Validate all references resolve to actual entities and create bidirectional edges.

### Step 1: Collect All Entity URNs

```python
def collect_all_urns(jsonld_file):
    """Build index of all entity URNs."""
    urns = set()

    for entity in load_jsonld(jsonld_file):
        urns.add(entity["@id"])

    return urns
```

### Step 2: Validate References

```python
def validate_references(jsonld_file, known_urns):
    """Check all references point to existing entities."""

    broken_refs = []

    for entity in load_jsonld(jsonld_file):
        for key, value in entity.items():
            # Check @id references
            if isinstance(value, dict) and "@id" in value:
                if value["@id"] not in known_urns:
                    broken_refs.append({
                        'source': entity["@id"],
                        'predicate': key,
                        'target': value["@id"]
                    })

            # Check arrays of references
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "@id" in item:
                        if item["@id"] not in known_urns:
                            broken_refs.append({
                                'source': entity["@id"],
                                'predicate': key,
                                'target': item["@id"]
                            })

    if broken_refs:
        print(f"❌ Found {len(broken_refs)} broken references:")
        for ref in broken_refs[:10]:
            print(f"  {ref['source']} --{ref['predicate']}--> {ref['target']}")
        raise ValueError("Broken references found - extraction incomplete")

    print(f"✅ All {count_references(jsonld_file)} references valid")
```

### Step 3: Create Bidirectional Edges

For navigability, create reverse relationships:

```python
def add_reverse_edges(entities):
    """Create bidirectional relationships."""

    reverse_map = {
        'belongsTo': 'hasNamespace',
        'dependsOn': 'requiredBy',
        'ownedBy': 'owns',
        'partOf': 'hasPart',
        'uses': 'usedBy'
    }

    new_edges = []

    for entity in entities:
        for key, value in entity.items():
            if key in reverse_map and isinstance(value, dict) and "@id" in value:
                # Create reverse edge
                target_id = value["@id"]
                reverse_predicate = reverse_map[key]

                new_edges.append({
                    'source': target_id,
                    'predicate': reverse_predicate,
                    'target': entity["@id"]
                })

    # Apply reverse edges to entities
    for edge in new_edges:
        target_entity = find_entity(entities, edge['source'])
        if edge['predicate'] not in target_entity:
            target_entity[edge['predicate']] = []
        target_entity[edge['predicate']].append({"@id": edge['target']})

    print(f"✅ Added {len(new_edges)} bidirectional edges")
    return entities
```

### Step 4: Infer Implicit Relationships

Create relationships not explicitly defined in data:

```python
def infer_relationships(entities):
    """Infer relationships from patterns."""

    inferred = []

    # Pattern 1: File path implies namespace
    # /services/cincinnati/namespaces/prod.yaml → cincinnati owns prod namespace
    for entity in entities:
        if entity["@type"] == "Namespace":
            path = entity.get("_source_file", "")
            service_match = re.search(r'/services/([^/]+)/', path)
            if service_match:
                service_name = service_match.group(1)
                service_urn = f"urn:service:{service_name}"

                if service_urn in known_urns:
                    inferred.append({
                        'source': service_urn,
                        'predicate': 'hasNamespace',
                        'target': entity["@id"],
                        'reason': 'file_path_structure'
                    })

    # Pattern 2: Label matching
    # metadata.labels.service = "foo" → links to urn:service:foo
    for entity in entities:
        if entity["@type"] == "Route":
            service_label = entity.get("serviceLabel")
            if service_label:
                service_urn = f"urn:service:{service_label}"
                if service_urn in known_urns:
                    inferred.append({
                        'source': service_urn,
                        'predicate': 'exposedViaRoute',
                        'target': entity["@id"],
                        'reason': 'label_matching'
                    })

    # Pattern 3: Name similarity (fuzzy matching)
    # Use with caution - validate inferences

    print(f"✅ Inferred {len(inferred)} implicit relationships")
    return inferred
```

### Validation Report

Generate comprehensive statistics:

```python
def generate_validation_report(entities):
    """Final validation and statistics."""

    stats = {
        'total_entities': len(entities),
        'entity_types': {},
        'total_relationships': 0,
        'relationship_types': {},
        'entities_without_names': [],
        'orphaned_entities': []  # Entities with no relationships
    }

    for entity in entities:
        # Count by type
        entity_type = entity["@type"]
        stats['entity_types'][entity_type] = stats['entity_types'].get(entity_type, 0) + 1

        # Check for name
        if "name" not in entity:
            stats['entities_without_names'].append(entity["@id"])

        # Count relationships
        relationship_count = 0
        for key, value in entity.items():
            if isinstance(value, dict) and "@id" in value:
                relationship_count += 1
                stats['relationship_types'][key] = stats['relationship_types'].get(key, 0) + 1
            elif isinstance(value, list):
                refs = [v for v in value if isinstance(v, dict) and "@id" in v]
                relationship_count += len(refs)
                stats['relationship_types'][key] = stats['relationship_types'].get(key, 0) + len(refs)

        stats['total_relationships'] += relationship_count

        if relationship_count == 0:
            stats['orphaned_entities'].append(entity["@id"])

    # Print report
    print("\n=== VALIDATION REPORT ===")
    print(f"\nTotal Entities: {stats['total_entities']}")
    print(f"Total Relationships: {stats['total_relationships']}")

    print(f"\nEntities by Type:")
    for entity_type, count in sorted(stats['entity_types'].items(), key=lambda x: -x[1]):
        print(f"  {entity_type}: {count}")

    print(f"\nRelationships by Type:")
    for rel_type, count in sorted(stats['relationship_types'].items(), key=lambda x: -x[1]):
        print(f"  {rel_type}: {count}")

    if stats['entities_without_names']:
        print(f"\n❌ WARNING: {len(stats['entities_without_names'])} entities without names")
        for urn in stats['entities_without_names'][:10]:
            print(f"  {urn}")

    if stats['orphaned_entities']:
        print(f"\n⚠️  {len(stats['orphaned_entities'])} orphaned entities (no relationships)")

    return stats
```

---

## Phase 3.5: Graph Validation & Repair

**Goal**: Validate graph integrity and repair broken references before loading into database.

**Why Critical**: Relationships often reference URNs that weren't extracted as entities, creating unnamed nodes in visualizations. This phase catches and fixes these issues.

### Common Graph Issues

1. **Broken References** (CRITICAL): Relationships pointing to non-existent entities
   - Symptom: Unnamed nodes in visualizer, queries returning incomplete data
   - Cause: Constructed URN doesn't match extracted entity URN
   - Example: Route `routesTo` `urn:k8s-service:...` but that Service wasn't extracted

2. **Missing Metadata**: Entities without name or type
   - Symptom: Empty nodes, failed validations
   - Cause: Extraction logic skipped required fields

3. **Duplicate URNs**: Same entity appears multiple times
   - Symptom: Inconsistent data, wasted storage
   - Cause: Multiple extraction paths hit same entity

4. **Circular References**: Entity references itself
   - Symptom: Infinite loops in traversal
   - Cause: Parent/child relationships with errors

### Validation Script

Use `validate_graph.py` to check graph integrity:

```bash
# Validate only (from extraction directory)
python validate_graph.py --input working/knowledge_graph.jsonld

# Validate and repair broken references
python validate_graph.py --input working/knowledge_graph.jsonld \
    --repair \
    --output working/knowledge_graph_repaired.jsonld
```

### What the Repair Does

1. **Scans all relationships**: Builds index of all referenced URNs
2. **Identifies broken refs**: Compares references against actual entities
3. **Reports missing entities**: Shows which URNs are referenced but don't exist

**Important**: The repair function creates stub entities as a temporary measure. For production graphs, you should instead:

- Extract the actual source entities if they exist in the repository
- Link to external resources (ResourceTemplates, Git repos) if entities are deployed dynamically
- Remove invalid references if they point to non-existent resources

### Validation Output Example

```
🔍 Validating 4672 entities...
  Found 4670 unique entity URNs
  Found 2074 unique referenced URNs

❌ ERRORS:
Found 732 broken references:
  ❌ urn:k8s-service:cluster-scope:cincinnati-policy-engine
     Referenced by: urn:k8s-route:cluster-scope:cincinnati (routesTo)
  ...

🔧 Repairing broken references...
  Created 732 stub entities

✅ Repaired graph saved (5404 entities)
```

### Best Practices for Preventing Issues

1. **Validate URN Construction**:

   ```python
   # ❌ Bad: Constructing URN without verifying entity exists
   route["routesTo"] = {"@id": f"urn:k8s-service:{namespace}:{service_name}"}

   # ✅ Good: Check if entity exists first
   service_urn = f"urn:k8s-service:{namespace}:{service_name}"
   if service_urn in entity_index:
       route["routesTo"] = {"@id": service_urn}
   else:
       print(f"⚠️  Service {service_urn} not found, skipping relationship")
   ```

2. **Build Entity Index First**:

   ```python
   # Build index before creating relationships
   entity_index = {entity["@id"]: entity for entity in entities}

   # Use index to validate relationships
   for entity in entities:
       for relationship in get_relationships(entity):
           target_urn = relationship["@id"]
           if target_urn not in entity_index:
               print(f"⚠️  Broken reference: {target_urn}")
   ```

3. **Extract Both Sides or Link to External Resources**:
   - **Option A**: Extract both entities if they exist in the repository
   - **Option B**: Extract deployment source metadata if entity is deployed from external source

   **When to use Option A** (extract both entities):
   - Both entities are defined in the repository
   - Example: Service YAML file exists alongside Route YAML file

   **When to use Option B** (link to deployment source):
   - Target entity is deployed dynamically (Kubernetes from templates, Terraform resources, etc.)
   - Entity definition exists in external Git repo
   - Entity is generated at runtime

   **Option B Pattern** (repository-specific):

   ```python
   # Determine WHERE the missing entity is actually defined
   # Common patterns:
   #   - Kubernetes: Templates in external Git repo (via SaaS/ArgoCD/Flux)
   #   - Terraform: Modules from terraform registry or Git
   #   - Helm: Charts from chart repositories
   #   - Serverless: Functions defined in separate repos

   # Extract metadata about the deployment source
   deployment_source = {
       "@id": "urn:deployment-source:{unique-id}",
       "@type": "DeploymentSource",  # Or more specific: ResourceTemplate, TerraformModule, HelmChart
       "name": "{source-name}",
       "repositoryUrl": "{git-repo-url}",
       "sourcePath": "{path-to-template-or-module}",
       "deploymentTool": "{saas|terraform|helm|kustomize|argocd}"
   }

   # Link the referencing entity to the deployment source
   referencing_entity["deployedVia"] = {"@id": "urn:deployment-source:{unique-id}"}
   ```

   **Concrete Examples by Repository Type**:
   - **app-interface**: Extract ResourceTemplate from SaaS files (`resourceTemplates` field)
   - **Terraform repo**: Extract TerraformModule from `module` blocks in \*.tf files
   - **Kubernetes repo with Helm**: Extract HelmChart from Chart.yaml dependencies
   - **ArgoCD repo**: Extract GitRepository from Application specs

4. **Use Validation in CI/CD**:

   ```bash
   # Fail build if validation errors
   python validate_graph.py --input graph.jsonld || exit 1
   ```

### Resolving Broken References - Best Practices

When validation finds broken references, determine the root cause:

1. **Entity Exists in Repository**:
   - Update extraction logic to capture the missing entity
   - Re-run extraction batch
   - Example: Missing Role files in `/data/teams/*/roles/`

2. **Entity is Deployed Dynamically** (from external sources):
   - **Identify the external source**: Git repo, template system, IaC tool (Terraform, Helm, etc.)
   - **Extract source metadata entities**: Create entities representing the external deployment source
   - **Link references to source entities**: Instead of broken reference → missing entity, use reference → source entity

   **Pattern to implement (repository-specific)**:

   ```python
   # 1. Find files that define external sources
   #    - app-interface: SaaS files with resourceTemplates
   #    - Terraform: module sources in *.tf
   #    - Helm: Chart.yaml with repository field
   #    - Kubernetes: Kustomization files with remote bases

   # 2. Extract source metadata
   source_entity = {
       "@id": "urn:deployment-source:unique-id",
       "@type": "DeploymentSource",  # Or ResourceTemplate, TerraformModule, HelmChart
       "name": "source-name",
       "repositoryUrl": "https://github.com/org/repo",
       "sourcePath": "/path/to/template",
       "deploymentTool": "saas|terraform|helm|kustomize"
   }

   # 3. Link referencing entity to source
   referencing_entity["deployedBy"] = {"@id": "urn:deployment-source:unique-id"}
   ```

   **Claude: For repositories with SaaS deployment files**, generate a script to extract ResourceTemplate entities. Use argparse for input/output paths. Follow the DeploymentSource pattern above.

3. **Reference is Invalid**:
   - Remove the broken reference from the source entity
   - Update extraction logic to validate references
   - Example: References to deleted/renamed entities

**Never rely on stub entities in production** - they lack metadata and break the "link to actual data" principle

---

## Phase 4: Graph Export

**Goal**: Export validated entities to JSON-LD format and load into graph database.

### JSON-LD Format Specification

```json
{
  "@context": {
    "@vocab": "http://example.org/vocab#",
    "urn": "http://example.org/entity/",
    "name": "http://schema.org/name",
    "description": "http://schema.org/description",
    "owner": "http://schema.org/owner",
    "dependsOn": {
      "@id": "http://example.org/vocab#dependsOn",
      "@type": "@id"
    },
    "belongsTo": {
      "@id": "http://example.org/vocab#belongsTo",
      "@type": "@id"
    }
  },
  "@graph": [
    {
      "@id": "urn:service:cincinnati",
      "@type": "Service",
      "name": "Cincinnati",
      "description": "OpenShift Update Service",
      "owner": [{ "name": "John Doe", "email": "jdoe@example.com" }],
      "dependsOn": [
        { "@id": "urn:dependency:github" },
        { "@id": "urn:dependency:aws" }
      ],
      "belongsTo": { "@id": "urn:product:openshift" }
    },
    {
      "@id": "urn:dependency:github",
      "@type": "Dependency",
      "name": "GitHub",
      "description": "Source code hosting",
      "sla": "99.95"
    }
  ]
}
```

### Export Process

```python
def export_to_jsonld(entities, output_file):
    """Export entities to JSON-LD format."""

    # Define context
    context = {
        "@vocab": "http://example.org/vocab#",
        "urn": "http://example.org/entity/"
    }

    # Add relationship type definitions
    for rel_type in get_all_relationship_types(entities):
        context[rel_type] = {
            "@id": f"http://example.org/vocab#{rel_type}",
            "@type": "@id"
        }

    # Build JSON-LD document
    document = {
        "@context": context,
        "@graph": entities
    }

    # Write to file
    with open(output_file, 'w') as f:
        json.dump(document, f, indent=2)

    print(f"✅ Exported {len(entities)} entities to {output_file}")

    # Validate JSON-LD syntax
    validate_jsonld(output_file)
```

### Loading into Dgraph

Use the provided `load_dgraph.py` script:

```bash
# From extraction directory
python load_dgraph.py \
  --input working/knowledge_graph.jsonld \
  --dgraph-url http://localhost:8080 \
  --drop-all  # Optional: clear existing data
```

See [load_dgraph.py](#load_dgraphpy) for implementation.

### Loading into Neo4j

Use the provided `load_neo4j.py` script:

```bash
# From extraction directory
python load_neo4j.py \
  --input working/knowledge_graph.jsonld \
  --neo4j-uri bolt://localhost:7687 \
  --username neo4j \
  --password your_password \
  --clear  # Optional: clear existing data
```

See [load_neo4j.py](#load_neo4jpy) for implementation.

---

## Best Practices

### 1. Entity Naming

**Rule**: ALL entities MUST have these predicates:

```json
{
  "@id": "urn:entity:unique-id",
  "@type": "EntityType",
  "name": "Human Readable Name"
}
```

**Why**: Entities without names appear as hex IDs (internal database UIDs) in visualizations.

**Exceptions**: Composite entities where the URN itself is descriptive may omit `name`:

```json
{
  "@id": "urn:endpoint:api.example.com/v1/metrics",
  "@type": "Endpoint",
  "host": "api.example.com",
  "path": "/v1/metrics",
  "fullUrl": "https://api.example.com/v1/metrics"
}
```

### 2. Extract Maximum Detail

**Philosophy**: "When in doubt, extract it."

Future queries are unpredictable. Extract ALL meaningful fields now, filter during queries.

❌ **Minimal** (only obvious fields):

```json
{
  "@id": "urn:dependency:github",
  "@type": "Dependency",
  "name": "GitHub"
}
```

✅ **Maximum Fidelity** (everything):

```json
{
  "@id": "urn:dependency:github",
  "@type": "Dependency",
  "name": "GitHub",
  "description": "GitHub is a development platform...",
  "statefulness": "Durable",
  "opsModel": "External",
  "statusPage": "https://www.githubstatus.com/",
  "sla": "99.95",
  "dependencyFailureImpact": "Major Outage",
  "monitoringProvider": "resource-template",
  "monitoringPath": "/observability/prometheus/...",
  "monitoringNamespace": { "@id": "urn:namespace:observability-prod" }
}
```

**Benefits**:

- Answers more questions without re-extraction
- Richer context for incident response
- Better analytics and reporting

### 3. Validation Checkpoints

Validate after EACH phase, not just at the end:

```python
# After Phase 0: Discovery
assert len(identified_entity_types) > 0, "No entities identified"

# After Phase 1: Schema Analysis
assert schema_catalog_valid(), "Invalid schema catalog"

# After each extraction batch
validate_batch(entities)

# After Phase 3: Relationship Resolution
assert broken_references == 0, f"{broken_references} broken refs found"

# After Phase 4: Export
validate_jsonld(output_file)
```

**Why**: Fail fast. Finding errors early saves hours of debugging.

### 4. URN Design Principles

| Principle           | Good Example                        | Bad Example                              |
| ------------------- | ----------------------------------- | ---------------------------------------- |
| **Globally Unique** | `urn:service:cincinnati`            | `service:cincinnati` (missing namespace) |
| **Human Readable**  | `urn:user:john-doe`                 | `urn:user:a3b8c9d2` (UUID)               |
| **Stable**          | `urn:cluster:prod-us-east-1`        | `urn:cluster:12345` (auto-increment)     |
| **Hierarchical**    | `urn:code-component:cincinnati:api` | `urn:code-component:api-v2-final`        |

### 5. Sub-Entity Guidelines

**Create separate entities when:**

- Item has 3+ properties
- Item needs independent queries
- Item has relationships to other entities

**Use simple arrays when:**

- Simple key-value pairs
- Purely descriptive data
- No additional relationships

Example:

```json
// ✅ Simple array (owners are just metadata)
{
  "@id": "urn:service:foo",
  "owner": [
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"}
  ]
}

// ✅ Sub-entities (code components have multiple relationships)
{
  "@id": "urn:service:foo",
  "hasCodeComponent": [
    {"@id": "urn:code-component:foo:api"},
    {"@id": "urn:code-component:foo:ui"}
  ]
}

{
  "@id": "urn:code-component:foo:api",
  "@type": "CodeComponent",
  "name": "api",
  "url": "https://github.com/org/api",
  "language": "Go",
  "maintainer": {"@id": "urn:user:alice"},
  "parentService": {"@id": "urn:service:foo"}
}
```

### 6. Relationship Resolution Order

Extract entities in dependency order:

```
1. Leaf entities (no dependencies)
   └─> Clusters, AWSAccounts, Products

2. Infrastructure entities
   └─> Namespaces, Environments

3. Application entities
   └─> Services, Databases, Caches

4. Access control
   └─> Users, Roles, Permissions

5. Observability
   └─> SLOs, Alerts, Dashboards
```

**Why**: Prevents broken references. If Service depends on Namespace, extract Namespace first.

### 7. Handle Schema Drift

Real-world schemas don't always match reality:

```python
def extract_with_schema_fallback(file, schema):
    """Try schema-driven, fall back to heuristic."""
    try:
        return extract_by_schema(file, schema)
    except SchemaValidationError as e:
        log_warning(f"Schema mismatch in {file}: {e}")
        return extract_by_heuristic(file)
```

### 8. Batch Processing

For large repositories (10,000+ files), process in batches:

```python
BATCH_SIZE = 1000

for i in range(0, len(files), BATCH_SIZE):
    batch = files[i:i+BATCH_SIZE]
    entities = extract_batch(batch)
    validate_batch(entities)
    append_to_jsonld(entities, output_file)
    print(f"Processed {i+len(batch)}/{len(files)} files")
```

### 9. Incremental Updates

For ongoing repositories, track changes:

```python
# Track file modification times
def needs_reextraction(file, last_run_time):
    return os.path.getmtime(file) > last_run_time

# Re-extract only changed files
changed_files = [f for f in all_files if needs_reextraction(f, last_run)]
entities = extract_files(changed_files)

# Merge with existing graph
merge_into_graph(entities, existing_graph)
```

### 10. Error Handling

Don't let single file errors stop entire extraction:

```python
def extract_all_files(files):
    entities = []
    errors = []

    for file in files:
        try:
            entity = extract_file(file)
            entities.append(entity)
        except Exception as e:
            errors.append({'file': file, 'error': str(e)})
            continue  # Keep going

    if errors:
        print(f"⚠️  {len(errors)} files failed:")
        for err in errors[:10]:
            print(f"  {err['file']}: {err['error']}")

    print(f"✅ Successfully extracted {len(entities)} entities")
    return entities, errors
```

---

## Case Studies

### Case Study 1: App-Interface Repository (Detailed Example)

**Repository**: Red Hat's app-interface - 10,882 YAML configuration files for OpenShift services

**Structure**:

```
app-interface/
├── qontract-schemas/       # 156 JSON Schema files
├── data/
│   ├── services/           # 3,541 service definitions
│   ├── dependencies/       # 799 dependency configs
│   ├── aws/                # 729 AWS resources
│   ├── teams/              # ~800 team definitions
│   └── ...
└── resources/              # 3,225 Kubernetes manifests
    ├── routes/
    ├── configmaps/
    └── ...
```

#### Phase 0: Discovery

```bash
# File inventory
$ find . -name "*.yml" -o -name "*.yaml" | wc -l
14107

# Schema detection
$ find qontract-schemas/schemas -name "*.yml" | wc -l
156

# Sample analysis
$ head data/services/cincinnati/app.yml
```

**Decision**: Schema-driven extraction (156 schemas available).

#### Phase 1: Schema Analysis

Built schema catalog mapping 156 schemas to entity types:

```json
{
  "schemas": [
    {
      "schema_file": "/schemas/app-1.yml",
      "entity_type": "Service",
      "urn_pattern": "urn:service:{name}",
      "required_predicates": ["name", "description", "serviceOwners"],
      "optional_predicates": ["grafanaUrl", "slackChannel", "sopsUrl"],
      "relationships": [
        {
          "field": "dependencies[].$ref",
          "target_type": "Dependency",
          "predicate": "dependsOn"
        },
        {
          "field": "product.$ref",
          "target_type": "Product",
          "predicate": "partOf"
        }
      ],
      "file_pattern": "data/services/**/app.yml"
    },
    {
      "schema_file": "/schemas/namespace-1.yml",
      "entity_type": "Namespace",
      "urn_pattern": "urn:namespace:{name}",
      "required_predicates": ["name", "cluster", "app"],
      "relationships": [
        {
          "field": "cluster.$ref",
          "target_type": "Cluster",
          "predicate": "runsOn"
        },
        {
          "field": "app.$ref",
          "target_type": "Service",
          "predicate": "belongsTo"
        }
      ],
      "file_pattern": "data/services/**/namespaces/*.yml"
    }
  ]
}
```

#### Phase 2: Entity Extraction (15 Batches)

**Batch 1-3**: Core entities (Services, Namespaces, Clusters, CI/CD, SLOs)

- 59 Services
- 146 Namespaces
- 82 Clusters
- 200 SaaS deployments
- 119 SLOs

**Batch 4-8**: Access & Cloud (Users, Roles, AWS, Dependencies)

- 1,764 Users
- 465 Roles
- 105 AWS Accounts
- **15 Dependency services** (GitHub, AWS, OpenShift, etc.)

**Batch 9-14**: Kubernetes Resources (Routes, ConfigMaps, Prometheus)

- 121 Routes
- 107 ConfigMaps
- 238 PrometheusRules
- 1,028 Alert definitions

**Total**: 6,332 entities extracted

#### Example Extraction: Dependency Service

From `data/dependencies/github/service.yml`:

```yaml
# Source file
$schema: /dependencies/dependency-1.yml
name: GitHub
description: |
  GitHub is a development platform inspired by the way you work...
statefulness: Durable
opsModel: External
statusPage: https://www.githubstatus.com/
SLA: 99.95
dependencyFailureImpact: Major Outage
monitoringProvider: resource-template
monitoringPath: /observability/prometheus/...
monitoringNamespace:
  $ref: /services/app-sre-observability/namespaces/production.yml
```

Extracted to JSON-LD:

```json
{
  "@id": "urn:dependency:github",
  "@type": "Dependency",
  "name": "GitHub",
  "description": "GitHub is a development platform inspired by the way you work...",
  "statefulness": "Durable",
  "opsModel": "External",
  "statusPage": "https://www.githubstatus.com/",
  "sla": "99.95",
  "dependencyFailureImpact": "Major Outage",
  "monitoringProvider": "resource-template",
  "monitoringPath": "/observability/prometheus/...",
  "monitoringNamespace": {
    "@id": "urn:namespace:app-sre-observability-production"
  }
}
```

#### Phase 3: Relationship Resolution

**Reference Resolution**:

- 28,259 relationships validated
- 0 broken references
- All `$ref` patterns resolved to URNs

**Bidirectional Edges** (1,634 added):

- `dependsOn` ↔ `requiredBy`
- `belongsTo` ↔ `hasNamespace`
- `runsOn` ↔ `hostsNamespace`

**Inferred Relationships** (269 added):

- File paths: `/services/cincinnati/namespaces/prod.yml` → `cincinnati hasNamespace prod`
- Labels: `metadata.labels.service: cincinnati` → `cincinnati exposedViaRoute route-123`
- Image references: `image: quay.io/app-sre/cincinnati` → `cincinnati usesImage cincinnati-image`

#### Phase 4: Export & Load

**Output**:

- `extraction/working/knowledge_graph.jsonld`: 82,863 triples (9.6 MB)
- Loaded into Dgraph: 81,087 triples (1,776 complex PromQL expressions skipped)

**Final Statistics**:

```
Total Entities: 6,332
Total Relationships: 28,259

Top Entity Types:
  User: 1,764
  Alert: 1,028
  ExternalResource: 496
  Role: 465
  Component: 406
  Namespace: 146
  Service: 59
```

#### Lessons Learned

1. **Missing Batch Discovery**: Batch 6 (Dependencies) was planned but not executed initially. Dependencies appeared as unnamed hex IDs in visualizer. **Fix**: Always validate that ALL planned batches are executed.

2. **Dgraph Predicate Indexing**: Dgraph CAN index predicates containing colons (`:`) when wrapped in angle brackets. Predicates must use format `<predicate>: type @index(indexType) .` in schema. Key predicates (name, \_type, url, email, id, path, namespace) should be indexed for performance. **Performance**: Indexed queries are ~10x faster than filter-based queries.

3. **Complex PromQL Expressions**: PromQL with nested quotes and `{{}}` broke RDF parser. **Solution**: Skip during conversion (2% data loss acceptable for expressions).

4. **Schema Drift**: Some YAML files didn't match their schemas (Jira instances, Vault configs). **Solution**: Graceful fallback to heuristic extraction.

#### Query Examples

**With Indexes** (recommended - 10x faster):

```graphql
# Find all services (using indexed _type)
{
  services(func: eq(<_type>, "Service")) {
    <name>
    <description>
    count(uid)
  }
}

# Find service by name (using indexed name)
{
  service(func: eq(<name>, "acs-fleet-manager")) @filter(eq(<_type>, "Service")) {
    <name>
    <description>
    <hasCodeComponent> {
      <name>
      <url>
    }
  }
}

# Find all GitHub dependencies (using indexed name + reverse edge)
{
  github(func: eq(<name>, "GitHub")) {
    <name>
    <~dependsOn> {  # Reverse edge
      <name>
      <_type>
    }
  }
}
```

**Without Indexes** (slower fallback):

```graphql
# When predicate is not indexed, use has() + filter
{
  endpoint(func: has(<fullUrl>))
    @filter(eq(<fullUrl>, "https://api.openshift.com/api/v1/upgrades")) {
    <fullUrl>
    <routedBy> {
      <name>
      <belongsTo> {
        <name>
      }
    }
  }
}
```

---

### Case Study 2: Kubernetes Manifest Repository

**Repository**: Generic Kubernetes configurations (no qontract-schemas)

**Structure**:

```
k8s-configs/
├── namespaces/
│   ├── production/
│   │   ├── namespace.yaml
│   │   ├── deployments/
│   │   ├── services/
│   │   └── ingresses/
│   └── staging/
└── cluster-resources/
    ├── crds/
    └── rbac/
```

#### Phase 0: Discovery

```bash
# No schemas found - use heuristic extraction
$ find . -name "*schema*"
# (empty)

# Identify Kubernetes resources
$ head namespaces/production/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    team: platform
```

**Decision**: Heuristic extraction based on Kubernetes `kind` field.

#### Phase 2: Heuristic Extraction

```python
def extract_k8s_resource(filepath, data):
    """Extract Kubernetes resource heuristically."""

    # Use 'kind' as entity type
    entity_type = data['kind']

    # Build URN from namespace + name
    namespace = data['metadata'].get('namespace', 'cluster')
    name = data['metadata']['name']
    urn = f"urn:k8s:{namespace}:{entity_type.lower()}:{name}"

    entity = {
        "@id": urn,
        "@type": entity_type,
        "name": name,
        "namespace": namespace
    }

    # Extract all metadata labels
    for label_key, label_value in data['metadata'].get('labels', {}).items():
        entity[f"label_{label_key}"] = label_value

    # Extract spec fields
    for spec_key, spec_value in data.get('spec', {}).items():
        entity[spec_key] = extract_spec_field(spec_value)

    # Infer relationships from references
    if entity_type == "Ingress":
        # Ingress → Service
        for rule in data['spec'].get('rules', []):
            for path in rule.get('http', {}).get('paths', []):
                service_name = path['backend']['service']['name']
                service_urn = f"urn:k8s:{namespace}:service:{service_name}"
                entity.setdefault('routesTo', []).append({"@id": service_urn})

    return entity
```

#### Extracted Entities

```json
{
  "@id": "urn:k8s:production:ingress:api-gateway",
  "@type": "Ingress",
  "name": "api-gateway",
  "namespace": "production",
  "label_team": "platform",
  "label_app": "api",
  "host": "api.example.com",
  "routesTo": [
    {"@id": "urn:k8s:production:service:api-backend"}
  ]
}

{
  "@id": "urn:k8s:production:service:api-backend",
  "@type": "Service",
  "name": "api-backend",
  "namespace": "production",
  "selector": {"app": "api", "tier": "backend"},
  "port": 8080,
  "targetPort": 8080
}

{
  "@id": "urn:k8s:production:deployment:api-backend",
  "@type": "Deployment",
  "name": "api-backend",
  "namespace": "production",
  "replicas": 3,
  "image": "registry.example.com/api:v1.2.3",
  "matchesService": {"@id": "urn:k8s:production:service:api-backend"}
}
```

**Total**: ~500 entities from 200 YAML files.

---

### Case Study 3: OpenAPI Repository

**Repository**: REST API definitions (OpenAPI 3.0 specs)

**Structure**:

```
api-specs/
├── openapi.yaml          # Main API spec
├── components/
│   ├── schemas/
│   ├── parameters/
│   └── responses/
└── paths/
    ├── users.yaml
    ├── products.yaml
    └── orders.yaml
```

#### Phase 1: OpenAPI Schema Analysis

```yaml
# openapi.yaml
openapi: 3.0.0
info:
  title: E-Commerce API
paths:
  /users:
    $ref: "./paths/users.yaml"
  /products:
    $ref: "./paths/products.yaml"
components:
  schemas:
    User:
      type: object
      required: [id, email]
      properties:
        id: { type: string }
        email: { type: string }
        name: { type: string }
```

#### Phase 2: Entity Extraction

Extract entities from OpenAPI components:

```python
def extract_openapi_entities(openapi_spec):
    """Extract entities from OpenAPI specification."""

    entities = []

    # Extract schema definitions as entity types
    for schema_name, schema_def in openapi_spec['components']['schemas'].items():
        entity = {
            "@id": f"urn:schema:{schema_name.lower()}",
            "@type": "Schema",
            "name": schema_name,
            "properties": list(schema_def.get('properties', {}).keys()),
            "required": schema_def.get('required', [])
        }
        entities.append(entity)

    # Extract endpoints
    for path, path_def in openapi_spec['paths'].items():
        for method, operation in path_def.items():
            if method in ['get', 'post', 'put', 'delete']:
                entity = {
                    "@id": f"urn:endpoint:{method}:{path.replace('/', ':')}",
                    "@type": "Endpoint",
                    "name": f"{method.upper()} {path}",
                    "method": method.upper(),
                    "path": path,
                    "operationId": operation.get('operationId'),
                    "summary": operation.get('summary')
                }

                # Link to schema
                if 'requestBody' in operation:
                    schema_ref = operation['requestBody']['content']['application/json']['schema']['$ref']
                    schema_name = schema_ref.split('/')[-1]
                    entity['accepts'] = {"@id": f"urn:schema:{schema_name.lower()}"}

                entities.append(entity)

    return entities
```

**Extracted**:

- 25 Schema entities
- 47 Endpoint entities
- Relationships: Endpoint → Schema (accepts/returns)

---

### Case Study 4: Terraform Infrastructure

**Repository**: Infrastructure as Code (Terraform modules)

**Structure**:

```
terraform/
├── main.tf
├── modules/
│   ├── vpc/
│   ├── eks/
│   └── rds/
└── environments/
    ├── prod.tfvars
    └── staging.tfvars
```

#### Phase 2: Heuristic Extraction

```python
def extract_terraform_resources(tf_file):
    """Extract Terraform resources as entities."""

    # Parse .tf file (use HCL parser)
    config = hcl.loads(open(tf_file).read())

    entities = []

    for resource_type, resources in config.get('resource', {}).items():
        for resource_name, resource_config in resources.items():
            entity = {
                "@id": f"urn:terraform:{resource_type}:{resource_name}",
                "@type": resource_type,
                "name": resource_name,
                **resource_config  # All terraform attributes
            }

            # Extract dependencies
            for key, value in resource_config.items():
                if isinstance(value, str) and value.startswith('${'):
                    # Terraform interpolation: ${aws_vpc.main.id}
                    ref_match = re.search(r'\$\{(\w+)\.(\w+)\.', value)
                    if ref_match:
                        ref_type, ref_name = ref_match.groups()
                        entity.setdefault('dependsOn', []).append({
                            "@id": f"urn:terraform:{ref_type}:{ref_name}"
                        })

            entities.append(entity)

    return entities
```

**Extracted**:

- 156 Terraform resources (VPCs, subnets, EKS clusters, RDS instances)
- Dependencies automatically inferred from interpolations

---

## Troubleshooting

### Problem: Entities Appear as Hex IDs

**Symptom**: Visualizer shows "0x29948fa" instead of entity name.

**Cause**: Entity exists in graph but lacks `name` predicate.

**Solution**:

```python
# Find entities without names
entities_without_names = [
    e for e in entities
    if "name" not in e
]

# Add names
for entity in entities_without_names:
    # Use URN or type as fallback
    entity["name"] = entity["@id"].split(":")[-1]
```

### Problem: Broken References

**Symptom**: References point to non-existent entities.

**Cause**: Entity referenced before being extracted, or typo in URN.

**Solution**:

```python
# Collect all URNs
all_urns = {e["@id"] for e in entities}

# Find broken refs
for entity in entities:
    for key, value in entity.items():
        if isinstance(value, dict) and "@id" in value:
            if value["@id"] not in all_urns:
                print(f"Broken: {entity['@id']} --{key}--> {value['@id']}")
```

Fix by:

1. Extracting missing entities
2. Correcting URN typos
3. Removing invalid references

### Problem: Graph Database Index Errors

**Symptom** (Dgraph): "Predicate name is not indexed"

**Cause**: Schema doesn't include `@index` directive for the predicate.

**Solution 1** (Recommended): Add indexes during schema generation:

```python
# In load_dgraph.py generate_schema():
indexed_predicates = {'name', '_type', 'url', 'email', 'id', 'path', 'namespace'}

if predicate in indexed_predicates:
    schema_lines.append(f"<{predicate}>: string @index(exact, term) .")
```

**Solution 2** (Workaround): Use filter-based queries without indexes:

```graphql
# ❌ Requires index
{ services(func: eq(<name>, "Cincinnati")) }

# ✅ Works without index (slower)
{
  services(func: has(<name>))
    @filter(eq(<name>, "Cincinnati"))
}
```

**Note**: Predicates with colons (`:`) CAN be indexed when wrapped in angle brackets `<predicate>` in both schema and queries.

### Problem: RDF Parsing Errors

**Symptom**: "Invalid syntax" when loading RDF.

**Common Causes**:

1. **Unescaped quotes**: `"description": "He said "hello""`
   - Fix: Escape quotes: `"He said \"hello\""`

2. **Newlines in literals**: Multi-line strings
   - Fix: Use `\n` or convert to single line

3. **Special characters**: `{`, `}`, `<`, `>`
   - Fix: URL-encode in URNs

4. **Graph labels**: N-Quads have 4 parts, RDF expects 3
   - Fix: Strip 4th field (graph label)

### Problem: Duplicate Entities

**Symptom**: Same entity appears multiple times with different URNs.

**Cause**: Inconsistent URN generation.

**Solution**:

```python
# Normalize URN generation
def normalize_urn(entity_type, identifier):
    # Lowercase, remove special chars
    clean_id = identifier.lower().replace(" ", "-")
    clean_id = re.sub(r'[^a-z0-9-]', '', clean_id)
    return f"urn:{entity_type}:{clean_id}"

# Deduplicate
unique_entities = {}
for entity in entities:
    urn = entity["@id"]
    if urn not in unique_entities:
        unique_entities[urn] = entity
    else:
        # Merge properties
        unique_entities[urn].update(entity)

entities = list(unique_entities.values())
```

### Problem: Slow Extraction

**Symptom**: Extraction takes hours for large repos.

**Solutions**:

1. **Parallel processing**:

```python
from multiprocessing import Pool

def extract_file(filepath):
    # ... extraction logic
    return entity

with Pool(8) as pool:  # 8 parallel workers
    entities = pool.map(extract_file, all_files)
```

2. **Batch processing**:

```python
BATCH_SIZE = 1000
for i in range(0, len(files), BATCH_SIZE):
    batch = files[i:i+BATCH_SIZE]
    process_batch(batch)
```

3. **Skip unchanged files**:

```python
if os.path.getmtime(file) < last_run_time:
    skip_file(file)
```

### Problem: Schema Validation Failures

**Symptom**: Data doesn't match schema.

**Solution**: Graceful fallback

```python
try:
    validate_against_schema(data, schema)
    return extract_by_schema(data, schema)
except ValidationError as e:
    log_warning(f"Schema mismatch: {e}")
    return extract_by_heuristic(data)
```

---

## Appendix: Loader Script Specifications

### load_dgraph.py

See separate file: `load_dgraph.py`

**Usage**:

```bash
# From extraction directory
python load_dgraph.py \
  --input working/knowledge_graph.jsonld \
  --dgraph-url http://localhost:8080 \
  --drop-all
```

**Features**:

- JSON-LD to Dgraph RDF conversion
- Schema generation and application
- Validation before load
- Progress reporting

### load_neo4j.py

See separate file: `load_neo4j.py`

**Usage**:

```bash
# From extraction directory
python load_neo4j.py \
  --input working/knowledge_graph.jsonld \
  --neo4j-uri bolt://localhost:7687 \
  --username neo4j \
  --password secret \
  --clear
```

**Features**:

- JSON-LD to Cypher conversion
- Index creation
- Batch loading (for large graphs)
- Validation before load

---

## Quick Reference

### Extraction Checklist

- [ ] **Phase 0**: Repository discovered and analyzed
- [ ] **Phase 1**: Schemas analyzed OR heuristic plan created
- [ ] **Phase 2**: All entity batches extracted
  - [ ] All entities have `@id`, `@type`, `name`
  - [ ] Maximum detail captured
  - [ ] Validation passed for each batch
- [ ] **Phase 3**: Relationships resolved
  - [ ] Zero broken references
  - [ ] Bidirectional edges created
  - [ ] Implicit relationships inferred
- [ ] **Phase 4**: JSON-LD exported and validated
- [ ] **Load**: Graph database loaded successfully

### Common Commands

```bash
# Discovery
find . -name "*.yaml" | wc -l
tree -L 3 -d

# Extraction (Claude Code generates script)
# Output to extraction/working/ directory
python extract.py --output extraction/working/knowledge_graph.jsonld

# Validation
python -m json.tool extraction/working/knowledge_graph.jsonld > /dev/null

# Load into Dgraph
cd extraction
python load_dgraph.py --input working/knowledge_graph.jsonld

# Load into Neo4j
python load_neo4j.py --input working/knowledge_graph.jsonld
```

---

**Last Updated**: 2025-10-06
**Framework Version**: 1.0
**Compatible Graph Databases**: Dgraph 23.1+, Neo4j 4.0+, any JSON-LD compliant database
