# Entity Type Discovery Report

**Data Source**: app-interface repository
**Domain**: Infrastructure Configuration Management
**Sample Size**: 12 service YAML files analyzed
**Discovery Method**: General Entity Type Discovery Framework (5-step process)

---

## Discovered Entity Types

### Type 1: CodeRepository

**Pattern Type**: identifier
**Pattern**: Repository URL from gitlab: <https://domain/org/repo>

**Examples**:

- `https://gitlab.cee.redhat.com/service/app-interface/-/tree/master/docs/app-sre/sop`
- `https://github.com/app-sre/container-images/tree/master/debug-container-fedramp`
- `https://github.com/app-sre/container-images/tree/master/debug-container`
- `https://gitlab.cee.redhat.com/dtsd/housekeeping`
- `https://gitlab.cee.redhat.com/dtsd/saas-crypt`

**Field Contexts**:

- `sopsUrl`
- `quayRepos.items.description`
- `codeComponents[].url`
- `codeComponents.url`
- `architectureDocument`

**URN Pattern**: `urn:code-repository:{platform}:{org}:{repo}`
**Queryability**: Find repos by org, Find services using repo X, Map code to services
**Confidence**: HIGH (95.0%)
**Instances Found**: 179

**Discovery Reasoning**:
URL pattern + domain knowledge (gitlab) + field semantics (codeComponents/url)

---

### Type 2: MonitoringDashboard

**Pattern Type**: identifier
**Pattern**: Grafana monitoring dashboard URL from field 'url'

**Examples**:

- `https://grafana.app-sre.devshift.net/d/xNTPSl-Vk/appsre-overview`
- `https://grafana.app-sre.devshift.net/d/D1C839d82/acs-fleet-manager`
- `https://grafana.app-sre.devshift.net/d/T2kek3H9a/acs-fleet-manager-slos?orgId=1`
- `https://grafana.app-sre.devshift.net/d/Integrations/integrations?orgId=1`

**Field Contexts**:

- `grafanaUrls.url`

**URN Pattern**: `urn:monitoring-dashboard:{tool}:{dashboard-id}`
**Queryability**: Find dashboards for service X, Which services use Grafana, Show monitoring coverage
**Confidence**: HIGH (90.0%)
**Instances Found**: 5

**Discovery Reasoning**:
URL pattern + grafana domain + field semantics (grafanaUrls)

---

### Type 3: EmailAddress

**Pattern Type**: identifier
**Pattern**: Email format: user@domain from field 'email'

**Examples**:

- `sd-app-sre@redhat.com`
- `sd-app-sre+ft-4@redhat.com`
- `rhacs-eng-ms@redhat.com`
- `apahim@redhat.com`
- `jgwosdz@redhat.com`

**Field Contexts**:

- `serviceOwners[].email`
- `serviceOwners.email`

**URN Pattern**: `urn:email-address:{normalized-email}`
**Queryability**: Find all services owned by email X, Show contacts for service, List team responsibilities
**Confidence**: HIGH (90.0%)
**Instances Found**: 26

**Discovery Reasoning**:
Pattern recognition: email format (@) + field semantics (email/contact)

---

### Type 4: ServiceEndpoint

**Pattern Type**: identifier
**Pattern**: Service endpoint URL from field 'architectureDocument'

**Examples**:

- `https://service.pages.redhat.com/dev-guidelines/docs/appsre`
- `tkn-cli-serve-openshift-pipelines.apps.app-sre-stage-0.k3s7.p1.openshiftapps.com:443`
- `pipelines-as-code-controller-openshift-pipelines.apps.app-sre-stage-0.k3s7.p1.openshiftapps.com:443`
- `pipelines-as-code-controller-openshift-pipelines.apps.rosa.appsres09ue1.24ep.p3.openshiftapps.com:443`
- `tkn-cli-serve-openshift-pipelines.apps.rosa.appsres09ue1.24ep.p3.openshiftapps.com:443`

**Field Contexts**:

- `architectureDocument`
- `endPoints.url`
- `sopsUrl`
- `codeComponents.imageBuildUrl`

**URN Pattern**: `urn:service-endpoint:{normalized-url}`
**Queryability**: Find endpoints for service X, Show all monitored endpoints, Map endpoints to services
**Confidence**: HIGH (85.0%)
**Instances Found**: 49

**Discovery Reasoning**:
URL/host:port pattern + field semantics (endPoints/url)

---

### Type 5: DocumentationResource

**Pattern Type**: identifier
**Pattern**: Documentation URL from field 'architectureDocument'

**Examples**:

- `https://TODO`
- `https://TBD`

**Field Contexts**:

- `architectureDocument`
- `sopsUrl`

**URN Pattern**: `urn:documentation:{hash}`
**Queryability**: Find docs for service X, Show architecture documents
**Confidence**: MEDIUM (80.0%)
**Instances Found**: 5

**Discovery Reasoning**:
URL pattern + field semantics (document/docs/sop/architecture)

---

### Type 6: DependencyReference

**Pattern Type**: structural
**Pattern**: Dependency reference from field 'dependencies'

**Examples**:

- `/dependencies/aws/service.yml`
- `/dependencies/ci-ext/service.yml`
- `/dependencies/quay/service.yml`
- `/dependencies/ci-int/service.yml`
- `/dependencies/github/service.yml`

**Field Contexts**:

- `dependencies`

**URN Pattern**: ``
**Queryability**:
**Confidence**: MEDIUM (75.0%)
**Instances Found**: 11

**Discovery Reasoning**:
Structural pattern: $ref reference + dependencies context

---

## Discovery Statistics

- Total unique entity types discovered: 6
- Entity types (HIGH confidence >= 85%): 4
- Entity types (MEDIUM confidence 60-85%): 2
- Total pattern instances found: 275
