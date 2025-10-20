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

### Two-Pass Extraction Strategy

**Problem**: Relationships often fail because they reference entities that haven't been extracted yet, or reference URNs that don't match the actual extracted entity URNs. This causes broken references (18% in baseline analysis).

**Solution**: Extract in two passes - entities first, relationships second.

#### Pass 1: Entity Extraction & Index Building

Extract all entities and build a URN index before creating any cross-entity relationships.

```python
def extract_entities_pass1(files, schema_config):
    """
    Pass 1: Extract entities and build URN index.

    - Extract ALL entities from files
    - Assign URNs and validate entity structure
    - Build index mapping URN -> entity
    - DO NOT create cross-entity relationships yet
    """
    entities = []
    entity_index = {}  # URN -> entity mapping

    for filepath in files:
        data = load_yaml_or_json(filepath)

        # Create entity with URN
        urn = generate_urn(schema_config['urn_pattern'], data)

        entity = {
            "@id": urn,
            "@type": schema_config['entity_type']
        }

        # Extract ALL scalar fields (strings, numbers, booleans)
        for field in schema_config['required_predicates']:
            value = get_nested_field(data, field)
            if value is None:
                log_error(f"Missing required field '{field}' in {filepath}")
            # Only add non-reference values
            if not is_reference_field(value):
                entity[field] = value

        for field in schema_config['optional_predicates']:
            value = get_nested_field(data, field)
            if value is not None and not is_reference_field(value):
                entity[field] = value

        # Store reference fields for Pass 2 (don't resolve yet)
        entity['_pending_refs'] = []
        for rel in schema_config['relationships']:
            ref_value = get_nested_field(data, rel['field'])
            if ref_value:
                entity['_pending_refs'].append({
                    'field': rel['field'],
                    'predicate': rel['predicate'],
                    'target_type': rel['target_type'],
                    'ref_value': ref_value
                })

        # Validate entity has required fields
        validate_entity_before_extraction(entity, filepath)

        entities.append(entity)
        entity_index[urn] = entity

    return entities, entity_index


def is_reference_field(value):
    """Check if field contains a reference to another entity."""
    if isinstance(value, dict):
        # Check for $ref pattern
        if '$ref' in value:
            return True
        # Check for @id pattern (already resolved reference)
        if '@id' in value:
            return True
    elif isinstance(value, str):
        # Check for $ref string pattern
        if value.startswith('$ref:') or '.yml' in value or '.yaml' in value:
            return True
    return False
```

#### Pass 2: Relationship Resolution with Validation

Resolve all references using the entity index, validating each one exists.

```python
def extract_relationships_pass2(entities, entity_index, schema_config):
    """
    Pass 2: Resolve relationships with validation.

    - For each entity's pending references
    - Resolve $ref to target URN
    - Validate target URN exists in entity_index
    - Add relationship if valid, log warning if broken
    """
    broken_refs = []
    created_refs = 0
    skipped_refs = 0

    for entity in entities:
        pending_refs = entity.pop('_pending_refs', [])

        for ref in pending_refs:
            # Resolve $ref to target URN
            target_urn = resolve_reference(
                ref['ref_value'],
                ref['target_type'],
                entity_index
            )

            if target_urn is None:
                log_warning(
                    f"Could not resolve reference: "
                    f"{entity['@id']} --{ref['predicate']}--> {ref['ref_value']}"
                )
                skipped_refs += 1
                continue

            # Validate target exists in index
            if target_urn not in entity_index:
                broken_refs.append({
                    'source': entity["@id"],
                    'predicate': ref['predicate'],
                    'target': target_urn,
                    'reason': 'target_not_extracted'
                })
                log_warning(
                    f"Broken reference (target not extracted): "
                    f"{entity['@id']} --{ref['predicate']}--> {target_urn}"
                )
                skipped_refs += 1
                continue

            # Target exists - create relationship
            entity[ref['predicate']] = {"@id": target_urn}
            created_refs += 1

    # Report results
    print(f"✅ Pass 2 completed:")
    print(f"   Created {created_refs} relationships")
    print(f"   Skipped {skipped_refs} broken references")
    print(f"   Broken reference rate: {100*skipped_refs/(created_refs+skipped_refs):.1f}%")

    if broken_refs:
        print(f"\n⚠️  Found {len(broken_refs)} broken references:")
        for ref in broken_refs[:10]:
            print(f"   {ref['source']} --{ref['predicate']}--> {ref['target']}")

        # Save broken refs for analysis
        save_broken_refs_report(broken_refs, 'broken_refs_report.json')

    return entities, broken_refs
```

#### Enhanced Reference Resolution with $ref Following

Follow `$ref` links to extract referenced entities before creating relationships.

```python
def resolve_reference(ref_value, target_type, entity_index):
    """
    Resolve a reference to a target URN.

    Handles multiple reference patterns:
    - $ref: "/path/to/file.yml" -> extract and get URN
    - Direct URN reference
    - Inline object with identifying fields
    """
    # Pattern 1: $ref to file path
    if isinstance(ref_value, dict) and '$ref' in ref_value:
        file_path = ref_value['$ref']

        # Check if already extracted
        target_urn = find_urn_by_source_file(entity_index, file_path)
        if target_urn:
            return target_urn

        # Not extracted yet - extract now
        log_info(f"Following $ref: {file_path}")
        target_entity = extract_referenced_entity(file_path, target_type)
        if target_entity:
            # Add to index
            entity_index[target_entity['@id']] = target_entity
            return target_entity['@id']
        else:
            log_warning(f"Could not extract referenced entity: {file_path}")
            return None

    # Pattern 2: String file path
    elif isinstance(ref_value, str) and ('.yml' in ref_value or '.yaml' in ref_value):
        # Same as Pattern 1
        target_urn = find_urn_by_source_file(entity_index, ref_value)
        if target_urn:
            return target_urn

        target_entity = extract_referenced_entity(ref_value, target_type)
        if target_entity:
            entity_index[target_entity['@id']] = target_entity
            return target_entity['@id']
        return None

    # Pattern 3: Direct URN reference
    elif isinstance(ref_value, str) and ref_value.startswith('urn:'):
        return ref_value

    # Pattern 4: Inline object with name/id
    elif isinstance(ref_value, dict):
        # Try to construct URN from inline data
        return construct_urn_from_object(ref_value, target_type)

    else:
        log_warning(f"Unknown reference pattern: {ref_value}")
        return None


def find_urn_by_source_file(entity_index, file_path):
    """Find entity URN by source file path."""
    # Normalize file path
    normalized_path = normalize_file_path(file_path)

    for urn, entity in entity_index.items():
        entity_source = entity.get('_source_file', '')
        if normalize_file_path(entity_source) == normalized_path:
            return urn

    return None


def extract_referenced_entity(file_path, expected_type):
    """
    Extract an entity from a referenced file.

    Used when following $ref links during Pass 2.
    """
    try:
        data = load_yaml_or_json(file_path)

        # Infer schema config from expected type
        schema_config = get_schema_config(expected_type)
        if not schema_config:
            log_warning(f"No schema config for type: {expected_type}")
            return None

        # Extract entity (Pass 1 style - no relationships)
        urn = generate_urn(schema_config['urn_pattern'], data)

        entity = {
            "@id": urn,
            "@type": expected_type,
            "_source_file": file_path
        }

        # Extract scalar fields only
        for field in schema_config.get('required_predicates', []):
            value = get_nested_field(data, field)
            if value is not None and not is_reference_field(value):
                entity[field] = value

        for field in schema_config.get('optional_predicates', []):
            value = get_nested_field(data, field)
            if value is not None and not is_reference_field(value):
                entity[field] = value

        validate_entity_before_extraction(entity, file_path)

        log_info(f"Extracted referenced entity: {urn} from {file_path}")
        return entity

    except Exception as e:
        log_error(f"Failed to extract referenced entity from {file_path}: {e}")
        return None
```

#### URN Standardization & Validation

Ensure URN construction is consistent across all entity types.

```python
def generate_urn(urn_pattern, data):
    """
    Generate URN from pattern and data.

    Patterns:
    - urn:type:{name} -> urn:service:cincinnati
    - urn:type:{parent}:{name} -> urn:namespace:prod:app-sre
    - urn:type:{field1}:{field2} -> custom composite keys
    """
    import re

    # Find all placeholders in pattern
    placeholders = re.findall(r'\{([^}]+)\}', urn_pattern)

    # Replace each placeholder with data value
    urn = urn_pattern
    for placeholder in placeholders:
        value = get_nested_field(data, placeholder)

        if value is None:
            raise ValueError(
                f"Missing required field '{placeholder}' for URN pattern: {urn_pattern}"
            )

        # Normalize value for URN
        normalized = normalize_urn_component(value)
        urn = urn.replace(f"{{{placeholder}}}", normalized)

    # Validate final URN
    validate_urn(urn)

    return urn


def normalize_urn_component(value):
    """
    Normalize a value for use in URN.

    Rules:
    - Lowercase
    - Replace spaces with hyphens
    - URL-encode special characters
    - Preserve path separators for path-based URNs
    """
    import urllib.parse

    if not isinstance(value, str):
        value = str(value)

    # Lowercase
    value = value.lower()

    # Replace spaces with hyphens
    value = value.replace(' ', '-')

    # Replace underscores with hyphens for consistency
    value = value.replace('_', '-')

    # URL-encode special characters (except : and / for hierarchical URNs)
    # Encode everything except alphanumeric, hyphen, colon, slash
    safe_chars = 'abcdefghijklmnopqrstuvwxyz0123456789-:/'
    encoded = ''.join(
        c if c in safe_chars else urllib.parse.quote(c)
        for c in value
    )

    return encoded


def validate_urn(urn):
    """
    Validate URN format.

    Requirements:
    - Starts with 'urn:'
    - Has at least 3 segments (urn:type:identifier)
    - No empty segments
    - No invalid characters
    """
    if not urn.startswith('urn:'):
        raise ValueError(f"URN must start with 'urn:': {urn}")

    segments = urn.split(':')
    if len(segments) < 3:
        raise ValueError(f"URN must have at least 3 segments: {urn}")

    for i, segment in enumerate(segments):
        if not segment:
            raise ValueError(f"URN segment {i} is empty: {urn}")

    return True


# URN validation during extraction
def extract_entity_with_urn_validation(data, filepath, schema_config):
    """Extract entity with URN validation."""

    try:
        # Generate and validate URN
        urn = generate_urn(schema_config['urn_pattern'], data)

    except ValueError as e:
        log_error(f"URN generation failed for {filepath}: {e}")
        raise

    entity = {
        "@id": urn,
        "@type": schema_config['entity_type'],
        "_source_file": filepath
    }

    # ... rest of extraction

    return entity
```

#### Integration: Two-Pass Extraction Flow

Complete extraction workflow using two-pass strategy.

```python
def extract_all_entities_two_pass(schema_catalog, output_file):
    """
    Complete two-pass extraction workflow.

    1. Build dependency graph of entity types
    2. Extract in dependency order (Pass 1 for each batch)
    3. Resolve all relationships (Pass 2 across all entities)
    4. Detect and link orphaned entities
    """
    all_entities = []
    global_entity_index = {}

    # Determine extraction order (entities with no dependencies first)
    batches = build_dependency_batches(schema_catalog)

    print(f"Starting two-pass extraction for {len(batches)} batches...")

    # PASS 1: Extract all entities
    for batch_num, batch in enumerate(batches, 1):
        print(f"\n--- Batch {batch_num}/{len(batches)} (Pass 1) ---")

        for schema_config in batch:
            entity_type = schema_config['entity_type']
            files = glob(schema_config['file_pattern'])

            print(f"Extracting {len(files)} {entity_type} entities...")

            # Pass 1: Extract entities only
            entities, entity_index = extract_entities_pass1(files, schema_config)

            all_entities.extend(entities)
            global_entity_index.update(entity_index)

            print(f"  Extracted {len(entities)} {entity_type} entities")

    print(f"\n✅ Pass 1 complete: {len(all_entities)} entities extracted")
    print(f"   Entity index size: {len(global_entity_index)} URNs")

    # PASS 2: Resolve all relationships
    print(f"\n--- Pass 2: Relationship Resolution ---")

    all_broken_refs = []

    for schema_config in flatten_batches(batches):
        entity_type = schema_config['entity_type']

        # Get entities of this type
        type_entities = [e for e in all_entities if e['@type'] == entity_type]

        if not type_entities:
            continue

        print(f"Resolving relationships for {len(type_entities)} {entity_type} entities...")

        # Pass 2: Resolve relationships
        resolved_entities, broken_refs = extract_relationships_pass2(
            type_entities,
            global_entity_index,
            schema_config
        )

        all_broken_refs.extend(broken_refs)

    print(f"\n✅ Pass 2 complete:")
    print(f"   Total broken references: {len(all_broken_refs)}")
    print(f"   Broken reference rate: {100*len(all_broken_refs)/len(all_entities):.2f}%")

    # Expected: < 2% broken references (down from 18% baseline)
    if len(all_broken_refs) > 0.02 * len(all_entities):
        print(f"\n⚠️  WARNING: Broken reference rate exceeds target (2%)")
        print(f"   Consider extracting missing entity types or fixing URN construction")

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

**Expected Impact**:

- Broken references: 18% → < 2% (90% reduction)
- Orphaned entities: 3% → < 0.5% (83% reduction)
- Enables detection of missing entity types before relationships fail
- Provides clear broken reference reports for debugging
- Allows on-demand extraction of referenced entities via $ref following

### Orphan Detection & Prevention

After Pass 2 completes, detect and attempt to link entities with no relationships.

#### Orphan Detection

Identify entities that have no inbound or outbound relationships.

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

### Free-Text Entity Extraction (AI-Driven)

**New Best Practice (Iteration 5)**: Extract entities and relationships from free-text fields using AI-driven pattern recognition. This is where Claude Code's natural language understanding excels - recognizing tool mentions, technology references, and relationships in descriptions, documentation, and comments.

**Principle**: Description fields, documentation, and comments are rich sources of entity and relationship information that structured extraction misses. Instead of rigid pattern matching, Claude Code should intelligently analyze natural language to extract:

- Tool and system dependencies ("uses Prometheus", "deployed via ArgoCD")
- Team and ownership information ("maintained by Platform team")
- Technology stack details ("written in Go", "React frontend")
- Infrastructure and environment context ("runs on AWS", "deployed to cluster X")
- Integration and dependency mentions ("integrates with GitHub API", "calls Vault")

**What to Look For in Free-Text Fields**:

Common patterns in app-interface descriptions that indicate extractable entities and relationships:

1. **Tool/System Mentions**:
   - "uses Prometheus for metrics"
   - "deployed to ArgoCD"
   - "backed by PostgreSQL database"
   - "monitored via Grafana dashboards"
   - "uses Vault for secrets management"

2. **Team/Ownership Mentions**:
   - "maintained by Platform team"
   - "owned by SRE"
   - "developed by Red Hat Advanced Cluster Security team"
   - "point of contact: <engineering-team@example.com>"

3. **Dependency Mentions**:
   - "integrates with GitHub API"
   - "calls Vault for secrets"
   - "depends on OpenShift Hive"
   - "connects to external service X"

4. **Technology Stack Mentions**:
   - "written in Go"
   - "React frontend with TypeScript"
   - "Python backend using Django"
   - "gRPC API service"
   - "uses Redis for caching"

5. **Infrastructure Mentions**:
   - "runs on AWS"
   - "deployed to production cluster app-sre-prod-04"
   - "uses S3 for storage"
   - "hosted in us-east-1 region"
   - "Kubernetes deployment on OpenShift"

**How Claude Code Should Reason About Free Text**:

When analyzing description fields, Claude Code should:

1. **Identify entity mentions** by recognizing proper nouns and technical terms
2. **Classify entity types** based on context (Prometheus = MonitoringTool, Go = ProgrammingLanguage)
3. **Extract relationships** by recognizing action verbs and relationship keywords
4. **Assign confidence levels** based on explicitness of the mention
5. **Validate against known entity index** to avoid creating duplicates

**Example: AI Reasoning Process**

```
Input Description:
"This service uses Prometheus for metrics and is deployed via ArgoCD to production clusters.
The backend is written in Go and uses PostgreSQL for data persistence. Maintained by the
Platform Engineering team."

Claude Code Analysis:
1. Tool mentions detected:
   - "Prometheus" (context: "uses...for metrics") → MonitoringTool
   - "ArgoCD" (context: "deployed via") → DeploymentTool
   - "PostgreSQL" (context: "uses...for data persistence") → Database

2. Technology mention:
   - "Go" (context: "written in") → ProgrammingLanguage

3. Team mention:
   - "Platform Engineering team" (context: "maintained by") → Team

4. Infrastructure context:
   - "production clusters" (implies production environment)

Extracted Entities:
- urn:monitoring-tool:prometheus (@type: MonitoringTool, name: "Prometheus")
- urn:deployment-tool:argocd (@type: DeploymentTool, name: "ArgoCD")
- urn:database:postgresql (@type: Database, name: "PostgreSQL")
- urn:programming-language:go (@type: ProgrammingLanguage, name: "Go")
- urn:team:platform-engineering (@type: Team, name: "Platform Engineering")

Extracted Relationships:
- service --usesTool--> urn:monitoring-tool:prometheus (confidence: HIGH, purpose: "metrics")
- service --deployedVia--> urn:deployment-tool:argocd (confidence: HIGH)
- service --usesDatabase--> urn:database:postgresql (confidence: HIGH, purpose: "data persistence")
- service --writtenIn--> urn:programming-language:go (confidence: HIGH)
- service --maintainedBy--> urn:team:platform-engineering (confidence: HIGH)
- service --environment--> "production" (confidence: MEDIUM, inferred from "production clusters")
```

**Confidence Levels for AI Extraction**:

Claude Code should assign confidence based on how explicit the mention is:

**HIGH Confidence** (extract and create relationships automatically):

- Explicit tool/system names with action verbs: "uses X", "deployed to Y", "backed by Z"
- Clear ownership statements: "maintained by Team X", "owned by Y"
- Specific technology declarations: "written in Go", "React frontend"
- Direct integration mentions: "integrates with X API", "calls Y service"

**MEDIUM Confidence** (extract entity, flag relationship for review):

- Implied relationships: "running on AWS" (implies infrastructure dependency)
- Contextual inferences: "production environment" → environment type
- Indirect mentions: "uses Kubernetes" when context is OpenShift (Kubernetes is implied)

**LOW Confidence** (log for manual review, do not auto-extract):

- Vague mentions without clear relationships: "various tools", "multiple services"
- Ambiguous references: "the database" (which database?)
- Uncertain context: mentions in conditional statements ("may use X if...")

**Entity Types to Extract from Descriptions**:

Claude Code should recognize and extract these entity types from free text:

1. **Tools/Systems** (HIGH confidence for known tools):
   - Monitoring: Prometheus, Grafana, Datadog, New Relic
   - Deployment: ArgoCD, Flux, Jenkins, GitLab CI, GitHub Actions
   - Secrets Management: Vault, AWS Secrets Manager, Sealed Secrets
   - Service Mesh: Istio, Linkerd, Consul
   - Logging: ElasticSearch, Splunk, Loki
   - Tracing: Jaeger, Zipkin, OpenTelemetry

2. **Technologies** (HIGH confidence for known technologies):
   - Programming Languages: Go, Python, Java, TypeScript, Rust, etc.
   - Frameworks: Django, Flask, Spring Boot, React, Vue, Angular
   - Protocols: gRPC, REST, GraphQL, HTTP, HTTPS
   - Data Formats: JSON, YAML, Protocol Buffers, Avro

3. **Infrastructure** (MEDIUM-HIGH confidence):
   - Cloud Providers: AWS, GCP, Azure, IBM Cloud
   - Platforms: OpenShift, Kubernetes, Cloud Foundry
   - Storage: S3, GCS, Azure Blob, RDS, DynamoDB
   - Compute: EC2, EKS, GKE, Lambda, Cloud Run
   - Regions: us-east-1, eu-west-1, etc.

4. **Teams** (HIGH confidence with clear ownership keywords):
   - Keywords: "maintained by", "owned by", "developed by", "team:", "contact:"
   - Extract team name and create Team entity if not exists
   - Link to service via "maintainedBy" or "ownedBy" relationship

5. **External Services** (MEDIUM-HIGH confidence):
   - GitHub, GitLab, Bitbucket (code hosting)
   - Quay, Docker Hub, ECR (container registries)
   - Jira, ServiceNow (ticketing)
   - PagerDuty, Opsgenie (incident management)
   - Slack, Email (communication channels)

**Relationship Patterns Claude Code Should Recognize**:

Natural language phrases to relationship mappings:

| Natural Language Pattern | Extracted Relationship | Example |
|--------------------------|------------------------|---------|
| "uses X for Y" | service --uses--> X (purpose: Y) | "uses Prometheus for metrics" |
| "backed by X" | service --backedBy--> X | "backed by PostgreSQL database" |
| "deployed via X" | service --deployedVia--> X | "deployed via ArgoCD" |
| "maintained by X team" | service --maintainedBy--> Team X | "maintained by Platform team" |
| "integrates with X" | service --integratesWith--> X | "integrates with GitHub API" |
| "stores data in X" | service --storesDataIn--> X | "stores data in S3 buckets" |
| "written in X" | service --writtenIn--> X | "written in Go" |
| "runs on X" | service --runsOn--> X | "runs on AWS infrastructure" |
| "calls X for Y" | service --dependsOn--> X (purpose: Y) | "calls Vault for secrets" |
| "monitored via X" | service --monitoredBy--> X | "monitored via Grafana" |
| "deployed to X" | service --deployedTo--> X | "deployed to production cluster" |
| "uses X as Y" | service --uses--> X (role: Y) | "uses Redis as cache" |

**Examples of AI Reasoning with Confidence Levels**:

**Example 1: High Confidence Extraction**

```
Description: "ACS Fleet Manager uses PostgreSQL for data persistence and Prometheus for
monitoring. Deployed via ArgoCD to production OpenShift clusters."

Claude Code Reasoning:
✅ HIGH confidence entities:
  - PostgreSQL (Database) - explicit mention with clear purpose
  - Prometheus (MonitoringTool) - explicit mention with clear purpose
  - ArgoCD (DeploymentTool) - explicit deployment mechanism
  - OpenShift (Platform) - explicit deployment target

✅ HIGH confidence relationships:
  - service --usesDatabase--> PostgreSQL (purpose: "data persistence")
  - service --monitoredBy--> Prometheus
  - service --deployedVia--> ArgoCD
  - service --deployedTo--> OpenShift

Action: Extract all entities and relationships automatically
```

**Example 2: Medium Confidence Extraction**

```
Description: "This service runs on AWS and uses various monitoring tools. It may integrate
with external APIs depending on configuration."

Claude Code Reasoning:
✅ HIGH confidence:
  - AWS (CloudProvider) - explicit infrastructure mention

⚠️ MEDIUM confidence:
  - "various monitoring tools" - too vague, no specific tool names
  - "may integrate with external APIs" - conditional, uncertain

❌ LOW confidence:
  - "external APIs" - too generic, no specific API names

Action:
- Extract AWS infrastructure entity with relationship (HIGH confidence)
- Flag "various monitoring tools" for manual review (MEDIUM)
- Skip "external APIs" extraction (LOW confidence)
```

**Example 3: Mixed Confidence with Validation**

```
Description: "Backend written in Python using FastAPI. Frontend is React with TypeScript.
Uses some form of caching, possibly Redis."

Claude Code Reasoning:
✅ HIGH confidence:
  - Python (ProgrammingLanguage) - explicit with framework context
  - FastAPI (Framework) - explicit framework mention
  - React (Framework) - explicit frontend framework
  - TypeScript (ProgrammingLanguage) - explicit language

⚠️ MEDIUM confidence:
  - "some form of caching" - caching confirmed but tool unclear

⚠️ LOW-MEDIUM confidence:
  - Redis (Cache) - mentioned as "possibly", uncertain

Action:
- Extract Python, FastAPI, React, TypeScript with relationships (HIGH)
- Create generic "caching" relationship without specific tool (MEDIUM)
- Flag Redis mention for validation: check if Redis entity exists in system
  - If exists: create relationship with MEDIUM confidence
  - If not: log for manual review
```

**Quality Guidelines for AI Extraction**:

Claude Code should follow these quality principles:

1. **Don't Over-Extract**:
   - ❌ Skip: "uses various tools" (too vague)
   - ❌ Skip: "multiple databases" (no specifics)
   - ❌ Skip: "standard monitoring" (no tool specified)
   - ✅ Extract: "uses Prometheus and Grafana" (specific tools)

2. **Validate Entity Existence**:

   ```python
   # Before creating new entity from description
   if extracted_tool_name in known_tools_index:
       # Use existing entity URN
       entity_urn = known_tools_index[extracted_tool_name]
   else:
       # Validate it's a real/known tool
       if is_known_tool(extracted_tool_name):
           # Create new entity
           entity_urn = create_tool_entity(extracted_tool_name)
       else:
           # Flag for manual review
           log_warning(f"Unknown tool mentioned: {extracted_tool_name}")
   ```

3. **Avoid Duplicates**:
   - Normalize names: "Prometheus" and "prometheus" are the same
   - Handle variations: "GitHub" vs "Github" vs "github.com"
   - Check entity index before creating new entities
   - Merge with existing entities when appropriate

4. **Context Matters**:
   - "Python" in description → ProgrammingLanguage (not snake)
   - "Go" in "written in Go" → ProgrammingLanguage
   - "Go" in "Go to production" → not an entity (action verb)
   - Use surrounding context to disambiguate

5. **Standardize Naming**:
   - "Github" → "GitHub" (proper capitalization)
   - "postgres" → "PostgreSQL" (canonical name)
   - "k8s" → "Kubernetes" (expand abbreviations)
   - "aws" → "AWS" (standard acronym format)
   - Use canonical entity names for consistency

6. **Handle Uncertainty**:
   - If confidence is LOW: log for manual review, don't auto-create
   - If entity type is unclear: use generic type ("Tool", "System") with flag
   - If relationship is ambiguous: create with "relatedTo" predicate + note
   - Always include confidence level in extracted relationship metadata

**Integration with Extraction Workflow**:

Free-text analysis should integrate with the existing two-pass extraction:

```
For each YAML file:

  # Pass 1: Structured Extraction
  1. Extract structured entities (from fields like 'name', 'type', etc.)
  2. Build entity index with all structured entities

  # Pass 1.5: Free-Text Analysis (NEW - Iteration 5)
  3. Read description/documentation/comment fields
  4. Apply AI-driven free-text analysis:
     a. Identify tool/technology/team mentions
     b. Classify entity types based on context
     c. Extract relationships with confidence levels
     d. Validate against entity index (avoid duplicates)
     e. Create new entities for HIGH confidence mentions
     f. Flag MEDIUM confidence for review
     g. Skip LOW confidence
  5. Add extracted entities to entity index

  # Pass 2: Relationship Resolution
  6. Resolve structured relationships (existing pattern)
  7. Create free-text extracted relationships (HIGH confidence only)
  8. Validate all relationships against entity index
  9. Generate reports for MEDIUM/LOW confidence extractions

  # Validation
  10. Track free-text extraction metrics:
      - Entities extracted from descriptions
      - Relationships created from free text
      - Confidence distribution (HIGH/MEDIUM/LOW)
      - Validation success rate
```

**Python Script Role (Minimal)**:

The Python extraction script's job for free-text extraction:

```python
# Minimal orchestration only - AI does the heavy lifting
def extract_from_description(service_entity, description_text):
    """
    Extract entities/relationships from description via Claude Code API.

    Args:
        service_entity: The parent service entity
        description_text: The description field content

    Returns:
        extracted_entities: List of entities found in description
        extracted_relationships: List of relationships with confidence
    """
    # Call Claude Code API with PROCESS.md guidance
    prompt = f"""
    Analyze this service description and extract entities and relationships.
    Follow the patterns in PROCESS.md Section: Free-Text Entity Extraction.

    Service: {service_entity['name']}
    Description: {description_text}

    Extract:
    1. Tools, technologies, infrastructure mentioned
    2. Teams and ownership information
    3. Dependencies and integrations
    4. Assign confidence levels (HIGH/MEDIUM/LOW)
    5. Return as structured JSON
    """

    response = call_claude_code_api(prompt, context=PROCESS_MD)

    # Parse Claude's response
    extracted = parse_extraction_response(response)

    # Validate against entity index
    validated_entities = validate_extracted_entities(
        extracted['entities'],
        entity_index
    )

    # Filter relationships by confidence
    high_confidence_rels = [
        r for r in extracted['relationships']
        if r['confidence'] == 'HIGH'
    ]

    return validated_entities, high_confidence_rels
```

**Key Point**: The Python script just:

- Calls Claude Code API with the description text
- Provides PROCESS.md guidance as context
- Validates Claude's extractions against entity index
- Filters by confidence level
- Returns structured results

It does NOT:

- Parse natural language (Claude does this)
- Recognize entity types (Claude does this)
- Infer relationships (Claude does this)
- Understand context (Claude does this)

**Expected Impact from Free-Text Extraction**:

Based on baseline analysis, app-interface descriptions contain rich information. Expected improvements:

| Metric | Before Iteration 5 | After Iteration 5 | Improvement |
|--------|-------------------|-------------------|-------------|
| **Entities from descriptions** | 0 | +500-1,000 | New capability |
| **Tools/Technologies extracted** | ~50 (structured only) | +200-400 | 4-8x increase |
| **Team entities** | ~30 (structured) | +50-100 | 2-4x increase |
| **Relationships from free text** | 0 | +1,000-2,000 | New capability |
| **Service queryability** | Structured only | + natural language context | Richer queries |
| **Graph density** | 1.9 rel/entity | 2.5-3.0 rel/entity | +30-60% |

**Examples of New Query Capabilities After Iteration 5**:

1. **Tool/Technology queries**:
   - "Find all services using Prometheus for monitoring"
   - "Show services written in Go"
   - "List services deployed via ArgoCD"
   - "Find services using PostgreSQL databases"

2. **Team/Ownership queries**:
   - "Show all services maintained by Platform Engineering team"
   - "Find services owned by SRE teams"
   - "List services without explicit team ownership"

3. **Integration queries**:
   - "Find services integrating with GitHub API"
   - "Show services that use Vault for secrets"
   - "List services with external dependencies"

4. **Infrastructure queries**:
   - "Find all services running on AWS"
   - "Show services deployed to production clusters"
   - "List services using S3 for storage"

5. **Technology stack queries**:
   - "Find all React frontends"
   - "Show services using gRPC"
   - "List services with Redis caching"

**Metrics to Track for Iteration 5**:

- Total entities extracted from description fields
- Entity types extracted (Tools, Technologies, Teams, Infrastructure, etc.)
- Relationships created from free text
- Confidence level distribution (HIGH/MEDIUM/LOW)
- Validation success rate (entities matched to known entities vs new)
- Duplicate prevention success (entities recognized vs created)
- Name standardization success (variations normalized correctly)
- Query pattern count enabled by free-text extraction
- Description coverage (% of services with extractable descriptions)
- Average entities extracted per description field

---

### Nested Structure Sub-Entity Extraction

**New Best Practice (Iteration 4)**: Extract nested structures as separate entities to enable independent querying and richer relationship modeling.

**Problem**: Flattening nested data into inline properties loses structural relationships and queryability. For example:

- Cannot query "which services are owned by user X" if owners are inline arrays
- Cannot find "all endpoints monitored by provider Y" if monitoring configs are nested objects
- Cannot traverse "repos → teams with access" if permissions are embedded

**Solution**: Extract nested structures as first-class entities with bidirectional relationships.

#### Decision Criteria: When to Create Sub-Entities

Use these criteria to decide whether nested data should become separate entities:

**Create Sub-Entities When**:

1. **Property Count Threshold**: Item has 3+ distinct properties

   ```yaml
   # 3+ properties → extract as entity
   serviceOwners:
   - name: "John Doe"
     email: "jdoe@example.com"
     role: "technical_lead"  # 3 properties → ServiceOwner entity
   ```

2. **Independent Queryability**: Need to query by this field independently

   ```
   # Query: "Show all services owned by John Doe"
   # Requires ServiceOwner to be an entity
   ```

3. **Relationship Potential**: Item has or could have relationships to other entities

   ```yaml
   # Endpoint has relationships to certificates, monitoring, alerts
   endpoints:
   - url: api.example.com
     monitoring: blackbox-tls  # → links to MonitoringProvider
     certificate: cert-123     # → links to Certificate
   ```

4. **Reusability**: Same item appears across multiple parent entities

   ```yaml
   # Same user owns multiple services → extract as User entity
   # Multiple endpoints use same monitoring → extract as MonitoringConfig
   ```

**Use Inline Arrays When**:

1. **Simple Key-Value Pairs**: Only 1-2 properties, purely descriptive

   ```json
   {
     "tags": ["production", "critical"]  // Simple array, no sub-entity
   }
   ```

2. **No Query Independence**: Never need to query by these values alone
3. **No Relationships**: Item doesn't reference or relate to other entities

#### Decision Function

```python
def should_create_sub_entity(nested_item, field_name, parent_entity):
    """
    Determine if a nested item should be extracted as a separate entity.

    Returns: (bool, str) - (should_extract, entity_type)
    """
    # Criterion 1: Property count
    if isinstance(nested_item, dict):
        property_count = len([k for k in nested_item.keys() if not k.startswith('$')])
        if property_count >= 3:
            return (True, infer_entity_type_from_field(field_name, nested_item))

    # Criterion 2: Known queryable patterns
    queryable_fields = {
        'serviceOwners': 'ServiceOwner',
        'endpoints': 'Endpoint',
        'codeComponents': 'CodeComponent',
        'quayRepos': 'QuayRepository',
        'escalationPolicy': 'EscalationPolicy',
        'resourceRequests': 'ResourceLimit',
        'resourceLimits': 'ResourceLimit',
        'monitoring': 'MonitoringConfig',
        'permissions': 'Permission'
    }

    if field_name in queryable_fields:
        return (True, queryable_fields[field_name])

    # Criterion 3: Has reference fields ($ref, relationships)
    if isinstance(nested_item, dict):
        has_references = any(
            isinstance(v, dict) and '$ref' in v
            for v in nested_item.values()
        )
        if has_references:
            return (True, infer_entity_type_from_field(field_name, nested_item))

    # Criterion 4: Reusable across parents (detected during extraction)
    # This requires tracking seen items - implement in extraction loop

    # Default: inline
    return (False, None)
```

#### Common Sub-Entity Patterns for App-Interface

Based on baseline analysis, these patterns occur frequently in app-interface data:

**Pattern 1: ServiceOwner - Extract from Owner Arrays**

Owners contain user contact information and roles - should be queryable entities.

```python
def extract_service_owners(service_data, service_urn, entity_index):
    """
    Extract service owners as User entities with ownership relationships.

    Input YAML:
        serviceOwners:
        - name: "John Doe"
          email: "jdoe@example.com"
        - name: "Jane Smith"
          email: "jsmith@example.com"
          role: "technical_lead"

    Output: User entities + ownership relationships
    """
    owners = service_data.get('serviceOwners', [])
    owner_entities = []

    for owner in owners:
        # Create or reference User entity
        email = owner.get('email')
        if not email:
            log_warning(f"ServiceOwner missing email in {service_urn}")
            continue

        # URN based on email (global identifier)
        owner_urn = f"urn:user:{normalize_urn_component(email)}"

        # Check if user already exists in index
        if owner_urn in entity_index:
            owner_entity = entity_index[owner_urn]
        else:
            # Create new User entity
            owner_entity = {
                "@id": owner_urn,
                "@type": "User",
                "name": owner.get('name', extract_name_from_email(email)),
                "email": email
            }

            # Add optional fields
            if 'role' in owner:
                owner_entity['role'] = owner['role']
            if 'githubUsername' in owner:
                owner_entity['githubUsername'] = owner['githubUsername']

            entity_index[owner_urn] = owner_entity
            owner_entities.append(owner_entity)

        # Create bidirectional ownership relationship
        # Service → User (hasOwner)
        if 'hasOwner' not in service_data:
            service_data['hasOwner'] = []
        service_data['hasOwner'].append({"@id": owner_urn})

        # User → Service (owns)
        if 'owns' not in owner_entity:
            owner_entity['owns'] = []
        owner_entity['owns'].append({"@id": service_urn})

    return owner_entities


def extract_name_from_email(email):
    """Extract name from email address."""
    # john.doe@example.com → "John Doe"
    local_part = email.split('@')[0]
    name = local_part.replace('.', ' ').replace('_', ' ').title()
    return name
```

**Pattern 2: Endpoint - Extract Service Endpoints**

Endpoints are routable URLs with monitoring, certificates, and dependencies.

```python
def extract_endpoints(service_data, service_urn, entity_index):
    """
    Extract endpoints as separate entities with monitoring relationships.

    Input YAML:
        endPoints:
        - url: api.example.com
          monitoring:
          - provider: blackbox-tls-expiration
            timeout: 30s
        - url: metrics.example.com/health
          public: true

    Output: Endpoint entities with monitoring links
    """
    endpoints_data = service_data.get('endPoints', [])
    endpoint_entities = []

    for idx, endpoint_data in enumerate(endpoints_data):
        url = endpoint_data.get('url')
        if not url:
            log_warning(f"Endpoint missing URL in {service_urn}")
            continue

        # URN based on URL (composite key)
        endpoint_urn = f"urn:endpoint:{normalize_urn_component(url)}"

        endpoint_entity = {
            "@id": endpoint_urn,
            "@type": "Endpoint",
            "name": url,  # Fallback name
            "fullUrl": f"https://{url}" if not url.startswith('http') else url,
            "url": url
        }

        # Extract properties
        if 'public' in endpoint_data:
            endpoint_entity['isPublic'] = endpoint_data['public']
        if 'path' in endpoint_data:
            endpoint_entity['path'] = endpoint_data['path']

        # Extract monitoring configs as relationships
        if 'monitoring' in endpoint_data:
            monitoring_configs = endpoint_data['monitoring']
            for mon_config in monitoring_configs:
                if isinstance(mon_config, dict) and 'provider' in mon_config:
                    # Link to monitoring provider
                    provider = mon_config['provider']
                    provider_urn = f"urn:monitoring-provider:{normalize_urn_component(provider)}"

                    if 'monitoredBy' not in endpoint_entity:
                        endpoint_entity['monitoredBy'] = []
                    endpoint_entity['monitoredBy'].append({"@id": provider_urn})

                    # Could extract timeout, interval as properties
                    if 'timeout' in mon_config:
                        endpoint_entity['monitoringTimeout'] = mon_config['timeout']

        # Bidirectional relationship with service
        if 'hasEndpoint' not in service_data:
            service_data['hasEndpoint'] = []
        service_data['hasEndpoint'].append({"@id": endpoint_urn})

        endpoint_entity['belongsToService'] = {"@id": service_urn}

        entity_index[endpoint_urn] = endpoint_entity
        endpoint_entities.append(endpoint_entity)

    return endpoint_entities
```

**Pattern 3: CodeComponent - Extract from Code Components Array**

Code components are Git repositories, build configs, and deployment artifacts.

```python
def extract_code_components(service_data, service_urn, entity_index):
    """
    Extract code components as separate entities.

    Input YAML:
        codeComponents:
        - name: "api-server"
          url: "https://github.com/org/api-server"
          resource: openshift_resources
          language: Go
        - name: "web-ui"
          url: "https://github.com/org/web-ui"
          language: TypeScript

    Output: CodeComponent entities
    """
    components_data = service_data.get('codeComponents', [])
    component_entities = []

    for component_data in components_data:
        name = component_data.get('name')
        if not name:
            log_warning(f"CodeComponent missing name in {service_urn}")
            continue

        # Parent-scoped URN (component names unique within service)
        # Extract service name from URN
        service_name = service_urn.split(':')[-1]
        component_urn = f"urn:code-component:{service_name}:{normalize_urn_component(name)}"

        component_entity = {
            "@id": component_urn,
            "@type": "CodeComponent",
            "name": name
        }

        # Extract properties
        if 'url' in component_data:
            component_entity['repositoryUrl'] = component_data['url']
        if 'language' in component_data:
            component_entity['primaryLanguage'] = component_data['language']
        if 'resource' in component_data:
            component_entity['resourceType'] = component_data['resource']

        # Bidirectional relationship
        if 'hasCodeComponent' not in service_data:
            service_data['hasCodeComponent'] = []
        service_data['hasCodeComponent'].append({"@id": component_urn})

        component_entity['componentOf'] = {"@id": service_urn}

        entity_index[component_urn] = component_entity
        component_entities.append(component_entity)

    return component_entities
```

**Pattern 4: QuayRepo - Extract Quay Repositories with Permissions**

Quay repositories have teams, permissions, and access control.

```python
def extract_quay_repos(service_data, service_urn, entity_index):
    """
    Extract Quay repositories and their permissions as entities.

    Input YAML:
        quayRepos:
        - org:
            $ref: /dependencies/quay/app-sre.yml
          teams:
          - permissions:
            - $ref: /permissions/quay-admin.yml
            role: admin
          items:
          - name: service-api
            description: "API container images"
            public: false

    Output: QuayRepository entities + QuayPermission entities
    """
    quay_repos_data = service_data.get('quayRepos', [])
    repo_entities = []

    for repo_group in quay_repos_data:
        org_ref = repo_group.get('org', {})
        items = repo_group.get('items', [])
        teams = repo_group.get('teams', [])

        for item in items:
            repo_name = item.get('name')
            if not repo_name:
                continue

            # Global URN (quay repos are globally unique per org)
            service_name = service_urn.split(':')[-1]
            repo_urn = f"urn:quay-repo:{service_name}:{normalize_urn_component(repo_name)}"

            repo_entity = {
                "@id": repo_urn,
                "@type": "QuayRepository",
                "name": repo_name
            }

            # Extract properties
            if 'description' in item:
                repo_entity['description'] = item['description']
            if 'public' in item:
                repo_entity['isPublic'] = item['public']

            # Infer repository URL
            # Requires resolving org $ref or using default
            repo_entity['repositoryUrl'] = f"https://quay.io/repository/{repo_name}"

            # Extract permissions as sub-entities
            for team in teams:
                role = team.get('role', 'read')
                permissions_refs = team.get('permissions', [])

                for perm_ref in permissions_refs:
                    # Create permission entity
                    perm_urn = f"urn:quay-permission:{repo_name}:{role}"

                    perm_entity = {
                        "@id": perm_urn,
                        "@type": "QuayPermission",
                        "name": f"{repo_name} {role} permission",
                        "role": role,
                        "grantsAccessTo": {"@id": repo_urn}
                    }

                    if 'hasPermission' not in repo_entity:
                        repo_entity['hasPermission'] = []
                    repo_entity['hasPermission'].append({"@id": perm_urn})

                    entity_index[perm_urn] = perm_entity

            # Link to service
            if 'hasQuayRepo' not in service_data:
                service_data['hasQuayRepo'] = []
            service_data['hasQuayRepo'].append({"@id": repo_urn})

            repo_entity['belongsToService'] = {"@id": service_urn}

            entity_index[repo_urn] = repo_entity
            repo_entities.append(repo_entity)

    return repo_entities
```

**Pattern 5: EscalationPolicy - Extract Nested Escalation Policies**

Escalation policies define alert routing and on-call schedules.

```python
def extract_escalation_policy(service_data, service_urn, entity_index):
    """
    Extract escalation policy as a separate entity.

    Input YAML:
        escalationPolicy:
          name: "Primary on-call"
          channels:
          - pagerduty: team-primary
          - slack: "#team-alerts"
          rules:
          - delay: 0
            target: pagerduty

    Output: EscalationPolicy entity
    """
    policy_data = service_data.get('escalationPolicy')
    if not policy_data or not isinstance(policy_data, dict):
        return []

    # Parent-scoped URN
    service_name = service_urn.split(':')[-1]
    policy_name = policy_data.get('name', 'default')
    policy_urn = f"urn:escalation-policy:{service_name}:{normalize_urn_component(policy_name)}"

    policy_entity = {
        "@id": policy_urn,
        "@type": "EscalationPolicy",
        "name": policy_name
    }

    # Extract channels
    if 'channels' in policy_data:
        channels = policy_data['channels']
        for channel in channels:
            if 'pagerduty' in channel:
                policy_entity['pagerdutyChannel'] = channel['pagerduty']
            if 'slack' in channel:
                policy_entity['slackChannel'] = channel['slack']

    # Extract rules (could be sub-entities if complex)
    if 'rules' in policy_data:
        policy_entity['escalationRules'] = policy_data['rules']

    # Link to service
    service_data['hasEscalationPolicy'] = {"@id": policy_urn}
    policy_entity['appliesTo'] = {"@id": service_urn}

    entity_index[policy_urn] = policy_entity
    return [policy_entity]
```

**Pattern 6: ResourceLimit - Extract Resource Requests/Limits**

Resource limits define compute quotas and constraints.

```python
def extract_resource_limits(namespace_data, namespace_urn, entity_index):
    """
    Extract resource requests and limits as queryable entities.

    Input YAML:
        resourceQuota:
          requests:
            cpu: "100"
            memory: "256Gi"
          limits:
            cpu: "200"
            memory: "512Gi"

    Output: ResourceQuota entity with structured limits
    """
    quota_data = namespace_data.get('resourceQuota')
    if not quota_data or not isinstance(quota_data, dict):
        return []

    # Create resource quota entity
    namespace_name = namespace_urn.split(':')[-1]
    quota_urn = f"urn:resource-quota:{namespace_name}"

    quota_entity = {
        "@id": quota_urn,
        "@type": "ResourceQuota",
        "name": f"{namespace_name} Resource Quota"
    }

    # Extract requests
    if 'requests' in quota_data:
        requests = quota_data['requests']
        if 'cpu' in requests:
            quota_entity['requestsCpu'] = requests['cpu']
        if 'memory' in requests:
            quota_entity['requestsMemory'] = requests['memory']

    # Extract limits
    if 'limits' in quota_data:
        limits = quota_data['limits']
        if 'cpu' in limits:
            quota_entity['limitsCpu'] = limits['cpu']
        if 'memory' in limits:
            quota_entity['limitsMemory'] = limits['memory']

    # Link to namespace
    namespace_data['hasResourceQuota'] = {"@id": quota_urn}
    quota_entity['appliesTo'] = {"@id": namespace_urn}

    entity_index[quota_urn] = quota_entity
    return [quota_entity]
```

#### Generic Sub-Entity Extraction Pattern

For other nested structures not covered above:

```python
def extract_sub_entity(parent_data, field_name, parent_urn, entity_index):
    """
    Generic sub-entity extraction for nested objects.

    Use this for any nested structure that meets sub-entity criteria.
    """
    nested_data = parent_data.get(field_name)
    if not nested_data:
        return []

    # Handle array of objects
    if isinstance(nested_data, list):
        sub_entities = []
        for idx, item in enumerate(nested_data):
            if not isinstance(item, dict):
                continue

            # Check if should extract as entity
            should_extract, entity_type = should_create_sub_entity(
                item, field_name, parent_data
            )

            if should_extract:
                sub_entity = create_sub_entity(
                    item, entity_type, parent_urn, idx, entity_index
                )
                sub_entities.append(sub_entity)

        return sub_entities

    # Handle single nested object
    elif isinstance(nested_data, dict):
        should_extract, entity_type = should_create_sub_entity(
            nested_data, field_name, parent_data
        )

        if should_extract:
            sub_entity = create_sub_entity(
                nested_data, entity_type, parent_urn, 0, entity_index
            )
            return [sub_entity]

    return []


def create_sub_entity(data, entity_type, parent_urn, index, entity_index):
    """Create a sub-entity with parent-scoped URN."""
    # Generate URN
    parent_name = parent_urn.split(':')[-1]

    # Try to get name from data
    name = data.get('name') or data.get('id') or f"item-{index}"

    sub_urn = f"urn:{entity_type.lower()}:{parent_name}:{normalize_urn_component(name)}"

    sub_entity = {
        "@id": sub_urn,
        "@type": entity_type,
        "name": name
    }

    # Extract all properties (non-reference fields)
    for key, value in data.items():
        if key in ['name', 'id']:  # Already used in URN
            continue
        if not is_reference_field(value):
            sub_entity[key] = value

    # Add parent relationship
    sub_entity['parentEntity'] = {"@id": parent_urn}

    entity_index[sub_urn] = sub_entity
    return sub_entity
```

#### URN Patterns for Sub-Entities

Choose appropriate URN patterns based on scope and reusability:

**Parent-Scoped URNs** (for items unique within parent):

```
urn:code-component:{service_name}:{component_name}
urn:escalation-policy:{service_name}:{policy_name}
urn:resource-quota:{namespace_name}
```

**Global URNs** (for reusable entities):

```
urn:user:{email}  # User can own multiple services
urn:monitoring-provider:{provider_name}  # Provider used by multiple endpoints
urn:quay-org:{org_name}  # Org contains multiple repos
```

**Composite URNs** (for unique combinations):

```
urn:endpoint:{host}:{path}
urn:quay-permission:{repo_name}:{team_name}:{role}
```

#### Integration with Extraction Workflow

Add sub-entity extraction to the main extraction loop:

```python
def extract_entity_with_sub_entities(data, filepath, schema_config, entity_index):
    """Extract entity and its nested sub-entities."""

    # Extract main entity (Pass 1 style)
    main_entity = extract_entity_pass1(data, filepath, schema_config)
    main_urn = main_entity["@id"]

    # Add to index
    entity_index[main_urn] = main_entity

    # Extract sub-entities based on entity type
    sub_entities = []

    if main_entity["@type"] == "Service":
        # Extract service-specific sub-entities
        sub_entities.extend(extract_service_owners(data, main_urn, entity_index))
        sub_entities.extend(extract_endpoints(data, main_urn, entity_index))
        sub_entities.extend(extract_code_components(data, main_urn, entity_index))
        sub_entities.extend(extract_quay_repos(data, main_urn, entity_index))
        sub_entities.extend(extract_escalation_policy(data, main_urn, entity_index))

    elif main_entity["@type"] == "Namespace":
        # Extract namespace-specific sub-entities
        sub_entities.extend(extract_resource_limits(data, main_urn, entity_index))

    # Generic extraction for other nested structures
    for field_name in data.keys():
        if field_name not in ['serviceOwners', 'endPoints', 'codeComponents', 'quayRepos']:
            sub_entities.extend(
                extract_sub_entity(data, field_name, main_urn, entity_index)
            )

    return main_entity, sub_entities
```

**Expected Impact**:

Based on baseline analysis, nested structure extraction should yield:

- **~2,000 new entities** from sub-structures (ServiceOwners, Endpoints, CodeComponents, etc.)
- **~4,000 new relationships** (bidirectional parent-child links)
- **2x-3x entity count increase** for complex services with many nested components
- **Improved queryability**: Can now query "find all services owned by user X", "find endpoints monitored by provider Y"
- **Richer graph structure**: Relationship density increases from 1.9 → 3.5 avg relationships per entity

**Simple Sub-Entity Pattern** (for basic nested structures):

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

**When to use simple inline arrays:**

- Simple key-value pairs (1-2 properties)
- Purely descriptive data
- No additional relationships needed

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
        'sparse_entities': [],  # Entities with < 3 fields
        'sub_entities_by_type': {},  # Track sub-entity extraction (Iteration 4)
        'parent_entities_with_sub_entities': 0,  # Count parents with sub-entities
        'parent_child_relationships': 0  # Count parent-child links
    }

    # Sub-entity types to track (Iteration 4)
    sub_entity_types = {
        'ServiceOwner', 'User', 'Endpoint', 'CodeComponent',
        'QuayRepository', 'QuayPermission', 'EscalationPolicy',
        'ResourceQuota', 'MonitoringConfig'
    }

    for entity in entities:
        entity_type = entity.get('@type')

        # Track sub-entities by type (Iteration 4)
        if entity_type in sub_entity_types:
            quality_report['sub_entities_by_type'][entity_type] = \
                quality_report['sub_entities_by_type'].get(entity_type, 0) + 1

        # Check description presence
        if 'description' in entity:
            quality_report['entities_with_descriptions'] += 1

        # Count relationships
        relationship_count = 0
        has_sub_entities = False

        for key, value in entity.items():
            if isinstance(value, dict) and "@id" in value:
                relationship_count += 1

                # Check for parent-child relationships (Iteration 4)
                if key in ['hasOwner', 'hasEndpoint', 'hasCodeComponent', 'hasQuayRepo',
                          'hasEscalationPolicy', 'hasResourceQuota', 'hasPermission']:
                    has_sub_entities = True
                    quality_report['parent_child_relationships'] += 1

            elif isinstance(value, list):
                refs = [v for v in value if isinstance(v, dict) and "@id" in v]
                relationship_count += len(refs)

                # Check for parent-child relationships in arrays (Iteration 4)
                if key in ['hasOwner', 'hasEndpoint', 'hasCodeComponent', 'hasQuayRepo',
                          'hasEscalationPolicy', 'hasResourceQuota', 'hasPermission']:
                    has_sub_entities = True
                    quality_report['parent_child_relationships'] += len(refs)

        # Track parent entities with sub-entities (Iteration 4)
        if has_sub_entities:
            quality_report['parent_entities_with_sub_entities'] += 1

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

    # Sub-entity extraction metrics (Iteration 4)
    if quality_report['sub_entities_by_type']:
        print(f"\n📊 Sub-Entity Extraction Metrics (Iteration 4):")
        total_sub_entities = sum(quality_report['sub_entities_by_type'].values())
        print(f"  Total sub-entities: {total_sub_entities}")
        print(f"  Sub-entities by type:")
        for entity_type, count in sorted(quality_report['sub_entities_by_type'].items(),
                                        key=lambda x: -x[1]):
            print(f"    {entity_type}: {count}")
        print(f"  Parent entities with sub-entities: {quality_report['parent_entities_with_sub_entities']}")
        print(f"  Parent-child relationships: {quality_report['parent_child_relationships']}")

        # Calculate percentage of parents with sub-entities
        # This helps validate extraction completeness
        parent_types = ['Service', 'Namespace', 'Application']
        parent_count = sum(1 for e in entities if e.get('@type') in parent_types)
        if parent_count > 0:
            pct_with_sub = (100.0 * quality_report['parent_entities_with_sub_entities'] /
                           parent_count)
            print(f"  Percentage of parents with sub-entities: {pct_with_sub:.1f}%")

    return quality_report
```

---

## Phase 3: Relationship Resolution

**Goal**: Validate all references resolve to actual entities and create bidirectional edges.

**Note**: When using the Two-Pass Extraction Strategy (see Phase 2), most of this validation happens proactively during Pass 2. This phase provides additional validation patterns for single-pass extraction or post-extraction validation.

### Proactive Reference Validation Pattern

**Best Practice**: Validate references BEFORE creating them, not after.

```python
def create_relationship_with_validation(source_entity, predicate, target_urn, entity_index):
    """
    Create a relationship with proactive validation.

    Returns: True if relationship created, False if validation failed
    """
    # Validate target exists
    if target_urn not in entity_index:
        log_warning(
            f"Cannot create relationship: target does not exist\n"
            f"  Source: {source_entity['@id']}\n"
            f"  Predicate: {predicate}\n"
            f"  Target: {target_urn}"
        )
        return False

    # Validate target has required metadata
    target_entity = entity_index[target_urn]
    if 'name' not in target_entity or not target_entity['name']:
        log_warning(
            f"Target entity lacks name (will appear as hex ID)\n"
            f"  Target: {target_urn}\n"
            f"  Referenced by: {source_entity['@id']}"
        )
        # Create relationship anyway but log warning

    # Create relationship
    if predicate not in source_entity:
        source_entity[predicate] = []

    if isinstance(source_entity[predicate], list):
        source_entity[predicate].append({"@id": target_urn})
    else:
        source_entity[predicate] = {"@id": target_urn}

    return True


def validate_and_create_relationships(entities, entity_index):
    """
    Validate all relationships before creating them.

    Use this pattern in single-pass extraction when relationships
    are created during entity extraction.
    """
    stats = {
        'created': 0,
        'failed': 0,
        'missing_targets': []
    }

    for entity in entities:
        # Get pending relationships
        pending_refs = entity.get('_pending_refs', [])

        for ref in pending_refs:
            target_urn = ref['target_urn']
            predicate = ref['predicate']

            # Validate and create
            if create_relationship_with_validation(
                entity, predicate, target_urn, entity_index
            ):
                stats['created'] += 1
            else:
                stats['failed'] += 1
                stats['missing_targets'].append({
                    'source': entity['@id'],
                    'predicate': predicate,
                    'target': target_urn
                })

        # Clean up temporary field
        if '_pending_refs' in entity:
            del entity['_pending_refs']

    print(f"\n📊 Relationship Validation:")
    print(f"   Created: {stats['created']}")
    print(f"   Failed: {stats['failed']}")

    if stats['missing_targets']:
        print(f"\n⚠️  {len(stats['missing_targets'])} broken references detected:")
        for ref in stats['missing_targets'][:10]:
            print(f"   {ref['source']} --{ref['predicate']}--> {ref['target']}")

    return stats
```

### Reference Validation Before Creation

**Pattern**: Check-then-create instead of create-then-validate

```python
# ❌ BAD: Create first, validate later
def extract_service_old(data, entity_index):
    service = {
        "@id": f"urn:service:{data['name']}",
        "@type": "Service",
        "name": data['name']
    }

    # Create relationship without checking
    if 'namespace' in data:
        namespace_urn = f"urn:namespace:{data['namespace']}"
        service['belongsTo'] = {"@id": namespace_urn}  # May be broken!

    return service


# ✅ GOOD: Validate before creating
def extract_service_new(data, entity_index):
    service = {
        "@id": f"urn:service:{data['name']}",
        "@type": "Service",
        "name": data['name']
    }

    # Validate before creating relationship
    if 'namespace' in data:
        namespace_urn = f"urn:namespace:{data['namespace']}"

        # Check if target exists
        if namespace_urn in entity_index:
            service['belongsTo'] = {"@id": namespace_urn}
        else:
            log_warning(
                f"Namespace {namespace_urn} not found for service {service['@id']}\n"
                f"  Skipping belongsTo relationship"
            )
            # Option: Create stub or skip relationship
            # Option: Add to broken_refs report for follow-up

    return service
```

### URN Matching Validation

**Problem**: Constructed URNs don't match actual extracted entity URNs

**Solution**: Validate URN construction against entity index

```python
def validate_urn_construction(expected_urn, entity_index, entity_type):
    """
    Validate that a constructed URN exists in the entity index.

    If not found, attempt to find the correct URN using fuzzy matching.
    """
    # Exact match
    if expected_urn in entity_index:
        return expected_urn

    # URN not found - try fuzzy matching
    log_warning(f"URN not found: {expected_urn}")

    # Try alternative URN patterns for this entity type
    alternatives = generate_alternative_urns(expected_urn, entity_type)

    for alt_urn in alternatives:
        if alt_urn in entity_index:
            log_info(f"Found alternative URN: {alt_urn}")
            return alt_urn

    # Try searching by name
    name_segment = expected_urn.split(':')[-1]
    matching_urns = [
        urn for urn, entity in entity_index.items()
        if entity.get('@type') == entity_type and
        name_segment in urn
    ]

    if len(matching_urns) == 1:
        log_info(f"Found URN by name match: {matching_urns[0]}")
        return matching_urns[0]
    elif len(matching_urns) > 1:
        log_warning(
            f"Multiple URNs match {name_segment}: {matching_urns}\n"
            f"  Cannot determine correct URN"
        )

    # No match found
    return None


def generate_alternative_urns(urn, entity_type):
    """
    Generate alternative URN patterns for common mismatches.

    Common issues:
    - Different casing (Cincinnati vs cincinnati)
    - Different separators (my-service vs my_service)
    - Missing/extra namespace prefix
    """
    alternatives = []

    parts = urn.split(':')
    if len(parts) < 3:
        return alternatives

    # Try lowercase version
    alternatives.append(':'.join([p.lower() for p in parts]))

    # Try with underscores instead of hyphens
    last_part = parts[-1]
    if '-' in last_part:
        parts[-1] = last_part.replace('-', '_')
        alternatives.append(':'.join(parts))

    # Try with hyphens instead of underscores
    last_part = parts[-1]
    if '_' in last_part:
        parts[-1] = last_part.replace('_', '-')
        alternatives.append(':'.join(parts))

    # Try without middle segments (urn:type:parent:name -> urn:type:name)
    if len(parts) > 3:
        alternatives.append(f"{parts[0]}:{parts[1]}:{parts[-1]}")

    # Try with namespace prefix (urn:type:name -> urn:type:cluster:name)
    # This requires knowing common prefixes - repository specific

    return list(set(alternatives))  # Deduplicate
```

### $ref Resolution Enhancement

**Pattern**: Follow $ref links to ensure target entities are extracted

```python
def resolve_ref_with_extraction(ref_value, entity_index, base_path):
    """
    Resolve a $ref, extracting the target entity if needed.

    Handles:
    - Relative paths: ../namespaces/prod.yml
    - Absolute paths: /data/services/foo/app.yml
    - Already extracted: Check index first
    """
    # Already a URN
    if isinstance(ref_value, str) and ref_value.startswith('urn:'):
        return ref_value

    # Extract file path from $ref
    if isinstance(ref_value, dict) and '$ref' in ref_value:
        file_path = ref_value['$ref']
    elif isinstance(ref_value, str):
        file_path = ref_value
    else:
        log_warning(f"Unknown $ref format: {ref_value}")
        return None

    # Resolve relative path
    if file_path.startswith('./') or file_path.startswith('../'):
        file_path = os.path.normpath(os.path.join(base_path, file_path))

    # Check if already extracted (by file path)
    for urn, entity in entity_index.items():
        if entity.get('_source_file') == file_path:
            log_info(f"$ref already extracted: {file_path} -> {urn}")
            return urn

    # Not extracted - extract now
    log_info(f"Following $ref: {file_path}")

    try:
        # Load and extract entity
        data = load_yaml_or_json(file_path)

        # Infer entity type from schema or file path
        entity_type = infer_entity_type(data, file_path)

        # Get schema config for this type
        schema_config = get_schema_config(entity_type)
        if not schema_config:
            log_warning(f"No schema config for type {entity_type}")
            return None

        # Extract entity
        entity = extract_entity_pass1(data, file_path, schema_config)

        # Add to index
        entity_index[entity['@id']] = entity

        log_info(f"Extracted $ref entity: {entity['@id']}")
        return entity['@id']

    except Exception as e:
        log_error(f"Failed to extract $ref {file_path}: {e}")
        return None


def build_dependency_graph(files, base_dir):
    """
    Build a dependency graph of files based on $ref links.

    Use this to determine extraction order - extract referenced
    entities before entities that reference them.
    """
    dependency_graph = {}  # file -> [files it references]

    for file_path in files:
        try:
            data = load_yaml_or_json(file_path)
            refs = find_all_refs(data)

            # Resolve relative paths
            resolved_refs = []
            for ref in refs:
                if ref.startswith('./') or ref.startswith('../'):
                    ref = os.path.normpath(os.path.join(os.path.dirname(file_path), ref))
                resolved_refs.append(ref)

            dependency_graph[file_path] = resolved_refs

        except Exception as e:
            log_warning(f"Could not parse {file_path}: {e}")
            dependency_graph[file_path] = []

    return dependency_graph


def topological_sort_files(dependency_graph):
    """
    Sort files in dependency order using topological sort.

    Files with no dependencies come first.
    """
    from collections import deque

    # Calculate in-degrees
    in_degree = {file: 0 for file in dependency_graph}
    for file, deps in dependency_graph.items():
        for dep in deps:
            if dep in in_degree:
                in_degree[dep] += 1

    # Queue files with no dependencies
    queue = deque([file for file, degree in in_degree.items() if degree == 0])
    sorted_files = []

    while queue:
        file = queue.popleft()
        sorted_files.append(file)

        # Reduce in-degree for dependent files
        for dep in dependency_graph.get(file, []):
            if dep in in_degree:
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

    # Check for cycles
    if len(sorted_files) != len(dependency_graph):
        log_warning("Circular dependencies detected - extraction order may not be optimal")

    return sorted_files
```

### Step 1: Collect All Entity URNs

```python
def collect_all_urns(jsonld_file):
    """Build index of all entity URNs."""
    urns = set()

    for entity in load_jsonld(jsonld_file):
        urns.add(entity["@id"])

    return urns
```

### Step 2: Validate References (Post-Extraction)

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

### AI-Driven Relationship Inference (Repository-Agnostic)

**New Best Practice (Iteration 6)**: Use Claude Code's AI reasoning to discover and adapt to any repository's organizational patterns, then infer relationships based on discovered patterns rather than hardcoded rules.

**Key Principle**: The AI should **learn the repository's patterns** through analysis, then **adapt extraction logic** based on discovered patterns. This works for ANY code/data repository (Python projects, Node.js apps, Kubernetes configs, Terraform IaC, documentation repos, etc.).

#### Universal Inference Principles

Claude Code should analyze ANY repository to discover:

1. **Organizational patterns** (how files are structured)
2. **Naming conventions** (how things are named)
3. **Reference patterns** (how entities link to each other)
4. **Ownership patterns** (who owns what)
5. **Dependency patterns** (what depends on what)

Then **ADAPT extraction logic** based on discovered patterns.

#### Pattern Discovery Process (AI-Driven)

**Step 1: Repository Structure Analysis**

Claude Code reads directory tree and identifies organizational patterns:

```python
def discover_organizational_patterns(repo_path):
    """
    AI-driven discovery of how repository organizes entities.

    Claude Code should analyze directory structure and identify patterns like:
    - Files organized by type: /services/{name}/, /packages/{name}/, /components/{name}/
    - Files organized by team: /teams/{team}/, /orgs/{org}/
    - Files organized by function: /frontend/, /backend/, /infrastructure/
    - Files organized by environment: /prod/, /staging/, /dev/

    Returns: Discovered organizational patterns with confidence
    """

    # AI Analysis Example:
    # "I see files organized in /services/{service_name}/ directories.
    #  Each service directory contains:
    #  - app.yml (main service definition)
    #  - namespaces/*.yml (namespace configurations)
    #  - dependencies/*.yml (dependency declarations)
    #
    #  Pattern discovered: Files in /services/foo/ belong to service 'foo'"

    patterns = []

    # Pattern 1: Type-based organization
    # Example discoveries:
    # - /services/{name}/ → service entities
    # - /packages/{name}/ → package entities
    # - /teams/{name}/ → team entities
    # - /components/{name}/ → component entities

    # Pattern 2: Hierarchical organization
    # Example discoveries:
    # - /services/{service}/namespaces/{ns}/ → service owns namespace
    # - /products/{product}/services/ → product contains services
    # - /teams/{team}/repos/ → team owns repositories

    # Pattern 3: Function-based organization
    # Example discoveries:
    # - /frontend/ → frontend components
    # - /backend/ → backend services
    # - /infrastructure/ → infrastructure resources
    # - /docs/ → documentation entities

    return patterns
```

**Example Discoveries** (works for any repo):

```
# Python project discovery:
"I found packages organized in /src/packages/{name}/.
 Files in each package directory include __init__.py, tests/, README.md.
 Pattern: Files in /src/packages/foo/ belong to package 'foo'."

# Kubernetes config discovery:
"I found services organized in /services/{name}/ with subdirectories:
 - /services/{name}/deployments/
 - /services/{name}/configmaps/
 - /services/{name}/secrets/
 Pattern: Resources in /services/foo/* belong to service 'foo'."

# Terraform IaC discovery:
"I found modules organized in /modules/{module_name}/ with files:
 - main.tf, variables.tf, outputs.tf
 Pattern: Resources in /modules/foo/ belong to module 'foo'."
```

**Step 2: Naming Convention Detection**

Claude Code analyzes file/entity names for patterns:

```python
def discover_naming_conventions(entity_names):
    """
    AI-driven discovery of naming patterns in repository.

    Claude Code should identify patterns like:
    - {service}-{env} → service deployed to environment
    - {name}-team → team entity
    - test-{name} or {name}.test → test for entity
    - {prefix}-{name}-{suffix} → composite naming

    Returns: Discovered naming patterns with examples
    """

    # AI Analysis Example:
    # "I notice many entities following the pattern '{name}-prod', '{name}-staging':
    #  - api-gateway-prod
    #  - user-service-prod
    #  - auth-service-staging
    #
    #  Pattern discovered: {service}-{environment} indicates deployment relationship"

    # Example discoveries across repo types:

    # Code repository patterns:
    # - test_{name}.py / {name}_test.py → test file for {name}.py
    # - {name}.spec.ts / {name}.test.ts → test file for {name}.ts
    # - {component}Component.tsx → React component
    # - use{Hook}.ts → React hook

    # Config repository patterns:
    # - {service}-{env}.yml → service in environment
    # - {team}-team.yml → team entity
    # - {name}-deployment.yml → deployment resource
    # - {cluster}-{namespace}-{resource} → hierarchical naming

    # IaC repository patterns:
    # - {resource}-{environment}.tf → Terraform resource
    # - {module}_module.tf → Terraform module
    # - {name}-network.tf → networking resource

    return naming_patterns
```

**Step 3: Reference Pattern Recognition**

Claude Code identifies how entities reference each other:

```python
def discover_reference_patterns(files):
    """
    AI-driven discovery of how entities reference each other.

    Claude Code should recognize:
    - Language-specific: import, require, #include
    - Data-specific: $ref, dependencies[], uses[]
    - Generic: file paths, URLs, identifiers

    Returns: Reference patterns by language/format
    """

    # AI Analysis Example:
    # "I see multiple reference patterns in this repository:
    #
    #  In Python files:
    #  - from packages.auth import User → import dependency
    #  - import database.models → import dependency
    #
    #  In YAML files:
    #  - $ref: /services/foo/app.yml → cross-file reference
    #  - dependencies:
    #      - name: postgresql → external dependency
    #
    #  In Terraform:
    #  - module.vpc.id → module reference
    #  - aws_vpc.main → resource reference"

    # Language-specific patterns:
    language_patterns = {
        'python': ['import', 'from...import'],
        'javascript': ['import...from', 'require()'],
        'typescript': ['import...from', 'import type'],
        'go': ['import'],
        'java': ['import'],
        'c/c++': ['#include'],
        'rust': ['use', 'mod']
    }

    # Data format patterns:
    data_patterns = {
        'yaml': ['$ref', 'dependencies[]', 'uses[]'],
        'json': ['$ref', '"@id"', 'references[]'],
        'terraform': ['module.X', 'resource.X', 'var.X'],
        'kubernetes': ['configMapRef', 'secretRef', 'volumeMount']
    }

    return reference_patterns
```

**Step 4: Metadata Pattern Analysis**

Claude Code finds structured metadata in files:

```python
def discover_metadata_patterns(files):
    """
    AI-driven discovery of metadata fields containing relationship info.

    Claude Code should find:
    - YAML: labels, annotations, tags
    - JSON: metadata objects
    - Code: decorators, comments, docstrings
    - Git: authors, committers, history

    Returns: Metadata patterns and their meanings
    """

    # AI Analysis Example:
    # "I found consistent metadata patterns:
    #
    #  In Kubernetes YAML:
    #  - metadata.labels.app → application name
    #  - metadata.labels.team → owning team
    #  - metadata.labels.environment → deployment environment
    #
    #  In Python files:
    #  - @author docstring tag → author/owner
    #  - @depends_on decorator → dependency
    #
    #  In package.json:
    #  - author field → package owner
    #  - dependencies object → package dependencies"

    # YAML/JSON metadata patterns:
    structured_metadata = {
        'kubernetes': ['metadata.labels', 'metadata.annotations'],
        'docker': ['labels', 'maintainer'],
        'npm': ['author', 'contributors', 'dependencies'],
        'python': ['author', 'maintainers', 'requires'],
        'terraform': ['tags', 'labels']
    }

    # Code metadata patterns:
    code_metadata = {
        'python': ['@author', '@maintainer', '@depends'],
        'javascript': ['@author', '@module', '@requires'],
        'java': ['@author', '@version', '@deprecated']
    }

    # Git metadata:
    git_metadata = ['commit authors', 'file owners (git blame)', 'modification patterns']

    return metadata_patterns
```

#### Universal Relationship Inference Patterns

**Pattern 1: Directory-Based Ownership (Works for any repo)**

```python
def infer_directory_ownership_relationships(entities, entity_index):
    """
    AI Reasoning:
    "I see files organized in directories by entity type.
     Files in /services/foo/ likely belong to service 'foo'.
     Files in /components/bar/ likely belong to component 'bar'."

    Generic Rule Claude Should Apply:
    - If files are grouped in {type}/{name}/ structure
    - Create entity for {name} of type {type}
    - Create belongsTo/partOf relationships

    Works for:
    - Code repos: /packages/, /modules/, /components/
    - Config repos: /services/, /apps/, /clusters/
    - Docs repos: /products/, /features/, /teams/
    - IaC repos: /environments/, /modules/, /resources/
    """

    inferred = []

    # Example for Python project:
    # /src/packages/auth/
    # /src/packages/database/
    # → auth and database are packages, files in each belong to that package

    # Example for Kubernetes configs:
    # /services/api-gateway/deployments/
    # /services/user-service/configmaps/
    # → api-gateway and user-service are services, resources in each belong to that service

    # Example for Terraform:
    # /modules/vpc/main.tf
    # /modules/ec2/main.tf
    # → vpc and ec2 are modules, resources in each belong to that module

    # Generic pattern (Claude adapts):
    for entity in entities:
        source_file = entity.get('_source_file', '')

        # Detect organizational pattern (AI discovers this)
        # Examples: /TYPE/NAME/, /NAME-TYPE/, /TYPE-NAME/
        pattern_match = detect_organizational_pattern(source_file)

        if pattern_match:
            parent_type = pattern_match['type']
            parent_name = pattern_match['name']
            parent_urn = f"urn:{parent_type.lower()}:{normalize_urn_component(parent_name)}"

            if parent_urn in entity_index:
                inferred.append({
                    'source': parent_urn,
                    'predicate': 'contains',  # or 'owns', 'has', depending on type
                    'target': entity["@id"],
                    'reason': 'directory_structure',
                    'confidence': 'high'
                })

    return inferred
```

**Pattern 2: File Proximity Relationships (Universal)**

```python
def infer_file_proximity_relationships(entities, entity_index):
    """
    AI Reasoning:
    "Files in the same directory are likely related.
     test-foo.py next to foo.py → test file tests foo.py
     foo.ts and foo.test.ts → test relationship
     README.md in directory → documents contents of directory"

    Generic Rule:
    - Files with similar names in same directory → related
    - test-{name} or {name}.test → tests relationship
    - README/docs → documents relationship
    - {name}.config → configures relationship

    Works across all repository types.
    """

    inferred = []

    # Group entities by directory
    by_directory = {}
    for entity in entities:
        source_file = entity.get('_source_file', '')
        if source_file:
            directory = os.path.dirname(source_file)
            by_directory.setdefault(directory, []).append(entity)

    # Find relationships within directories
    for directory, dir_entities in by_directory.items():
        # Pattern 2a: Test file relationships
        # test_auth.py + auth.py → test tests auth
        # auth.test.ts + auth.ts → test tests auth
        # auth_test.go + auth.go → test tests auth

        # Pattern 2b: Documentation relationships
        # README.md documents all files in directory
        # docs/ directory documents parent

        # Pattern 2c: Configuration relationships
        # config.yml configures application
        # .eslintrc configures linter
        # setup.py configures package

        # Pattern 2d: Companion files
        # foo.py + foo.pyi → type stub for implementation
        # component.tsx + component.module.css → styles for component

        # Claude discovers these patterns by analyzing file naming in the repo

        for entity in dir_entities:
            filename = os.path.basename(entity.get('_source_file', ''))

            # Test relationship detection (language-agnostic)
            if is_test_file(filename):
                tested_file = find_tested_file(filename, dir_entities)
                if tested_file:
                    inferred.append({
                        'source': entity["@id"],
                        'predicate': 'tests',
                        'target': tested_file["@id"],
                        'reason': 'file_proximity_test',
                        'confidence': 'high'
                    })

            # Documentation relationship detection
            if is_documentation_file(filename):
                for other_entity in dir_entities:
                    if other_entity != entity and not is_documentation_file(other_entity.get('_source_file', '')):
                        inferred.append({
                            'source': entity["@id"],
                            'predicate': 'documents',
                            'target': other_entity["@id"],
                            'reason': 'file_proximity_documentation',
                            'confidence': 'medium'
                        })

    return inferred
```

**Pattern 3: Import/Dependency Inference (Language-Agnostic)**

```python
def infer_import_dependency_relationships(entities, entity_index):
    """
    AI Reasoning:
    "This file imports/requires/includes other files.
     These are dependencies."

    Language-Specific Detection:
    - Python: import X, from X import Y
    - JavaScript: import X from 'Y', require('X')
    - Go: import "package"
    - Java: import package.Class
    - C/C++: #include "header.h"
    - YAML: $ref, dependencies[]
    - Terraform: module "name" { source = "..." }

    Claude Should:
    1. Recognize the language/format
    2. Extract import/dependency statements
    3. Resolve to target entities
    4. Create dependsOn/imports relationships
    """

    inferred = []

    for entity in entities:
        source_file = entity.get('_source_file', '')
        if not source_file:
            continue

        # Detect language/format
        language = detect_language(source_file)

        # Extract dependencies using language-specific patterns
        dependencies = extract_dependencies(source_file, language)

        for dep in dependencies:
            # Resolve dependency to entity URN
            target_urn = resolve_dependency_to_urn(dep, entity_index, language)

            if target_urn and target_urn in entity_index:
                inferred.append({
                    'source': entity["@id"],
                    'predicate': 'dependsOn',  # or 'imports', 'includes', 'requires'
                    'target': target_urn,
                    'reason': f'{language}_import',
                    'confidence': 'high'
                })

    return inferred


def extract_dependencies(source_file, language):
    """
    Extract dependency statements based on language.
    Claude Code should recognize patterns for each language.
    """

    # Python
    if language == 'python':
        # import module
        # from package import Class
        # from . import relative
        return extract_python_imports(source_file)

    # JavaScript/TypeScript
    elif language in ['javascript', 'typescript']:
        # import X from 'module'
        # import { Y } from 'module'
        # require('module')
        return extract_js_imports(source_file)

    # Go
    elif language == 'go':
        # import "package/path"
        # import alias "package/path"
        return extract_go_imports(source_file)

    # Java
    elif language == 'java':
        # import package.Class;
        # import package.*;
        return extract_java_imports(source_file)

    # C/C++
    elif language in ['c', 'cpp']:
        # #include "header.h"
        # #include <system_header.h>
        return extract_cpp_includes(source_file)

    # YAML
    elif language == 'yaml':
        # $ref: /path/to/file.yml
        # dependencies:
        #   - name: postgresql
        return extract_yaml_refs(source_file)

    # Terraform
    elif language == 'terraform':
        # module "name" { source = "..." }
        # resource "type" "name" { ... }
        return extract_terraform_deps(source_file)

    # Add more languages as needed

    return []
```

**Pattern 4: Naming-Based Relationships (Generic)**

```python
def infer_naming_based_relationships(entities, entity_index):
    """
    AI Reasoning:
    "Entity names contain clues about relationships:
     - my-service-prod → service 'my-service' in environment 'prod'
     - platform-team → team entity
     - api-gateway-deployment → deployment of api-gateway
     - user-service-test → test for user-service"

    Generic Patterns Claude Should Recognize:
    - {entity}-{environment} → deployed to environment
    - {name}-team → team entity
    - {name}-{type} → entity of specific type
    - {parent}-{child} → hierarchical relationship

    Works across repository types.
    """

    inferred = []

    # Build name index for pattern matching
    entities_by_name = {}
    for entity in entities:
        name = entity.get('name', '').lower()
        if name:
            entities_by_name.setdefault(name, []).append(entity)

    # Pattern 4a: Service-Environment naming
    # Examples: api-gateway-prod, user-service-staging, auth-service-dev
    # Pattern: {service}-{environment}

    environments = ['prod', 'production', 'staging', 'stage', 'dev', 'development', 'test', 'qa']

    for entity in entities:
        name = entity.get('name', '').lower()

        for env in environments:
            if name.endswith(f'-{env}'):
                service_name = name[:-len(env)-1]  # Remove -env suffix

                # Find matching service entity
                for candidate in entities_by_name.get(service_name, []):
                    if candidate.get('@type') in ['Service', 'Application', 'Component']:
                        # Create environment entity if doesn't exist
                        env_urn = f"urn:environment:{env}"

                        inferred.append({
                            'source': candidate["@id"],
                            'predicate': 'deployedTo',
                            'target': env_urn,
                            'reason': 'naming_pattern_service_environment',
                            'confidence': 'medium'
                        })
                        break

    # Pattern 4b: Team naming
    # Examples: platform-team, sre-team, engineering-team
    # Pattern: {name}-team

    for entity in entities:
        name = entity.get('name', '').lower()

        if name.endswith('-team'):
            team_base_name = name[:-5]  # Remove -team suffix

            # Find services/components matching team name
            for candidate in entities:
                candidate_name = candidate.get('name', '').lower()

                # If service name contains team base name, likely owned by that team
                if team_base_name in candidate_name and candidate.get('@type') in ['Service', 'Application', 'Component']:
                    inferred.append({
                        'source': entity["@id"],
                        'predicate': 'owns',
                        'target': candidate["@id"],
                        'reason': 'naming_pattern_team_ownership',
                        'confidence': 'medium'
                    })

    # Pattern 4c: Type suffix naming
    # Examples: api-gateway-deployment, user-service-configmap, auth-secret
    # Pattern: {name}-{type}

    type_suffixes = {
        'deployment': 'Deployment',
        'service': 'Service',
        'configmap': 'ConfigMap',
        'secret': 'Secret',
        'ingress': 'Ingress',
        'route': 'Route',
        'test': 'Test',
        'mock': 'Mock'
    }

    for entity in entities:
        name = entity.get('name', '').lower()

        for suffix, entity_type in type_suffixes.items():
            if name.endswith(f'-{suffix}'):
                base_name = name[:-len(suffix)-1]

                # Find matching base entity
                for candidate in entities_by_name.get(base_name, []):
                    inferred.append({
                        'source': entity["@id"],
                        'predicate': 'instanceOf',  # or 'deploysTo', 'configures', etc.
                        'target': candidate["@id"],
                        'reason': f'naming_pattern_type_suffix_{suffix}',
                        'confidence': 'medium'
                    })
                    break

    return inferred
```

**Pattern 5: Metadata-Based Relationships (Format-Agnostic)**

```python
def infer_metadata_based_relationships(entities, entity_index):
    """
    AI Reasoning:
    "Metadata fields contain relationship information:
     - labels.team: 'platform' → owned by platform team
     - tags: ['production'] → deployed to production
     - author: 'jdoe' → created by jdoe"

    Generic Detection (Claude adapts to format):
    - YAML: labels, annotations, tags, metadata
    - JSON: tags, labels, metadata, attributes
    - Code comments: @author, @owner, @team
    - Git: commit authors, file owners (git blame)
    - Kubernetes: metadata.labels, metadata.annotations

    Works across all data formats.
    """

    inferred = []

    for entity in entities:
        # Pattern 5a: Team/owner labels
        # Kubernetes: metadata.labels.team
        # JSON: tags.team, labels.team
        # Python: @team decorator/docstring

        team_label = (
            entity.get('teamLabel') or
            entity.get('label_team') or
            entity.get('labels', {}).get('team') or
            entity.get('metadata', {}).get('labels', {}).get('team')
        )

        if team_label:
            team_urn = f"urn:team:{normalize_urn_component(team_label)}"
            if team_urn in entity_index:
                inferred.append({
                    'source': team_urn,
                    'predicate': 'owns',
                    'target': entity["@id"],
                    'reason': 'metadata_team_label',
                    'confidence': 'high'
                })

        # Pattern 5b: Environment tags
        # tags: ['production'], labels.environment: 'prod'

        tags = entity.get('tags', [])
        env_label = entity.get('labels', {}).get('environment')

        environments_found = []
        if isinstance(tags, list):
            environments_found.extend([t for t in tags if t.lower() in ['production', 'staging', 'development', 'test']])
        if env_label:
            environments_found.append(env_label)

        for env in environments_found:
            env_urn = f"urn:environment:{normalize_urn_component(env)}"
            inferred.append({
                'source': entity["@id"],
                'predicate': 'deployedTo',
                'target': env_urn,
                'reason': 'metadata_environment_tag',
                'confidence': 'high'
            })

        # Pattern 5c: Owner annotations
        # annotations.owner, @author docstring

        owner = (
            entity.get('owner') or
            entity.get('annotations', {}).get('owner') or
            entity.get('author')
        )

        if owner:
            # Could be user email or team name
            if '@' in str(owner):
                owner_urn = f"urn:user:{normalize_urn_component(owner)}"
            else:
                owner_urn = f"urn:team:{normalize_urn_component(owner)}"

            if owner_urn in entity_index:
                inferred.append({
                    'source': owner_urn,
                    'predicate': 'owns',
                    'target': entity["@id"],
                    'reason': 'metadata_owner',
                    'confidence': 'high'
                })

    return inferred
```

**Pattern 6: Temporal Relationships (Repository History)**

```python
def infer_temporal_relationships(entities, entity_index, repo_path):
    """
    AI Reasoning:
    "Git history reveals relationships:
     - Files modified together → related
     - Same authors → same team
     - Frequent co-commits → dependency relationship"

    Claude Should Analyze:
    - git log: commit history, authors
    - git blame: file ownership
    - Modification patterns: files changed together
    - Author patterns: team membership inference

    Works for any Git repository.
    """

    inferred = []

    try:
        import subprocess

        # Pattern 6a: Co-modification relationships
        # Files frequently modified together are likely related

        # Get commit history
        commits = subprocess.check_output(
            ['git', 'log', '--pretty=format:%H', '--name-only'],
            cwd=repo_path,
            text=True
        ).strip().split('\n\n')

        # Build co-modification matrix
        co_modifications = {}
        for commit in commits:
            lines = commit.strip().split('\n')
            if len(lines) < 2:
                continue

            files_in_commit = lines[1:]  # Skip commit hash

            for i, file1 in enumerate(files_in_commit):
                for file2 in files_in_commit[i+1:]:
                    pair = tuple(sorted([file1, file2]))
                    co_modifications[pair] = co_modifications.get(pair, 0) + 1

        # Find entities for frequently co-modified files
        for (file1, file2), count in co_modifications.items():
            if count >= 5:  # Threshold: modified together 5+ times
                entity1 = find_entity_by_source_file(entities, file1)
                entity2 = find_entity_by_source_file(entities, file2)

                if entity1 and entity2:
                    inferred.append({
                        'source': entity1["@id"],
                        'predicate': 'relatedTo',
                        'target': entity2["@id"],
                        'reason': 'git_co_modification',
                        'confidence': 'medium',
                        'count': count
                    })

        # Pattern 6b: Author-based ownership
        # Files primarily modified by same author likely owned by same person/team

        # Get file authors (git blame)
        file_authors = {}
        for entity in entities:
            source_file = entity.get('_source_file', '')
            if not source_file or not os.path.exists(os.path.join(repo_path, source_file)):
                continue

            try:
                blame_output = subprocess.check_output(
                    ['git', 'blame', '--line-porcelain', source_file],
                    cwd=repo_path,
                    text=True
                )

                # Extract author emails
                authors = []
                for line in blame_output.split('\n'):
                    if line.startswith('author-mail'):
                        email = line.split('<')[1].split('>')[0]
                        authors.append(email)

                # Find primary author (most lines)
                if authors:
                    from collections import Counter
                    primary_author = Counter(authors).most_common(1)[0][0]
                    file_authors[entity["@id"]] = primary_author

            except subprocess.CalledProcessError:
                pass

        # Group entities by primary author
        by_author = {}
        for urn, author in file_authors.items():
            by_author.setdefault(author, []).append(urn)

        # Create author entities and ownership relationships
        for author, entity_urns in by_author.items():
            if len(entity_urns) >= 2:  # Author has 2+ files
                author_urn = f"urn:user:{normalize_urn_component(author)}"

                for entity_urn in entity_urns:
                    inferred.append({
                        'source': author_urn,
                        'predicate': 'maintains',
                        'target': entity_urn,
                        'reason': 'git_primary_author',
                        'confidence': 'medium'
                    })

    except Exception as e:
        # Git not available or not a git repo
        print(f"Warning: Could not extract git history: {e}")

    return inferred
```

#### Adaptability Framework for Claude Code

When Claude Code encounters a **NEW repository type**, follow this framework:

**1. DISCOVER patterns (don't assume)**:

```
Questions Claude Should Ask:
- "What's the directory structure?"
- "How are files organized?"
- "What naming conventions are used?"
- "What metadata exists?"
- "What reference patterns exist?"

Analysis Process:
1. Read directory tree
2. Sample files from each major directory
3. Identify common patterns across samples
4. Categorize patterns by type (org, naming, refs, metadata)
```

**2. INFER relationships based on discovered patterns**:

```
Application Process:
1. Apply universal patterns that work everywhere:
   - Directory ownership
   - File proximity

2. Detect language/format-specific patterns:
   - Python imports → dependsOn
   - YAML $ref → references
   - Terraform module → uses

3. Recognize metadata patterns:
   - labels.team → ownedBy
   - tags: ['prod'] → deployedTo
```

**3. VALIDATE inferences**:

```
Validation Questions:
- "Do inferred relationships make sense?"
- "Are there counter-examples?"
- "Is the confidence level appropriate?"

Adjustment Process:
- Check consistency across similar entities
- Look for exceptions to the pattern
- Adjust confidence based on consistency
- Flag ambiguous cases for review
```

**4. REPORT discovered patterns**:

```
Claude Should Report:
- "I found services organized in /services/{name}/"
- "I detected Python imports creating dependencies"
- "I noticed label.team metadata indicating ownership"
- "I discovered {N} high-confidence relationships via pattern X"

Include:
- Pattern descriptions
- Example matches
- Confidence levels
- Statistics (count, coverage %)
```

#### Testing Framework (Prepare for Real Extraction)

To test this iteration, Claude Code will:

**1. Analyze sample repository** (start with app-interface subset)

**2. Discover organizational patterns**:

- Directory structure analysis
- Naming convention detection
- Reference pattern recognition
- Metadata pattern analysis

**3. Infer relationships using general patterns**:

- Apply Pattern 1: Directory-based ownership
- Apply Pattern 2: File proximity
- Apply Pattern 3: Import/dependency detection
- Apply Pattern 4: Naming-based relationships
- Apply Pattern 5: Metadata-based relationships
- Apply Pattern 6: Temporal relationships (if Git available)

**4. Report**:

- Patterns discovered (with examples)
- Relationships inferred (by pattern)
- Confidence levels (high/medium/low distribution)
- Validation results (consistency checks)

**Metrics to measure**:

- Relationships inferred (count)
- Inference patterns applied (which ones worked)
- Accuracy (manual validation sample)
- Coverage (% entities with inferred relationships)
- Time to discover patterns
- Time to apply patterns

**Example Test Output**:

```
Repository Analysis: /path/to/repo

Discovered Patterns:
1. Directory organization: /services/{service_name}/ (42 services found)
2. Naming convention: {service}-{env} (23 instances)
3. Python imports detected (156 dependencies)
4. Kubernetes labels.team found (89 ownership relationships)
5. Git co-modification detected (45 related pairs)

Inferred Relationships:
- Total inferred: 355 relationships
- High confidence: 234 (66%)
- Medium confidence: 98 (28%)
- Low confidence: 23 (6%)

Coverage:
- Entities with inferred relationships: 78%
- Entities still orphaned: 22%

Patterns Applied Successfully:
✅ Pattern 1 (Directory ownership): 42 relationships
✅ Pattern 2 (File proximity): 18 relationships
✅ Pattern 3 (Import dependencies): 156 relationships
✅ Pattern 4 (Naming patterns): 23 relationships
✅ Pattern 5 (Metadata labels): 89 relationships
✅ Pattern 6 (Git co-modification): 27 relationships
```

### Step 4: Infer Implicit Relationships

Create relationships not explicitly defined in data, particularly useful for linking orphaned entities.

#### Inferred Relationship Patterns

Orphaned entities often lack explicit relationships but can be linked through inference patterns based on file paths, naming conventions, and metadata.

**Pattern 1: File-Path-Based Relationship Inference**

Infer ownership and containment from directory structure.

```python
def infer_file_path_relationships(entities, entity_index):
    """
    Infer relationships from file path structure.

    Common patterns:
    - /services/foo/namespaces/prod.yml → Service "foo" hasNamespace "prod"
    - /teams/foo-team/services/bar.yml → Team "foo-team" owns Service "bar"
    - /products/acme/services/ → Product "acme" contains services
    - /services/foo/databases/ → Service "foo" uses databases
    """
    inferred = []

    for entity in entities:
        source_file = entity.get("_source_file", "")
        if not source_file:
            continue

        entity_type = entity.get("@type")

        # Pattern 1a: Services own namespaces in their directory
        if entity_type == "Namespace":
            # /services/cincinnati/namespaces/prod.yaml → cincinnati hasNamespace prod
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

        # Pattern 1b: Teams own services in their directory
        elif entity_type == "Service":
            # /teams/platform-team/services/api.yml → platform-team owns api
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

        # Pattern 1c: Products contain services
        elif entity_type == "Service":
            # /products/openshift/services/console.yml → openshift contains console
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

        # Pattern 1d: AWS accounts contain namespaces
        elif entity_type == "Namespace":
            # /aws/account-123/namespaces/prod.yml → account-123 contains prod namespace
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

    print(f"   File-path-based: {len(inferred)} relationships inferred")
    return inferred


def infer_naming_relationships(entities, entity_index):
    """
    Infer relationships from naming patterns.

    Common patterns:
    - Team "cincinnati-team" owns Service "cincinnati"
    - GitHub org "app-sre" manages repos for services in app-sre
    - Namespace "cincinnati-prod" belongs to Service "cincinnati"
    """
    inferred = []

    # Build name index for fuzzy matching
    entities_by_type = {}
    for entity in entities:
        entity_type = entity.get("@type")
        if entity_type:
            entities_by_type.setdefault(entity_type, []).append(entity)

    # Pattern 2a: Team names match service names (with "-team" suffix)
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

    # Pattern 2b: GitHub org names match service names
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

    # Pattern 2c: Namespace names contain service names with env suffix
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

    print(f"   Naming-based: {len(inferred)} relationships inferred")
    return inferred


def infer_metadata_relationships(entities, entity_index):
    """
    Infer relationships from metadata fields.

    Extract relationships from:
    - Labels (metadata.labels.team: "foo")
    - Annotations
    - Description fields mentioning other entities
    """
    inferred = []

    for entity in entities:
        entity_type = entity.get("@type")

        # Pattern 3a: Label-based relationships
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

            # Check for team label
            team_label = (
                entity.get("teamLabel") or
                entity.get("label_team") or
                entity.get("labels", {}).get("team")
            )

            if team_label:
                team_urn = f"urn:team:{normalize_urn_component(team_label)}"
                if team_urn in entity_index:
                    inferred.append({
                        'source': team_urn,
                        'predicate': 'owns',
                        'target': entity["@id"],
                        'reason': 'metadata_label_team',
                        'confidence': 'high'
                    })

        # Pattern 3b: Annotation-based relationships
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
                elif owner_urn_user in entity_index:
                    inferred.append({
                        'source': owner_urn_user,
                        'predicate': 'owns',
                        'target': entity["@id"],
                        'reason': 'metadata_annotation_owner',
                        'confidence': 'medium'
                    })

        # Pattern 3c: Description field entity mentions
        description = entity.get("description", "")
        if description and isinstance(description, str):
            # Look for entity name mentions in description
            # Simple pattern: "managed by {team-name}" or "part of {product-name}"
            for other_entity in entities:
                other_name = other_entity.get("name", "")
                if not other_name or len(other_name) < 4:  # Skip short names (too many false positives)
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
                    elif other_type == "Product" and any(word in description.lower() for word in ["part of", "component of", "within"]):
                        inferred.append({
                            'source': entity["@id"],
                            'predicate': 'partOf',
                            'target': other_entity["@id"],
                            'reason': 'description_mention_product',
                            'confidence': 'low'
                        })

    print(f"   Metadata-based: {len(inferred)} relationships inferred")
    return inferred


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

After detecting orphans, attempt to link them using inference patterns.

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

**Validation After Linking**:

After applying inferred relationships, validate that the orphan rate meets the target.

```python
# In extract_all_entities_two_pass()
final_orphan_report = detect_orphans(all_entities, global_entity_index)

if final_orphan_report['orphan_rate'] > 0.5:
    print(f"⚠️  WARNING: Orphan rate {final_orphan_report['orphan_rate']:.1f}% exceeds target (0.5%)")
    print(f"   Consider:")
    print(f"   - Reviewing medium-confidence inferred links")
    print(f"   - Extracting additional entity types")
    print(f"   - Adding explicit relationships to source data")
else:
    print(f"✅ Orphan rate {final_orphan_report['orphan_rate']:.1f}% meets target (< 0.5%)")
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

**Best Practice (Iteration 2)**: Use proactive prevention strategies (Two-Pass Extraction in Phase 2, Reference Validation in Phase 3) to avoid broken references BEFORE they're created, rather than repairing them afterward. This phase provides validation and repair as a safety net.

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

### Best Practices for Preventing Issues (Iteration 2 Improvements)

**Priority 1: Use Two-Pass Extraction** (See Phase 2)

The most effective prevention strategy is two-pass extraction:

- Pass 1: Extract ALL entities, build complete URN index
- Pass 2: Create relationships with validation against index

**Expected impact**: Reduces broken references from 18% to < 2%

**Priority 2: Proactive Reference Validation** (See Phase 3)

Validate references BEFORE creating them:

```python
# ❌ BAD: Create relationship without validation
route["routesTo"] = {"@id": f"urn:k8s-service:{namespace}:{service_name}"}

# ✅ GOOD: Validate before creating relationship
service_urn = f"urn:k8s-service:{namespace}:{service_name}"

# Check if target exists in index
if service_urn in entity_index:
    route["routesTo"] = {"@id": service_urn}
else:
    # Target not found - try alternatives
    validated_urn = validate_urn_construction(service_urn, entity_index, 'K8sService')
    if validated_urn:
        route["routesTo"] = {"@id": validated_urn}
    else:
        log_warning(
            f"Service {service_urn} not found for route {route['@id']}\n"
            f"  Skipping routesTo relationship"
        )
        # Log for follow-up extraction or correction
```

**Priority 3: URN Standardization** (See Phase 2)

Use consistent URN generation with validation:

```python
# ❌ BAD: Inconsistent URN construction
service_urn = f"urn:service:{data['name']}"  # No normalization

# ✅ GOOD: Use standardized URN generation
service_urn = generate_urn(
    schema_config['urn_pattern'],
    data
)  # Handles normalization, validation, error handling
```

**Priority 4: $ref Following** (See Phase 3)

Follow $ref links to extract referenced entities:

```python
# ❌ BAD: Assume $ref target is already extracted
target_urn = f"urn:namespace:{ref_value['$ref'].split('/')[-1].replace('.yml', '')}"

# ✅ GOOD: Follow $ref and extract if needed
target_urn = resolve_ref_with_extraction(
    ref_value,
    entity_index,
    base_path
)  # Extracts target if not already in index
```

**Priority 5: Build Entity Index First**

Always build complete index before creating cross-entity relationships:

```python
# ✅ GOOD: Two-pass approach
# Pass 1: Build index
entity_index = {}
for file in files:
    entity = extract_entity_pass1(file, schema_config)
    entity_index[entity["@id"]] = entity

# Pass 2: Create relationships with validation
for entity in entity_index.values():
    for relationship in get_pending_relationships(entity):
        target_urn = relationship["target_urn"]
        if target_urn in entity_index:
            create_relationship(entity, relationship["predicate"], target_urn)
        else:
            log_warning(f"Broken reference: {target_urn}")
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

**Best Practice (Iteration 2)**: Use Two-Pass Extraction instead of dependency ordering:

- Pass 1: Extract ALL entities regardless of type
- Pass 2: Resolve ALL relationships with validation
- **Benefit**: Eliminates need to manually determine dependency order, handles circular dependencies gracefully

### 6.5 Two-Pass Extraction for Broken Reference Prevention

**New Best Practice (Iteration 2)**: Always use two-pass extraction to prevent broken references.

**Problem**: 18% of references in baseline extraction were broken because:

- Target entities not extracted yet
- URN construction mismatches
- $ref links point to unextracted files

**Solution**: Two-pass extraction with validation (see Phase 2)

```python
# Pass 1: Extract all entities, build URN index
all_entities = []
entity_index = {}

for entity_type_config in schema_catalog:
    entities, index = extract_entities_pass1(
        files=glob(entity_type_config['file_pattern']),
        schema_config=entity_type_config
    )
    all_entities.extend(entities)
    entity_index.update(index)

# Pass 2: Resolve relationships with validation
for entity_type_config in schema_catalog:
    type_entities = [e for e in all_entities if e['@type'] == entity_type_config['entity_type']]
    resolved, broken = extract_relationships_pass2(
        type_entities,
        entity_index,
        entity_type_config
    )
    # Track broken references for analysis
```

**Expected Impact**:

- Broken references: 18% → < 2% (90% reduction)
- All missing entities detected before relationship creation
- Clear reports of what needs extraction

**When to Use**:

- All extractions (should be default approach)
- Especially important when:
  - Repository has cross-file $ref links
  - Entity types have complex dependency graphs
  - URN construction patterns vary by type

### 6.6 URN Validation and Standardization

**New Best Practice (Iteration 2)**: Standardize URN generation across all entity types.

**Problem**: Inconsistent URN construction causes mismatches between constructed URNs and actual entity URNs.

**Solution**: Use centralized URN generation with validation (see Phase 2)

```python
# ❌ BAD: Ad-hoc URN construction
service_urn = f"urn:service:{name}"  # No normalization
namespace_urn = f"urn:namespace:{ns_name.upper()}"  # Inconsistent casing
route_urn = f"urn:route:{cluster}_{namespace}_{name}"  # Wrong separator

# ✅ GOOD: Centralized, validated URN generation
service_urn = generate_urn("urn:service:{name}", data)
namespace_urn = generate_urn("urn:namespace:{cluster}:{name}", data)
route_urn = generate_urn("urn:route:{cluster}:{namespace}:{name}", data)
```

**URN Normalization Rules** (applied automatically by `generate_urn()`):

- Lowercase all segments
- Replace spaces with hyphens
- Replace underscores with hyphens
- URL-encode special characters
- Validate format (urn:type:identifier...)

**Benefits**:

- Consistent URN format across all entity types
- Prevents mismatches from casing/separator differences
- Catches missing required fields early
- Enables reliable relationship validation

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

### 6.8 Nested Structure Sub-Entity Extraction

**New Best Practice (Iteration 4)**: Extract nested structures as separate entities to maximize graph richness and queryability.

**Problem**: Flattening nested data loses structural information and query capabilities:

```yaml
# Flattened approach (baseline)
service:
  name: "acs-fleet-manager"
  owner_email: "rhacs-eng-ms@redhat.com"
  owner_name: "Red Hat Advanced Cluster Security"
  endpoint_1_url: "api.example.com"
  endpoint_1_monitoring: "blackbox-tls"
  endpoint_2_url: "metrics.example.com"
  # Cannot query: "Which services does user X own?"
  # Cannot query: "Which endpoints use monitoring provider Y?"
```

**Solution**: Extract nested structures as first-class entities:

```python
# Extract ServiceOwners as User entities
service = {
    "@id": "urn:service:acs-fleet-manager",
    "hasOwner": [{"@id": "urn:user:rhacs-eng-ms@redhat.com"}]
}

user = {
    "@id": "urn:user:rhacs-eng-ms@redhat.com",
    "@type": "User",
    "name": "Red Hat Advanced Cluster Security",
    "email": "rhacs-eng-ms@redhat.com",
    "owns": [{"@id": "urn:service:acs-fleet-manager"}]
}

# Now queryable: "Show all services owned by rhacs-eng-ms@redhat.com"
```

**Decision Tree for Sub-Entity vs Inline**:

```
Does the nested item have 3+ properties?
  └─ YES → Extract as sub-entity
  └─ NO → Continue...

Do you need to query by this field independently?
  └─ YES → Extract as sub-entity
  └─ NO → Continue...

Does the item have relationships to other entities?
  └─ YES → Extract as sub-entity
  └─ NO → Continue...

Does the same item appear in multiple parents?
  └─ YES → Extract as sub-entity
  └─ NO → Keep inline
```

**Common Patterns from App-Interface** (see Phase 2 for code):

1. **ServiceOwner → User** entities with `hasOwner`/`owns` relationships
2. **Endpoint** entities with `belongsToService`/`hasEndpoint` and `monitoredBy` relationships
3. **CodeComponent** entities with `componentOf`/`hasCodeComponent` relationships
4. **QuayRepository** entities with permissions and team access
5. **EscalationPolicy** entities for alert routing
6. **ResourceQuota** entities for compute limits

**Expected Impact**:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Total entities | 11,294 | ~13,300 | +2,000 entities |
| Total relationships | 21,964 | ~26,000 | +4,000 relationships |
| Avg relationships/entity | 1.9 | 3.5 | +84% connectivity |
| New query patterns | 0 | 20+ | Enable complex queries |

**Example: Service with Sub-Entities** (before/after):

```yaml
# Before: Flat extraction (baseline)
{
  "@id": "urn:service:acs-fleet-manager",
  "@type": "Service",
  "name": "ACS Fleet Manager",
  "owner_email": "rhacs-eng-ms@redhat.com",  # Inline - not queryable
  "endpoint_1": "api.example.com",  # Inline - not queryable
  "component_1_name": "api-server",  # Inline - not queryable
  "component_1_url": "https://github.com/org/api"
}

# After: Sub-entity extraction (Iteration 4)
# Main service
{
  "@id": "urn:service:acs-fleet-manager",
  "@type": "Service",
  "name": "ACS Fleet Manager",
  "hasOwner": [{"@id": "urn:user:rhacs-eng-ms@redhat.com"}],
  "hasEndpoint": [{"@id": "urn:endpoint:api.example.com"}],
  "hasCodeComponent": [{"@id": "urn:code-component:acs-fleet-manager:api-server"}]
}

# Owner as User entity
{
  "@id": "urn:user:rhacs-eng-ms@redhat.com",
  "@type": "User",
  "name": "Red Hat Advanced Cluster Security",
  "email": "rhacs-eng-ms@redhat.com",
  "owns": [{"@id": "urn:service:acs-fleet-manager"}]
}

# Endpoint entity
{
  "@id": "urn:endpoint:api.example.com",
  "@type": "Endpoint",
  "name": "api.example.com",
  "fullUrl": "https://api.example.com",
  "belongsToService": {"@id": "urn:service:acs-fleet-manager"},
  "monitoredBy": [{"@id": "urn:monitoring-provider:blackbox-tls"}]
}

# CodeComponent entity
{
  "@id": "urn:code-component:acs-fleet-manager:api-server",
  "@type": "CodeComponent",
  "name": "api-server",
  "repositoryUrl": "https://github.com/org/api",
  "componentOf": {"@id": "urn:service:acs-fleet-manager"}
}

# Result: 1 service → 4 entities, 8 relationships (2x increase)
# Enables queries:
# - "Show all services owned by user X"
# - "Show all endpoints monitored by provider Y"
# - "Show all code components using language Z"
```

**Metrics to Track**:

- Sub-entity count by type (ServiceOwner, Endpoint, CodeComponent, etc.)
- Parent-child relationship count (bidirectional)
- Percentage of parent entities with sub-entities extracted
- Relationship density before/after sub-entity extraction
- Query pattern count enabled by sub-entities

### 6.9 Free-Text Entity Extraction with AI

**New Best Practice (Iteration 5)**: Leverage AI-driven natural language understanding to extract entities and relationships from free-text fields (descriptions, documentation, comments).

### 6.10 AI-Driven Relationship Inference for Any Repository

**New Best Practice (Iteration 6)**: Use Claude Code's AI reasoning to discover and adapt to any repository's organizational patterns, enabling universal relationship inference that works across all repository types.

**Key Principle**: AI-first approach where Claude Code **learns the repository's patterns** through analysis, then **adapts extraction logic** dynamically. No hardcoded app-interface assumptions.

#### Universal Patterns vs Repository-Specific Patterns

**Universal Patterns** (work for ANY repository):

- **Directory ownership**: `/services/{name}/` → service owns contents (works for /packages/, /modules/, /components/)
- **File proximity**: `test_foo.py` next to `foo.py` → test relationship (works across Python, JS, Go, etc.)
- **Import dependencies**: `import X` → depends on X (works for Python, JS, Go, Java, C++, YAML, Terraform)
- **Naming conventions**: `{name}-prod` → deployed to prod environment (works across config repos, IaC repos)
- **Metadata labels**: `labels.team: X` → owned by team X (works for Kubernetes, Docker, npm, Python packages)
- **Git history**: Files modified together → related (works for any Git repository)

**Repository-Specific Patterns** (Claude discovers during analysis):

- **App-interface**: `/data/services/{name}/app.yml` → service entity
- **Python project**: `/src/packages/{name}/__init__.py` → package entity
- **Terraform**: `/modules/{name}/main.tf` → module entity
- **Kubernetes**: `/services/{name}/deployments/` → deployment resources
- **Documentation**: `/docs/{product}/` → product documentation

#### How Claude Code Discovers and Adapts

**Step 1: Pattern Discovery** (AI analyzes repository structure)

```
Claude Code Analysis Example:

Repository: /path/to/python-project

Discovery Process:
1. Read directory tree:
   /src/packages/auth/
   /src/packages/database/
   /src/packages/api/

2. Sample files:
   - /src/packages/auth/__init__.py (Python module)
   - /src/packages/auth/models.py (imports database)
   - /src/packages/auth/test_auth.py (test file)

3. Identified patterns:
   - Organizational: /src/packages/{name}/ structure (type-based organization)
   - Naming: test_{name}.py pattern (test file naming)
   - Reference: Python import statements
   - Metadata: __author__ docstrings, setup.py author field

4. Discovered relationships:
   - Files in /src/packages/auth/ belong to 'auth' package (directory ownership)
   - test_auth.py tests auth package (file proximity + naming)
   - api package imports database package (Python imports)
```

**Step 2: Pattern Application** (AI applies discovered patterns)

```
Application Example:

Pattern Discovered: /src/packages/{name}/ → package entity

AI Application:
1. For each directory matching /src/packages/{name}/:
   - Create package entity: urn:package:{name}
   - Link files in directory to package (belongsTo relationship)

2. For Python files in package:
   - Extract import statements
   - Create dependsOn relationships to imported packages

3. For test files (test_*.py, *_test.py):
   - Link to tested package (tests relationship)

Result:
- auth package (3 modules, 1 test file)
- database package (5 modules, 2 test files)
- api package (4 modules, depends on auth and database)
```

**Step 3: Cross-Repository Adaptability**

Claude Code applies the SAME reasoning process to different repository types:

**Example 1: Node.js Project**

```
Discovery:
- /packages/{name}/package.json → npm package
- import X from 'Y' → dependency
- {name}.spec.ts → test file

Application:
- Create Package entities from package.json
- Extract dependencies from import statements
- Link test files to packages
```

**Example 2: Kubernetes Config Repository**

```
Discovery:
- /services/{name}/deployments/*.yml → Kubernetes resources
- metadata.labels.app: {name} → application label
- kind: Deployment → resource type

Application:
- Create Service entities from directory structure
- Link resources via labels
- Create deployment relationships
```

**Example 3: Terraform IaC Repository**

```
Discovery:
- /modules/{name}/main.tf → Terraform module
- module.{name} references → module dependency
- tags = { environment = "prod" } → environment metadata

Application:
- Create Module entities
- Extract module dependencies
- Link modules to environments via tags
```

#### Examples Across Different Repository Types

**Python Project Example**:

```python
# Repository: /path/to/python-app

# Directory structure:
/src/
  packages/
    auth/
      __init__.py
      models.py
      test_auth.py
    database/
      __init__.py
      models.py
      test_database.py
    api/
      __init__.py
      routes.py
      test_api.py

# Claude Code Reasoning:
"I see packages organized in /src/packages/{name}/ directories.
 Each package has __init__.py, implementation files, and test files.
 Test files follow test_{name}.py pattern.
 Imports show dependencies between packages."

# Discovered Patterns:
1. Directory ownership: /src/packages/{name}/ → package 'name'
2. File proximity: test_{name}.py → tests {name} package
3. Python imports: from database import X → api depends on database

# Relationships Inferred:
- auth package has modules: __init__.py, models.py
- auth package tested by: test_auth.py
- api package depends on: auth, database
- database package has no external dependencies
```

**Node.js App Example**:

```javascript
// Repository: /path/to/node-app

// Directory structure:
/packages/
  frontend/
    package.json
    src/index.tsx
    src/components/
  backend/
    package.json
    src/server.ts
    src/routes/
  shared/
    package.json
    src/types.ts

// Claude Code Reasoning:
"I see monorepo with packages in /packages/{name}/.
 Each package has package.json defining dependencies.
 Import statements show cross-package dependencies.
 TypeScript files import from shared types."

// Discovered Patterns:
1. Directory ownership: /packages/{name}/ → npm package 'name'
2. File proximity: package.json defines package metadata
3. Import dependencies: import X from '../shared' → frontend depends on shared

// Relationships Inferred:
- frontend package (React app)
- backend package (Express server)
- shared package (TypeScript types)
- frontend depends on: shared
- backend depends on: shared
```

**Kubernetes Config Example**:

```yaml
# Repository: /path/to/k8s-configs

# Directory structure:
/services/
  api-gateway/
    deployments/
      production.yml
      staging.yml
    configmaps/
      app-config.yml
  user-service/
    deployments/
      production.yml
    secrets/
      db-credentials.yml

# Claude Code Reasoning:
"I see services organized in /services/{name}/ directories.
 Each service has subdirectories for resource types.
 YAML files have Kubernetes 'kind' field defining resource type.
 Labels indicate service name and environment."

# Discovered Patterns:
1. Directory ownership: /services/{name}/ → service 'name'
2. Naming convention: production.yml, staging.yml → environment
3. Metadata labels: metadata.labels.app → service name
4. Kubernetes kind: Deployment, ConfigMap, Secret → resource types

# Relationships Inferred:
- api-gateway service has: 2 deployments, 1 configmap
- user-service has: 1 deployment, 1 secret
- api-gateway-production deployed to: production environment
- api-gateway-staging deployed to: staging environment
```

**Terraform IaC Example**:

```hcl
# Repository: /path/to/terraform

# Directory structure:
/modules/
  vpc/
    main.tf
    variables.tf
    outputs.tf
  ec2/
    main.tf
    variables.tf
    outputs.tf
/environments/
  prod/
    main.tf  # uses modules/vpc and modules/ec2
  staging/
    main.tf

# Claude Code Reasoning:
"I see modules organized in /modules/{name}/ directories.
 Each module has main.tf, variables.tf, outputs.tf.
 Environments use modules via module blocks.
 Tags indicate environment and ownership."

# Discovered Patterns:
1. Directory ownership: /modules/{name}/ → Terraform module 'name'
2. Module references: module "vpc" { source = "../modules/vpc" } → dependency
3. Metadata tags: tags = { environment = "prod" } → environment

# Relationships Inferred:
- vpc module (network infrastructure)
- ec2 module (compute instances)
- prod environment uses: vpc module, ec2 module
- staging environment uses: vpc module, ec2 module
- prod environment has tag: production
- staging environment has tag: staging
```

#### Testing and Validation Approach

**Testing Strategy**:

1. **Sample Repository Selection**:
   - Start with small subset (100-200 files)
   - Test across different repo types (Python, Node.js, K8s, Terraform)
   - Validate pattern discovery works consistently

2. **Pattern Discovery Validation**:
   - Manually review discovered patterns
   - Verify patterns match actual repo organization
   - Check for false positives/negatives

3. **Relationship Inference Testing**:
   - Measure relationships inferred vs. manual baseline
   - Validate high-confidence relationships (target: >90% accuracy)
   - Review medium-confidence for false positives (target: <20%)

4. **Cross-Repository Validation**:
   - Apply same patterns to different repo types
   - Verify adaptability (patterns generalize)
   - Measure coverage (% entities with inferred relationships)

**Expected Metrics** (after Iteration 6):

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Relationships inferred | 269 (Iteration 3) | 5,000-8,000 | AI discovers more patterns |
| Relationship density | 2.5 | 4.0+ | relationships per entity |
| Patterns discovered | 4 (hardcoded) | 10+ (AI-discovered) | Universal + repo-specific |
| Repository types supported | 1 (app-interface) | Any (Python, JS, K8s, Terraform, docs) | Adaptability |
| High-confidence accuracy | Unknown | >90% | Manual validation |
| Coverage (entities with inferred rels) | 78% | 90%+ | Pattern application success |

**Validation Checklist**:

- [ ] Patterns work for Python projects
- [ ] Patterns work for Node.js apps
- [ ] Patterns work for Kubernetes configs
- [ ] Patterns work for Terraform IaC
- [ ] No hardcoded app-interface assumptions
- [ ] Claude Code reports discovered patterns
- [ ] Confidence levels assigned correctly
- [ ] High-confidence accuracy >90%
- [ ] Relationship density reaches 4.0+
- [ ] 5,000-8,000 relationships inferred

#### Key Differences from Previous Iterations

**Iteration 3 (Hardcoded Patterns)**:

- ❌ App-interface specific: `/data/services/`, `/data/namespaces/`
- ❌ Fixed patterns: Team names, GitHub orgs, AWS accounts
- ✅ 269 relationships inferred (good for app-interface)
- ❌ Doesn't work for other repository types

**Iteration 6 (Universal AI Patterns)**:

- ✅ Repository-agnostic: Works for `/services/`, `/packages/`, `/modules/`, any structure
- ✅ AI discovers patterns: Analyzes repo, identifies organizational structure
- ✅ 5,000-8,000 relationships inferred (works for any repo)
- ✅ Adapts to Python, Node.js, Kubernetes, Terraform, documentation repos

**Example Comparison**:

```
Iteration 3 (Hardcoded):
if '/data/services/' in filepath:  # App-interface specific
    service_name = filepath.split('/')[2]
    # Create relationship

Iteration 6 (AI-Discovered):
# Claude Code analyzes repo and discovers:
# "I see files organized in /services/{name}/ pattern"
# "I see files organized in /packages/{name}/ pattern"
# "I see files organized in /modules/{name}/ pattern"
# Then applies pattern dynamically based on what was discovered
```

**Benefits of AI-First Approach**:

1. **Works for any repository** (not just app-interface)
2. **Discovers patterns automatically** (no manual coding)
3. **Adapts to new structures** (learns organizational patterns)
4. **Higher coverage** (finds more relationships)
5. **Testable immediately** (can run on sample repos now)

---

**Why AI Excels at This**:

1. **Context Understanding**: AI understands natural language context that rigid pattern matching misses
   - Distinguishes "uses Prometheus" (tool dependency) from "Prometheus said..." (mention in comment)
   - Recognizes "Go" as programming language in "written in Go" vs action verb in "go to production"
   - Interprets implied relationships from contextual clues

2. **Entity Recognition**: AI recognizes proper nouns and technical terms without explicit lists
   - Identifies tool names: "ArgoCD", "PostgreSQL", "Vault"
   - Recognizes technologies: "React", "TypeScript", "gRPC"
   - Detects team names: "Platform Engineering team", "SRE"
   - Spots infrastructure mentions: "AWS", "OpenShift", "S3"

3. **Relationship Inference**: AI infers relationships from action verbs and context
   - "uses X for Y" → service --uses--> X (purpose: Y)
   - "maintained by Team X" → service --maintainedBy--> Team X
   - "deployed via Y" → service --deployedVia--> Y
   - "backed by Z database" → service --backedBy--> Z

4. **Confidence Assignment**: AI evaluates extraction certainty based on explicitness
   - HIGH: "uses PostgreSQL for data persistence" (explicit, clear)
   - MEDIUM: "running on AWS" (implied infrastructure dependency)
   - LOW: "various tools" (too vague, skip)

5. **Duplicate Prevention**: AI validates against entity index before creating
   - Normalizes variations: "GitHub", "Github", "github.com" → same entity
   - Checks if tool already exists in index
   - Merges with canonical entity names

**Patterns Claude Code Should Apply**:

**Pattern 1: Tool/System Dependency Detection**

```
Input: "This service uses Prometheus for metrics and is deployed via ArgoCD."

Analysis:
- "Prometheus" + "uses...for metrics" → MonitoringTool entity
- "ArgoCD" + "deployed via" → DeploymentTool entity

Extract:
- urn:monitoring-tool:prometheus (@type: MonitoringTool, name: "Prometheus")
- urn:deployment-tool:argocd (@type: DeploymentTool, name: "ArgoCD")
- service --uses--> prometheus (confidence: HIGH, purpose: "metrics")
- service --deployedVia--> argocd (confidence: HIGH)
```

**Pattern 2: Team/Ownership Recognition**

```
Input: "Maintained by the Platform Engineering team. Contact: platform-team@example.com"

Analysis:
- "Platform Engineering team" + "maintained by" → Team entity
- Email domain confirms organizational team

Extract:
- urn:team:platform-engineering (@type: Team, name: "Platform Engineering")
- service --maintainedBy--> team (confidence: HIGH)
- Add contact email to Team entity
```

**Pattern 3: Technology Stack Extraction**

```
Input: "Backend written in Go using gRPC. Frontend is React with TypeScript."

Analysis:
- "Go" + "written in" → ProgrammingLanguage
- "gRPC" + "using" → Protocol/Technology
- "React" → Framework (frontend context)
- "TypeScript" → ProgrammingLanguage (with React context)

Extract:
- urn:programming-language:go (@type: ProgrammingLanguage, name: "Go")
- urn:protocol:grpc (@type: Protocol, name: "gRPC")
- urn:framework:react (@type: Framework, name: "React")
- urn:programming-language:typescript (@type: ProgrammingLanguage, name: "TypeScript")
- service --writtenIn--> go (confidence: HIGH)
- service --uses--> grpc (confidence: HIGH)
- service --frontendUses--> react (confidence: HIGH)
- service --frontendLanguage--> typescript (confidence: HIGH)
```

**Pattern 4: Infrastructure Context Inference**

```
Input: "Deployed to production cluster app-sre-prod-04 in AWS us-east-1."

Analysis:
- "app-sre-prod-04" + "production cluster" → Cluster entity
- "AWS" + "us-east-1" → CloudProvider + Region

Extract:
- urn:cluster:app-sre-prod-04 (@type: Cluster, name: "app-sre-prod-04")
- urn:cloud-provider:aws (@type: CloudProvider, name: "AWS")
- urn:region:us-east-1 (@type: Region, name: "us-east-1")
- service --deployedTo--> cluster (confidence: HIGH)
- service --runsOn--> aws (confidence: HIGH)
- service --region--> us-east-1 (confidence: MEDIUM, inferred)
```

**Pattern 5: Integration/Dependency Mentions**

```
Input: "Integrates with GitHub API for repository management and calls Vault for secrets."

Analysis:
- "GitHub API" + "integrates with" → ExternalService entity
- "Vault" + "calls...for secrets" → SecretsManagement entity

Extract:
- urn:external-service:github-api (@type: ExternalService, name: "GitHub API")
- urn:secrets-management:vault (@type: SecretsManagement, name: "Vault")
- service --integratesWith--> github-api (confidence: HIGH, purpose: "repository management")
- service --dependsOn--> vault (confidence: HIGH, purpose: "secrets")
```

**Example Transformations (Description → Entities)**:

**Example 1: Rich Service Description**

```yaml
# Before: Only structured data
service:
  name: "acs-fleet-manager"
  description: |
    ACS Fleet Manager is the control plane for Red Hat Advanced Cluster Security.
    It uses PostgreSQL for data persistence and Prometheus for monitoring.
    Deployed via ArgoCD to production OpenShift clusters. Backend is written in Go
    with gRPC APIs. Maintained by the RHACS Engineering team.

# After: Structured + Free-Text Extraction
# Main service (structured)
{
  "@id": "urn:service:acs-fleet-manager",
  "@type": "Service",
  "name": "ACS Fleet Manager",
  "description": "ACS Fleet Manager is the control plane..."
}

# Extracted from description (AI-driven):
# 1. Database
{
  "@id": "urn:database:postgresql",
  "@type": "Database",
  "name": "PostgreSQL"
}

# 2. Monitoring Tool
{
  "@id": "urn:monitoring-tool:prometheus",
  "@type": "MonitoringTool",
  "name": "Prometheus"
}

# 3. Deployment Tool
{
  "@id": "urn:deployment-tool:argocd",
  "@type": "DeploymentTool",
  "name": "ArgoCD"
}

# 4. Platform
{
  "@id": "urn:platform:openshift",
  "@type": "Platform",
  "name": "OpenShift"
}

# 5. Programming Language
{
  "@id": "urn:programming-language:go",
  "@type": "ProgrammingLanguage",
  "name": "Go"
}

# 6. Protocol
{
  "@id": "urn:protocol:grpc",
  "@type": "Protocol",
  "name": "gRPC"
}

# 7. Team
{
  "@id": "urn:team:rhacs-engineering",
  "@type": "Team",
  "name": "RHACS Engineering"
}

# Relationships extracted from description:
# - service --usesDatabase--> postgresql (HIGH, purpose: "data persistence")
# - service --monitoredBy--> prometheus (HIGH)
# - service --deployedVia--> argocd (HIGH)
# - service --deployedTo--> openshift (HIGH)
# - service --writtenIn--> go (HIGH)
# - service --uses--> grpc (HIGH)
# - service --maintainedBy--> rhacs-engineering (HIGH)

# Result: 1 service description → 7 new entities, 7 relationships
```

**Example 2: Minimal Description with Inference**

```yaml
# Before
service:
  name: "api-gateway"
  description: "API Gateway running on AWS with Redis caching"

# After: AI extracts even from minimal context
# Extracted entities:
# - urn:cloud-provider:aws (@type: CloudProvider, name: "AWS")
# - urn:cache:redis (@type: Cache, name: "Redis")

# Relationships:
# - service --runsOn--> aws (HIGH confidence)
# - service --uses--> redis (HIGH confidence, purpose: "caching")

# Result: 2 entities, 2 relationships from minimal description
```

**Expected Impact**:

| Metric | Before Iteration 5 | After Iteration 5 | Improvement |
|--------|-------------------|-------------------|-------------|
| **Entities from descriptions** | 0 | +500-1,000 | New capability |
| **Tools/Technologies** | ~50 (structured) | +200-400 | 4-8x increase |
| **Team entities** | ~30 (structured) | +50-100 | 2-4x increase |
| **Relationships from free text** | 0 | +1,000-2,000 | New capability |
| **Graph density** | 1.9 rel/entity | 2.5-3.0 rel/entity | +30-60% |

**Query Patterns Enabled**:

After Iteration 5, new query capabilities become available:

1. **Tool/Technology queries**:
   - "Find all services using Prometheus for monitoring"
   - "Show services written in Go"
   - "List services deployed via ArgoCD"

2. **Team/Ownership queries**:
   - "Show services maintained by Platform Engineering team"
   - "Find services without explicit team ownership"

3. **Integration queries**:
   - "Find services integrating with GitHub API"
   - "Show services that use Vault for secrets"

4. **Infrastructure queries**:
   - "Find all services running on AWS"
   - "Show services deployed to production clusters"

5. **Technology stack queries**:
   - "Find all React frontends"
   - "Show services using gRPC"
   - "List services with Redis caching"

**Validation Guidelines**:

Track these metrics to validate free-text extraction quality:

1. **Extraction Coverage**:
   - % of services with extractable descriptions
   - Average entities extracted per description field
   - Description fields processed vs skipped

2. **Confidence Distribution**:
   - HIGH confidence extractions (target: > 70%)
   - MEDIUM confidence extractions (< 20%)
   - LOW confidence extractions (< 10%, should be skipped)

3. **Entity Validation**:
   - New entities created vs matched to existing (duplicate prevention)
   - Name standardization success rate
   - Entity type classification accuracy

4. **Relationship Quality**:
   - Relationships created from free text
   - Validation success rate (target URN exists in index)
   - Relationship predicate variety (uses, deployedVia, maintainedBy, etc.)

5. **Graph Enrichment**:
   - Total entity count increase
   - Total relationship count increase
   - Graph density improvement (relationships per entity)

6. **Query Capability**:
   - Number of new query patterns enabled
   - Query types now answerable (tools, teams, integrations, etc.)

7. **Manual Review**:
   - MEDIUM confidence extractions flagged for review
   - False positive rate (incorrect extractions)
   - False negative rate (missed extractions)

8. **Performance**:
   - Time to process description fields
   - API call count (if using external AI service)
   - Extraction throughput (entities/descriptions per minute)

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
