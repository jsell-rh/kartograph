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
    def __init__(self, dgraph_url: str, drop_all: bool = False):
        self.dgraph_url = dgraph_url.rstrip("/")
        self.drop_all = drop_all
        self.predicate_types: Dict[str, str] = {}
        self.relationship_predicates: Set[str] = set()
        self.entity_types: Set[str] = set()

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
        """Analyze JSON-LD to infer Dgraph schema."""
        print("🔬 Analyzing schema...")

        entities = jsonld["@graph"]
        context = jsonld.get("@context", {})

        # Analyze entities to determine predicate types and collect entity types
        for entity in entities:
            # Collect entity types for schema generation
            if "@type" in entity:
                entity_type = entity["@type"]
                if isinstance(entity_type, list):
                    self.entity_types.update(entity_type)
                else:
                    self.entity_types.add(entity_type)

            for key, value in entity.items():
                if key in ["@id", "@type"]:
                    continue

                # Check if it's a relationship (reference to another entity)
                is_relationship = False

                if isinstance(value, dict) and "@id" in value:
                    is_relationship = True
                elif isinstance(value, list):
                    if value and isinstance(value[0], dict) and "@id" in value[0]:
                        is_relationship = True

                if is_relationship:
                    self.relationship_predicates.add(key)
                    self.predicate_types[key] = "uid"
                elif key not in self.predicate_types:
                    # Infer scalar type
                    if isinstance(value, bool):
                        self.predicate_types[key] = "bool"
                    elif isinstance(value, int):
                        self.predicate_types[key] = "int"
                    elif isinstance(value, float):
                        self.predicate_types[key] = "float"
                    else:
                        self.predicate_types[key] = "string"

        print(f"  Found {len(self.predicate_types)} predicates")
        print(f"  Found {len(self.relationship_predicates)} relationships")
        print(f"  Found {len(self.entity_types)} entity types")

    def generate_schema(self) -> str:
        """Generate Dgraph schema from inferred types."""
        schema_lines = []

        # Define Dgraph types for expand(_all_) support
        # All types include all predicates for simplicity
        all_predicates = []
        for predicate in sorted(self.predicate_types.keys()):
            clean_predicate = self._encode_predicate(predicate)
            all_predicates.append(f"  {clean_predicate}")

        for entity_type in sorted(self.entity_types):
            schema_lines.append(f"type {entity_type} {{")
            schema_lines.extend(all_predicates)
            schema_lines.append("}")

        schema_lines.append("")  # Blank line for readability

        # Predicates that should be indexed for fast queries
        indexed_predicates = {"name", "url", "email", "id", "path", "namespace"}

        # Add type predicate (from @type in JSON-LD) with index first
        schema_lines.append("type: string @index(exact, term) .")

        # Add type definitions
        for predicate, pred_type in sorted(self.predicate_types.items()):
            # Use simple clean predicate name
            clean_predicate = self._encode_predicate(predicate)

            if pred_type == "uid":
                # Relationship with reverse edge
                schema_lines.append(f"{clean_predicate}: [uid] @reverse .")
            else:
                # Add indexes for key predicates
                if predicate in indexed_predicates:
                    if pred_type == "string":
                        # Add trigram, fulltext, and standard indexes for name predicate
                        # trigram is required for regexp() matching
                        if predicate == "name":
                            schema_lines.append(
                                f"{clean_predicate}: {pred_type} @index(exact, term, fulltext, trigram) ."
                            )
                        else:
                            schema_lines.append(
                                f"{clean_predicate}: {pred_type} @index(exact, term, trigram) ."
                            )
                    elif pred_type == "int":
                        schema_lines.append(
                            f"{clean_predicate}: {pred_type} @index(int) ."
                        )
                    elif pred_type == "bool":
                        schema_lines.append(
                            f"{clean_predicate}: {pred_type} @index(bool) ."
                        )
                    elif pred_type == "float":
                        schema_lines.append(
                            f"{clean_predicate}: {pred_type} @index(float) ."
                        )
                    else:
                        schema_lines.append(f"{clean_predicate}: {pred_type} .")
                else:
                    # Scalar type without index
                    schema_lines.append(f"{clean_predicate}: {pred_type} .")

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
                            # Nested object (serialize as JSON string)
                            obj_str = json.dumps(item).replace('"', '\\"')
                            nquads.append(f'{subject} <{predicate}> "{obj_str}" .')
                        else:
                            obj = self._format_literal(item)
                            if obj:  # Only add if not None
                                nquads.append(f"{subject} <{predicate}> {obj} .")

                else:
                    # Scalar value
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
        """Clean predicate name (strip @ prefix)."""
        # Strip @ prefix if present (e.g., @type -> type)
        return predicate.lstrip("@")

    def _format_literal(self, value: Any) -> str:
        """Format literal value for N-Quads."""
        # Skip None values
        if value is None:
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
            # Skip if contains complex characters or "None" string
            if "{{" in value_str or "}}" in value_str or value_str == "None":
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

        response = requests.post(
            f"{self.dgraph_url}/alter",
            data=schema,
            headers={"Content-Type": "text/plain"},
        )

        if response.status_code == 200:
            print("✅ Schema applied")
        else:
            print(f"⚠️  Schema application returned: {response.text}")
            # Continue anyway - schema may be partially applied

    def load_nquads(self, nquads: List[str], schema: str):
        """Load N-Quads into Dgraph using dgraph live command."""
        print(f"📊 Loading {len(nquads)} triples into Dgraph...")

        # Filter out None values (skipped triples)
        nquads = [nq for nq in nquads if nq is not None]

        # Create temporary files for schema and data
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as schema_file:
            schema_file.write(schema)
            schema_path = schema_file.name

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".rdf", delete=False
        ) as data_file:
            data_file.write("\n".join(nquads))
            data_path = data_file.name

        try:
            # Parse dgraph URL to get host and port
            from urllib.parse import urlparse

            parsed = urlparse(self.dgraph_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 8080

            # Determine alpha gRPC and zero ports
            # Makefile sets: HTTP=8082, gRPC=9081, Zero=5081 (all increment together)
            if "localhost" in host or "127.0.0.1" in host:
                alpha_port = port + 999  # HTTP 8082 -> gRPC 9081
                zero_port = port - 3001  # HTTP 8082 -> Zero 5081
            else:
                # Remote dgraph - gRPC port not accessible, skip dgraph live
                alpha_port = None
                zero_port = None

            # Try to use dgraph live command
            dgraph_cmd = None

            # Skip dgraph live if alpha_port is not available (remote dgraph)
            if alpha_port is None:
                print(f"  Remote dgraph detected - using HTTP API...")
                self._load_via_http(nquads)
            # Check if dgraph is available locally
            if subprocess.run(["which", "dgraph"], capture_output=True).returncode == 0:
                dgraph_cmd = [
                    "dgraph",
                    "live",
                    "-f",
                    data_path,
                    "-s",
                    schema_path,
                    "-a",
                    f"{host}:{alpha_port}",
                    "-z",
                    f"{host}:{zero_port}",
                    "--format=rdf",
                ]
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
                    "-v",
                    f"{schema_path}:/tmp/schema.txt:ro",
                    "dgraph/dgraph:v23.1.1",
                    "dgraph",
                    "live",
                    "-f",
                    "/tmp/data.rdf",
                    "-s",
                    "/tmp/schema.txt",
                    "-a",
                    f"{host}:{alpha_port}",
                    "-z",
                    f"{host}:{zero_port}",
                    "--format=rdf",
                ]
                print(f"Running: '{' '.join(dgraph_cmd)}'")

            if dgraph_cmd:
                # Execute dgraph live command
                result = subprocess.run(
                    dgraph_cmd, capture_output=True, text=True, timeout=300
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
                    print(f"  Falling back to HTTP API...")
                    self._load_via_http(nquads)
            else:
                print(f"  No dgraph command available, using HTTP API...")
                self._load_via_http(nquads)

        finally:
            # Clean up temporary files
            try:
                os.unlink(schema_path)
                os.unlink(data_path)
            except:
                pass

    def _load_via_http(self, nquads: List[str]):
        """Fallback: Load via HTTP API (less reliable for bulk data)."""
        print(f"  ⚠️  Warning: HTTP API may not persist large datasets reliably")
        print(f"  💡 Tip: Use 'dgraph live' command manually for best results")

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

        # Drop existing data if requested
        if self.drop_all:
            self.drop_all_data()

        # Apply schema BEFORE loading data (critical for reverse indexes)
        self.apply_schema(schema)

        # Convert to N-Quads and load via dgraph live
        nquads = self.convert_to_nquads(jsonld)
        self.load_nquads(nquads, schema)

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
        "--drop-all",
        action="store_true",
        help="Drop all existing data before loading (WARNING: destructive)",
    )

    args = parser.parse_args()

    # Confirm drop-all
    if args.drop_all:
        print("⚠️  WARNING: --drop-all will delete ALL existing data in Dgraph!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    # Run loader
    loader = DgraphLoader(args.dgraph_url, args.drop_all)
    loader.run(args.input)


if __name__ == "__main__":
    main()
