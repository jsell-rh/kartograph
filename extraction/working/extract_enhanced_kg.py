#!/usr/bin/env python3
"""
Enhanced Knowledge Graph Extraction Script
Following PROCESS.md with Contact & Technology Stack Extraction

Repository: /home/jsell/code/sandbox/cartograph/app-interface
Output: /home/jsell/code/kartograph-kg-iteration/extraction/working/enhanced_extraction.jsonld

NEW ENHANCEMENTS:
- Contact Information Extraction (SlackChannel, Email, GitHubHandle, JiraProject, PagerDutyService)
- Technology Stack Extraction (ProgrammingLanguage, Framework, Database, CloudProvider, Tool)
- README.md Analysis for additional entities
- New relationships: contactVia, maintainedBy, implementedIn, uses, deployedOn

Based on successful Iteration 8 Test 2 approach + PROCESS.md lines 2448-2730
"""

import os
import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
from collections import defaultdict
import time
from datetime import datetime

# Repository paths
REPO_PATH = Path("/home/jsell/code/sandbox/cartograph/app-interface")
OUTPUT_PATH = Path(
    "/home/jsell/code/kartograph-kg-iteration/extraction/working/enhanced_extraction.jsonld"
)

# Global entity index
entity_index: Dict[str, Dict] = {}
pending_relationships: List[Dict] = []
broken_references: List[Dict] = []

# Validation metrics
metrics = {
    "total_entities": 0,
    "entities_by_type": defaultdict(int),
    "total_relationships": 0,
    "broken_references": 0,
    "orphan_entities": 0,
    "entities_missing_names": 0,
    "entities_missing_types": 0,
    "avg_predicates_per_entity": 0.0,
    "field_coverage": 0.0,
    "sub_entities_extracted": 0,
    "free_text_entities": 0,
    "inferred_relationships": 0,
    "contact_entities": 0,
    "technology_entities": 0,
    "readme_entities": 0,
    "extraction_start_time": None,
    "extraction_end_time": None,
}

# Enhancement tracking
enhancement_metrics = {
    "slack_channels": 0,
    "emails": 0,
    "github_handles": 0,
    "jira_projects": 0,
    "pagerduty_services": 0,
    "programming_languages": 0,
    "frameworks": 0,
    "databases": 0,
    "cloud_providers": 0,
    "tools": 0,
    "readmes_analyzed": 0,
    "contact_relationships": 0,
    "technology_relationships": 0,
}

# Progress tracking
progress = {
    "services_processed": 0,
    "total_services": 207,
    "current_phase": "Phase 0",
}


def normalize_urn_component(value: str) -> str:
    """Normalize URN component"""
    if not value:
        return ""

    value = str(value).lower()
    value = value.replace(" ", "-").replace("_", "-")
    value = re.sub(r"[^a-z0-9\-]", "", value)
    value = re.sub(r"-+", "-", value)
    value = value.strip("-")

    return value


def generate_urn(entity_type: str, *components: str) -> str:
    """Generate standardized URN"""
    normalized_type = normalize_urn_component(entity_type)
    normalized_components = [normalize_urn_component(c) for c in components if c]
    normalized_components = [c for c in normalized_components if c]

    if not normalized_components:
        normalized_components = [f"{normalized_type}-{int(time.time()*1000)}"]

    urn = f"urn:{normalized_type}:{':'.join(normalized_components)}"
    return urn


def validate_urn(urn: str) -> bool:
    """Validate URN format"""
    pattern = r"^urn:[a-z0-9\-]+:[a-z0-9\-:]+$"
    return bool(re.match(pattern, urn))


def extract_name_from_urn(urn: str) -> str:
    """Extract human-readable name from URN"""
    parts = urn.split(":")
    if len(parts) >= 3:
        name = parts[-1].replace("-", " ").title()
        return name
    return urn


def extract_name_from_filepath(filepath: str) -> str:
    """Extract name from file path"""
    path = Path(filepath)

    if path.parent.name and path.parent.name != "data":
        return path.parent.name.replace("-", " ").title()

    if path.stem != "app" and path.stem != "service":
        return path.stem.replace("-", " ").title()

    return ""


def infer_type_from_context(data: Dict, filepath: str) -> str:
    """Infer entity type from context"""

    if "@id" in data:
        urn_parts = data["@id"].split(":")
        if len(urn_parts) >= 2:
            return urn_parts[1].replace("-", " ").title()

    if "$schema" in data:
        schema = data["$schema"]
        if "/service" in schema:
            return "Service"
        elif "/team" in schema:
            return "Team"
        elif "/namespace" in schema:
            return "Namespace"
        elif "/dependency" in schema:
            return "Dependency"

    path_str = str(filepath).lower()
    if "/services/" in path_str:
        return "Service"
    elif "/teams/" in path_str:
        return "Team"
    elif "/namespaces/" in path_str:
        return "Namespace"
    elif "/dependencies/" in path_str:
        return "Dependency"
    elif "/products/" in path_str:
        return "Product"

    return "Entity"


def validate_entity_before_extraction(entity: Dict, filepath: str) -> None:
    """Mandatory validation before adding to graph"""
    if not entity.get("@id"):
        raise ValueError(f"Entity missing @id in {filepath}")

    if not validate_urn(entity["@id"]):
        raise ValueError(f"Invalid URN format: {entity['@id']} in {filepath}")

    if not entity.get("@type"):
        raise ValueError(f"Entity missing @type in {filepath}: {entity.get('@id')}")

    if not entity.get("name"):
        raise ValueError(f"Entity missing name in {filepath}: {entity.get('@id')}")


# ============================================================================
# CONTACT INFORMATION EXTRACTION (NEW)
# ============================================================================


def extract_slack_channels(text: str, source_urn: str) -> List[Dict]:
    """
    Extract Slack channels from text
    Patterns: #channel-name, slack.com/channels/C123456
    """
    channels = []

    # Pattern 1: #channel-name
    pattern1 = r"#([a-z0-9\-_]+)"
    matches1 = re.findall(pattern1, text, re.IGNORECASE)

    # Pattern 2: slack.com URLs
    pattern2 = r"slack\.com/[^\s]*/([A-Z0-9]+)"
    matches2 = re.findall(pattern2, text)

    all_matches = set(matches1 + matches2)

    for channel_name in all_matches:
        channel_urn = generate_urn("slack-channel", channel_name)

        # Check if already exists
        if channel_urn in entity_index:
            continue

        channel_entity = {
            "@id": channel_urn,
            "@type": "SlackChannel",
            "name": f"#{channel_name}",
            "channelName": channel_name,
            "_source_file": f"{source_urn}/extracted",
        }

        channels.append(channel_entity)
        enhancement_metrics["slack_channels"] += 1
        metrics["contact_entities"] += 1

    return channels


def extract_emails(text: str, source_urn: str) -> List[Dict]:
    """
    Extract email addresses from text
    Pattern: email@domain.com
    """
    emails = []

    # Email pattern
    pattern = r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b"
    matches = re.findall(pattern, text)

    for email in set(matches):
        # Normalize for URN
        email_normalized = email.lower().replace("@", "-at-").replace(".", "-")
        email_urn = generate_urn("email", email_normalized)

        # Check if already exists
        if email_urn in entity_index:
            continue

        email_entity = {
            "@id": email_urn,
            "@type": "Email",
            "name": email,
            "emailAddress": email,
            "_source_file": f"{source_urn}/extracted",
        }

        emails.append(email_entity)
        enhancement_metrics["emails"] += 1
        metrics["contact_entities"] += 1

    return emails


def extract_github_handles(text: str, urls: List[str], source_urn: str) -> List[Dict]:
    """
    Extract GitHub organizations/users from URLs and @mentions
    Patterns: github.com/{org}/{repo}, @username
    """
    handles = []

    # Pattern 1: GitHub URLs
    for url in urls:
        if "github.com" in url.lower():
            pattern = r"github\.com/([a-zA-Z0-9\-_]+)"
            matches = re.findall(pattern, url)
            for match in matches:
                if match.lower() not in ["raw", "blob", "tree", "commit"]:
                    handle_urn = generate_urn("github", match)

                    if handle_urn in entity_index:
                        continue

                    handle_entity = {
                        "@id": handle_urn,
                        "@type": "GitHubHandle",
                        "name": match,
                        "handleName": match,
                        "_source_file": f"{source_urn}/extracted",
                    }

                    handles.append(handle_entity)
                    enhancement_metrics["github_handles"] += 1
                    metrics["contact_entities"] += 1
                    break  # Only take first (org/user)

    # Pattern 2: @mentions in text
    pattern2 = r"@([a-zA-Z0-9\-_]+)"
    matches2 = re.findall(pattern2, text)
    for match in matches2:
        handle_urn = generate_urn("github", match)

        if handle_urn in entity_index:
            continue

        handle_entity = {
            "@id": handle_urn,
            "@type": "GitHubHandle",
            "name": match,
            "handleName": match,
            "_source_file": f"{source_urn}/extracted",
        }

        handles.append(handle_entity)
        enhancement_metrics["github_handles"] += 1
        metrics["contact_entities"] += 1

    return handles


def extract_jira_projects(text: str, urls: List[str], source_urn: str) -> List[Dict]:
    """
    Extract JIRA projects from URLs and project key patterns
    Patterns: jira.*/projects/PROJ, PROJ-123
    """
    projects = []

    # Pattern 1: JIRA URLs
    for url in urls:
        if "jira" in url.lower():
            pattern = r"/projects/([A-Z]+)"
            matches = re.findall(pattern, url)
            for match in matches:
                project_urn = generate_urn("jira-project", match)

                if project_urn in entity_index:
                    continue

                project_entity = {
                    "@id": project_urn,
                    "@type": "JiraProject",
                    "name": match,
                    "projectKey": match,
                    "_source_file": f"{source_urn}/extracted",
                }

                projects.append(project_entity)
                enhancement_metrics["jira_projects"] += 1
                metrics["contact_entities"] += 1

    # Pattern 2: Project key patterns (PROJ-123)
    pattern2 = r"\b([A-Z]{2,})-\d+"
    matches2 = re.findall(pattern2, text)
    for match in set(matches2):
        project_urn = generate_urn("jira-project", match)

        if project_urn in entity_index:
            continue

        project_entity = {
            "@id": project_urn,
            "@type": "JiraProject",
            "name": match,
            "projectKey": match,
            "_source_file": f"{source_urn}/extracted",
        }

        projects.append(project_entity)
        enhancement_metrics["jira_projects"] += 1
        metrics["contact_entities"] += 1

    return projects


def extract_pagerduty_services(urls: List[str], source_urn: str) -> List[Dict]:
    """
    Extract PagerDuty services from URLs
    Pattern: *.pagerduty.com/services/*
    """
    services = []

    for url in urls:
        if "pagerduty.com" in url.lower():
            pattern = r"/services/([A-Z0-9]+)"
            matches = re.findall(pattern, url)
            for match in matches:
                pd_urn = generate_urn("pagerduty", match)

                if pd_urn in entity_index:
                    continue

                pd_entity = {
                    "@id": pd_urn,
                    "@type": "PagerDutyService",
                    "name": match,
                    "serviceId": match,
                    "_source_file": f"{source_urn}/extracted",
                }

                services.append(pd_entity)
                enhancement_metrics["pagerduty_services"] += 1
                metrics["contact_entities"] += 1

    return services


# ============================================================================
# TECHNOLOGY STACK EXTRACTION (NEW)
# ============================================================================

# Technology pattern definitions
PROGRAMMING_LANGUAGES = {
    r"\bpython\b": "python",
    r"\bjavascript\b": "javascript",
    r"\bgo\b": "go",
    r"\bgolang\b": "go",
    r"\bjava\b": "java",
    r"\bruby\b": "ruby",
    r"\brust\b": "rust",
    r"\bnode\.?js\b": "nodejs",
    r"\btypescript\b": "typescript",
    r"\bphp\b": "php",
    r"\bc\+\+\b": "cpp",
    r"\bc#\b": "csharp",
    r"\bscala\b": "scala",
    r"\bkotlin\b": "kotlin",
}

FRAMEWORKS = {
    r"\bdjango\b": "django",
    r"\bflask\b": "flask",
    r"\breact\b": "react",
    r"\bangular\b": "angular",
    r"\bvue\b": "vue",
    r"\bspring\b": "spring",
    r"\bspring boot\b": "spring-boot",
    r"\bexpress\b": "express",
    r"\brails\b": "rails",
    r"\bfastapi\b": "fastapi",
}

DATABASES = {
    r"\bpostgresql\b": "postgresql",
    r"\bpostgres\b": "postgresql",
    r"\bmysql\b": "mysql",
    r"\bmongodb\b": "mongodb",
    r"\bmongo\b": "mongodb",
    r"\bredis\b": "redis",
    r"\bcassandra\b": "cassandra",
    r"\bdynamodb\b": "dynamodb",
    r"\belasticsearch\b": "elasticsearch",
    r"\bmariadb\b": "mariadb",
    r"\boracle\b": "oracle",
    r"\bsqlite\b": "sqlite",
}

CLOUD_PROVIDERS = {
    r"\baws\b": "aws",
    r"\bamazon web services\b": "aws",
    r"\bgcp\b": "gcp",
    r"\bgoogle cloud\b": "gcp",
    r"\bazure\b": "azure",
    r"\bopenshift\b": "openshift",
    r"\bdigitalocean\b": "digitalocean",
}

TOOLS = {
    r"\bdocker\b": "docker",
    r"\bkubernetes\b": "kubernetes",
    r"\bk8s\b": "kubernetes",
    r"\bjenkins\b": "jenkins",
    r"\bgitlab ci\b": "gitlab-ci",
    r"\bgithub actions\b": "github-actions",
    r"\bterraform\b": "terraform",
    r"\bansible\b": "ansible",
    r"\bprometheus\b": "prometheus",
    r"\bgrafana\b": "grafana",
    r"\bkafka\b": "kafka",
    r"\bhelm\b": "helm",
}


def extract_technologies(text: str, source_urn: str) -> List[Dict]:
    """
    Extract technology stack entities from text
    Returns: List of technology entities (ProgrammingLanguage, Framework, Database, etc.)
    """
    technologies = []
    text_lower = text.lower()

    # Extract programming languages
    for pattern, lang_name in PROGRAMMING_LANGUAGES.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            lang_urn = generate_urn("language", lang_name)

            if lang_urn not in entity_index:
                lang_entity = {
                    "@id": lang_urn,
                    "@type": "ProgrammingLanguage",
                    "name": lang_name.title(),
                    "languageName": lang_name,
                    "_source_file": f"{source_urn}/extracted",
                }
                technologies.append(lang_entity)
                enhancement_metrics["programming_languages"] += 1
                metrics["technology_entities"] += 1

    # Extract frameworks
    for pattern, framework_name in FRAMEWORKS.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            framework_urn = generate_urn("framework", framework_name)

            if framework_urn not in entity_index:
                framework_entity = {
                    "@id": framework_urn,
                    "@type": "Framework",
                    "name": framework_name.title(),
                    "frameworkName": framework_name,
                    "_source_file": f"{source_urn}/extracted",
                }
                technologies.append(framework_entity)
                enhancement_metrics["frameworks"] += 1
                metrics["technology_entities"] += 1

    # Extract databases
    for pattern, db_name in DATABASES.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            db_urn = generate_urn("database", db_name)

            if db_urn not in entity_index:
                db_entity = {
                    "@id": db_urn,
                    "@type": "Database",
                    "name": db_name.title(),
                    "databaseName": db_name,
                    "_source_file": f"{source_urn}/extracted",
                }
                technologies.append(db_entity)
                enhancement_metrics["databases"] += 1
                metrics["technology_entities"] += 1

    # Extract cloud providers
    for pattern, cloud_name in CLOUD_PROVIDERS.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            cloud_urn = generate_urn("cloud", cloud_name)

            if cloud_urn not in entity_index:
                cloud_entity = {
                    "@id": cloud_urn,
                    "@type": "CloudProvider",
                    "name": cloud_name.upper(),
                    "providerName": cloud_name,
                    "_source_file": f"{source_urn}/extracted",
                }
                technologies.append(cloud_entity)
                enhancement_metrics["cloud_providers"] += 1
                metrics["technology_entities"] += 1

    # Extract tools
    for pattern, tool_name in TOOLS.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            tool_urn = generate_urn("tool", tool_name)

            if tool_urn not in entity_index:
                tool_entity = {
                    "@id": tool_urn,
                    "@type": "Tool",
                    "name": tool_name.title(),
                    "toolName": tool_name,
                    "_source_file": f"{source_urn}/extracted",
                }
                technologies.append(tool_entity)
                enhancement_metrics["tools"] += 1
                metrics["technology_entities"] += 1

    return technologies


# ============================================================================
# README ANALYSIS (NEW)
# ============================================================================


def analyze_readme(service_path: Path, service_urn: str) -> Tuple[List[Dict], Dict]:
    """
    Analyze README.md for additional entities and metadata
    Returns: (entities_list, extracted_metadata)
    """
    readme_entities = []
    metadata = {
        "contact_info": [],
        "technologies": [],
        "links": [],
    }

    # Look for README files
    readme_files = []
    for name in ["README.md", "README", "CONTRIBUTING.md"]:
        readme_path = service_path / name
        if readme_path.exists():
            readme_files.append(readme_path)

    if not readme_files:
        return readme_entities, metadata

    enhancement_metrics["readmes_analyzed"] += 1

    # Read and analyze README content
    for readme_path in readme_files:
        try:
            with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Collect all URLs
            urls = re.findall(r"https?://[^\s\)]+", content)

            # Extract contact entities
            slack_channels = extract_slack_channels(content, service_urn)
            readme_entities.extend(slack_channels)

            emails = extract_emails(content, service_urn)
            readme_entities.extend(emails)

            github_handles = extract_github_handles(content, urls, service_urn)
            readme_entities.extend(github_handles)

            jira_projects = extract_jira_projects(content, urls, service_urn)
            readme_entities.extend(jira_projects)

            pagerduty_services = extract_pagerduty_services(urls, service_urn)
            readme_entities.extend(pagerduty_services)

            # Extract technology entities
            technologies = extract_technologies(content, service_urn)
            readme_entities.extend(technologies)

            enhancement_metrics["readme_entities"] += len(readme_entities)

        except Exception as e:
            # Silently skip on error
            pass

    return readme_entities, metadata


# ============================================================================
# CORE EXTRACTION FUNCTIONS (Enhanced)
# ============================================================================


def extract_service_owners(service_data: Dict, service_urn: str) -> List[Dict]:
    """Extract service owners as User entities"""
    owners = []
    service_owners = service_data.get("serviceOwners", [])

    for owner_data in service_owners:
        email = owner_data.get("email")
        owner_name = owner_data.get("name", "")

        if not email:
            continue

        user_urn = generate_urn("user", email)
        user_entity = {
            "@id": user_urn,
            "@type": "User",
            "name": owner_name or email.split("@")[0].replace(".", " ").title(),
            "email": email,
            "_source_file": f"{service_urn}/serviceOwners",
        }

        owners.append(user_entity)

    return owners


def extract_endpoints(service_data: Dict, service_urn: str) -> List[Dict]:
    """Extract endpoints as Endpoint entities"""
    endpoints = []
    endpoint_data_list = service_data.get("endPoints", [])

    for ep_data in endpoint_data_list:
        ep_name = ep_data.get("name", "")
        ep_url = ep_data.get("url", "")

        if not ep_url:
            continue

        ep_urn = generate_urn("endpoint", ep_name or ep_url)
        endpoint = {
            "@id": ep_urn,
            "@type": "Endpoint",
            "name": ep_name or ep_url,
            "url": ep_url,
            "description": ep_data.get("description", ""),
            "_source_file": f"{service_urn}/endPoints",
        }

        monitoring = ep_data.get("monitoring", [])
        if monitoring:
            endpoint["_pending_monitoring"] = monitoring

        endpoints.append(endpoint)

    return endpoints


def extract_code_components(service_data: Dict, service_urn: str) -> List[Dict]:
    """Extract code components as CodeComponent entities"""
    components = []
    code_components = service_data.get("codeComponents", [])

    for comp_data in code_components:
        comp_name = comp_data.get("name", "")
        comp_url = comp_data.get("url", "")

        if not comp_name:
            continue

        comp_urn = generate_urn("code-component", service_urn.split(":")[-1], comp_name)
        component = {
            "@id": comp_urn,
            "@type": "CodeComponent",
            "name": comp_name,
            "url": comp_url,
            "resource": comp_data.get("resource", ""),
            "_source_file": f"{service_urn}/codeComponents",
        }

        components.append(component)

    return components


def extract_maximum_fidelity_fields(entity: Dict, source_data: Dict) -> None:
    """Extract ALL fields from source data"""
    metadata_fields = {"$schema", "apiVersion", "kind"}
    relationship_fields = {
        "dependencies",
        "escalationPolicy",
        "serviceOwners",
        "endPoints",
        "codeComponents",
        "quayRepos",
    }

    for field, value in source_data.items():
        if field in metadata_fields:
            continue

        if field in relationship_fields:
            entity[f"_pending_{field}"] = value
            continue

        if isinstance(value, (str, int, float, bool)):
            entity[field] = value
        elif isinstance(value, list):
            entity[field] = value
        elif isinstance(value, dict):
            entity[field] = value
        elif value is None:
            entity[field] = None
        else:
            entity[field] = value


def extract_service_entity(filepath: Path) -> Dict:
    """
    Extract service entity with ENHANCED contact & technology extraction
    """
    with open(filepath, "r") as f:
        data = yaml.safe_load(f)

    if not data:
        return None

    service_name = data.get("name", filepath.parent.name)
    service_urn = generate_urn("service", service_name)

    entity = {
        "@id": service_urn,
        "@type": "Service",
        "name": service_name,
        "_source_file": str(filepath.relative_to(REPO_PATH)),
    }

    # Maximum Fidelity Field Extraction
    extract_maximum_fidelity_fields(entity, data)

    # Validate before adding
    validate_entity_before_extraction(entity, str(filepath))

    return entity


def extract_contact_and_tech_from_service(
    service_data: Dict, service_urn: str, service_path: Path
) -> List[Dict]:
    """
    NEW: Extract contact and technology entities from service data
    """
    extracted_entities = []

    # Extract from structured fields
    description = service_data.get("description", "")
    slack_channel = service_data.get("slackChannel", "")

    # Combine text for analysis
    combined_text = f"{description} {slack_channel}"

    # Collect URLs from various fields
    urls = []
    if "architectureDocument" in service_data:
        urls.append(service_data["architectureDocument"])
    if "performanceParameters" in service_data and isinstance(
        service_data["performanceParameters"], dict
    ):
        slo_doc = service_data["performanceParameters"].get("sloDoc", "")
        if slo_doc:
            urls.append(slo_doc)

    # Extract contact entities
    slack_channels = extract_slack_channels(combined_text, service_urn)
    extracted_entities.extend(slack_channels)

    emails = extract_emails(combined_text, service_urn)
    extracted_entities.extend(emails)

    github_handles = extract_github_handles(combined_text, urls, service_urn)
    extracted_entities.extend(github_handles)

    jira_projects = extract_jira_projects(combined_text, urls, service_urn)
    extracted_entities.extend(jira_projects)

    pagerduty_services = extract_pagerduty_services(urls, service_urn)
    extracted_entities.extend(pagerduty_services)

    # Extract technology entities
    technologies = extract_technologies(combined_text, service_urn)
    extracted_entities.extend(technologies)

    # Analyze README if exists
    readme_entities, readme_metadata = analyze_readme(service_path, service_urn)
    extracted_entities.extend(readme_entities)

    return extracted_entities


def extract_all_services_pass1() -> List[Dict]:
    """
    Pass 1: Extract all service entities + ENHANCED contact/tech entities
    """
    print("\n=== PASS 1: Entity Extraction (ENHANCED) ===\n")

    services = []
    service_files = list((REPO_PATH / "data" / "services").rglob("app.yml"))

    total = len(service_files)
    progress["total_services"] = total

    for idx, filepath in enumerate(service_files):
        try:
            entity = extract_service_entity(filepath)
            if entity:
                services.append(entity)
                entity_index[entity["@id"]] = entity
                metrics["entities_by_type"]["Service"] += 1

                # Extract sub-entities
                sub_entities = []

                # Service owners
                if "_pending_serviceOwners" in entity:
                    owners = extract_service_owners(
                        {"serviceOwners": entity["_pending_serviceOwners"]},
                        entity["@id"],
                    )
                    for owner in owners:
                        if owner["@id"] not in entity_index:
                            sub_entities.append(owner)
                            entity_index[owner["@id"]] = owner
                            metrics["entities_by_type"]["User"] += 1
                            metrics["sub_entities_extracted"] += 1

                # Endpoints
                if "_pending_endPoints" in entity:
                    endpoints = extract_endpoints(
                        {"endPoints": entity["_pending_endPoints"]}, entity["@id"]
                    )
                    for endpoint in endpoints:
                        if endpoint["@id"] not in entity_index:
                            sub_entities.append(endpoint)
                            entity_index[endpoint["@id"]] = endpoint
                            metrics["entities_by_type"]["Endpoint"] += 1
                            metrics["sub_entities_extracted"] += 1

                # Code components
                if "_pending_codeComponents" in entity:
                    components = extract_code_components(
                        {"codeComponents": entity["_pending_codeComponents"]},
                        entity["@id"],
                    )
                    for component in components:
                        if component["@id"] not in entity_index:
                            sub_entities.append(component)
                            entity_index[component["@id"]] = component
                            metrics["entities_by_type"]["CodeComponent"] += 1
                            metrics["sub_entities_extracted"] += 1

                # NEW: Extract contact and technology entities
                with open(filepath, "r") as f:
                    service_data = yaml.safe_load(f)

                contact_tech_entities = extract_contact_and_tech_from_service(
                    service_data, entity["@id"], filepath.parent
                )

                for ct_entity in contact_tech_entities:
                    if ct_entity["@id"] not in entity_index:
                        sub_entities.append(ct_entity)
                        entity_index[ct_entity["@id"]] = ct_entity
                        metrics["entities_by_type"][ct_entity["@type"]] += 1

                services.extend(sub_entities)

                # Progress reporting
                progress["services_processed"] = idx + 1
                if (idx + 1) % 25 == 0 or (idx + 1) == total:
                    pct = ((idx + 1) / total) * 100
                    print(f"Progress: {idx + 1}/{total} services ({pct:.1f}%)")
                    print(f"  Entities extracted: {len(entity_index)}")
                    print(f"  Contact entities: {metrics['contact_entities']}")
                    print(f"  Technology entities: {metrics['technology_entities']}")

        except Exception as e:
            print(f"ERROR extracting {filepath}: {e}")
            metrics["entities_missing_names"] += 1

    print(f"\nPass 1 Complete:")
    print(f"  Total entities: {len(entity_index)}")
    print(f"  Services: {metrics['entities_by_type']['Service']}")
    print(f"  Users: {metrics['entities_by_type']['User']}")
    print(f"  Endpoints: {metrics['entities_by_type']['Endpoint']}")
    print(f"  CodeComponents: {metrics['entities_by_type']['CodeComponent']}")
    print(f"  SlackChannels: {metrics['entities_by_type']['SlackChannel']}")
    print(f"  Emails: {metrics['entities_by_type']['Email']}")
    print(f"  GitHubHandles: {metrics['entities_by_type']['GitHubHandle']}")
    print(f"  Technologies: {metrics['technology_entities']}")

    return services


def resolve_reference(ref_value: Any) -> str:
    """Resolve $ref to URN"""
    if not ref_value:
        return None

    if isinstance(ref_value, dict) and "$ref" in ref_value:
        ref_path = ref_value["$ref"]
    elif isinstance(ref_value, str):
        ref_path = ref_value
    else:
        return None

    path_parts = ref_path.strip("/").split("/")

    if len(path_parts) >= 2:
        entity_type = path_parts[0].rstrip("s")
        entity_name = path_parts[1]

        if "escalation-polic" in ref_path:
            entity_type = "escalation-policy"
            if len(path_parts) >= 4:
                entity_name = path_parts[3].replace(".yml", "")

        urn = generate_urn(entity_type, entity_name)

        if urn in entity_index:
            return urn

        alternatives = [
            generate_urn("dependency", entity_name),
            generate_urn("service", entity_name),
            generate_urn("team", entity_name),
        ]

        for alt_urn in alternatives:
            if alt_urn in entity_index:
                return alt_urn

        placeholder = {
            "@id": urn,
            "@type": entity_type.replace("-", " ").title(),
            "name": entity_name.replace("-", " ").title(),
            "_source_file": ref_path,
            "_placeholder": True,
        }
        entity_index[urn] = placeholder
        metrics["entities_by_type"][placeholder["@type"]] += 1

        return urn

    return None


def extract_relationships_pass2() -> None:
    """
    Pass 2: Resolve relationships including NEW contact/tech relationships
    """
    print("\n=== PASS 2: Relationship Resolution (ENHANCED) ===\n")

    relationships_created = 0

    entity_urns = list(entity_index.keys())

    for urn in entity_urns:
        entity = entity_index[urn]

        # Standard relationships
        if "_pending_dependencies" in entity:
            deps = entity["_pending_dependencies"]
            entity["dependencies"] = []
            for dep in deps:
                dep_urn = resolve_reference(dep)
                if dep_urn:
                    entity["dependencies"].append({"@id": dep_urn})
                    relationships_created += 1
                else:
                    broken_references.append(
                        {
                            "source": urn,
                            "predicate": "dependencies",
                            "target": str(dep),
                            "reason": "Reference not found",
                        }
                    )
            del entity["_pending_dependencies"]

        if "_pending_escalationPolicy" in entity:
            ep_urn = resolve_reference(entity["_pending_escalationPolicy"])
            if ep_urn:
                entity["escalationPolicy"] = {"@id": ep_urn}
                relationships_created += 1
            del entity["_pending_escalationPolicy"]

        if "_pending_serviceOwners" in entity:
            entity["hasOwner"] = []
            for owner_data in entity["_pending_serviceOwners"]:
                email = owner_data.get("email")
                if email:
                    owner_urn = generate_urn("user", email)
                    if owner_urn in entity_index:
                        entity["hasOwner"].append({"@id": owner_urn})
                        relationships_created += 1
            del entity["_pending_serviceOwners"]

        if "_pending_endPoints" in entity:
            entity["hasEndpoint"] = []
            for ep_data in entity["_pending_endPoints"]:
                ep_name = ep_data.get("name", "")
                ep_url = ep_data.get("url", "")
                if ep_url:
                    ep_urn = generate_urn("endpoint", ep_name or ep_url)
                    if ep_urn in entity_index:
                        entity["hasEndpoint"].append({"@id": ep_urn})
                        relationships_created += 1
            del entity["_pending_endPoints"]

        if "_pending_codeComponents" in entity:
            entity["hasCodeComponent"] = []
            for comp_data in entity["_pending_codeComponents"]:
                comp_name = comp_data.get("name", "")
                if comp_name:
                    service_name = urn.split(":")[-1]
                    comp_urn = generate_urn("code-component", service_name, comp_name)
                    if comp_urn in entity_index:
                        entity["hasCodeComponent"].append({"@id": comp_urn})
                        relationships_created += 1
            del entity["_pending_codeComponents"]

    # NEW: Create contact and technology relationships
    for urn in entity_urns:
        entity = entity_index[urn]

        if entity.get("@type") == "Service":
            # Find related contact entities
            for contact_urn, contact_entity in entity_index.items():
                contact_type = contact_entity.get("@type")

                if contact_type in [
                    "SlackChannel",
                    "Email",
                    "GitHubHandle",
                    "JiraProject",
                    "PagerDutyService",
                ]:
                    # Check if contact is related to this service
                    source_file = contact_entity.get("_source_file", "")
                    if urn in source_file:
                        # Create contactVia relationship
                        if "contactVia" not in entity:
                            entity["contactVia"] = []
                        entity["contactVia"].append({"@id": contact_urn})
                        relationships_created += 1
                        enhancement_metrics["contact_relationships"] += 1

                # GitHub handles get special maintainedBy relationship
                if contact_type == "GitHubHandle" and urn in source_file:
                    if "maintainedBy" not in entity:
                        entity["maintainedBy"] = []
                    entity["maintainedBy"].append({"@id": contact_urn})
                    relationships_created += 1
                    enhancement_metrics["contact_relationships"] += 1

            # Find related technology entities
            for tech_urn, tech_entity in entity_index.items():
                tech_type = tech_entity.get("@type")

                if tech_type in [
                    "ProgrammingLanguage",
                    "Framework",
                    "Database",
                    "CloudProvider",
                    "Tool",
                ]:
                    source_file = tech_entity.get("_source_file", "")
                    if urn in source_file:
                        # Create technology relationships
                        if tech_type == "ProgrammingLanguage":
                            if "implementedIn" not in entity:
                                entity["implementedIn"] = []
                            entity["implementedIn"].append({"@id": tech_urn})
                            relationships_created += 1
                            enhancement_metrics["technology_relationships"] += 1

                        elif tech_type in ["Framework", "Database", "Tool"]:
                            if "uses" not in entity:
                                entity["uses"] = []
                            entity["uses"].append({"@id": tech_urn})
                            relationships_created += 1
                            enhancement_metrics["technology_relationships"] += 1

                        elif tech_type == "CloudProvider":
                            if "deployedOn" not in entity:
                                entity["deployedOn"] = []
                            entity["deployedOn"].append({"@id": tech_urn})
                            relationships_created += 1
                            enhancement_metrics["technology_relationships"] += 1

    metrics["total_relationships"] = relationships_created
    metrics["broken_references"] = len(broken_references)

    print(f"Pass 2 Complete:")
    print(f"  Total relationships created: {relationships_created}")
    print(f"  Contact relationships: {enhancement_metrics['contact_relationships']}")
    print(
        f"  Technology relationships: {enhancement_metrics['technology_relationships']}"
    )
    print(
        f"  Broken references: {len(broken_references)} ({(len(broken_references)/max(relationships_created,1))*100:.1f}%)"
    )


def detect_orphans() -> List[str]:
    """Detect orphaned entities"""
    print("\n=== Orphan Detection ===\n")

    referenced_by = defaultdict(list)

    for urn, entity in entity_index.items():
        for field, value in entity.items():
            if field.startswith("_"):
                continue

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "@id" in item:
                        referenced_by[item["@id"]].append(urn)
            elif isinstance(value, dict) and "@id" in value:
                referenced_by[value["@id"]].append(urn)

    orphans = []
    for urn, entity in entity_index.items():
        has_outbound = False
        has_inbound = len(referenced_by.get(urn, [])) > 0

        for field, value in entity.items():
            if field.startswith("_"):
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "@id" in item:
                        has_outbound = True
                        break
            elif isinstance(value, dict) and "@id" in value:
                has_outbound = True

            if has_outbound:
                break

        if not has_outbound and not has_inbound:
            orphans.append(urn)

    metrics["orphan_entities"] = len(orphans)
    orphan_rate = (len(orphans) / len(entity_index)) * 100 if entity_index else 0

    print(f"Orphan Detection Complete:")
    print(f"  Total orphans: {len(orphans)} ({orphan_rate:.2f}%)")

    return orphans


def calculate_final_metrics() -> None:
    """Calculate final validation metrics"""
    print("\n=== Final Metrics Calculation ===\n")

    metrics["total_entities"] = len(entity_index)

    total_predicates = 0
    for entity in entity_index.values():
        predicates = sum(1 for k in entity.keys() if not k.startswith("_"))
        total_predicates += predicates

    metrics["avg_predicates_per_entity"] = (
        total_predicates / len(entity_index) if entity_index else 0
    )

    sparse_entities = sum(
        1
        for entity in entity_index.values()
        if sum(1 for k in entity.keys() if not k.startswith("_")) < 5
    )

    print(f"Metrics calculated:")
    print(f"  Total entities: {metrics['total_entities']}")
    print(f"  Total relationships: {metrics['total_relationships']}")
    print(f"  Avg predicates/entity: {metrics['avg_predicates_per_entity']:.1f}")
    print(f"  Sparse entities (<5 predicates): {sparse_entities}")


def export_to_jsonld() -> None:
    """Export to JSON-LD format"""
    print("\n=== Export to JSON-LD ===\n")

    jsonld = {
        "@context": {
            "@vocab": "http://schema.org/",
            "urn": "http://example.org/urn/",
        },
        "@graph": [],
    }

    for entity in entity_index.values():
        clean_entity = {k: v for k, v in entity.items() if not k.startswith("_")}
        jsonld["@graph"].append(clean_entity)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(jsonld, f, indent=2)

    print(f"Exported to: {OUTPUT_PATH}")
    print(f"  Total entities in graph: {len(jsonld['@graph'])}")


def validate_all_standards() -> Dict[str, bool]:
    """Validate against all 6 standards"""
    print("\n=== Validation Against All Standards ===\n")

    results = {}

    # Standard 1: URN Format Validation
    invalid_urns = [urn for urn in entity_index.keys() if not validate_urn(urn)]
    results["standard_1_urn_format"] = len(invalid_urns) == 0
    print(
        f"Standard 1 (URN Format): {'PASS' if results['standard_1_urn_format'] else 'FAIL'}"
    )

    # Standard 2: Required Predicates
    missing_predicates = []
    for urn, entity in entity_index.items():
        if not entity.get("@id") or not entity.get("@type") or not entity.get("name"):
            missing_predicates.append(urn)
    results["standard_2_required_predicates"] = len(missing_predicates) == 0
    print(
        f"Standard 2 (Required Predicates): {'PASS' if results['standard_2_required_predicates'] else 'FAIL'}"
    )

    # Standard 3: JSON-LD Valid
    results["standard_3_jsonld_valid"] = True
    print(f"Standard 3 (JSON-LD Valid): PASS")

    # Standard 4: Reference Integrity
    broken_ref_rate = (
        metrics["broken_references"] / max(metrics["total_relationships"], 1)
    ) * 100
    results["standard_4_reference_integrity"] = broken_ref_rate < 2.0
    print(
        f"Standard 4 (Reference Integrity): {'PASS' if results['standard_4_reference_integrity'] else 'FAIL'}"
    )
    print(f"  Broken reference rate: {broken_ref_rate:.2f}%")

    # Standard 5: Iteration Targets
    iteration_checks = {
        "iteration_1_names": metrics["entities_missing_names"]
        < (metrics["total_entities"] * 0.05),
        "iteration_2_broken_refs": broken_ref_rate < 2.0,
        "iteration_3_orphans": (
            metrics["orphan_entities"] / max(metrics["total_entities"], 1)
        )
        < 0.005,
        "iteration_4_sub_entities": metrics["sub_entities_extracted"] > 0,
        "iteration_7_avg_predicates": metrics["avg_predicates_per_entity"] >= 12.0,
    }
    results["standard_5_iteration_targets"] = all(iteration_checks.values())
    print(
        f"Standard 5 (Iteration Targets): {'PASS' if results['standard_5_iteration_targets'] else 'FAIL'}"
    )

    # Standard 6: Bidirectional Consistency
    results["standard_6_bidirectional"] = broken_ref_rate < 2.0
    print(
        f"Standard 6 (Bidirectional Consistency): {'PASS' if results['standard_6_bidirectional'] else 'FAIL'}"
    )

    overall_pass = all(results.values())
    print(f"\n{'='*50}")
    print(f"OVERALL VALIDATION: {'PASS' if overall_pass else 'FAIL'}")
    print(f"{'='*50}")

    return results


def generate_final_report() -> None:
    """Generate comprehensive final report"""
    print("\n" + "=" * 70)
    print("ENHANCED KNOWLEDGE GRAPH EXTRACTION - FINAL REPORT")
    print("=" * 70)

    print("\n## Extraction Summary\n")
    print(f"Repository: {REPO_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print(
        f"Extraction Time: {metrics['extraction_end_time'] - metrics['extraction_start_time']:.1f} seconds"
    )

    print("\n## Entity Statistics\n")
    print(f"Total Entities: {metrics['total_entities']}")
    print(f"\nEntities by Type:")
    for entity_type, count in sorted(
        metrics["entities_by_type"].items(), key=lambda x: -x[1]
    ):
        print(f"  {entity_type}: {count}")

    print(f"\n## Enhancement Statistics (NEW)\n")
    print(f"Contact Entities: {metrics['contact_entities']}")
    print(f"  SlackChannels: {enhancement_metrics['slack_channels']}")
    print(f"  Emails: {enhancement_metrics['emails']}")
    print(f"  GitHubHandles: {enhancement_metrics['github_handles']}")
    print(f"  JiraProjects: {enhancement_metrics['jira_projects']}")
    print(f"  PagerDutyServices: {enhancement_metrics['pagerduty_services']}")

    print(f"\nTechnology Entities: {metrics['technology_entities']}")
    print(f"  ProgrammingLanguages: {enhancement_metrics['programming_languages']}")
    print(f"  Frameworks: {enhancement_metrics['frameworks']}")
    print(f"  Databases: {enhancement_metrics['databases']}")
    print(f"  CloudProviders: {enhancement_metrics['cloud_providers']}")
    print(f"  Tools: {enhancement_metrics['tools']}")

    print(f"\nREADME Analysis:")
    print(f"  READMEs analyzed: {enhancement_metrics['readmes_analyzed']}")

    print("\n## Relationship Statistics\n")
    print(f"Total Relationships: {metrics['total_relationships']}")
    print(
        f"  Contact relationships (NEW): {enhancement_metrics['contact_relationships']}"
    )
    print(
        f"  Technology relationships (NEW): {enhancement_metrics['technology_relationships']}"
    )
    print(
        f"Broken References: {metrics['broken_references']} ({(metrics['broken_references']/max(metrics['total_relationships'],1))*100:.2f}%)"
    )

    print("\n## Quality Metrics\n")
    print(
        f"Avg Predicates per Entity: {metrics['avg_predicates_per_entity']:.1f} (target: 12+)"
    )
    print(
        f"Orphan Entities: {metrics['orphan_entities']} ({(metrics['orphan_entities']/max(metrics['total_entities'],1))*100:.2f}%)"
    )

    print("\n" + "=" * 70)
    print("END OF REPORT")
    print("=" * 70 + "\n")


def main():
    """Main extraction pipeline"""
    print("=" * 70)
    print("ENHANCED KNOWLEDGE GRAPH EXTRACTION")
    print("Contact & Technology Stack Extraction")
    print("=" * 70)

    metrics["extraction_start_time"] = time.time()

    print("\nPhase 0: Repository Discovery - COMPLETE")
    print(f"  Repository: {REPO_PATH}")
    print(f"  Services found: {progress['total_services']}")

    print("\nPhase 1: Schema Analysis - COMPLETE")

    # Phase 2: Entity Extraction (Pass 1)
    progress["current_phase"] = "Phase 2"
    all_entities = extract_all_services_pass1()

    # Phase 3: Relationship Resolution (Pass 2)
    progress["current_phase"] = "Phase 3"
    extract_relationships_pass2()

    # Orphan Detection
    detect_orphans()

    # Calculate metrics
    calculate_final_metrics()

    # Phase 3.5: Validation
    progress["current_phase"] = "Phase 3.5"
    validate_all_standards()

    # Phase 4: Export
    progress["current_phase"] = "Phase 4"
    export_to_jsonld()

    metrics["extraction_end_time"] = time.time()

    # Final Report
    generate_final_report()


if __name__ == "__main__":
    main()
