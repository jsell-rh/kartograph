# Iteration 5 Changes: AI-Driven Free-Text Entity Extraction

**Date**: 2025-10-20
**Status**: Complete (PROCESS.md updates)
**Focus**: Extract entities and relationships from description fields using AI-driven natural language understanding

---

## Overview

Iteration 5 enhances PROCESS.md with guidance for Claude Code (AI agent) to extract entities and relationships from free-text description fields. Unlike previous iterations that focused on structured data extraction patterns, this iteration leverages AI's natural language understanding capabilities to recognize tool mentions, technology stack details, team ownership, and infrastructure context embedded in service descriptions.

**Key Innovation**: AI-driven analysis instead of rigid regex patterns. Claude Code reasons about natural language to identify entities, classify types, infer relationships, and assign confidence levels.

---

## Files Modified

1. **/home/jsell/code/kartograph-kg-iteration/extraction/PROCESS.md**
   - **Lines 1342-1797**: Added "Free-Text Entity Extraction (AI-Driven)" subsection to Phase 2
   - **Lines 4557-4862**: Added Section 6.9 "Free-Text Entity Extraction with AI" to Best Practices
   - **Line 12**: Updated Goal #4 to include free-text extraction

2. **/home/jsell/code/kartograph-kg-iteration/extraction/ITERATIONS.md**
   - **Lines 713-1026**: Added complete Iteration 5 section with hypothesis, changes, examples, metrics

---

## What Changed

### New Capabilities Added to PROCESS.md

1. **AI Reasoning Framework** (Phase 2, lines 1342-1797):
   - 5-step process for Claude Code to analyze natural language
   - Confidence-based extraction (HIGH/MEDIUM/LOW levels)
   - Entity type classification (5 categories: Tools, Technologies, Infrastructure, Teams, External Services)
   - Relationship pattern recognition (12 natural language → graph predicate mappings)
   - Quality guidelines (6 principles to prevent over-extraction and ensure validation)

2. **Integration with Existing Workflow**:
   - Pass 1.5: Free-Text Analysis (between entity extraction and relationship resolution)
   - Minimal Python orchestration (calls Claude Code API, validates results, filters by confidence)
   - Entity index validation (prevent duplicates, normalize names, check existence)

3. **Comprehensive Examples** (Best Practices Section 6.9, lines 4557-4862):
   - Why AI excels at this task (5 reasons with examples)
   - 5 AI reasoning patterns (tool detection, team recognition, tech stack extraction, infrastructure inference, integration mentions)
   - 2 concrete before/after examples showing AI reasoning process

---

## Before/After Examples with AI Reasoning

### Example 1: Rich Service Description (ACS Fleet Manager)

**Input YAML** (from app-interface):

```yaml
service:
  name: "acs-fleet-manager"
  description: |
    ACS Fleet Manager is the control plane for Red Hat Advanced Cluster Security.
    It uses PostgreSQL for data persistence and Prometheus for monitoring.
    Deployed via ArgoCD to production OpenShift clusters. Backend is written in Go
    with gRPC APIs. Maintained by the RHACS Engineering team.
```

---

#### Before Iteration 5 (Structured Extraction Only)

**Extracted Entity**:

```json
{
  "@id": "urn:service:acs-fleet-manager",
  "@type": "Service",
  "name": "ACS Fleet Manager",
  "description": "ACS Fleet Manager is the control plane for Red Hat Advanced Cluster Security..."
}
```

**Result**:

- 1 service entity
- 0 relationships from description
- **Missed**: PostgreSQL, Prometheus, ArgoCD, OpenShift, Go, gRPC, RHACS Engineering team

---

#### After Iteration 5 (AI-Driven Free-Text Extraction)

**Claude Code AI Reasoning Process**:

**Step 1: Identify Entity Mentions**

```
Scanning description for proper nouns and technical terms...

Detected mentions:
- "PostgreSQL" (database technology)
- "Prometheus" (monitoring tool)
- "ArgoCD" (deployment tool)
- "OpenShift" (platform)
- "Go" (programming language - context: "written in")
- "gRPC" (protocol/technology)
- "RHACS Engineering team" (team organization)
- "Red Hat Advanced Cluster Security" (product/organization)
```

**Step 2: Classify Entity Types**

```
Analyzing context to determine entity types:

- "PostgreSQL" + "uses...for data persistence" → Database (HIGH confidence)
- "Prometheus" + "uses...for monitoring" → MonitoringTool (HIGH confidence)
- "ArgoCD" + "deployed via" → DeploymentTool (HIGH confidence)
- "OpenShift" + "deployed to...clusters" → Platform (HIGH confidence)
- "Go" + "written in" → ProgrammingLanguage (HIGH confidence)
  (NOT action verb "go to production" - context disambiguates)
- "gRPC" + "APIs" → Protocol (HIGH confidence)
- "RHACS Engineering team" + "maintained by" → Team (HIGH confidence)
```

**Step 3: Extract Relationships**

```
Recognizing action verbs and relationship keywords:

- "uses PostgreSQL for data persistence" → usesDatabase (purpose: data persistence)
- "uses...Prometheus for monitoring" → monitoredBy
- "deployed via ArgoCD" → deployedVia
- "deployed...to production OpenShift clusters" → deployedTo
- "written in Go" → writtenIn
- "with gRPC APIs" → uses (technology: gRPC)
- "maintained by the RHACS Engineering team" → maintainedBy
```

**Step 4: Assign Confidence Levels**

```
Evaluating extraction certainty:

All extractions: HIGH confidence
Reasoning:
- Explicit tool/technology names with clear action verbs
- Unambiguous context ("uses X for Y", "deployed via X", "written in X")
- No vague mentions ("various tools", "multiple services")
- Clear relationship keywords ("uses", "deployed", "maintained by")
```

**Step 5: Validate Against Entity Index**

```
Checking for existing entities:

PostgreSQL: Not in index → Create urn:database:postgresql
Prometheus: Not in index → Create urn:monitoring-tool:prometheus
ArgoCD: Not in index → Create urn:deployment-tool:argocd
OpenShift: Not in index → Create urn:platform:openshift
Go: Not in index → Create urn:programming-language:go
gRPC: Not in index → Create urn:protocol:grpc
RHACS Engineering: Not in index → Create urn:team:rhacs-engineering

All names normalized to canonical forms (PostgreSQL not postgres, ArgoCD not argo-cd)
```

---

**Extracted Entities** (7 new from description):

```json
[
  {
    "@id": "urn:database:postgresql",
    "@type": "Database",
    "name": "PostgreSQL"
  },
  {
    "@id": "urn:monitoring-tool:prometheus",
    "@type": "MonitoringTool",
    "name": "Prometheus"
  },
  {
    "@id": "urn:deployment-tool:argocd",
    "@type": "DeploymentTool",
    "name": "ArgoCD"
  },
  {
    "@id": "urn:platform:openshift",
    "@type": "Platform",
    "name": "OpenShift"
  },
  {
    "@id": "urn:programming-language:go",
    "@type": "ProgrammingLanguage",
    "name": "Go"
  },
  {
    "@id": "urn:protocol:grpc",
    "@type": "Protocol",
    "name": "gRPC"
  },
  {
    "@id": "urn:team:rhacs-engineering",
    "@type": "Team",
    "name": "RHACS Engineering"
  }
]
```

**Extracted Relationships** (7 new from description):

```json
{
  "@id": "urn:service:acs-fleet-manager",
  "@type": "Service",
  "name": "ACS Fleet Manager",
  "description": "ACS Fleet Manager is the control plane for Red Hat Advanced Cluster Security...",

  // NEW relationships from description analysis:
  "usesDatabase": {
    "@id": "urn:database:postgresql",
    "_confidence": "HIGH",
    "_purpose": "data persistence"
  },
  "monitoredBy": {
    "@id": "urn:monitoring-tool:prometheus",
    "_confidence": "HIGH"
  },
  "deployedVia": {
    "@id": "urn:deployment-tool:argocd",
    "_confidence": "HIGH"
  },
  "deployedTo": {
    "@id": "urn:platform:openshift",
    "_confidence": "HIGH"
  },
  "writtenIn": {
    "@id": "urn:programming-language:go",
    "_confidence": "HIGH"
  },
  "uses": {
    "@id": "urn:protocol:grpc",
    "_confidence": "HIGH",
    "_purpose": "APIs"
  },
  "maintainedBy": {
    "@id": "urn:team:rhacs-engineering",
    "_confidence": "HIGH"
  }
}
```

**Result**:

- 1 service description → **7 new entities + 7 new relationships**
- All extractions: HIGH confidence (auto-applied)
- Graph density for this service: 0 → 7 relationships (+700%)

---

### Example 2: Minimal Description (API Gateway)

**Input YAML**:

```yaml
service:
  name: "api-gateway"
  description: "API Gateway running on AWS with Redis caching"
```

---

#### Before Iteration 5

**Extracted Entity**:

```json
{
  "@id": "urn:service:api-gateway",
  "@type": "Service",
  "name": "API Gateway",
  "description": "API Gateway running on AWS with Redis caching"
}
```

**Result**: 1 service, 0 relationships from description

---

#### After Iteration 5

**Claude Code AI Reasoning**:

**Step 1-2: Identify and Classify**

```
Detected mentions:
- "AWS" (context: "running on") → CloudProvider (HIGH confidence)
- "Redis" (context: "caching") → Cache (HIGH confidence)
```

**Step 3-4: Extract Relationships and Assign Confidence**

```
- "running on AWS" → runsOn (HIGH confidence)
- "with Redis caching" → uses (HIGH confidence, purpose: caching)
```

**Step 5: Validate**

```
AWS: Not in index → Create urn:cloud-provider:aws
Redis: Not in index → Create urn:cache:redis
```

---

**Extracted Entities** (2 new):

```json
[
  {
    "@id": "urn:cloud-provider:aws",
    "@type": "CloudProvider",
    "name": "AWS"
  },
  {
    "@id": "urn:cache:redis",
    "@type": "Cache",
    "name": "Redis"
  }
]
```

**Extracted Relationships** (2 new):

```json
{
  "@id": "urn:service:api-gateway",
  "@type": "Service",
  "name": "API Gateway",
  "description": "API Gateway running on AWS with Redis caching",

  "runsOn": {
    "@id": "urn:cloud-provider:aws",
    "_confidence": "HIGH"
  },
  "uses": {
    "@id": "urn:cache:redis",
    "_confidence": "HIGH",
    "_purpose": "caching"
  }
}
```

**Result**: Even minimal descriptions yield **2 entities + 2 relationships**

---

### Example 3: Complex Technology Stack (E-Commerce Backend)

**Input YAML**:

```yaml
service:
  name: "ecommerce-backend"
  description: |
    E-commerce backend API built with Python using FastAPI framework.
    Frontend is React with TypeScript. Uses PostgreSQL for orders database,
    Redis for caching, and AWS S3 for product images. Deployed to production
    via GitHub Actions CI/CD pipeline. Monitored with Datadog.
```

---

#### Claude Code AI Reasoning

**Step 1-2: Identify and Classify**

```
Detected mentions:
- "Python" + "built with" → ProgrammingLanguage (HIGH)
- "FastAPI" + "framework" → Framework (HIGH)
- "React" + "frontend" → Framework (HIGH)
- "TypeScript" + "with React" → ProgrammingLanguage (HIGH)
- "PostgreSQL" + "orders database" → Database (HIGH)
- "Redis" + "caching" → Cache (HIGH)
- "AWS S3" + "product images" → Storage (HIGH)
- "GitHub Actions" + "CI/CD pipeline" → CITool (HIGH)
- "Datadog" + "monitored with" → MonitoringTool (HIGH)
```

**Step 3: Extract Relationships**

```
- "built with Python" → writtenIn
- "using FastAPI framework" → usesFramework
- "Frontend is React" → frontendFramework
- "with TypeScript" → frontendLanguage
- "Uses PostgreSQL for orders database" → usesDatabase (purpose: orders)
- "Redis for caching" → uses (purpose: caching)
- "AWS S3 for product images" → usesStorage (purpose: product images)
- "Deployed...via GitHub Actions" → deployedVia
- "Monitored with Datadog" → monitoredBy
```

**Result**: **9 entities + 9 relationships** from one description

---

### Example 4: Team and Ownership Context

**Input YAML**:

```yaml
service:
  name: "customer-portal"
  description: |
    Customer-facing web portal maintained by the Platform Engineering team.
    Point of contact: platform-team@example.com. Built and operated by the SRE team.
```

---

#### Claude Code AI Reasoning

**Step 1-2: Identify and Classify**

```
Detected mentions:
- "Platform Engineering team" + "maintained by" → Team (HIGH)
- "platform-team@example.com" + "point of contact" → Contact/Email (HIGH)
- "SRE team" + "built and operated by" → Team (HIGH)
```

**Step 3: Extract Relationships**

```
- "maintained by the Platform Engineering team" → maintainedBy
- "built and operated by the SRE team" → operatedBy
```

**Extracted Entities**:

```json
[
  {
    "@id": "urn:team:platform-engineering",
    "@type": "Team",
    "name": "Platform Engineering",
    "contact": "platform-team@example.com"
  },
  {
    "@id": "urn:team:sre",
    "@type": "Team",
    "name": "SRE"
  }
]
```

**Extracted Relationships**:

```json
{
  "@id": "urn:service:customer-portal",
  "maintainedBy": {
    "@id": "urn:team:platform-engineering",
    "_confidence": "HIGH"
  },
  "operatedBy": {
    "@id": "urn:team:sre",
    "_confidence": "HIGH"
  }
}
```

**Result**: **2 team entities + 2 relationships** enabling team ownership queries

---

## AI Reasoning Quality Examples

### Example 5: Context Disambiguation (HIGH vs LOW confidence)

**Input**:

```yaml
description: |
  This service runs on various tools and may use different databases
  depending on environment. Go to production requires approval.
```

#### Claude Code AI Analysis

**HIGH Confidence (auto-apply)**:

```
None - no explicit tool/technology mentions with clear context
```

**MEDIUM Confidence (log for review)**:

```
None
```

**LOW Confidence (skip)**:

```
- "various tools" - too vague, no specific tool names
- "different databases" - generic mention, no specific database
- "Go to production" - "Go" is action verb, not programming language
  Context: "Go to production" is idiomatic phrase, not technology mention
```

**Result**: 0 entities extracted (correctly skips vague/ambiguous mentions)

---

### Example 6: Name Standardization and Duplicate Prevention

**Input**:

```yaml
description: |
  Uses github for source control and Github Actions for CI.
  Code stored in github.com/org/repo.
```

#### Claude Code AI Reasoning

**Step 1-2: Identify and Classify**

```
Detected mentions:
- "github" (3 variations: "github", "Github Actions", "github.com")
```

**Step 5: Validate and Normalize**

```
Normalizing to canonical name: "GitHub"

Variations found:
- "github" → "GitHub" (standardized)
- "Github Actions" → "GitHub Actions" (product name)
- "github.com" → "GitHub" (domain → company)

Check entity index:
- urn:code-hosting:github exists? → YES
- Reuse existing entity, don't create duplicate

Result: 1 entity (GitHub), not 3 duplicates
```

**Extracted**:

```json
{
  "usesCodeHosting": {
    "@id": "urn:code-hosting:github",
    "_confidence": "HIGH"
  },
  "deployedVia": {
    "@id": "urn:ci-tool:github-actions",
    "_confidence": "HIGH"
  }
}
```

**Result**: Correctly identifies GitHub mentioned 3 times, creates 2 entities (GitHub + GitHub Actions), prevents duplicates

---

## Expected Impact Metrics

### Quantitative Improvements

| Metric | Before Iteration 5 | After Iteration 5 | Improvement |
|--------|-------------------|-------------------|-------------|
| **Total Entities** | 11,294 | 11,800-12,300 | +500-1,000 (+4-9%) |
| **Tools/Technologies** | ~50 (structured) | 250-450 | 4-8x increase |
| **Team Entities** | ~30 (structured) | 80-130 | 2-4x increase |
| **Total Relationships** | 21,964 | 23,000-24,000 | +1,000-2,000 (+5-9%) |
| **Graph Density** | 1.9 rel/entity | 2.5-3.0 rel/entity | +30-60% |
| **Description Coverage** | 0% | 70-90% | New capability |

### Qualitative Improvements

**New Query Capabilities** (20+ patterns):

1. **Tool Usage Queries**:
   - "Find all services using Prometheus for monitoring"
   - "Show services deployed via ArgoCD"
   - "List services using PostgreSQL databases"

2. **Technology Stack Queries**:
   - "Find services written in Go"
   - "Show React frontends"
   - "List services using gRPC"

3. **Team Ownership Queries**:
   - "Show services maintained by Platform Engineering team"
   - "Find services without team ownership"

4. **Infrastructure Queries**:
   - "Find services running on AWS"
   - "Show services using S3 storage"

5. **Integration Queries**:
   - "Find services integrating with GitHub API"
   - "Show services using Vault for secrets"

---

## Validation Metrics to Track

### Extraction Quality Metrics

1. **Entities Extracted from Descriptions**:
   - Target: 500-1,000 new entities
   - Breakdown by type (Tools, Technologies, Teams, Infrastructure, External Services)

2. **Confidence Distribution**:
   - Target: >70% HIGH confidence
   - <20% MEDIUM confidence
   - <10% LOW confidence (skipped)

3. **Validation Success**:
   - Entities matched to existing vs created new
   - Duplicate prevention rate (variations normalized correctly)
   - Name standardization rate (canonical names used)

4. **Relationship Quality**:
   - Relationships created from free text: 1,000-2,000
   - Validation success rate (target URN exists)
   - Relationship predicate variety (uses, deployedVia, maintainedBy, etc.)

5. **Graph Enrichment**:
   - Total entity count increase: +500-1,000
   - Total relationship count increase: +1,000-2,000
   - Graph density: 1.9 → 2.5-3.0 rel/entity

6. **Coverage**:
   - % of services with extractable descriptions: target 70-90%
   - Average entities extracted per description: target 2-5

### Manual Review Metrics

7. **False Positives**:
   - Incorrect entity extractions (target: <5%)
   - Incorrect relationship inferences (target: <5%)

8. **False Negatives**:
   - Missed entity mentions in descriptions (sample review)
   - Missed relationship keywords (sample review)

---

## Integration with Existing Workflow

### Updated Extraction Flow

```
Phase 0: Repository Discovery
  ↓
Phase 1: Schema Analysis
  ↓
Phase 2: Entity Extraction
  ├─ Pass 1: Extract structured entities
  ├─ Build entity index
  ├─ Pass 1.5: AI-Driven Free-Text Analysis (NEW - Iteration 5)
  │   ├─ Extract description fields from entities
  │   ├─ Call Claude Code API with PROCESS.md guidance
  │   ├─ Claude Code analyzes natural language (5-step process)
  │   ├─ Validate extractions against entity index
  │   ├─ Filter by confidence (apply HIGH only)
  │   └─ Add new entities to index
  └─ Pass 2: Resolve structured relationships
  ↓
Phase 3: Relationship Resolution
  ├─ Create free-text extracted relationships (HIGH confidence)
  ├─ Validate all relationships
  └─ Generate reports for MEDIUM/LOW confidence
  ↓
Phase 3.5: Graph Validation & Repair
  ↓
Phase 4: Graph Export
```

---

## Success Criteria

**Documentation (Complete)**:

- ✅ AI-driven extraction patterns documented in PROCESS.md
- ✅ Confidence-based framework defined (HIGH/MEDIUM/LOW)
- ✅ Entity types clearly categorized (5 categories)
- ✅ Relationship patterns mapped (12 natural language → predicate)
- ✅ Quality guidelines prevent over-extraction
- ✅ Integration workflow documented

**Implementation (Pending)**:

- ⏳ Python orchestration script (minimal - calls Claude Code API)
- ⏳ Re-extraction with free-text analysis
- ⏳ Metrics validation

**Target Metrics (Pending)**:

- ⏳ Entities from descriptions: 0 → 500-1,000
- ⏳ Relationships from free text: 0 → 1,000-2,000
- ⏳ Graph density: 1.9 → 2.5-3.0 rel/entity
- ⏳ Query patterns enabled: 20+
- ⏳ HIGH confidence rate: >70%

---

## Next Steps

1. **Implement Python orchestration script**:
   - Extract description fields from YAML entities
   - Call Claude Code API with description + PROCESS.md context
   - Parse Claude Code's structured extraction results
   - Validate against entity index (prevent duplicates)
   - Filter by confidence level (only apply HIGH automatically)
   - Log MEDIUM confidence for manual review

2. **Re-run extraction on app-interface**:
   - Process all service descriptions
   - Track extraction metrics
   - Validate confidence distribution
   - Measure graph density increase

3. **Validate results**:
   - Compare actual vs expected improvements
   - Analyze MEDIUM confidence extractions for false positives
   - Review LOW confidence skips for false negatives
   - Measure query capability improvements

4. **Plan Iteration 6** (potential focus areas):
   - Relationship strength/confidence scoring
   - Temporal analysis (track changes over time)
   - Deployment tracking (link to actual deployed resources)
   - Cross-repository entity linking

---

## Conclusion

Iteration 5 represents a fundamental shift in extraction methodology: from rigid pattern matching to AI-driven natural language understanding. By leveraging Claude Code's ability to reason about context, recognize entities, infer relationships, and assign confidence levels, we unlock a new source of graph data—free-text description fields—that was previously inaccessible to structured extraction.

**Key Achievements**:

1. Comprehensive AI reasoning framework documented in PROCESS.md
2. Confidence-based extraction prevents over-extraction and false positives
3. Entity type classification and relationship pattern recognition
4. Integration with existing two-pass extraction workflow
5. Expected 30-60% increase in graph density
6. 20+ new query patterns enabled

**Why This Matters**:
Description fields in app-interface contain rich contextual information about tools, technologies, teams, infrastructure, and dependencies that is only discoverable through natural language understanding—exactly where AI excels over rigid code patterns.
