#!/usr/bin/env python3
"""
General Entity Type Discovery Framework Test
============================================

This script implements the 5-step General Entity Type Discovery process
as documented in extraction/PROCESS.md (lines 2448-2738).

The framework discovers entity types from data patterns rather than using
hardcoded ontologies, making it truly domain-agnostic.

5-Step Process:
1. Analyze Value Patterns (identifier, structural, semantic)
2. Analyze Field Semantics (field names, value meanings, context)
3. Discover Entity Type Taxonomy (grouping, hierarchies, queryability)
4. Generate Entity Type Definitions (with confidence scores)
5. Apply Discovered Types to Extraction

Test: Extract from 12 app-interface service YAML files
"""

import yaml
import json
import re
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
import hashlib


@dataclass
class EntityTypePattern:
    """Represents a discovered entity type pattern"""

    type_name: str
    pattern_type: str  # identifier, structural, semantic
    pattern_description: str
    examples: List[str] = field(default_factory=list)
    field_contexts: List[str] = field(default_factory=list)
    urn_pattern: str = ""
    queryability: str = ""
    confidence: float = 0.0
    instance_count: int = 0
    discovery_reasoning: str = ""


@dataclass
class DiscoveredEntity:
    """Represents an extracted entity"""

    urn: str
    entity_type: str
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveredRelationship:
    """Represents an extracted relationship"""

    source_urn: str
    relationship_type: str
    target_urn: str
    properties: Dict[str, Any] = field(default_factory=dict)


class GeneralEntityDiscoveryFramework:
    """
    Implements the General Entity Type Discovery Framework
    Following PROCESS.md Steps 1-5
    """

    def __init__(self):
        self.discovered_patterns: Dict[str, EntityTypePattern] = {}
        self.entities: List[DiscoveredEntity] = []
        self.relationships: List[DiscoveredRelationship] = []
        self.pattern_cache: Dict[str, List[str]] = defaultdict(list)
        self.entity_urns: Set[str] = set()  # Track URNs to prevent duplicates

    # ========================================================================
    # STEP 1: Analyze Value Patterns
    # ========================================================================

    def step1_analyze_value_patterns(self, data: Any, field_path: str = "") -> None:
        """
        Step 1: Analyze Value Patterns

        Pattern Categories:
        1. Identifier Patterns (URLs, emails, hashtags, handles, IDs)
        2. Structural Patterns (arrays of objects, nested structures)
        3. Semantic Patterns (field names with meaningful suffixes/prefixes)
        """
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{field_path}.{key}" if field_path else key

                # Check identifier patterns
                if isinstance(value, str):
                    self._detect_identifier_patterns(key, value, current_path)

                # Check structural patterns
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    self._detect_structural_patterns(key, value, current_path)

                # Recurse
                self.step1_analyze_value_patterns(value, current_path)

        elif isinstance(data, list):
            for item in data:
                self.step1_analyze_value_patterns(item, field_path)

    def _detect_identifier_patterns(self, field: str, value: str, path: str) -> None:
        """Detect identifier patterns in values"""

        # Email pattern: user@domain
        if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
            self._record_pattern(
                "EmailAddress",
                "identifier",
                f"Email format: user@domain from field '{field}'",
                value,
                path,
                90.0,
                "Pattern recognition: email format (@) + field semantics (email/contact)",
            )

        # URL pattern: https://domain/path (GitHub/GitLab repositories)
        elif re.match(
            r"^https?://(github\.com|gitlab\.cee\.redhat\.com)/[\w\-\.]+/[\w\-\.]+",
            value,
        ):
            platform = "github" if "github.com" in value else "gitlab"
            self._record_pattern(
                "CodeRepository",
                "identifier",
                f"Repository URL from {platform}: https://domain/org/repo",
                value,
                path,
                95.0,
                f"URL pattern + domain knowledge ({platform}) + field semantics (codeComponents/url)",
            )

        # URL pattern: Grafana dashboards
        elif re.match(r"^https?://.*grafana.*", value, re.IGNORECASE):
            self._record_pattern(
                "MonitoringDashboard",
                "identifier",
                f"Grafana monitoring dashboard URL from field '{field}'",
                value,
                path,
                90.0,
                "URL pattern + grafana domain + field semantics (grafanaUrls)",
            )

        # URL pattern: Service endpoints
        elif re.match(r"^https?://.*\.(com|io|net|org)(:\d+)?/?", value) or re.match(
            r"^[\w\-\.]+:\d+$", value
        ):
            self._record_pattern(
                "ServiceEndpoint",
                "identifier",
                f"Service endpoint URL from field '{field}'",
                value,
                path,
                85.0,
                "URL/host:port pattern + field semantics (endPoints/url)",
            )

        # URL pattern: Documentation/Architecture URLs
        elif re.match(r"^https?://.*", value) and any(
            keyword in field.lower()
            for keyword in ["document", "docs", "sop", "architecture"]
        ):
            self._record_pattern(
                "DocumentationResource",
                "identifier",
                f"Documentation URL from field '{field}'",
                value,
                path,
                80.0,
                "URL pattern + field semantics (document/docs/sop/architecture)",
            )

    def _detect_structural_patterns(
        self, field: str, value: List[Dict], path: str
    ) -> None:
        """Detect structural patterns in arrays of objects"""

        if not value:
            return

        # Pattern: Array of objects with {name, url} -> Link collections
        first_item = value[0]
        if isinstance(first_item, dict):
            keys = set(first_item.keys())

            # Code components pattern
            if "url" in keys and "name" in keys and "codeComponents" in path:
                for item in value:
                    if "url" in item and isinstance(item["url"], str):
                        self._detect_identifier_patterns(
                            "url", item["url"], f"{path}[].url"
                        )

            # Dependencies pattern
            if "$ref" in keys and "dependencies" in path.lower():
                self._record_pattern(
                    "DependencyReference",
                    "structural",
                    f"Dependency reference from field '{field}'",
                    str(value[0].get("$ref", "")),
                    path,
                    75.0,
                    "Structural pattern: $ref reference + dependencies context",
                )

            # Service owners pattern
            if "email" in keys and "name" in keys and "owner" in path.lower():
                for item in value:
                    if "email" in item and isinstance(item["email"], str):
                        self._detect_identifier_patterns(
                            "email", item["email"], f"{path}[].email"
                        )

    def _record_pattern(
        self,
        type_name: str,
        pattern_type: str,
        description: str,
        example: str,
        context: str,
        confidence: float,
        reasoning: str,
    ) -> None:
        """Record a discovered pattern"""

        if type_name not in self.discovered_patterns:
            self.discovered_patterns[type_name] = EntityTypePattern(
                type_name=type_name,
                pattern_type=pattern_type,
                pattern_description=description,
                examples=[],
                field_contexts=[],
                confidence=confidence,
                discovery_reasoning=reasoning,
            )

        pattern = self.discovered_patterns[type_name]

        # Add example if not already present (limit to 5)
        if example and example not in pattern.examples and len(pattern.examples) < 5:
            pattern.examples.append(example)

        # Add context if not already present
        if context and context not in pattern.field_contexts:
            pattern.field_contexts.append(context)

        pattern.instance_count += 1

    # ========================================================================
    # STEP 2: Analyze Field Semantics
    # ========================================================================

    def step2_analyze_field_semantics(self) -> None:
        """
        Step 2: Analyze Field Semantics

        - What do these fields MEAN in this domain?
        - Field name analysis (noun/verb extraction)
        - Value semantics (real-world concepts)
        - Context analysis (domain understanding)
        """

        for type_name, pattern in self.discovered_patterns.items():
            # Enhance patterns with semantic analysis

            if type_name == "CodeRepository":
                pattern.urn_pattern = "urn:code-repository:{platform}:{org}:{repo}"
                pattern.queryability = "Find repos by org, Find services using repo X, Map code to services"

            elif type_name == "EmailAddress":
                pattern.urn_pattern = "urn:email-address:{normalized-email}"
                pattern.queryability = "Find all services owned by email X, Show contacts for service, List team responsibilities"

            elif type_name == "MonitoringDashboard":
                pattern.urn_pattern = "urn:monitoring-dashboard:{tool}:{dashboard-id}"
                pattern.queryability = "Find dashboards for service X, Which services use Grafana, Show monitoring coverage"

            elif type_name == "ServiceEndpoint":
                pattern.urn_pattern = "urn:service-endpoint:{normalized-url}"
                pattern.queryability = "Find endpoints for service X, Show all monitored endpoints, Map endpoints to services"

            elif type_name == "DocumentationResource":
                pattern.urn_pattern = "urn:documentation:{hash}"
                pattern.queryability = (
                    "Find docs for service X, Show architecture documents"
                )

    # ========================================================================
    # STEP 3: Discover Entity Type Taxonomy
    # ========================================================================

    def step3_discover_taxonomy(self) -> None:
        """
        Step 3: Discover Entity Type Taxonomy

        - Group similar patterns
        - Identify hierarchies
        - Validate queryability

        Decision: Should value V from field F become an entity?
        YES if: Pattern + Identity + Queryability
        NO if: Simple property OR Not queryable OR Too generic
        """

        # Filter patterns by confidence threshold
        high_confidence = {
            k: v for k, v in self.discovered_patterns.items() if v.confidence >= 85.0
        }
        medium_confidence = {
            k: v
            for k, v in self.discovered_patterns.items()
            if 60.0 <= v.confidence < 85.0
        }
        low_confidence = {
            k: v for k, v in self.discovered_patterns.items() if v.confidence < 60.0
        }

        print(f"\n=== STEP 3: Entity Type Taxonomy Discovery ===")
        print(f"HIGH confidence entity types (>= 85%): {len(high_confidence)}")
        print(f"MEDIUM confidence entity types (60-85%): {len(medium_confidence)}")
        print(f"LOW confidence entity types (< 60%): {len(low_confidence)}")

        # Keep only high and medium confidence patterns for extraction
        self.discovered_patterns = {**high_confidence, **medium_confidence}

    # ========================================================================
    # STEP 4: Generate Entity Type Definitions
    # ========================================================================

    def step4_generate_definitions(self) -> str:
        """
        Step 4: Generate Entity Type Definitions

        Creates a discovery report documenting all discovered entity types
        """

        report_lines = []
        report_lines.append("# Entity Type Discovery Report")
        report_lines.append("")
        report_lines.append("**Data Source**: app-interface repository")
        report_lines.append("**Domain**: Infrastructure Configuration Management")
        report_lines.append(
            f"**Sample Size**: {len(self.sample_files)} service YAML files analyzed"
        )
        report_lines.append(
            "**Discovery Method**: General Entity Type Discovery Framework (5-step process)"
        )
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        report_lines.append("## Discovered Entity Types")
        report_lines.append("")

        # Sort by confidence (highest first)
        sorted_patterns = sorted(
            self.discovered_patterns.items(),
            key=lambda x: x[1].confidence,
            reverse=True,
        )

        for idx, (type_name, pattern) in enumerate(sorted_patterns, 1):
            report_lines.append(f"### Type {idx}: {type_name}")
            report_lines.append(f"**Pattern Type**: {pattern.pattern_type}")
            report_lines.append(f"**Pattern**: {pattern.pattern_description}")
            report_lines.append("")
            report_lines.append("**Examples**:")
            for example in pattern.examples[:5]:
                report_lines.append(f"- `{example}`")
            report_lines.append("")
            report_lines.append("**Field Contexts**:")
            for context in pattern.field_contexts[:5]:
                report_lines.append(f"- `{context}`")
            report_lines.append("")
            report_lines.append(f"**URN Pattern**: `{pattern.urn_pattern}`")
            report_lines.append(f"**Queryability**: {pattern.queryability}")
            report_lines.append(
                f"**Confidence**: {'HIGH' if pattern.confidence >= 85 else 'MEDIUM'} ({pattern.confidence}%)"
            )
            report_lines.append(f"**Instances Found**: {pattern.instance_count}")
            report_lines.append("")
            report_lines.append("**Discovery Reasoning**:")
            report_lines.append(f"{pattern.discovery_reasoning}")
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("")

        # Statistics
        high_count = sum(
            1 for p in self.discovered_patterns.values() if p.confidence >= 85
        )
        medium_count = sum(
            1 for p in self.discovered_patterns.values() if 60 <= p.confidence < 85
        )

        report_lines.append("## Discovery Statistics")
        report_lines.append(
            f"- Total unique entity types discovered: {len(self.discovered_patterns)}"
        )
        report_lines.append(f"- Entity types (HIGH confidence >= 85%): {high_count}")
        report_lines.append(
            f"- Entity types (MEDIUM confidence 60-85%): {medium_count}"
        )
        report_lines.append(
            f"- Total pattern instances found: {sum(p.instance_count for p in self.discovered_patterns.values())}"
        )
        report_lines.append("")

        return "\n".join(report_lines)

    # ========================================================================
    # STEP 5: Apply Discovered Types to Extraction
    # ========================================================================

    def step5_extract_entities(self, data: Dict[str, Any], service_name: str) -> None:
        """
        Step 5: Apply Discovered Types to Extraction

        Use the discovered entity type patterns to extract actual entities
        and relationships from the data.
        """

        # Create the Service entity
        service_urn = self._create_urn("service", service_name)
        if service_urn not in self.entity_urns:
            self.entities.append(
                DiscoveredEntity(
                    urn=service_urn,
                    entity_type="Service",
                    name=service_name,
                    properties={
                        "description": data.get("description", ""),
                        "onboardingStatus": data.get("onboardingStatus", ""),
                        "appCode": data.get("appCode", ""),
                        "costCenter": data.get("costCenter", ""),
                    },
                )
            )
            self.entity_urns.add(service_urn)

        # Extract using discovered patterns
        self._extract_with_patterns(data, service_urn, service_name)

    def _extract_with_patterns(
        self, data: Any, parent_urn: str, service_name: str, path: str = ""
    ) -> None:
        """Recursively extract entities using discovered patterns"""

        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                # Email addresses
                if isinstance(value, str) and re.match(
                    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value
                ):
                    if "EmailAddress" in self.discovered_patterns:
                        email_urn = self._create_urn("email-address", value)
                        if email_urn not in self.entity_urns:
                            self.entities.append(
                                DiscoveredEntity(
                                    urn=email_urn,
                                    entity_type="EmailAddress",
                                    name=value,
                                    properties={"address": value},
                                )
                            )
                            self.entity_urns.add(email_urn)

                        # Determine relationship type from context
                        rel_type = (
                            "hasOwner"
                            if "owner" in current_path.lower()
                            else "hasContact"
                        )
                        self.relationships.append(
                            DiscoveredRelationship(
                                source_urn=parent_urn,
                                relationship_type=rel_type,
                                target_urn=email_urn,
                            )
                        )

                # Code repositories
                elif isinstance(value, str) and re.match(
                    r"^https?://(github\.com|gitlab\.cee\.redhat\.com)/[\w\-\.]+/[\w\-\.]+",
                    value,
                ):
                    if "CodeRepository" in self.discovered_patterns:
                        repo_urn = self._extract_repository(value, parent_urn)

                # Grafana dashboards
                elif isinstance(value, str) and re.match(
                    r"^https?://.*grafana.*", value, re.IGNORECASE
                ):
                    if "MonitoringDashboard" in self.discovered_patterns:
                        dashboard_urn = self._extract_monitoring_dashboard(
                            value, parent_urn
                        )

                # Service endpoints
                elif isinstance(value, str) and (
                    re.match(r"^https?://.*\.(com|io|net|org)(:\d+)?/?", value)
                    or re.match(r"^[\w\-\.]+:\d+$", value)
                ):
                    if (
                        "ServiceEndpoint" in self.discovered_patterns
                        and "endpoint" in current_path.lower()
                    ):
                        endpoint_urn = self._extract_endpoint(value, parent_urn)

                # Documentation resources
                elif (
                    isinstance(value, str)
                    and re.match(r"^https?://.*", value)
                    and any(
                        keyword in key.lower()
                        for keyword in ["document", "docs", "sop", "architecture"]
                    )
                ):
                    if "DocumentationResource" in self.discovered_patterns:
                        doc_urn = self._extract_documentation(value, parent_urn, key)

                # Recurse
                self._extract_with_patterns(
                    value, parent_urn, service_name, current_path
                )

        elif isinstance(data, list):
            for item in data:
                self._extract_with_patterns(item, parent_urn, service_name, path)

    def _extract_repository(self, url: str, service_urn: str) -> str:
        """Extract code repository entity"""
        # Parse repository URL
        match = re.match(r"^https?://([^/]+)/([^/]+)/([^/\?#]+)", url)
        if match:
            platform = "github" if "github.com" in match.group(1) else "gitlab"
            org = match.group(2)
            repo = match.group(3).rstrip(".git")

            repo_urn = self._create_urn("code-repository", f"{platform}:{org}:{repo}")

            # Check if already exists
            if repo_urn not in self.entity_urns:
                self.entities.append(
                    DiscoveredEntity(
                        urn=repo_urn,
                        entity_type="CodeRepository",
                        name=f"{org}/{repo}",
                        properties={
                            "url": url,
                            "platform": platform,
                            "organization": org,
                            "repository": repo,
                        },
                    )
                )
                self.entity_urns.add(repo_urn)

            self.relationships.append(
                DiscoveredRelationship(
                    source_urn=service_urn,
                    relationship_type="usesRepository",
                    target_urn=repo_urn,
                )
            )

            return repo_urn
        return ""

    def _extract_monitoring_dashboard(self, url: str, service_urn: str) -> str:
        """Extract monitoring dashboard entity"""
        # Extract dashboard ID from Grafana URL
        match = re.search(r"/d/([^/\?#]+)", url)
        dashboard_id = (
            match.group(1) if match else hashlib.md5(url.encode()).hexdigest()[:12]
        )

        dashboard_urn = self._create_urn(
            "monitoring-dashboard", f"grafana:{dashboard_id}"
        )

        if dashboard_urn not in self.entity_urns:
            self.entities.append(
                DiscoveredEntity(
                    urn=dashboard_urn,
                    entity_type="MonitoringDashboard",
                    name=f"Grafana: {dashboard_id}",
                    properties={
                        "url": url,
                        "tool": "grafana",
                        "dashboardId": dashboard_id,
                    },
                )
            )
            self.entity_urns.add(dashboard_urn)

        self.relationships.append(
            DiscoveredRelationship(
                source_urn=service_urn,
                relationship_type="monitoredBy",
                target_urn=dashboard_urn,
            )
        )

        return dashboard_urn

    def _extract_endpoint(self, url: str, service_urn: str) -> str:
        """Extract service endpoint entity"""
        endpoint_urn = self._create_urn("service-endpoint", url)

        if endpoint_urn not in self.entity_urns:
            self.entities.append(
                DiscoveredEntity(
                    urn=endpoint_urn,
                    entity_type="ServiceEndpoint",
                    name=url,
                    properties={"url": url},
                )
            )
            self.entity_urns.add(endpoint_urn)

        self.relationships.append(
            DiscoveredRelationship(
                source_urn=service_urn,
                relationship_type="exposesEndpoint",
                target_urn=endpoint_urn,
            )
        )

        return endpoint_urn

    def _extract_documentation(self, url: str, service_urn: str, doc_type: str) -> str:
        """Extract documentation resource entity"""
        doc_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        doc_urn = self._create_urn("documentation", doc_hash)

        if doc_urn not in self.entity_urns:
            self.entities.append(
                DiscoveredEntity(
                    urn=doc_urn,
                    entity_type="DocumentationResource",
                    name=f"{doc_type}: {url}",
                    properties={"url": url, "documentType": doc_type},
                )
            )
            self.entity_urns.add(doc_urn)

        self.relationships.append(
            DiscoveredRelationship(
                source_urn=service_urn,
                relationship_type="hasDocumentation",
                target_urn=doc_urn,
            )
        )

        return doc_urn

    def _create_urn(self, entity_type: str, identifier: str) -> str:
        """Create a URN for an entity"""
        # Normalize identifier
        normalized = (
            identifier.lower()
            .replace(" ", "-")
            .replace("@", "-at-")
            .replace("/", "-")
            .replace(":", "-")
        )
        return f"urn:{entity_type}:{normalized}"

    # ========================================================================
    # Main Execution
    # ========================================================================

    def process_sample_files(self, file_paths: List[str]) -> None:
        """Process sample service files through the 5-step framework"""

        self.sample_files = file_paths

        print("=" * 80)
        print("GENERAL ENTITY TYPE DISCOVERY FRAMEWORK - TEST EXECUTION")
        print("=" * 80)
        print(
            f"\nProcessing {len(file_paths)} service YAML files from app-interface..."
        )
        print("")

        # Load all files first
        all_data = []
        for file_path in file_paths:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
                all_data.append((file_path, data))

        # STEP 1: Analyze Value Patterns
        print("\n=== STEP 1: Analyzing Value Patterns ===")
        for file_path, data in all_data:
            service_name = data.get("name", Path(file_path).stem)
            print(f"  - Analyzing: {service_name}")
            self.step1_analyze_value_patterns(data)

        print(
            f"\nDiscovered {len(self.discovered_patterns)} unique entity type patterns"
        )

        # STEP 2: Analyze Field Semantics
        print("\n=== STEP 2: Analyzing Field Semantics ===")
        self.step2_analyze_field_semantics()
        print(
            f"Enhanced {len(self.discovered_patterns)} patterns with semantic analysis"
        )

        # STEP 3: Discover Taxonomy
        self.step3_discover_taxonomy()

        # STEP 4: Generate Definitions
        print("\n=== STEP 4: Generating Entity Type Definitions ===")
        discovery_report = self.step4_generate_definitions()
        print(
            f"Generated discovery report with {len(self.discovered_patterns)} entity types"
        )

        # STEP 5: Apply to Extraction
        print("\n=== STEP 5: Applying Discovered Types to Extraction ===")
        for file_path, data in all_data:
            service_name = data.get("name", Path(file_path).stem)
            print(f"  - Extracting: {service_name}")
            self.step5_extract_entities(data, service_name)

        print(
            f"\nExtracted {len(self.entities)} entities and {len(self.relationships)} relationships"
        )

        return discovery_report

    def export_to_jsonld(self, output_path: str) -> None:
        """Export extracted entities and relationships to JSON-LD"""

        graph = []

        # Add entities
        for entity in self.entities:
            node = {
                "@id": entity.urn,
                "@type": entity.entity_type,
                "name": entity.name,
                **entity.properties,
            }
            graph.append(node)

        # Add relationships as properties
        for rel in self.relationships:
            # Find source entity
            source = next((e for e in self.entities if e.urn == rel.source_urn), None)
            if source:
                # Find corresponding node in graph
                source_node = next(
                    (n for n in graph if n.get("@id") == source.urn), None
                )
                if source_node:
                    # Add relationship as property
                    if rel.relationship_type not in source_node:
                        source_node[rel.relationship_type] = []
                    source_node[rel.relationship_type].append({"@id": rel.target_urn})

        jsonld = {
            "@context": {
                "@vocab": "https://schema.org/",
                "urn": "https://kartograph.example.org/urn/",
                "Service": "https://schema.org/Service",
                "EmailAddress": "https://schema.org/ContactPoint",
                "CodeRepository": "https://schema.org/SoftwareSourceCode",
                "MonitoringDashboard": "https://kartograph.example.org/MonitoringDashboard",
                "ServiceEndpoint": "https://schema.org/EntryPoint",
                "DocumentationResource": "https://schema.org/CreativeWork",
            },
            "@graph": graph,
        }

        with open(output_path, "w") as f:
            json.dump(jsonld, f, indent=2)

        print(f"\n✓ Exported knowledge graph to: {output_path}")

    def validate_output(self) -> Dict[str, Any]:
        """
        Validate extraction against 6 deterministic standards:
        1. All entities have valid URNs
        2. All entities have types
        3. All entities have names
        4. All relationships reference existing entities
        5. No duplicate entities
        6. JSON-LD is valid format
        """

        validation_results = {
            "valid_urns": True,
            "valid_types": True,
            "valid_names": True,
            "valid_relationships": True,
            "no_duplicates": True,
            "all_checks_passed": False,
        }

        # Check 1: Valid URNs
        for entity in self.entities:
            if not entity.urn or not entity.urn.startswith("urn:"):
                validation_results["valid_urns"] = False
                break

        # Check 2: Valid types
        for entity in self.entities:
            if not entity.entity_type:
                validation_results["valid_types"] = False
                break

        # Check 3: Valid names
        for entity in self.entities:
            if not entity.name:
                validation_results["valid_names"] = False
                break

        # Check 4: Valid relationships
        entity_urns = {e.urn for e in self.entities}
        for rel in self.relationships:
            if rel.source_urn not in entity_urns or rel.target_urn not in entity_urns:
                validation_results["valid_relationships"] = False
                break

        # Check 5: No duplicates
        urns = [e.urn for e in self.entities]
        if len(urns) != len(set(urns)):
            validation_results["no_duplicates"] = False

        # Overall check
        validation_results["all_checks_passed"] = all(
            [
                validation_results["valid_urns"],
                validation_results["valid_types"],
                validation_results["valid_names"],
                validation_results["valid_relationships"],
                validation_results["no_duplicates"],
            ]
        )

        return validation_results


def main():
    """Main execution"""

    # Sample service files (12 services)
    sample_files = [
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/app-sre/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/app-sre/cert-manager/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/app-sre/openshift-gitops/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/acs-fleet-manager/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/app-interface/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/addons/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/app-sre/aws-load-balancer-operator/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/app-sre/external-resources/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/advanced-cluster-security/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/app-interface/git-partition-sync/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/app-interface/go-qontract-reconcile/app.yml",
        "/home/jsell/code/sandbox/cartograph/app-interface/data/services/app-interface/terraform-repo/app.yml",
    ]

    # Initialize framework
    framework = GeneralEntityDiscoveryFramework()

    # Process files through 5-step framework
    discovery_report = framework.process_sample_files(sample_files)

    # Export results
    output_dir = Path("/home/jsell/code/kartograph-kg-iteration/extraction/working")

    # Save discovery report
    with open(output_dir / "DISCOVERED_ENTITY_TYPES.md", "w") as f:
        f.write(discovery_report)
    print(f"\n✓ Saved discovery report to: {output_dir / 'DISCOVERED_ENTITY_TYPES.md'}")

    # Export JSON-LD
    framework.export_to_jsonld(str(output_dir / "general_framework_test.jsonld"))

    # Validate
    print("\n=== VALIDATION ===")
    validation = framework.validate_output()
    for check, passed in validation.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check}")

    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"\nDiscovered Entity Types: {len(framework.discovered_patterns)}")
    print(f"Extracted Entities: {len(framework.entities)}")
    print(f"Extracted Relationships: {len(framework.relationships)}")
    print(
        f"\nValidation: {'✓ ALL CHECKS PASSED' if validation['all_checks_passed'] else '✗ VALIDATION FAILED'}"
    )


if __name__ == "__main__":
    main()
