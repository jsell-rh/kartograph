# Iteration 8 Changes: AI-First Process Optimization

**Date**: 2025-10-22
**Status**: In Progress
**Focus**: Process Transformation - AI Reasoning Over Deterministic Scripts

---

## Executive Summary

Iteration 8 fundamentally transforms the knowledge graph extraction process from a **script-generation paradigm** to an **AI-first reasoning paradigm**. Claude Code agents now reason intelligently about data and make extraction decisions, while deterministic validators ensure output conforms to standards.

**Key Achievement**: Enable autonomous AI agents to execute the entire extraction process through reasoning, while maintaining strict output quality through deterministic validation.

---

## Problem Statement

### Current Paradigm (Mixed AI/Script)

**Process Flow**:

1. User asks Claude Code to extract knowledge graph
2. Claude Code generates Python extraction scripts
3. User runs Python scripts
4. Scripts execute deterministic extraction logic
5. Scripts validate output

**Limitations**:

- ❌ AI agent can't execute autonomously (requires script execution)
- ❌ Extraction logic is deterministic (can't adapt to unexpected patterns)
- ❌ AI intelligence limited to code generation, not data interpretation
- ❌ Can't leverage Claude's semantic understanding during extraction
- ❌ Iteration 5/6 patterns (free-text, universal inference) contradict script-based approach
- ❌ Testing requires human intervention to run generated scripts

**Example of Current Confusion**:

```python
# PROCESS.md says "Claude should analyze..." but shows:
def extract_service(data, schema):
    """Claude-generated extraction function."""
    # Hardcoded field list
    fields_to_extract = ['name', 'description', 'owner']

    for field in fields_to_extract:
        entity[field] = data.get(field)

    # AI can't reason about missing fields or adapt
```

### Target Paradigm (AI-First Reasoning)

**Process Flow**:

1. User asks Claude Code (agent) to extract knowledge graph
2. Agent autonomously reads repository using AI reasoning
3. Agent analyzes files, understands semantics, infers patterns
4. Agent extracts entities through intelligent decisions
5. Deterministic validators enforce output standards
6. Agent self-validates and iterates

**Benefits**:

- ✅ Fully autonomous execution by AI agents
- ✅ Adaptive extraction (handles unexpected patterns)
- ✅ Leverages Claude's semantic understanding
- ✅ Consistent with Iteration 5/6 AI-first patterns
- ✅ Self-testing and iteration possible
- ✅ No human intervention required

---

## Solution: AI-First Process Architecture

### Core Principle

**Separation of Concerns**:

```
┌─────────────────────────────────────────────────────┐
│         INTELLIGENCE LAYER (AI Reasoning)           │
│  - Analyzes repository structure                    │
│  - Understands data semantics                       │
│  - Decides what to extract                          │
│  - Infers relationships from context                │
│  - Adapts to unexpected patterns                    │
│  - Makes confident/uncertain judgments              │
└─────────────────────────────────────────────────────┘
                         ↓
                  Produces Output
                         ↓
┌─────────────────────────────────────────────────────┐
│       QUALITY LAYER (Deterministic Validation)      │
│  - Enforces URN format standards                    │
│  - Validates JSON-LD structure                      │
│  - Checks required predicates exist                 │
│  - Verifies reference integrity                     │
│  - Ensures schema conformance                       │
│  - Reports violations for AI to fix                 │
└─────────────────────────────────────────────────────┘
```

**Key Insight**: AI has maximum flexibility in **how** it extracts, but output **must** conform to strict standards.

### AI Reasoning Framework

#### Phase 0: Repository Discovery (AI Analyzes)

**AI Task**: Understand repository organization through reasoning

**AI Questions**:

1. "What is the purpose of this repository?" (code, config, docs, IaC)
2. "How are files organized?" (by type, by team, by function, by environment)
3. "What patterns exist?" (naming conventions, directory structures, metadata)
4. "What entity types likely exist?" (inferred from structure and file contents)
5. "How do entities relate?" (file proximity, naming patterns, metadata)

**AI Output**:

- Repository type classification (with confidence)
- Organizational pattern description
- Entity type hypotheses
- Relationship pattern hypotheses
- Extraction strategy recommendation

**Deterministic Validation**:

- Repository path exists and is accessible
- Files are readable
- No validation of AI's reasoning (flexible interpretation allowed)

**Example AI Reasoning**:

```
Agent Analysis of app-interface:

"I observe a configuration repository with 14,107 YAML files organized
in /data/{entity-type}/{name}/ structure.

Key patterns discovered:
1. Directory organization: /data/services/, /data/dependencies/, /data/teams/
   → Indicates entity-type-based organization

2. Schema references: Files contain $schema: /app-1.yml patterns
   → Formal schemas exist in /qontract-schemas/

3. Cross-references: Extensive use of $ref: /path/to/file.yml
   → Entities reference each other via file paths

4. Metadata fields: Most files have name, description, owner-like fields
   → Rich metadata available for extraction

Entity types hypothesized:
- Service (from /data/services/)
- Dependency (from /data/dependencies/)
- Team (from /data/teams/)
- Namespace (from namespace references)
- Cluster (from cluster references)

Extraction strategy: Schema-driven (156 schemas available) with AI-enhanced
field discovery for maximum fidelity."

Confidence: HIGH (clear patterns, formal schemas available)
```

No script generation - pure AI reasoning about repository structure.

#### Phase 1: Schema Analysis (AI Understands)

**AI Task**: Understand schemas semantically, not just parse them

**AI Questions**:

1. "What does this schema represent?" (conceptual understanding)
2. "What are the essential vs optional characteristics?"
3. "How do entities of this type relate to others?"
4. "What validation rules exist and why?"
5. "Are there implicit constraints not in the schema?"

**AI Output**:

- Semantic understanding of each entity type
- Required vs optional field categorization (with reasoning)
- Expected relationship patterns
- Validation constraint understanding
- Field importance ranking

**Deterministic Validation**:

- Schema is valid JSON Schema syntax
- No validation of AI's semantic interpretation

**Example AI Reasoning**:

```
Agent Analysis of /schemas/app-1.yml (Service schema):

"This schema defines a Service entity representing a software application
or microservice.

Essential characteristics:
- name: Primary identifier, human-readable (REQUIRED)
- description: Purpose and functionality (REQUIRED)
- serviceOwners: Accountability/contacts (REQUIRED for production services)

Operational metadata:
- grafanaUrl: Observability dashboard (OPTIONAL but critical for ops)
- slackChannel: Team communication (OPTIONAL but enables contact)
- sopsUrl: Runbook documentation (OPTIONAL but critical for incidents)

Relationships discovered:
- dependencies[]: External services this depends on
- namespaces[]: Kubernetes namespaces where deployed
- product: Product grouping/ownership

Inference: While schema marks many fields 'optional', operational context
suggests they're important for complete graph. Will extract ALL present
fields following Iteration 7 (Maximum Fidelity) guidance."

Confidence: HIGH (schema is well-documented and clear)
```

AI understands **why** fields exist, not just **what** they are.

#### Phase 2: Entity Extraction (AI Decides)

**AI Task**: Intelligently decide what to extract from each file

**AI Questions**:

1. "What entity type does this file represent?" (semantic classification)
2. "What fields should I extract?" (not from template, from reasoning)
3. "How should I handle this nested structure?" (sub-entity vs inline)
4. "What does this field mean in context?" (semantic understanding)
5. "Is this field important enough to extract?" (value judgment)

**AI Output**:

- JSON-LD entities with extracted fields
- Extraction decisions explained (why each field was included/excluded)
- Confidence scores per extraction
- Pending relationships (to resolve in Phase 3)

**Deterministic Validation**:

- ✅ URN format: `^urn:[a-z0-9-]+:[a-z0-9-:]+$`
- ✅ Required predicates exist: `@id`, `@type`, `name`
- ✅ JSON-LD syntax valid
- ✅ Field coverage >80% of source data (Iteration 7 target)
- ❌ No validation of AI's field selection logic

**Example AI Reasoning**:

```
Agent Extraction from /data/services/cincinnati/app.yml:

File Analysis:
- $schema: /app-1.yml → This is a Service entity
- name: "Cincinnati" → Primary identifier found
- description: Multi-line text describing update service
- serviceOwners: Array of 2 owners with email/name
- grafanaUrl: Present → Observability enabled
- slackChannel: Present → Team contact available
- appCode, costCenter, tier, criticality: All present → Rich operational metadata

Extraction Decisions:

1. Entity Type: Service (HIGH confidence - schema match)
   URN: urn:service:cincinnati (normalized from name)

2. Fields to Extract (applying Iteration 7 Maximum Fidelity):
   ✓ name, description (required, present)
   ✓ grafanaUrl, slackChannel, sopsUrl (optional but present → extract all)
   ✓ appCode, costCenter, tier, criticality (operational metadata → extract)
   ✓ onboardingStatus (status tracking → extract)
   ✗ $schema, apiVersion (structural metadata → skip per guidelines)

3. Nested Structures:
   - serviceOwners: 2 items with {name, email} → Apply Iteration 4
     Decision: Extract as User entities (meet sub-entity criteria)
     Reasoning: Independent queryability ("find services owned by X")

   - dependencies: Array of $ref → Relationships for Phase 3
     Decision: Defer to relationship resolution

4. Field Coverage: 12 of 14 fields extracted = 85.7% coverage ✓
   (Exceeds Iteration 7 target of >80%)

Output Entity:
{
  "@id": "urn:service:cincinnati",
  "@type": "Service",
  "name": "Cincinnati",
  "description": "OpenShift Update Service...",
  "onboardingStatus": "OnBoarded",
  "grafanaUrl": "https://grafana.example.com/...",
  "slackChannel": "#cincinnati-team",
  "sopsUrl": "https://github.com/...",
  "architectureDocument": "https://docs.example.com/...",
  "appCode": "CINC-001",
  "costCenter": "Engineering",
  "tier": "production",
  "criticality": "high",
  "hasOwner": [
    {"@id": "urn:user:jdoe@example.com"},
    {"@id": "urn:user:jsmith@example.com"}
  ],
  "_pending_refs": [
    {"field": "dependencies", "values": [...]}
  ]
}

Sub-Entities Created:
- urn:user:jdoe@example.com (User)
- urn:user:jsmith@example.com (User)

Confidence: HIGH (schema-guided, all required fields present, coverage excellent)
```

Deterministic Validation After AI Extraction:

```
✓ URN format valid: urn:service:cincinnati
✓ Required predicates present: @id, @type, name
✓ JSON-LD structure valid
✓ Field coverage: 85.7% > 80% target
✓ Sub-entity extraction: 2 User entities created
✓ Total: 14 predicates (exceeds Iteration 7 target of 12+)

Validation PASSED - Entity accepted
```

AI decided **what** to extract; validation enforced **output quality**.

#### Phase 3: Relationship Resolution (AI Infers)

**AI Task**: Discover and infer relationships through pattern recognition

**AI Questions**:

1. "What explicit relationships exist?" ($ref, references, dependencies)
2. "What implicit relationships can I infer?" (file paths, naming, metadata)
3. "What patterns suggest relationships?" (directory structure, labels, co-occurrence)
4. "How confident am I in each inference?" (HIGH/MEDIUM/LOW)
5. "Do these relationships make semantic sense?" (sanity check)

**AI Output**:

- Explicit relationships (from $ref, etc.)
- Inferred relationships with confidence scores
- Reasoning for each inference
- Validation against entity index

**Deterministic Validation**:

- ✅ All @id references exist in entity index
- ✅ Bidirectional relationships are symmetric
- ✅ No circular references (unless expected)
- ❌ No validation of AI's inference logic

**Example AI Reasoning** (applying Iteration 6 universal inference):

```
Agent Relationship Inference for Service "cincinnati":

Source File: /data/services/cincinnati/app.yml

Pattern 1: Directory Structure (HIGH confidence)
Observation: File located at /data/services/cincinnati/namespaces/prod.yml
Reasoning: Files in /services/{name}/ belong to service {name}
Inference: Service "cincinnati" hasNamespace "prod"
Validation: urn:namespace:cincinnati:prod exists in index ✓
Action: Create relationship

Pattern 2: Explicit $ref (HIGH confidence)
Observation: dependencies[0].$ref = "/data/dependencies/github/service.yml"
Reasoning: $ref points to dependency entity
Resolution: Follow $ref → urn:dependency:github
Validation: urn:dependency:github exists in index ✓
Action: Create relationship: cincinnati --dependsOn--> github

Pattern 3: Metadata Label (HIGH confidence)
Observation: metadata.labels.team = "cincinnati-team"
Reasoning: Team label indicates ownership
Inference: Team "cincinnati-team" owns Service "cincinnati"
Validation: urn:team:cincinnati-team exists in index ✓
Action: Create relationship: cincinnati-team --owns--> cincinnati

Pattern 4: Free-Text Description (MEDIUM confidence - Iteration 5)
Observation: Description mentions "uses PostgreSQL for data persistence"
Reasoning: Natural language indicates database dependency
Inference: Service "cincinnati" usesDatabase "postgresql"
Validation: urn:database:postgresql exists in index ✓
Confidence: MEDIUM (free-text extraction, could be aspirational vs actual)
Action: Create relationship with confidence annotation

Pattern 5: Naming Convention (MEDIUM confidence)
Observation: Namespace named "cincinnati-prod"
Reasoning: {service}-{env} naming pattern suggests relationship
Inference: Service "cincinnati" deployedTo environment "prod"
Validation: urn:environment:prod exists in index ✓
Confidence: MEDIUM (naming inference, not explicit)
Action: Create relationship

Relationships Created: 5
- High confidence: 3
- Medium confidence: 2
- Low confidence: 0 (skipped)

Broken Reference Prevention:
- Pre-creation validation: 5/5 targets exist in index
- Broken reference rate: 0% ✓ (Iteration 2 target: <2%)
```

Deterministic Validation:

```
✓ All relationship targets exist in entity index
✓ URN references valid format
✓ No circular references detected
✓ Bidirectional edges created where appropriate

Validation PASSED - Relationships accepted
```

AI inferred **which** relationships exist; validation ensured **reference integrity**.

#### Phase 3.5: Validation (AI Self-Validates + Deterministic Checks)

**AI Task**: Evaluate own work for quality and completeness

**AI Questions**:

1. "Did I extract all important fields?" (completeness check)
2. "Are my extraction decisions consistent?" (consistency check)
3. "Do inferred relationships make sense?" (sanity check)
4. "What is my confidence in the overall extraction?" (self-assessment)
5. "Where might I have made mistakes?" (error anticipation)

**AI Output**:

- Self-assessment report
- Confidence scores by entity type
- Potential issues flagged
- Recommended improvements
- Overall quality score

**Deterministic Validation** (enforces all standards):

- ✅ URN format compliance: 100%
- ✅ Required predicates: @id, @type, name present in all entities
- ✅ JSON-LD syntax: Valid
- ✅ Reference integrity: 0 broken references
- ✅ Field coverage: >80% (Iteration 7)
- ✅ Orphan rate: <0.5% (Iteration 3)
- ✅ Broken reference rate: <2% (Iteration 2)
- ✅ Sub-entity extraction: Applied where appropriate (Iteration 4)
- ✅ Free-text extraction: Applied to description fields (Iteration 5)
- ✅ Universal inference: Applied to discover patterns (Iteration 6)

**Example AI Self-Validation**:

```
Agent Self-Assessment Report:

Extraction Summary:
- Total entities extracted: 6,332
- Total relationships: 28,528
- Entity types: 15 distinct types
- Coverage: 94.2% of repository files processed

Quality Metrics (Self-Evaluated):

1. Completeness (HIGH confidence ✓)
   - Field coverage avg: 87.3% (target: >80%) ✓
   - All major entity types extracted ✓
   - Comprehensive relationship discovery ✓

2. Consistency (HIGH confidence ✓)
   - URN format standardized across all entities ✓
   - Naming conventions applied consistently ✓
   - Sub-entity decisions follow Iteration 4 criteria ✓

3. Accuracy (MEDIUM-HIGH confidence)
   - Explicit relationships: HIGH confidence ✓
   - Inferred relationships: 68% HIGH, 27% MEDIUM, 5% flagged for review
   - Free-text extractions: 156 entities, need human validation

4. Iteration Compliance:
   - Iteration 1 (Name/Type): 100% compliance ✓
   - Iteration 2 (Two-Pass): Applied, 0% broken refs ✓
   - Iteration 3 (Orphan Detection): 0.3% orphan rate ✓
   - Iteration 4 (Sub-Entities): 2,104 sub-entities created ✓
   - Iteration 5 (Free-Text): 156 entities from descriptions ✓
   - Iteration 6 (Universal Inference): 342 inferred relationships ✓
   - Iteration 7 (Max Fidelity): 87.3% avg coverage ✓

Potential Issues Identified:
⚠️  23 entities with <5 predicates (sparse extraction)
   → Recommend manual review of these files

⚠️  89 MEDIUM confidence inferred relationships
   → Flagged for human validation

⚠️  12 files failed parsing (malformed YAML)
   → Skipped, logged for investigation

Overall Confidence: HIGH
- Core extraction: 95% confident
- Relationship inference: 85% confident
- Free-text extraction: 70% confident (needs validation)

Recommendation: Proceed to deterministic validation, flag MEDIUM
confidence items for review.
```

Deterministic Validation Results:

```
Running all compliance checks...

✓ URN Format: 6,332/6,332 entities (100%)
✓ Required Predicates: 6,332/6,332 entities have @id, @type, name (100%)
✓ JSON-LD Syntax: Valid
✓ Reference Integrity: 28,528 references, 0 broken (0%)
✓ Field Coverage: 87.3% avg > 80% target
✓ Orphan Rate: 0.3% < 0.5% target
✓ Sub-Entity Extraction: 2,104 created (matches expectation)
✓ Predicate Density: 13.2 avg > 12 target (Iteration 7)

❌ 23 entities below minimum predicate threshold (5)
   → Manual review recommended

All critical validations PASSED
Warnings: 23 sparse entities flagged
```

**AI self-validates reasoning; deterministic checks enforce standards.**

### AI Decision Framework

#### Confidence Scoring

AI must assign confidence to all decisions:

**HIGH Confidence** (>90% certain):

- Schema-driven extraction with clear field mapping
- Explicit $ref relationships
- Directory structure patterns with multiple confirming signals
- Metadata labels with clear semantics

**MEDIUM Confidence** (60-90% certain):

- Inferred relationships from naming patterns
- Free-text entity extraction with contextual clues
- Sub-entity decisions with borderline criteria
- Optional field extraction when importance unclear

**LOW Confidence** (<60% certain):

- Ambiguous entity type classification
- Uncertain relationship patterns
- Vague free-text mentions
- Missing context for decision

**Actions by Confidence**:

- HIGH: Extract/infer automatically
- MEDIUM: Extract/infer but flag for review
- LOW: Skip or ask for clarification

#### Self-Validation Checkpoints

AI must validate own reasoning at key steps:

**After Phase 0**:

- "Do my organizational patterns make sense given file contents?"
- "Have I correctly identified entity types?"
- "Is my extraction strategy appropriate?"

**After Phase 2**:

- "Did I extract all important fields?"
- "Are my URNs consistent?"
- "Do my sub-entity decisions follow criteria?"

**After Phase 3**:

- "Do my inferred relationships make semantic sense?"
- "Have I checked all targets exist?"
- "Are my confidence levels appropriate?"

**After Phase 3.5**:

- "Does the overall graph structure make sense?"
- "Are there unexpected gaps or anomalies?"
- "What is my overall confidence in this extraction?"

#### Handling Uncertainty

When AI is uncertain:

**Option 1: Conservative Approach**

- Skip uncertain extraction
- Log decision with reasoning
- Flag for human review

**Option 2: Extract with Annotation**

- Include uncertain extraction
- Annotate with confidence score
- Add `_ai_uncertain: true` flag

**Option 3: Ask for Clarification** (if interactive)

- Explain uncertainty
- Request user guidance
- Apply guidance to similar cases

### Validation Standards (Deterministic)

All AI output must pass these checks:

#### 1. URN Format Validation

```regex
^urn:[a-z0-9-]+:[a-z0-9-:]+$
```

**Rules**:

- Must start with `urn:`
- Type segment: lowercase alphanumeric + hyphens
- Identifier segments: lowercase alphanumeric + hyphens + colons
- No spaces, underscores, or special characters
- Minimum 3 segments: `urn:type:identifier`

**Validation Function**:

```python
def validate_urn_format(urn):
    """Deterministic URN validation."""
    import re

    pattern = r'^urn:[a-z0-9-]+:[a-z0-9-:]+$'

    if not re.match(pattern, urn):
        return False, f"URN format invalid: {urn}"

    segments = urn.split(':')
    if len(segments) < 3:
        return False, f"URN must have at least 3 segments: {urn}"

    return True, None
```

#### 2. Required Predicates Validation

**Required for ALL entities**:

- `@id`: URN identifier
- `@type`: Entity type
- `name`: Human-readable name

**Validation Function**:

```python
def validate_required_predicates(entity):
    """Deterministic required field check."""
    required = ['@id', '@type', 'name']

    missing = [field for field in required if field not in entity]

    if missing:
        return False, f"Missing required predicates: {missing}"

    # Check not empty
    for field in required:
        if not entity[field]:
            return False, f"Required predicate '{field}' is empty"

    return True, None
```

#### 3. JSON-LD Syntax Validation

**Validation Function**:

```python
def validate_jsonld_syntax(entities):
    """Deterministic JSON-LD validation."""
    import json

    try:
        # Must be valid JSON
        json_str = json.dumps(entities)
        parsed = json.loads(json_str)

        # Must have @context or @graph
        if '@context' not in parsed and '@graph' not in parsed:
            if not isinstance(parsed, list):
                return False, "JSON-LD must have @context or be a list"

        return True, None

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
```

#### 4. Reference Integrity Validation

**Validation Function**:

```python
def validate_reference_integrity(entities):
    """Deterministic reference validation."""
    # Build entity index
    entity_index = {e['@id'] for e in entities}

    broken_refs = []

    for entity in entities:
        for key, value in entity.items():
            # Check dict references
            if isinstance(value, dict) and '@id' in value:
                if value['@id'] not in entity_index:
                    broken_refs.append({
                        'source': entity['@id'],
                        'predicate': key,
                        'target': value['@id']
                    })

            # Check list references
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and '@id' in item:
                        if item['@id'] not in entity_index:
                            broken_refs.append({
                                'source': entity['@id'],
                                'predicate': key,
                                'target': item['@id']
                            })

    if broken_refs:
        return False, f"Found {len(broken_refs)} broken references"

    return True, None
```

#### 5. Iteration-Specific Validations

**Iteration 2 (Two-Pass Extraction)**:

- Broken reference rate must be <2%

**Iteration 3 (Orphan Detection)**:

- Orphan rate must be <0.5%

**Iteration 4 (Sub-Entity Extraction)**:

- Sub-entities must have parent relationships
- Parent entities must reference sub-entities

**Iteration 7 (Maximum Fidelity)**:

- Field coverage must be >80% of source data
- Average predicates per entity must be >12

**Validation Function**:

```python
def validate_iteration_targets(entities, source_files):
    """Validate iteration-specific targets."""
    results = {}

    # Iteration 2: Broken reference rate
    broken_ref_rate = calculate_broken_ref_rate(entities)
    results['iteration_2'] = broken_ref_rate < 0.02  # <2%

    # Iteration 3: Orphan rate
    orphan_rate = calculate_orphan_rate(entities)
    results['iteration_3'] = orphan_rate < 0.005  # <0.5%

    # Iteration 7: Field coverage and predicate density
    avg_coverage = calculate_avg_field_coverage(entities, source_files)
    avg_predicates = calculate_avg_predicates(entities)

    results['iteration_7_coverage'] = avg_coverage > 0.80  # >80%
    results['iteration_7_predicates'] = avg_predicates > 12  # >12

    return all(results.values()), results
```

---

## Changes to PROCESS.md

### Section-by-Section Transformations

#### Overview Section

**BEFORE**:

```markdown
## Overview

### What This Framework Does

Transforms any structured repository into a queryable knowledge graph.

### Instructions for Claude

When a user asks you to extract a knowledge graph:
1. Follow this process systematically
2. Generate extraction scripts
3. Use absolute paths from arguments
...
```

**AFTER**:

```markdown
## Overview

### What This Framework Does

Transforms any structured repository into a queryable knowledge graph through
AI-first reasoning and autonomous execution.

### Execution Paradigm

**AI-First Reasoning**:
- Claude Code agents EXECUTE extraction through intelligent reasoning
- Agents analyze, understand, and make decisions autonomously
- No script generation - direct reasoning over data
- Adaptive to any repository structure

**Deterministic Validation**:
- All output must conform to strict standards
- URN format, JSON-LD structure, required predicates enforced
- Reference integrity validated
- Quality metrics measured

### Instructions for Claude Code Agents

When executing knowledge graph extraction:

1. **REASON, Don't Script**: Analyze repository through intelligent reasoning,
   not template-driven extraction

2. **UNDERSTAND Semantics**: Understand what data represents, not just parse it

3. **DECIDE Adaptively**: Make extraction decisions based on context and
   understanding

4. **VALIDATE Output**: Ensure output conforms to all standards (URN format,
   JSON-LD, required fields)

5. **SELF-ASSESS**: Evaluate your own work, assign confidence scores, flag
   uncertainties

6. **ITERATE**: If validation fails, analyze why and improve reasoning
...
```

#### Phase 0: Repository Discovery

**BEFORE** (Script-oriented):

```markdown
## Phase 0: Repository Discovery

**Goal**: Understand repository structure before writing extraction code.

### Step 1: Initial Scan

```bash
# Count files by type
find . -type f | sed 's/.*\.//' | sort | uniq -c
```

### Step 2: Schema Detection

...

```

**AFTER** (AI-oriented):
```markdown
## Phase 0: Repository Discovery

**Goal**: AI agent analyzes and understands repository organization through reasoning.

### AI Reasoning Process

**Step 1: Repository Purpose Analysis**

Agent asks:
- "What is this repository's purpose?" (code, config, docs, infrastructure)
- "What problem does it solve?"
- "Who uses it and how?"

Reasoning output:
- Repository classification (with confidence)
- Use case understanding
- Expected entity types

**Example AI Analysis**:
```

Agent: "Analyzing /app-interface repository...

Purpose: Configuration management repository for OpenShift services

- Contains service definitions, deployment configs, access control
- Used by SRE teams to manage production infrastructure
- Structured data (YAML) with formal schemas

Classification: Infrastructure Configuration Repository
Confidence: HIGH (clear patterns, formal schemas, consistent structure)"

```

**Step 2: Organizational Pattern Discovery**

Agent asks:
- "How are files organized?" (directory structure, naming)
- "What patterns exist?" (entity types, relationships)
- "What conventions are used?" (metadata, references)

Reasoning output:
- Organizational pattern description
- Entity type hypothesis
- Relationship pattern hypothesis

**Example AI Analysis**:
```

Agent: "Organizational pattern analysis...

Directory Structure:
/data/services/{service_name}/app.yml → Service entities
/data/dependencies/{dep_name}/service.yml → Dependency entities
/data/teams/{team_name}/ → Team entities

Pattern: Type-based organization with nested entity instances

File Naming:

- app.yml: Main entity definition
- service.yml: Service-type entities
- {name}.yml: Named entity instances

Pattern: Consistent naming by entity type

Cross-References:

- $ref: /path/to/file.yml → Explicit references
- $schema: /schemas/type.yml → Schema validation
- namespace.$ref → Relationship references

Pattern: File path-based referencing with schemas

Hypothesis: This is a schema-driven repository with ~15 entity types,
extensive cross-references, and formal validation.

Confidence: HIGH"

```

**Step 3: Sample Analysis**

Agent autonomously reads sample files to validate hypotheses:

```

Agent: "Sampling 10 files from /data/services/...

File 1: cincinnati/app.yml

- Schema: /app-1.yml ✓
- Has name, description, owners ✓
- References dependencies, namespaces ✓
- Pattern matches hypothesis ✓

File 2: acs-fleet-manager/app.yml

- Schema: /app-1.yml ✓
- Rich metadata (12+ fields) ✓
- Multiple owners, endpoints ✓
- Confirms pattern ✓

... (8 more samples)

Validation: 10/10 samples match organizational hypothesis
Confidence: Elevated to VERY HIGH

Entity types confirmed:

- Service (primary)
- Dependency (referenced)
- Namespace (referenced)
- Owner/User (nested in services)
- Endpoint (nested in services)

Extraction Strategy: Schema-driven with AI field discovery
Estimated entities: ~5,000-10,000
Estimated relationships: ~20,000-30,000"

```

**Step 4: Extraction Strategy Selection**

Agent decides approach based on analysis:

**Decision Matrix**:
```

Schemas available? YES → Schema-driven extraction
  ↓
Are schemas comprehensive? YES → High confidence extraction
  ↓
Need AI enhancement? YES → Combine schema + AI field discovery
  ↓
Strategy: Schema-driven with Maximum Fidelity (Iteration 7)

```

**No Script Generation** - Agent has analyzed and is ready to execute.

### Deterministic Validation

None required at this phase - AI reasoning is exploratory.

Agent output will be validated in extraction phases.
```

#### Phase 2: Entity Extraction

**BEFORE** (Template-driven):

```markdown
## Phase 2: Entity Extraction

### Extraction Pattern

```python
def extract_entity_type(schema_config, output_file):
    """Extract entities of a single type."""
    entities = []

    files = glob(schema_config['file_pattern'])

    for filepath in files:
        data = load_yaml_or_json(filepath)

        # Create entity with URN
        urn = generate_urn(schema_config['urn_pattern'], data)

        entity = {
            "@id": urn,
            "@type": schema_config['entity_type']
        }

        # Extract required fields
        for field in schema_config['required_predicates']:
            value = get_nested_field(data, field)
            entity[field] = value

        entities.append(entity)
```

**AFTER** (AI-driven):

```markdown
## Phase 2: Entity Extraction

### AI Extraction Process

Agent executes extraction through reasoning, not templates.

**Step 1: File-by-File Analysis**

For each file, agent reasons:

**Question 1**: "What entity type does this represent?"
- Read $schema reference → Understand entity type
- Analyze structure → Confirm type matches pattern
- Classify with confidence

**Question 2**: "What fields should I extract?"
- Identify ALL fields in source (not from template)
- Categorize: identity, descriptive, metadata, config, relationships, resources, contact, status
- Apply Iteration 7 (Maximum Fidelity): Extract everything meaningful
- Decide per-field with reasoning

**Question 3**: "How should I handle nested structures?"
- Check Iteration 4 sub-entity criteria (3+ properties, queryable, relationships)
- Decide: sub-entity or inline
- Create bidirectional relationships if sub-entity

**Question 4**: "What is my extraction confidence?"
- Schema match: HIGH
- Field completeness: Check coverage
- Sub-entity decisions: Validate criteria
- Overall: Assign confidence score

**Example AI Extraction**:

```

Agent extracting /data/services/cincinnati/app.yml:

=== ANALYSIS ===
File: cincinnati/app.yml
Schema: /app-1.yml (Service schema matched)
Entity Type: Service (HIGH confidence)

Source Fields Discovered:

1. name: "Cincinnati" ✓ (required)
2. description: "OpenShift Update Service..." ✓ (required)
3. serviceOwners: [{name, email}, {name, email}] ✓ (required)
4. grafanaUrl: "https://..." ✓ (optional but present)
5. slackChannel: "#cincinnati-team" ✓ (optional but present)
6. sopsUrl: "https://..." ✓ (optional but present)
7. architectureDocument: "https://..." ✓ (optional but present)
8. appCode: "CINC-001" ✓ (optional but present)
9. costCenter: "Engineering" ✓ (optional but present)
10. tier: "production" ✓ (optional but present)
11. criticality: "high" ✓ (optional but present)
12. dependencies: [$ref, $ref, ...] ✓ (relationships)
13. $schema: /app-1.yml ✗ (structural metadata - skip)
14. apiVersion: v1 ✗ (structural metadata - skip)

=== FIELD EXTRACTION DECISIONS ===

Identity: name → Extract ✓
Descriptive: description → Extract ✓
Resources: grafanaUrl, sopsUrl, architectureDocument → Extract ALL ✓
Contact: slackChannel → Extract ✓
Configuration: appCode, costCenter, tier, criticality → Extract ALL ✓
  (Iteration 7: Don't skip "optional" operational metadata)
Status: onboardingStatus (if present) → Extract ✓

Nested: serviceOwners

- Analysis: Array of 2 items, each with {name, email, role}
- Properties per item: 3 ✓ (meets Iteration 4 criteria)
- Independent queryability: YES ✓ ("find services owned by user X")
- Decision: Extract as User sub-entities ✓

Nested: dependencies

- Analysis: Array of $ref values
- Decision: Defer to Phase 3 relationship resolution ✓

Field Coverage: 12 extracted / 14 total = 85.7%
Target: >80% (Iteration 7) ✓

=== EXTRACTION OUTPUT ===

Main Entity:
{
  "@id": "urn:service:cincinnati",
  "@type": "Service",
  "name": "Cincinnati",
  "description": "OpenShift Update Service that provides update recommendations...",
  "onboardingStatus": "OnBoarded",
  "grafanaUrl": "<https://grafana.example.com/d/cincinnati>",
  "slackChannel": "#cincinnati-team",
  "sopsUrl": "<https://github.com/org/cincinnati/docs/sops>",
  "architectureDocument": "<https://docs.example.com/arch/cincinnati>",
  "appCode": "CINC-001",
  "costCenter": "Engineering",
  "tier": "production",
  "criticality": "high",
  "hasOwner": [
    {"@id": "urn:user:jdoe@example.com"},
    {"@id": "urn:user:jsmith@example.com"}
  ],
  "_pending_refs": [...] // For Phase 3
}

Sub-Entities:
{
  "@id": "urn:user:jdoe@example.com",
  "@type": "User",
  "name": "John Doe",
  "email": "<jdoe@example.com>",
  "role": "technical_lead",
  "owns": [{"@id": "urn:service:cincinnati"}]
}
{
  "@id": "urn:user:jsmith@example.com",
  "@type": "User",
  "name": "Jane Smith",
  "email": "<jsmith@example.com>",
  "owns": [{"@id": "urn:service:cincinnati"}]
}

Total Predicates: 14 (exceeds Iteration 7 target of 12+) ✓

Confidence: HIGH

- Schema match: HIGH ✓
- Field coverage: 85.7% ✓
- Sub-entity decisions: Applied criteria correctly ✓

```

**No template execution** - Agent reasoned about each field individually.

### Deterministic Validation (After AI Extraction)

```python
# Validate each entity after AI extraction
for entity in extracted_entities:
    # URN format
    valid, error = validate_urn_format(entity['@id'])
    if not valid:
        raise ValidationError(f"URN invalid: {error}")

    # Required predicates
    valid, error = validate_required_predicates(entity)
    if not valid:
        raise ValidationError(f"Missing predicates: {error}")

    # Field coverage (Iteration 7)
    coverage = calculate_field_coverage(entity, source_data)
    if coverage < 0.80:
        warn(f"Low coverage: {coverage:.1%} for {entity['@id']}")

    # Predicate count (Iteration 7)
    predicate_count = count_predicates(entity)
    if predicate_count < 5:
        warn(f"Sparse entity: {predicate_count} predicates for {entity['@id']}")

# All validations passed → Accept entities
```

AI decides **what** to extract; validation ensures **quality standards** met.

```

### Key PROCESS.md Updates

1. **Replace all Python code templates** with AI reasoning examples
2. **Remove script generation instructions** - agents execute directly
3. **Add confidence scoring** to all AI decisions
4. **Add self-validation checkpoints** after each phase
5. **Separate AI reasoning from deterministic validation** clearly
6. **Update all examples** to show AI thought process, not code execution
7. **Add "Deterministic Validation" sections** after each AI reasoning section
8. **Emphasize autonomy** - agents must execute end-to-end

---

## Testing Plan

### Phase 1: Process Validation (Before Agent Testing)

**Goal**: Ensure PROCESS.md is complete and coherent for AI execution

**Checks**:
1. ✓ All phases have AI reasoning guidance (no script generation)
2. ✓ Confidence scoring framework defined
3. ✓ Self-validation checkpoints specified
4. ✓ Deterministic validation standards clear
5. ✓ Examples show AI reasoning, not code execution
6. ✓ Agent autonomy expectations clear

### Phase 2: Agent Execution Test

**Goal**: Test if sub-agent can execute extraction autonomously

**Test Setup**:
- Repository: `/home/jsell/code/sandbox/cartograph/app-interface`
- Agent: Launch general-purpose agent with PROCESS.md context
- Constraint: Agent must execute end-to-end without human intervention

**Agent Instructions**:
```

You are an AI agent executing knowledge graph extraction following PROCESS.md.

Repository: /home/jsell/code/sandbox/cartograph/app-interface
Output: /home/jsell/code/kartograph-kg-iteration/extraction/working/test_extraction.jsonld

Execute all phases:

- Phase 0: Analyze repository structure (AI reasoning)
- Phase 1: Understand schemas (AI reasoning)
- Phase 2: Extract entities (AI reasoning + validation)
- Phase 3: Resolve relationships (AI reasoning + validation)
- Phase 3.5: Validate output (AI self-assessment + deterministic checks)

Report:

- Your reasoning at each step
- Confidence scores for decisions
- Validation results
- Any issues encountered
- Final quality assessment

Follow PROCESS.md exactly. Do not generate scripts - reason and extract directly.

```

**Success Criteria**:
1. Agent completes extraction autonomously (no human intervention)
2. All deterministic validations pass
3. Agent provides confidence scores and reasoning
4. Output conforms to standards (URN, JSON-LD, required predicates)
5. Iteration targets met (coverage >80%, predicates >12, broken refs <2%, orphans <0.5%)

**Failure Modes to Watch**:
- Agent tries to generate scripts instead of reasoning
- Agent gets confused about autonomy boundaries
- Deterministic validations fail
- Agent can't self-assess quality
- Agent can't adapt to unexpected patterns

### Phase 3: Iteration Based on Agent Feedback

If agent execution fails or performs poorly:

1. **Analyze agent behavior**: Where did it struggle?
2. **Identify PROCESS.md gaps**: What guidance was missing or unclear?
3. **Update PROCESS.md**: Add clarity, examples, reasoning patterns
4. **Re-test with agent**: Verify improvements work
5. **Iterate until success**: Repeat until agent executes correctly

**Feedback Loop**:
```

Test Agent → Agent Fails → Analyze Failure → Update PROCESS.md → Re-test
     ↑                                                               ↓
     └─────────────────── Iterate Until Success ───────────────────┘

```

---

## Success Criteria

### Iteration 8 Complete When:

1. ✅ PROCESS.md fully transformed to AI-first paradigm
2. ✅ All script generation instructions removed
3. ✅ AI reasoning patterns documented for all phases
4. ✅ Deterministic validation standards defined
5. ✅ Confidence scoring framework integrated
6. ✅ Self-validation checkpoints specified
7. ✅ Sub-agent successfully executes extraction autonomously
8. ✅ All deterministic validations pass on agent output
9. ✅ Iteration targets met (coverage, predicates, broken refs, orphans)
10. ✅ Agent provides quality self-assessment

### Expected Metrics (After Iteration 8):

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Agent Autonomy** | 100% | Agent completes extraction without human intervention |
| **Reasoning Quality** | HIGH | Agent provides clear reasoning for all decisions |
| **Confidence Scoring** | All decisions | Every extraction/inference has confidence score |
| **Validation Pass Rate** | 100% | All deterministic validations pass |
| **URN Format** | 100% | All URNs conform to standard |
| **Required Predicates** | 100% | All entities have @id, @type, name |
| **Field Coverage** | >80% | Average field coverage exceeds target (Iteration 7) |
| **Predicate Density** | >12 | Average predicates per entity exceeds target |
| **Broken References** | <2% | Broken reference rate meets target (Iteration 2) |
| **Orphan Rate** | <0.5% | Orphan entity rate meets target (Iteration 3) |
| **Sub-Entity Extraction** | Applied | Iteration 4 criteria applied correctly |
| **Free-Text Extraction** | Applied | Iteration 5 patterns used where applicable |
| **Universal Inference** | Applied | Iteration 6 patterns discovered and applied |

---

## Implementation Status

- ⏳ PROCESS.md transformation (in progress)
- ⏳ ITERATION_8_CHANGES.md documentation (this file)
- ⏳ ITERATIONS.md update (pending)
- ⏳ Agent execution test (pending)
- ⏳ Iteration based on feedback (pending)

---

## Next Steps

1. **Complete PROCESS.md transformation**:
   - Update all phases with AI reasoning patterns
   - Remove all script generation instructions
   - Add deterministic validation sections
   - Include AI reasoning examples

2. **Test with sub-agent**:
   - Launch agent with PROCESS.md context
   - Execute extraction on app-interface
   - Observe agent behavior and results
   - Collect feedback

3. **Iterate PROCESS.md**:
   - Analyze any agent failures
   - Update guidance based on observed issues
   - Re-test until agent succeeds
   - Document learnings

4. **Finalize Iteration 8**:
   - Update ITERATIONS.md
   - Document final metrics
   - Archive successful extraction
   - Mark iteration complete

---

**Key Insight**: By transforming to an AI-first paradigm with deterministic validation, we enable:
- **Autonomous execution** by AI agents (no human intervention)
- **Adaptive reasoning** (handles unexpected patterns)
- **Quality assurance** (strict standards enforced)
- **Self-improvement** (agents test and iterate on process)
- **Full leverage** of Claude Code's intelligence

This is the culmination of Iterations 0-7, enabling true AI-first knowledge graph extraction.
