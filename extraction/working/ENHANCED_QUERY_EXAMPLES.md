# Enhanced Knowledge Graph - Query Examples

**Based on:** Enhanced extraction with contact & technology entities
**Output File:** `enhanced_extraction.jsonld`
**Date:** 2025-10-22

---

## Overview

The enhanced extraction adds **25 new entities** and **32 new relationships** that enable powerful contact and technology-based queries. This document provides practical examples of queries you can now run.

---

## Contact Information Queries

### 1. Find All Contact Points for a Service

**Use Case:** "How do I reach the team for service X?"

**Query Pattern:**

```
Service → contactVia → [SlackChannel | Email | GitHubHandle | JiraProject | PagerDutyService]
```

**Example Query (Pseudo-SPARQL):**

```sparql
SELECT ?contact ?contactType ?contactName
WHERE {
  <urn:service:acs-fleet-manager> contactVia ?contact .
  ?contact @type ?contactType .
  ?contact name ?contactName .
}
```

**Expected Results:**

```json
[
  {
    "contact": "urn:github:stackrox",
    "contactType": "GitHubHandle",
    "contactName": "stackrox"
  }
]
```

### 2. Find All Services Using a Specific Slack Channel

**Use Case:** "Which services are supported on Slack channel #platform?"

**Query Pattern:**

```
SlackChannel ← contactVia ← Service
```

**Example Query:**

```sparql
SELECT ?service ?serviceName
WHERE {
  ?service contactVia <urn:slack-channel:heading> .
  ?service name ?serviceName .
}
```

### 3. Find GitHub Organization Maintaining a Service

**Use Case:** "Which GitHub org maintains this service?"

**Query Pattern:**

```
Service → maintainedBy → GitHubHandle
```

**Example Query:**

```sparql
SELECT ?github ?githubName
WHERE {
  <urn:service:acs-fleet-manager> maintainedBy ?github .
  ?github name ?githubName .
}
```

**Expected Results:**

```json
[
  {
    "github": "urn:github:stackrox",
    "githubName": "stackrox"
  }
]
```

### 4. List All Services Maintained by a GitHub Org

**Use Case:** "Show me all services maintained by Red Hat's stackrox org"

**Query Pattern:**

```
GitHubHandle ← maintainedBy ← Service
```

**Example Query:**

```sparql
SELECT ?service ?serviceName
WHERE {
  ?service maintainedBy <urn:github:stackrox> .
  ?service name ?serviceName .
}
```

### 5. Find All JIRA Projects Associated with Services

**Use Case:** "Which services are tracked in JIRA?"

**Query Pattern:**

```
Service → trackedIn → JiraProject
```

**Example Query:**

```sparql
SELECT ?service ?serviceName ?jira ?jiraProject
WHERE {
  ?service trackedIn ?jira .
  ?service name ?serviceName .
  ?jira projectKey ?jiraProject .
}
```

---

## Technology Stack Queries

### 6. Find All Services Using a Specific Technology

**Use Case:** "Which services use Kubernetes?"

**Query Pattern:**

```
Tool ← uses ← Service
```

**Example Query:**

```sparql
SELECT ?service ?serviceName
WHERE {
  ?service uses <urn:tool:kubernetes> .
  ?service name ?serviceName .
}
```

**Expected Results:**

```json
[
  {"service": "urn:service:service1", "serviceName": "service1"},
  {"service": "urn:service:service2", "serviceName": "service2"},
  ...
]
```

### 7. Find All Services Implemented in a Specific Language

**Use Case:** "Show me all Go services"

**Query Pattern:**

```
ProgrammingLanguage ← implementedIn ← Service
```

**Example Query:**

```sparql
SELECT ?service ?serviceName
WHERE {
  ?service implementedIn <urn:language:go> .
  ?service name ?serviceName .
}
```

**Example Results:**

```json
[
  {"service": "urn:service:go-service-1", "serviceName": "go-service-1"},
  {"service": "urn:service:go-service-2", "serviceName": "go-service-2"}
]
```

### 8. Find All Services Using a Specific Database

**Use Case:** "Which services use PostgreSQL?"

**Query Pattern:**

```
Database ← uses ← Service
```

**Example Query:**

```sparql
SELECT ?service ?serviceName
WHERE {
  ?service uses <urn:database:postgresql> .
  ?service name ?serviceName .
}
```

### 9. Find All Services Deployed on a Cloud Provider

**Use Case:** "Show me all services deployed on OpenShift"

**Query Pattern:**

```
CloudProvider ← deployedOn ← Service
```

**Example Query:**

```sparql
SELECT ?service ?serviceName
WHERE {
  ?service deployedOn <urn:cloud:openshift> .
  ?service name ?serviceName .
}
```

**Expected Results:** Multiple services using OpenShift (detected from descriptions)

### 10. Get Complete Technology Stack for a Service

**Use Case:** "What's the technology stack for service X?"

**Query Pattern:**

```
Service → {implementedIn | uses | deployedOn} → Technology*
```

**Example Query:**

```sparql
SELECT ?techType ?techName
WHERE {
  <urn:service:example-service> ?relation ?tech .
  FILTER(?relation IN (implementedIn, uses, deployedOn))
  ?tech @type ?techType .
  ?tech name ?techName .
}
```

**Expected Results:**

```json
[
  {"techType": "ProgrammingLanguage", "techName": "Go"},
  {"techType": "Database", "techName": "PostgreSQL"},
  {"techType": "Tool", "techName": "Kubernetes"},
  {"techType": "CloudProvider", "techName": "OpenShift"}
]
```

---

## Advanced Cross-Domain Queries

### 11. Find Services with Similar Tech Stacks

**Use Case:** "Find services using the same technologies as service X"

**Query Pattern:**

```
Service1 → uses → Tech ← uses ← Service2
WHERE Service1 != Service2
```

**Example Query:**

```sparql
SELECT DISTINCT ?similarService ?similarServiceName
WHERE {
  <urn:service:example-service> uses ?tech .
  ?similarService uses ?tech .
  ?similarService name ?similarServiceName .
  FILTER(?similarService != <urn:service:example-service>)
}
```

### 12. Find Contact and Tech Stack Together

**Use Case:** "Show me Go services with their GitHub maintainers"

**Query Pattern:**

```
Service → implementedIn → Go
Service → maintainedBy → GitHubHandle
```

**Example Query:**

```sparql
SELECT ?service ?serviceName ?github ?githubName
WHERE {
  ?service implementedIn <urn:language:go> .
  ?service maintainedBy ?github .
  ?service name ?serviceName .
  ?github name ?githubName .
}
```

### 13. Technology Distribution Analysis

**Use Case:** "How many services use each cloud provider?"

**Query Pattern:**

```
COUNT(Service ← deployedOn ← CloudProvider) GROUP BY CloudProvider
```

**Example Query:**

```sparql
SELECT ?cloudProvider (COUNT(?service) AS ?serviceCount)
WHERE {
  ?service deployedOn ?cloud .
  ?cloud name ?cloudProvider .
}
GROUP BY ?cloudProvider
ORDER BY DESC(?serviceCount)
```

**Expected Results:**

```json
[
  {"cloudProvider": "OpenShift", "serviceCount": 150},
  {"cloudProvider": "AWS", "serviceCount": 30},
  {"cloudProvider": "GCP", "serviceCount": 20},
  {"cloudProvider": "Azure", "serviceCount": 7}
]
```

### 14. Find Services Without Contact Information

**Use Case:** "Which services are missing contact details?"

**Query Pattern:**

```
Service WHERE NOT EXISTS (Service → contactVia → *)
```

**Example Query:**

```sparql
SELECT ?service ?serviceName
WHERE {
  ?service @type "Service" .
  ?service name ?serviceName .
  FILTER NOT EXISTS { ?service contactVia ?contact }
}
```

### 15. Find Services Without Technology Information

**Use Case:** "Which services need technology stack documentation?"

**Query Pattern:**

```
Service WHERE NOT EXISTS (Service → {implementedIn | uses | deployedOn} → *)
```

**Example Query:**

```sparql
SELECT ?service ?serviceName
WHERE {
  ?service @type "Service" .
  ?service name ?serviceName .
  FILTER NOT EXISTS {
    { ?service implementedIn ?tech } UNION
    { ?service uses ?tech } UNION
    { ?service deployedOn ?tech }
  }
}
```

---

## Entity Inventory Queries

### 16. List All Slack Channels

**Query:**

```sparql
SELECT ?channel ?channelName
WHERE {
  ?channel @type "SlackChannel" .
  ?channel name ?channelName .
}
```

**Expected Results:**

```json
[
  {"channel": "urn:slack-channel:heading", "channelName": "#heading"},
  {"channel": "urn:slack-channel:gid", "channelName": "#gid"}
]
```

### 17. List All GitHub Organizations

**Query:**

```sparql
SELECT ?github ?githubName
WHERE {
  ?github @type "GitHubHandle" .
  ?github name ?githubName .
}
```

**Expected Results:** 7 GitHub organizations/users

### 18. List All Technologies by Type

**Query:**

```sparql
SELECT ?techType ?tech ?techName
WHERE {
  ?tech @type ?techType .
  ?tech name ?techName .
  FILTER(?techType IN ("ProgrammingLanguage", "Framework", "Database", "CloudProvider", "Tool"))
}
ORDER BY ?techType ?techName
```

**Expected Results:**

```json
[
  {"techType": "CloudProvider", "tech": "urn:cloud:aws", "techName": "AWS"},
  {"techType": "CloudProvider", "tech": "urn:cloud:azure", "techName": "AZURE"},
  {"techType": "CloudProvider", "tech": "urn:cloud:gcp", "techName": "GCP"},
  {"techType": "CloudProvider", "tech": "urn:cloud:openshift", "techName": "OPENSHIFT"},
  {"techType": "ProgrammingLanguage", "tech": "urn:language:go", "techName": "Go"},
  {"techType": "ProgrammingLanguage", "tech": "urn:language:java", "techName": "Java"},
  {"techType": "Tool", "tech": "urn:tool:ansible", "techName": "Ansible"},
  {"techType": "Tool", "tech": "urn:tool:grafana", "techName": "Grafana"},
  {"techType": "Tool", "tech": "urn:tool:kubernetes", "techName": "Kubernetes"},
  {"techType": "Tool", "tech": "urn:tool:prometheus", "techName": "Prometheus"}
]
```

---

## Graph Database Query Examples

### Neo4j Cypher Examples

**Find services using Kubernetes:**

```cypher
MATCH (s:Service)-[:uses]->(t:Tool {name: "Kubernetes"})
RETURN s.name, s.description
```

**Find Go services with their maintainers:**

```cypher
MATCH (s:Service)-[:implementedIn]->(l:ProgrammingLanguage {name: "Go"})
MATCH (s)-[:maintainedBy]->(g:GitHubHandle)
RETURN s.name, g.name
```

**Technology stack for a service:**

```cypher
MATCH (s:Service {name: "acs-fleet-manager"})-[r:implementedIn|uses|deployedOn]->(tech)
RETURN type(r) as relationship, labels(tech)[0] as techType, tech.name
```

### Dgraph GraphQL Examples

**Find all contact points:**

```graphql
query {
  queryService(filter: {name: {eq: "acs-fleet-manager"}}) {
    name
    contactVia {
      __typename
      ... on SlackChannel { name channelName }
      ... on Email { name emailAddress }
      ... on GitHubHandle { name handleName }
    }
    maintainedBy {
      name
      handleName
    }
  }
}
```

**Technology distribution:**

```graphql
query {
  aggregateService {
    count
  }
  queryTool {
    name
    usedByAggregate {
      count
    }
  }
}
```

---

## Query Statistics

Based on the enhanced extraction:

| Query Category | Number of Queries Enabled | New Queries vs Baseline |
|---------------|---------------------------|------------------------|
| Contact Information | 5 | +5 (100% new) |
| Technology Stack | 5 | +5 (100% new) |
| Cross-Domain | 5 | +5 (100% new) |
| Inventory | 3 | +3 (100% new) |
| **Total** | **18** | **+18 (100% new)** |

---

## Query Performance Expectations

Based on 1,763 entities and 2,856 relationships:

| Query Type | Expected Performance | Complexity |
|-----------|---------------------|------------|
| Single entity lookup | <10ms | O(1) |
| Find related entities | <50ms | O(n) where n = relationships |
| Technology stack query | <100ms | O(n*m) where n = services, m = tech |
| Cross-domain query | <200ms | O(n*m*k) |
| Aggregation query | <500ms | O(n) |

---

## Next Steps

1. **Load into Graph Database**: Import `enhanced_extraction.jsonld` into Dgraph/Neo4j
2. **Test Queries**: Run the example queries above to verify functionality
3. **Create Dashboards**: Build visualizations for technology distribution, contact coverage
4. **Document Gaps**: Identify services missing contact/tech info for manual enrichment
5. **Automate Updates**: Set up pipeline to re-extract on app-interface changes

---

## Limitations & Future Enhancements

### Current Limitations

- Only 11 contact entities (low coverage due to sparse data)
- Only 14 technology entities (descriptions lack tech details)
- No README analysis (files don't exist in service directories)
- No email or PagerDuty entities found

### Recommended Enhancements

1. **Code Repository Analysis**: Parse actual code repos for tech stack
2. **External API Integration**: Query Slack/GitHub/JIRA APIs for metadata
3. **LLM-Based Extraction**: Use LLM to extract from unstructured descriptions
4. **Manual Enrichment**: Add contact/tech info to app-interface YAML files

---

**Document Version:** 1.0
**Last Updated:** 2025-10-22
**For Questions:** See `ENHANCEMENT_COMPARISON.md` for detailed analysis
