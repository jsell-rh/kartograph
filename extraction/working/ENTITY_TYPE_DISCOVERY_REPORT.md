# Entity Type Discovery Report

**Data Source**: app-interface repository
**Domain**: Infrastructure Configuration / Platform Operations
**Sample Size**: 7 files analyzed

## Discovered Entity Types

### Application

**Pattern**: Service/application definitions

**URN Pattern**: `urn:app:{name}`

**Confidence**: 98%

**Field Patterns**: $schema:/app-sre/app-1.yml

**Queryability**:

- List all apps
- App dependencies
- Ownership

### OpenshiftNamespace

**Pattern**: Kubernetes/OpenShift namespace configurations

**URN Pattern**: `urn:openshift-namespace:{cluster}:{name}`

**Confidence**: 95%

**Field Patterns**: $schema:/openshift/namespace-1.yml

**Queryability**:

- Find namespaces by cluster
- Resource isolation

### User

**Pattern**: User accounts with org/GitHub/Quay usernames

**URN Pattern**: `urn:user:{org_username}`

**Confidence**: 95%

**Field Patterns**: $schema:/access/user-1.yml, org_username

**Queryability**:

- Find users by team
- User permissions

### Environment

**Pattern**: Deployment environments (prod, stage, integration)

**URN Pattern**: `urn:environment:{product}:{name}`

**Confidence**: 93%

**Field Patterns**: $schema:/app-sre/environment-1.yml, servicePhase

**Queryability**:

- Find envs by product
- Deployment topology

### SaaSDeployment

**Pattern**: SaaS file tracking deployments

**URN Pattern**: `urn:saas-deployment:{name}`

**Confidence**: 92%

**Field Patterns**: $schema:/app-sre/saas-file-2.yml, resourceTemplates

**Queryability**:

- Find deployments
- Promotion paths

### SLODocument

**Pattern**: Service Level Objective definitions

**URN Pattern**: `urn:slo-document:{service}`

**Confidence**: 90%

**Field Patterns**: $schema:/app-sre/slo-document-1.yml, slos

**Queryability**:

- Find SLOs by service
- Availability targets

### JenkinsConfig

**Pattern**: CI/CD pipeline configurations

**URN Pattern**: `urn:jenkins-config:{name}`

**Confidence**: 88%

**Field Patterns**: $schema:/dependencies/jenkins-config-1.yml

**Queryability**:

- Find CI configs
- Build pipelines

## Discovery Statistics

- Total patterns discovered: 7
- HIGH confidence (>85%): 7
- MEDIUM confidence (60-85%): 0
- LOW confidence (<60%): 0
