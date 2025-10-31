#!/usr/bin/env python3
"""
Load JSON-LD knowledge graph into Dgraph.

Converts JSON-LD format to Dgraph RDF/mutations and loads via HTTP API.
Validates data before loading and creates schema automatically.

Usage:
    python load_dgraph.py --input graph.jsonld --dgraph-url http://localhost:8080
    python load_dgraph.py --input graph.jsonld --drop-all  # Clear existing data
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
from typing import Any, Dict, List, Set
import requests


class DgraphLoader:
    def __init__(
        self,
        dgraph_url: str,
        drop_all: bool = False,
        grpc_port: int = None,
        zero_port: int = None,
    ):
        self.dgraph_url = dgraph_url.rstrip("/")
        self.drop_all = drop_all
        self.grpc_port = grpc_port  # Optional override for gRPC port
        self.zero_port = zero_port  # Optional override for Zero port
        self.predicate_types: Dict[str, str] = {}
        self.predicate_type_observations: Dict[str, Set[str]] = (
            {}
        )  # Track all types seen
        self.relationship_predicates: Set[str] = set()
        self.entity_types: Set[str] = set()
        self.type_predicates: Dict[str, Set[str]] = {}  # Track predicates per type

    def load_jsonld(self, filepath: str) -> Dict[str, Any]:
        """Load and parse JSON-LD file."""
        print(f"📖 Loading {filepath}...")

        with open(filepath, "r") as f:
            data = json.load(f)

        if "@graph" not in data:
            raise ValueError("Invalid JSON-LD: missing '@graph' key")

        entities = data["@graph"]
        print(f"✅ Loaded {len(entities)} entities")

        return data

    def validate_jsonld(self, jsonld: Dict[str, Any]) -> bool:
        """Validate JSON-LD structure."""
        print("🔍 Validating JSON-LD...")

        entities = jsonld["@graph"]
        errors = []

        for i, entity in enumerate(entities):
            # Check required fields
            if "@id" not in entity:
                errors.append(f"Entity {i}: missing @id")
            if "@type" not in entity:
                errors.append(f"Entity {i}: missing @type")
            if "name" not in entity:
                errors.append(
                    f"Entity {i} ({entity.get('@id', 'unknown')}): missing name"
                )

        if errors:
            print(f"❌ Validation failed with {len(errors)} errors:")
            for error in errors[:10]:
                print(f"  {error}")
            return False

        print(f"✅ Validation passed")
        return True

    def analyze_schema(self, jsonld: Dict[str, Any]):
        """Analyze JSON-LD to infer Dgraph schema with mixed type detection."""
        print("🔬 Analyzing schema...")

        entities = jsonld["@graph"]

        # Analyze entities to determine predicate types and collect entity types
        for entity in entities:
            # Collect entity types for schema generation
            entity_types_for_this_entity = []
            if "@type" in entity:
                entity_type = entity["@type"]
                if isinstance(entity_type, list):
                    self.entity_types.update(entity_type)
                    entity_types_for_this_entity = entity_type
                else:
                    self.entity_types.add(entity_type)
                    entity_types_for_this_entity = [entity_type]

            for key, value in entity.items():
                if key in ["@id", "@type"]:
                    continue

                # Clean predicate name (strip @ prefix) to avoid duplicates
                # Both @name and name should map to the same predicate
                clean_key = self._encode_predicate(key)

                # Track which types use this predicate (for sparse type definitions)
                for etype in entity_types_for_this_entity:
                    if etype not in self.type_predicates:
                        self.type_predicates[etype] = set()
                    self.type_predicates[etype].add(clean_key)

                # Initialize tracking set if needed
                if clean_key not in self.predicate_type_observations:
                    self.predicate_type_observations[clean_key] = set()

                # Check if it's a relationship (reference to another entity)
                is_relationship = False

                if isinstance(value, dict) and "@id" in value:
                    is_relationship = True
                elif isinstance(value, list):
                    # Check all items in list to detect mixed types
                    for item in value:
                        if isinstance(item, dict) and "@id" in item:
                            is_relationship = True
                        elif item is not None:
                            # Non-reference item in list
                            scalar_type = self._infer_scalar_type(item)
                            if scalar_type:  # Only add if not None
                                self.predicate_type_observations[clean_key].add(
                                    scalar_type
                                )

                if is_relationship:
                    self.relationship_predicates.add(clean_key)
                    self.predicate_type_observations[clean_key].add("uid")
                else:
                    # Infer and track scalar type
                    scalar_type = self._infer_scalar_type(value)
                    if scalar_type:  # Only add if not None (skip dicts/lists)
                        self.predicate_type_observations[clean_key].add(scalar_type)

        # Resolve mixed types
        self._resolve_predicate_types()

        print(f"  Found {len(self.predicate_types)} predicates")
        print(f"  Found {len(self.relationship_predicates)} relationships")
        print(f"  Found {len(self.entity_types)} entity types")

    def _infer_scalar_type(self, value: Any) -> str:
        """Infer the scalar type of a value."""
        # Skip dicts and lists - they're not scalar types
        if isinstance(value, (dict, list)):
            return None

        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        else:
            return "string"

    def _resolve_predicate_types(self):
        """
        Resolve predicate types based on all observations.
        If a predicate has mixed types (e.g., sometimes uid, sometimes string),
        default to string to avoid type mismatch errors.
        """
        print("🔄 Resolving mixed types...")

        mixed_type_count = 0

        for predicate, observed_types in self.predicate_type_observations.items():
            if len(observed_types) == 1:
                # Only one type seen - use it
                self.predicate_types[predicate] = list(observed_types)[0]
            else:
                # Mixed types detected
                mixed_type_count += 1

                # If uid is mixed with any scalar type, prefer uid (relationships are more important)
                if "uid" in observed_types:
                    print(
                        f"  ⚠️  {predicate}: mixed types {observed_types} → preferring uid (relationships)"
                    )
                    self.predicate_types[predicate] = "uid"
                    # Keep in relationship predicates
                    self.relationship_predicates.add(predicate)
                else:
                    # Mixed scalar types - choose string as most permissive
                    print(
                        f"  ⚠️  {predicate}: mixed scalar types {observed_types} → defaulting to string"
                    )
                    self.predicate_types[predicate] = "string"

        if mixed_type_count > 0:
            print(f"  Found {mixed_type_count} predicates with mixed types")

    def generate_schema(self) -> str:
        """Generate Dgraph schema from inferred types with sparse type definitions."""
        schema_lines = []

        # Generate sparse type definitions - each type only lists predicates it uses
        print("📋 Generating sparse type definitions...")
        total_type_predicates = 0
        for entity_type in sorted(self.entity_types):
            if entity_type in self.type_predicates:
                predicates = sorted(self.type_predicates[entity_type])
                schema_lines.append(f"type {entity_type} {{")
                for predicate in predicates:
                    schema_lines.append(f"  {predicate}")
                schema_lines.append("}")
                total_type_predicates += len(predicates)

        print(
            f"  Generated {len(self.entity_types)} types with avg {total_type_predicates // max(len(self.entity_types), 1)} predicates each"
        )
        schema_lines.append("")  # Blank line for readability

        # Predicates that should be indexed for fast queries
        indexed_predicates = {"name", "url", "email", "id", "path", "namespace"}

        # Add type predicate (from @type in JSON-LD) with index first
        schema_lines.append("type: string @index(exact, term) .")

        # Add predicate definitions
        # Note: predicates are already cleaned (@ prefix stripped) during analyze_schema
        for predicate, pred_type in sorted(self.predicate_types.items()):
            # Skip 'type' since we already defined it explicitly above
            if predicate == "type":
                continue

            if pred_type == "uid":
                # Relationship with reverse edge
                schema_lines.append(f"{predicate}: [uid] @reverse .")
            else:
                # Add indexes for key predicates (check against cleaned name)
                if predicate in indexed_predicates:
                    if pred_type == "string":
                        # Add trigram, fulltext, and standard indexes for name predicate
                        # trigram is required for regexp() matching
                        if predicate == "name":
                            schema_lines.append(
                                f"{predicate}: {pred_type} @index(exact, term, fulltext, trigram) ."
                            )
                        else:
                            schema_lines.append(
                                f"{predicate}: {pred_type} @index(exact, term, trigram) ."
                            )
                    elif pred_type == "int":
                        schema_lines.append(f"{predicate}: {pred_type} @index(int) .")
                    elif pred_type == "bool":
                        schema_lines.append(f"{predicate}: {pred_type} @index(bool) .")
                    elif pred_type == "float":
                        schema_lines.append(f"{predicate}: {pred_type} @index(float) .")
                    else:
                        schema_lines.append(f"{predicate}: {pred_type} .")
                else:
                    # Scalar type without index
                    schema_lines.append(f"{predicate}: {pred_type} .")

        return "\n".join(schema_lines)

    def convert_to_nquads(self, jsonld: Dict[str, Any]) -> List[str]:
        """Convert JSON-LD to N-Quads format for Dgraph."""
        print("🔄 Converting to N-Quads...")

        nquads = []
        entities = jsonld["@graph"]

        for entity in entities:
            subject = self._encode_urn(entity["@id"])

            # Add dgraph.type for expand(_all_) support
            if "@type" in entity:
                entity_type = entity["@type"]
                if isinstance(entity_type, list):
                    for t in entity_type:
                        nquads.append(f'{subject} <dgraph.type> "{t}" .')
                else:
                    nquads.append(f'{subject} <dgraph.type> "{entity_type}" .')

            for key, value in entity.items():
                if key == "@id":
                    continue

                predicate = self._encode_predicate(key)

                # Handle different value types
                if isinstance(value, dict) and "@id" in value:
                    # Relationship to another entity
                    obj = self._encode_urn(value["@id"])
                    nquads.append(f"{subject} <{predicate}> {obj} .")

                elif isinstance(value, list):
                    # Array of values
                    for item in value:
                        if isinstance(item, dict) and "@id" in item:
                            obj = self._encode_urn(item["@id"])
                            nquads.append(f"{subject} <{predicate}> {obj} .")
                        elif isinstance(item, dict):
                            # Skip nested objects if predicate is uid type
                            if (
                                predicate in self.predicate_types
                                and self.predicate_types[predicate] == "uid"
                            ):
                                continue
                            # Skip empty objects
                            if not item:
                                continue
                            # Nested object (serialize as JSON string)
                            obj_str = json.dumps(item).replace('"', '\\"')
                            nquads.append(f'{subject} <{predicate}> "{obj_str}" .')
                        else:
                            # Skip scalars if predicate is uid type
                            if (
                                predicate in self.predicate_types
                                and self.predicate_types[predicate] == "uid"
                            ):
                                continue
                            obj = self._format_literal(item)
                            if obj:  # Only add if not None
                                nquads.append(f"{subject} <{predicate}> {obj} .")

                else:
                    # Scalar value
                    # Skip if this predicate is defined as uid type (mixed type case)
                    if (
                        predicate in self.predicate_types
                        and self.predicate_types[predicate] == "uid"
                    ):
                        # This predicate should only have uid values, skip scalars
                        continue

                    obj = self._format_literal(value)
                    if obj:  # Only add if not None
                        nquads.append(f"{subject} <{predicate}> {obj} .")

        print(f"✅ Generated {len(nquads)} triples")
        return nquads

    def _encode_urn(self, urn: str) -> str:
        """Encode URN for Dgraph (handle special characters)."""
        # URL-encode special characters but keep URN structure
        encoded = urllib.parse.quote(urn, safe=":")
        return f"<{encoded}>"

    def _encode_predicate(self, predicate: str) -> str:
        """Clean predicate name (strip @ prefix and sanitize special characters)."""
        # Strip @ prefix if present (e.g., @type -> type)
        clean = predicate.lstrip("@")

        # Replace special characters that aren't valid in Dgraph predicates
        # Dgraph allows: alphanumeric, underscore, hyphen, period
        # Replace $ with underscore (e.g., $schema -> _schema, $ref -> _ref)
        clean = clean.replace("$", "_")

        # Replace other potentially problematic characters
        clean = clean.replace(":", "_")
        clean = clean.replace("/", "_")
        clean = clean.replace("\\", "_")

        # Handle Dgraph reserved words by prefixing with underscore
        # Reserved: uid, dgraph.*, etc.
        dgraph_reserved = {"uid"}
        if clean in dgraph_reserved:
            clean = f"_{clean}"

        # Prevent predicates starting with "dgraph." (reserved namespace)
        if clean.startswith("dgraph."):
            clean = f"_{clean}"

        return clean

    def _format_literal(self, value: Any) -> str:
        """Format literal value for N-Quads."""
        # Skip None values
        if value is None:
            return None

        # Skip empty dicts/objects (they should be relationships, not literals)
        if isinstance(value, dict):
            return None

        if isinstance(value, bool):
            return f'"{str(value).lower()}"^^<xs:boolean>'
        elif isinstance(value, int):
            return f'"{value}"^^<xs:int>'
        elif isinstance(value, float):
            return f'"{value}"^^<xs:float>'
        else:
            # String - escape quotes and newlines
            value_str = (
                str(value)
                .replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
            )
            # Skip if contains braces (serialized objects), brackets (serialized arrays), or "None" string
            if (
                "{" in value_str
                or "}" in value_str
                or "[" in value_str
                or "]" in value_str
                or value_str == "None"
            ):
                return None
            return f'"{value_str}"'

    def drop_all_data(self):
        """Drop all existing data in Dgraph."""
        print("🗑️  Dropping all existing data...")

        response = requests.post(f"{self.dgraph_url}/alter", json={"drop_all": True})

        if response.status_code == 200:
            print("✅ All data dropped")
        else:
            print(f"❌ Failed to drop data: {response.text}")
            sys.exit(1)

    def apply_schema(self, schema: str):
        """Apply schema to Dgraph."""
        print("📝 Applying schema...")
        print(
            f"  Schema length: {len(schema)} characters, {len(schema.split(chr(10)))} lines"
        )

        try:
            response = requests.post(
                f"{self.dgraph_url}/alter",
                data=schema,
                headers={"Content-Type": "text/plain"},
                timeout=30,
            )

            if response.status_code == 200:
                # Check for errors in JSON response (Dgraph returns 200 even with errors!)
                try:
                    result = response.json()
                    if "errors" in result and result["errors"]:
                        errors = result["errors"]
                        error_msgs = [e.get("message", str(e)) for e in errors]
                        print(f"❌ Schema application returned errors:")
                        for msg in error_msgs:
                            print(f"  - {msg}")

                        # Check for schema conflict errors
                        schema_conflict = any(
                            "Schema change not allowed" in msg or "scalar to uid" in msg
                            for msg in error_msgs
                        )
                        if schema_conflict:
                            print("")
                            print("💡 Schema Conflict Detected!")
                            print(
                                "   The new data has a different schema than existing data in Dgraph."
                            )
                            print(
                                "   Predicates cannot change from scalar to uid (relationship) or vice versa."
                            )
                            print("")
                            print("   Solutions:")
                            print("   1. Drop all existing data and reload:")
                            print(
                                "      cd app && make load-data GRAPH_FILE=<your-file> DROP_ALL=true"
                            )
                            print("")
                            print("   2. Manually fix the schema conflict in Dgraph")
                            print("")

                        raise Exception(f"Schema errors: {'; '.join(error_msgs)}")
                    else:
                        print("✅ Schema applied successfully")
                except json.JSONDecodeError:
                    # Not JSON, probably success
                    print("✅ Schema applied successfully")
                    print(f"  Response (text): {response.text[:200]}")
            else:
                print(
                    f"❌ Schema application failed with status {response.status_code}"
                )
                print(f"  Response: {response.text[:500]}")
                raise Exception(f"Schema application failed: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error applying schema: {e}")
            raise

    def load_nquads(self, nquads: List[str], schema: str = None):
        """
        Load N-Quads into Dgraph using dgraph live command.

        Args:
            nquads: List of N-Quad triples to load
            schema: Optional schema string to pass to dgraph live (prevents auto-schema)
        """
        print(f"📊 Loading {len(nquads)} triples into Dgraph...")

        # Filter out None values (skipped triples)
        nquads = [nq for nq in nquads if nq is not None]

        # Create temporary file for data
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".rdf", delete=False
        ) as data_file:
            data_file.write("\n".join(nquads))
            data_path = data_file.name

        # Create temporary file for schema (prevents dgraph live from auto-generating)
        schema_path = None
        if schema:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".schema", delete=False
            ) as schema_file:
                schema_file.write(schema)
                schema_path = schema_file.name

        try:
            # Parse dgraph URL to get host and port
            from urllib.parse import urlparse

            parsed = urlparse(self.dgraph_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 8080

            # Determine alpha gRPC and zero ports
            # Use explicitly provided ports if available (from Makefile port-forwarding)
            if self.grpc_port is not None and self.zero_port is not None:
                alpha_port = self.grpc_port
                zero_port = self.zero_port
            # Standard Dgraph ports: HTTP=8080, gRPC=9080, Zero=5080
            elif "localhost" in host or "127.0.0.1" in host:
                alpha_port = port + 1000  # HTTP 8080 -> gRPC 9080
                zero_port = port - 3000  # HTTP 8080 -> Zero 5080
            else:
                # Remote dgraph - gRPC port not accessible, skip dgraph live
                alpha_port = None
                zero_port = None

            # Try to use dgraph live command
            dgraph_cmd = None

            # Skip dgraph live if alpha_port is not available (remote dgraph)
            if alpha_port is None:
                print(f"  Remote dgraph detected - using HTTP API...")
                self._load_via_http(nquads, schema=schema)
                return
            # Check if dgraph is available locally
            if subprocess.run(["which", "dgraph"], capture_output=True).returncode == 0:
                dgraph_cmd = [
                    "dgraph",
                    "live",
                    "-f",
                    data_path,
                    "-a",
                    f"{host}:{alpha_port}",
                    "-z",
                    f"{host}:{zero_port}",
                    "--format=rdf",
                ]
                # Add schema file if provided (prevents auto-schema generation)
                if schema_path:
                    dgraph_cmd.extend(["-s", schema_path])
            # Check if Docker is available - use dgraph Docker image
            elif (
                subprocess.run(["which", "docker"], capture_output=True).returncode == 0
            ):
                # Use dgraph Docker image to run dgraph live
                print(f"  Using dgraph Docker image...")
                dgraph_cmd = [
                    "docker",
                    "run",
                    "--rm",
                    "--network=host",  # Use host network to access localhost ports
                    "-v",
                    f"{data_path}:/tmp/data.rdf:ro",
                ]
                # Mount schema file if provided
                if schema_path:
                    dgraph_cmd.extend(["-v", f"{schema_path}:/tmp/schema.txt:ro"])

                dgraph_cmd.extend(
                    [
                        "dgraph/dgraph:v23.1.1",
                        "dgraph",
                        "live",
                        "-f",
                        "/tmp/data.rdf",
                        "-a",
                        f"{host}:{alpha_port}",
                        "-z",
                        f"{host}:{zero_port}",
                        "--format=rdf",
                    ]
                )

                # Add schema flag if provided
                if schema_path:
                    dgraph_cmd.extend(["-s", "/tmp/schema.txt"])

                print(f"Running: '{' '.join(dgraph_cmd)}'")

            if dgraph_cmd:
                # Execute dgraph live command
                # Timeout: 3h for large datasets (354K+ triples)
                # Note: Loading can be slow due to indexing, especially with sparse types
                result = subprocess.run(
                    dgraph_cmd, capture_output=True, text=True, timeout=60 * 60 * 3
                )

                # dgraph live outputs to stderr even on success, check return code
                if result.returncode == 0:
                    # Check if output contains success indicators
                    output = result.stdout + result.stderr
                    if "N-Quads processed" in output or "Number of TXs run" in output:
                        print(
                            f"✅ Successfully loaded {len(nquads)} triples via dgraph live"
                        )
                        # Extract stats if available
                        for line in output.split("\n"):
                            if "N-Quads processed" in line or "Time spent" in line:
                                print(f"  {line.strip()}")
                    else:
                        print(f"⚠️  dgraph live completed but output unclear")
                        print(f"  {result.stdout[:200]}")
                else:
                    print(f"❌ dgraph live failed (exit code {result.returncode})")
                    print(f"  {result.stderr}")

                    # Check for schema conflicts in error output
                    if (
                        "Schema change not allowed" in result.stderr
                        or "scalar to uid" in result.stderr
                    ):
                        print("")
                        print("💡 Schema Conflict Detected!")
                        print(
                            "   The new data has a different schema than existing data in Dgraph."
                        )
                        print("")
                        print("   Solution: Drop all existing data and reload:")
                        print(
                            "      cd app && make load-data GRAPH_FILE=<your-file> DROP_ALL=true"
                        )
                        print("")

                    print(f"  Falling back to HTTP API...")
                    self._load_via_http(nquads, schema=schema)
            else:
                print(f"  No dgraph command available, using HTTP API...")
                self._load_via_http(nquads, schema=schema)

        finally:
            # Clean up temporary files
            try:
                os.unlink(data_path)
            except:
                pass
            if schema_path:
                try:
                    os.unlink(schema_path)
                except:
                    pass

    def _load_via_http(self, nquads: List[str], schema: str = None):
        """Fallback: Load via HTTP API (less reliable for bulk data)."""
        print(f"  ⚠️  Warning: HTTP API may not persist large datasets reliably")
        print(f"  💡 Tip: Use 'dgraph live' command manually for best results")

        # Apply schema via HTTP if provided (since we're not using dgraph live)
        if schema:
            print(f"  📝 Applying schema via HTTP...")
            self.apply_schema(schema)

        # Batch mutations for efficiency
        BATCH_SIZE = 1000
        total_loaded = 0

        for i in range(0, len(nquads), BATCH_SIZE):
            batch = nquads[i : i + BATCH_SIZE]
            rdf_data = "\n".join(batch)

            response = requests.post(
                f"{self.dgraph_url}/mutate?commitNow=true",
                data=rdf_data,
                headers={"Content-Type": "application/rdf"},
            )

            if response.status_code == 200:
                total_loaded += len(batch)
                print(f"  Loaded {total_loaded}/{len(nquads)} triples...")
            else:
                print(f"❌ Batch {i} failed: {response.text}")

        print(f"  Completed HTTP loading: {total_loaded} triples")

        if total_loaded < len(nquads):
            skipped = len(nquads) - total_loaded
            print(f"⚠️  Skipped {skipped} triples ({skipped*100//len(nquads)}%)")

    def query_stats(self):
        """Query Dgraph for statistics."""
        print("\n📊 Querying statistics...")

        query = """
        {
          stats(func: has(dgraph.type)) {
            count(uid)
          }

          types(func: has(dgraph.type)) @groupby(dgraph.type) {
            count(uid)
          }
        }
        """

        response = requests.post(
            f"{self.dgraph_url}/query",
            data=query,
            headers={"Content-Type": "application/dql"},
        )

        if response.status_code == 200:
            result = response.json()
            print(f"\n=== DGRAPH STATISTICS ===")

            if "data" in result and "stats" in result["data"]:
                total = result["data"]["stats"][0]["count"]
                print(f"Total entities: {total}")

            if "data" in result and "types" in result["data"]:
                print(f"\nEntities by type:")
                for group in result["data"]["types"]:
                    if "@groupby" in group:
                        for type_data in group["@groupby"]:
                            entity_type = type_data.get("dgraph.type")
                            count = type_data.get("count", 0)
                            print(f"  {entity_type}: {count}")
        else:
            print(f"⚠️  Could not query stats: {response.text}")

    def run(self, input_file: str):
        """Main execution flow."""
        # Load and validate
        jsonld = self.load_jsonld(input_file)

        if not self.validate_jsonld(jsonld):
            sys.exit(1)

        # Analyze schema
        self.analyze_schema(jsonld)
        schema = self.generate_schema()

        # Debug: Save schema to file for inspection
        with open("/tmp/dgraph_schema_debug.txt", "w") as f:
            f.write(schema)
        print(f"📄 Schema saved to /tmp/dgraph_schema_debug.txt for inspection")

        # Drop existing data if requested
        if self.drop_all:
            self.drop_all_data()

        # Convert to N-Quads
        nquads = self.convert_to_nquads(jsonld)

        # Load data with schema (schema passed to dgraph live, or applied via HTTP as fallback)
        # Note: Schema is NOT applied via HTTP first because dgraph live with -s flag will handle it
        self.load_nquads(nquads, schema=schema)

        # Report statistics
        self.query_stats()

        print("\n✅ Load complete!")


def main():
    parser = argparse.ArgumentParser(
        description="Load JSON-LD knowledge graph into Dgraph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load into local Dgraph
  python load_dgraph.py --input graph.jsonld

  # Clear existing data and load
  python load_dgraph.py --input graph.jsonld --drop-all

  # Load into remote Dgraph
  python load_dgraph.py --input graph.jsonld --dgraph-url http://dgraph.example.com:8080
        """,
    )

    parser.add_argument("--input", required=True, help="Path to JSON-LD input file")

    parser.add_argument(
        "--dgraph-url",
        default="http://localhost:8080",
        help="Dgraph Alpha HTTP endpoint (default: http://localhost:8080)",
    )

    parser.add_argument(
        "--grpc-port",
        type=int,
        default=None,
        help="Dgraph Alpha gRPC port (default: derived from HTTP port)",
    )

    parser.add_argument(
        "--zero-port",
        type=int,
        default=None,
        help="Dgraph Zero gRPC port (default: derived from HTTP port)",
    )

    parser.add_argument(
        "--drop-all",
        action="store_true",
        help="Drop all existing data before loading (WARNING: destructive)",
    )

    args = parser.parse_args()

    # Confirm drop-all
    if args.drop_all:
        print("⚠️  WARNING: --drop-all will delete ALL existing data in Dgraph!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower().strip() != "yes":
            print("Aborted.")
            sys.exit(0)

    # Run loader
    loader = DgraphLoader(
        args.dgraph_url,
        args.drop_all,
        grpc_port=args.grpc_port,
        zero_port=args.zero_port,
    )
    loader.run(args.input)


if __name__ == "__main__":
    main()
