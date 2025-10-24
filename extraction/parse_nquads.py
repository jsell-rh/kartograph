#!/usr/bin/env python3
"""Parse N-Quads file and convert to JSON-LD entities."""

import re
import json
from collections import defaultdict
from typing import Dict, List, Any


def parse_nquad_line(line: str) -> tuple:
    """Parse a single N-Quad line into (subject, predicate, object)."""
    # Match pattern: <subject> <predicate> "literal" .
    # or <subject> <predicate> <object> .
    match = re.match(r"<([^>]+)>\s+<([^>]+)>\s+(.+)\s+\.$", line.strip())
    if not match:
        return None

    subject, predicate, obj = match.groups()

    # Extract object value
    if obj.startswith('"'):
        # String literal - extract without quotes
        obj_match = re.match(r'"((?:[^"\\]|\\.)*)"', obj)
        if obj_match:
            obj_value = obj_match.group(1)
        else:
            obj_value = obj.strip('"')
    elif obj.startswith("<") and obj.endswith(">"):
        # URI reference
        obj_value = obj[1:-1]
    else:
        obj_value = obj

    return subject, predicate, obj_value


def extract_entity_id_and_type(urn: str) -> tuple:
    """Extract type and ID from a URN like urn:route:grafana-via-openshift."""
    parts = urn.split(":", 2)
    if len(parts) >= 3 and parts[0] == "urn":
        entity_type = parts[1]
        entity_id = parts[2]
        # Capitalize type for proper entity types
        entity_type = entity_type.replace("-", "_").title().replace("_", "")
        # Handle special cases
        if entity_type == "K8sService":
            entity_type = "KubernetesService"
        elif entity_type == "ServiceMonitor":
            entity_type = "ServiceMonitor"
        elif entity_type == "PrometheusRules":
            entity_type = "PrometheusRules"
        return entity_type, entity_id
    return None, None


def predicate_to_property(predicate: str) -> str:
    """Convert predicate URN to property name."""
    if predicate.startswith("urn:predicate:"):
        return predicate.replace("urn:predicate:", "")
    return predicate


def build_entities(nquads_file: str) -> Dict[str, Any]:
    """Build entities from N-Quads file."""
    entities_map = defaultdict(lambda: {"properties": defaultdict(list)})
    types_discovered = set()

    with open(nquads_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parsed = parse_nquad_line(line)
            if not parsed:
                continue

            subject, predicate, obj = parsed

            # Extract entity type and ID
            entity_type, entity_id = extract_entity_id_and_type(subject)
            if not entity_type:
                continue

            # Store entity
            entity_key = subject
            if "@id" not in entities_map[entity_key]:
                entities_map[entity_key]["@id"] = subject

            # Convert predicate to property name
            prop_name = predicate_to_property(predicate)

            # Handle special properties
            if prop_name == "type":
                entities_map[entity_key]["@type"] = obj
                types_discovered.add(obj)
            elif prop_name == "name":
                entities_map[entity_key]["name"] = obj
            else:
                # Check if object is a URN reference
                if obj.startswith("urn:"):
                    # It's a relationship
                    entities_map[entity_key]["properties"][prop_name].append(
                        {"@id": obj}
                    )
                else:
                    # It's a literal value
                    entities_map[entity_key]["properties"][prop_name].append(obj)

    # Convert to final format
    final_entities = []
    for entity_key, entity_data in entities_map.items():
        entity = {
            "@id": entity_data["@id"],
            "@type": entity_data.get("@type", "Entity"),
            "name": entity_data.get("name", entity_key.split(":")[-1]),
        }

        # Add all other properties
        for prop_name, values in entity_data["properties"].items():
            if len(values) == 1:
                entity[prop_name] = values[0]
            elif len(values) > 1:
                entity[prop_name] = values

        final_entities.append(entity)

    return {
        "entities": final_entities,
        "metadata": {
            "entity_count": len(final_entities),
            "types_discovered": sorted(list(types_discovered)),
            "files_processed": 2,
        },
    }


if __name__ == "__main__":
    import sys

    nquads_file = (
        "/home/jsell/code/sandbox/cartograph/app-interface/batch9-14-extracted.nq"
    )

    print("Parsing N-Quads file...", file=sys.stderr)
    result = build_entities(nquads_file)

    print(f"Extracted {result['metadata']['entity_count']} entities", file=sys.stderr)
    print(
        f"Types discovered: {', '.join(result['metadata']['types_discovered'])}",
        file=sys.stderr,
    )

    # Output JSON
    print(json.dumps(result, indent=2))
