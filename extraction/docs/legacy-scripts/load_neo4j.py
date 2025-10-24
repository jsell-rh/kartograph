#!/usr/bin/env python3
"""
Load JSON-LD knowledge graph into Neo4j.

Converts JSON-LD format to Cypher CREATE statements and loads via Bolt protocol.
Validates data before loading and creates indexes automatically.

Usage:
    python load_neo4j.py --input graph.jsonld --uri bolt://localhost:7687
    python load_neo4j.py --input graph.jsonld --clear  # Clear existing data
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Set

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable, AuthError
except ImportError:
    print("❌ neo4j driver not installed. Install with: pip install neo4j")
    sys.exit(1)


class Neo4jLoader:
    def __init__(self, uri: str, username: str, password: str, clear: bool = False):
        self.uri = uri
        self.username = username
        self.password = password
        self.clear = clear
        self.driver = None
        self.entity_types: Set[str] = set()
        self.relationship_types: Set[str] = set()

    def connect(self):
        """Connect to Neo4j database."""
        print(f"🔌 Connecting to Neo4j at {self.uri}...")

        try:
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.username, self.password)
            )

            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()

            print("✅ Connected to Neo4j")

        except AuthError:
            print("❌ Authentication failed. Check username/password.")
            sys.exit(1)
        except ServiceUnavailable:
            print(f"❌ Could not connect to Neo4j at {self.uri}")
            sys.exit(1)

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

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

    def analyze_graph(self, jsonld: Dict[str, Any]):
        """Analyze JSON-LD to identify entity and relationship types."""
        print("🔬 Analyzing graph structure...")

        entities = jsonld["@graph"]

        for entity in entities:
            # Collect entity types
            entity_type = entity.get("@type")
            if entity_type:
                self.entity_types.add(entity_type)

            # Collect relationship types
            for key, value in entity.items():
                if key in ["@id", "@type", "name", "description"]:
                    continue

                # Check if it's a relationship
                is_relationship = False

                if isinstance(value, dict) and "@id" in value:
                    is_relationship = True
                elif isinstance(value, list):
                    if value and isinstance(value[0], dict) and "@id" in value[0]:
                        is_relationship = True

                if is_relationship:
                    self.relationship_types.add(key)

        print(f"  Found {len(self.entity_types)} entity types")
        print(f"  Found {len(self.relationship_types)} relationship types")

    def clear_database(self):
        """Delete all nodes and relationships."""
        print("🗑️  Clearing all data from Neo4j...")

        with self.driver.session() as session:
            result = session.run("MATCH (n) DETACH DELETE n")
            print("✅ All data cleared")

    def create_constraints(self):
        """Create constraints and indexes."""
        print("📝 Creating constraints and indexes...")

        with self.driver.session() as session:
            # Create uniqueness constraint on @id for each entity type
            for entity_type in self.entity_types:
                try:
                    session.run(
                        f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{entity_type}) "
                        f"REQUIRE n.id IS UNIQUE"
                    )
                except Exception as e:
                    # Constraint may already exist
                    pass

            # Create index on name property
            try:
                session.run("CREATE INDEX IF NOT EXISTS FOR (n) ON (n.name)")
            except Exception as e:
                pass

        print("✅ Constraints and indexes created")

    def load_entities(self, jsonld: Dict[str, Any]):
        """Load entities as nodes."""
        print("📊 Loading entities as nodes...")

        entities = jsonld["@graph"]

        # Create nodes in batches for efficiency
        BATCH_SIZE = 1000

        with self.driver.session() as session:
            for i in range(0, len(entities), BATCH_SIZE):
                batch = entities[i : i + BATCH_SIZE]

                # Build UNWIND query for batch
                nodes_data = []

                for entity in batch:
                    # Extract properties (exclude relationships)
                    properties = {
                        "id": entity["@id"],
                        "type": entity.get("@type", "Unknown"),
                    }

                    for key, value in entity.items():
                        if key in ["@id", "@type"]:
                            continue

                        # Skip relationships (will be created separately)
                        is_relationship = False
                        if isinstance(value, dict) and "@id" in value:
                            is_relationship = True
                        elif isinstance(value, list):
                            if (
                                value
                                and isinstance(value[0], dict)
                                and "@id" in value[0]
                            ):
                                is_relationship = True

                        if not is_relationship:
                            # Store scalar values or serialize complex ones
                            if isinstance(value, (str, int, float, bool)):
                                properties[key] = value
                            elif isinstance(value, list):
                                # Array of scalars
                                if all(
                                    isinstance(v, (str, int, float, bool))
                                    for v in value
                                ):
                                    properties[key] = value
                                else:
                                    # Serialize as JSON
                                    properties[key] = json.dumps(value)
                            else:
                                properties[key] = json.dumps(value)

                    nodes_data.append(properties)

                # Execute batch insert
                query = """
                UNWIND $nodes AS node
                CREATE (n)
                SET n = node
                SET n:Entity
                """

                # Add label based on type
                for entity_type in self.entity_types:
                    query += f"""
                    FOREACH (_ IN CASE WHEN node.type = '{entity_type}' THEN [1] ELSE [] END |
                        SET n:{entity_type}
                    )
                    """

                session.run(query, nodes=nodes_data)

                print(
                    f"  Loaded {min(i+BATCH_SIZE, len(entities))}/{len(entities)} nodes..."
                )

        print(f"✅ Loaded {len(entities)} nodes")

    def load_relationships(self, jsonld: Dict[str, Any]):
        """Load relationships as edges."""
        print("📊 Loading relationships...")

        entities = jsonld["@graph"]
        total_relationships = 0

        with self.driver.session() as session:
            for entity in entities:
                source_id = entity["@id"]

                for key, value in entity.items():
                    if key in ["@id", "@type", "name", "description"]:
                        continue

                    # Process relationships
                    if isinstance(value, dict) and "@id" in value:
                        # Single relationship
                        target_id = value["@id"]

                        session.run(
                            f"""
                            MATCH (source {{id: $source_id}})
                            MATCH (target {{id: $target_id}})
                            CREATE (source)-[:{self._sanitize_relationship_name(key)}]->(target)
                            """,
                            source_id=source_id,
                            target_id=target_id,
                        )

                        total_relationships += 1

                    elif isinstance(value, list):
                        # Array of relationships
                        for item in value:
                            if isinstance(item, dict) and "@id" in item:
                                target_id = item["@id"]

                                session.run(
                                    f"""
                                    MATCH (source {{id: $source_id}})
                                    MATCH (target {{id: $target_id}})
                                    CREATE (source)-[:{self._sanitize_relationship_name(key)}]->(target)
                                    """,
                                    source_id=source_id,
                                    target_id=target_id,
                                )

                                total_relationships += 1

                # Progress reporting
                if total_relationships % 1000 == 0:
                    print(f"  Loaded {total_relationships} relationships...")

        print(f"✅ Loaded {total_relationships} relationships")

    def _sanitize_relationship_name(self, name: str) -> str:
        """Sanitize relationship name for Cypher."""
        # Replace special characters with underscores
        sanitized = name.replace(":", "_").replace("@", "").replace("-", "_")
        return sanitized.upper()

    def query_stats(self):
        """Query Neo4j for statistics."""
        print("\n📊 Querying statistics...")

        with self.driver.session() as session:
            # Count nodes
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()["count"]

            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]

            # Count by label
            result = session.run(
                """
                MATCH (n)
                RETURN labels(n) as labels, count(n) as count
                ORDER BY count DESC
            """
            )

            print(f"\n=== NEO4J STATISTICS ===")
            print(f"Total nodes: {node_count}")
            print(f"Total relationships: {rel_count}")

            print(f"\nNodes by type:")
            for record in result:
                labels = [l for l in record["labels"] if l != "Entity"]
                if labels:
                    label = labels[0]
                    count = record["count"]
                    print(f"  {label}: {count}")

    def run(self, input_file: str):
        """Main execution flow."""
        # Connect
        self.connect()

        try:
            # Load and validate
            jsonld = self.load_jsonld(input_file)

            if not self.validate_jsonld(jsonld):
                sys.exit(1)

            # Analyze and prepare
            self.analyze_graph(jsonld)

            # Clear if requested
            if self.clear:
                self.clear_database()

            # Create constraints
            self.create_constraints()

            # Load data
            self.load_entities(jsonld)
            self.load_relationships(jsonld)

            # Report statistics
            self.query_stats()

            print("\n✅ Load complete!")

        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(
        description="Load JSON-LD knowledge graph into Neo4j",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load into local Neo4j
  python load_neo4j.py --input graph.jsonld

  # Clear existing data and load
  python load_neo4j.py --input graph.jsonld --clear

  # Load into remote Neo4j
  python load_neo4j.py --input graph.jsonld \\
    --uri bolt://neo4j.example.com:7687 \\
    --username neo4j \\
    --password secret
        """,
    )

    parser.add_argument("--input", required=True, help="Path to JSON-LD input file")

    parser.add_argument(
        "--uri",
        default="bolt://localhost:7687",
        help="Neo4j Bolt URI (default: bolt://localhost:7687)",
    )

    parser.add_argument(
        "--username", default="neo4j", help="Neo4j username (default: neo4j)"
    )

    parser.add_argument(
        "--password", help="Neo4j password (or set NEO4J_PASSWORD environment variable)"
    )

    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all existing data before loading (WARNING: destructive)",
    )

    args = parser.parse_args()

    # Get password from env if not provided
    if not args.password:
        import os

        args.password = os.environ.get("NEO4J_PASSWORD")
        if not args.password:
            print(
                "❌ Password required. Use --password or set NEO4J_PASSWORD environment variable."
            )
            sys.exit(1)

    # Confirm clear
    if args.clear:
        print("⚠️  WARNING: --clear will delete ALL existing data in Neo4j!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    # Run loader
    loader = Neo4jLoader(args.uri, args.username, args.password, args.clear)
    loader.run(args.input)


if __name__ == "__main__":
    main()
