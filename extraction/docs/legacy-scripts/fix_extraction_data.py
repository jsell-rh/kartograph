#!/usr/bin/env python3
"""
Fix schema_guided_full_extraction.jsonld by:
1. Converting Relationship entities to actual predicates on source entities
2. Adding name fields to EmailAddress entities
3. Removing metadata entities
"""

import json
import sys


def fix_extraction_data(input_file, output_file):
    print(f"Loading {input_file}...")

    with open(input_file, "r") as f:
        data = json.load(f)

    graph = data.get("@graph", [])
    print(f"Loaded {len(graph)} entities")

    # Create entity index by @id
    entity_index = {}
    relationships = []
    entities_to_remove = []

    for i, entity in enumerate(graph):
        entity_type = entity.get("@type")
        entity_id = entity.get("@id")

        if entity_type == "Relationship":
            relationships.append(entity)
            entities_to_remove.append(i)
        elif entity_type == "ExtractionMetadata":
            entities_to_remove.append(i)
        elif entity_id:
            entity_index[entity_id] = entity

    print(f"Found {len(relationships)} Relationship entities to convert")
    print(f"Found {len(entities_to_remove)} entities to remove")

    # Process relationships and add as predicates to source entities
    relationships_added = 0
    relationships_skipped = 0

    for rel in relationships:
        from_urn = rel.get("from")
        to_urn = rel.get("to")
        rel_type = rel.get("relationshipType")

        if not from_urn or not to_urn or not rel_type:
            relationships_skipped += 1
            continue

        # Find source entity
        source_entity = entity_index.get(from_urn)
        if not source_entity:
            relationships_skipped += 1
            continue

        # Add relationship as predicate
        if rel_type not in source_entity:
            # First occurrence - add as object reference
            source_entity[rel_type] = {"@id": to_urn}
            relationships_added += 1
        elif (
            isinstance(source_entity[rel_type], dict)
            and "@id" in source_entity[rel_type]
        ):
            # Second occurrence - convert to array
            existing = source_entity[rel_type]
            source_entity[rel_type] = [existing, {"@id": to_urn}]
            relationships_added += 1
        elif isinstance(source_entity[rel_type], list):
            # Already an array - append
            source_entity[rel_type].append({"@id": to_urn})
            relationships_added += 1
        else:
            # Predicate exists but with different format - skip to avoid conflicts
            relationships_skipped += 1

    print(f"Converted {relationships_added} relationships to predicates")
    print(
        f"Skipped {relationships_skipped} relationships (missing source or conflicts)"
    )

    # Fix EmailAddress entities - add name field
    email_fixed = 0
    for entity in entity_index.values():
        if entity.get("@type") == "EmailAddress" and (
            not entity.get("name") or entity.get("name") == ""
        ):
            # Use email field as name, or extract from URN
            if "email" in entity and entity["email"]:
                entity["name"] = entity["email"]
                email_fixed += 1
            elif "@id" in entity:
                # Extract from URN: urn:emailaddress:user_domain.com -> user@domain.com
                urn_parts = entity["@id"].split(":", 2)
                if len(urn_parts) == 3:
                    # Convert underscores back to @ and + symbols
                    name_part = urn_parts[2].replace("_", "@", 1)
                    entity["name"] = name_part
                    email_fixed += 1

    print(f"Fixed {email_fixed} EmailAddress entities by adding name field")

    # Remove Relationship and ExtractionMetadata entities
    new_graph = [
        entity for i, entity in enumerate(graph) if i not in entities_to_remove
    ]

    print(f"Removed {len(entities_to_remove)} entities")
    print(f"Final entity count: {len(new_graph)}")

    # Validate all entities have required fields
    missing_name = []
    missing_type = []
    missing_id = []

    for entity in new_graph:
        if not entity.get("@id"):
            missing_id.append(entity)
        if not entity.get("@type"):
            missing_type.append(entity)
        if not entity.get("name") or entity.get("name") == "":
            missing_name.append(
                f"{entity.get('@type', 'Unknown')}:{entity.get('@id', 'no-id')}"
            )

    print(f"\nValidation:")
    print(f"  Entities missing @id: {len(missing_id)}")
    print(f"  Entities missing @type: {len(missing_type)}")
    print(f"  Entities missing name: {len(missing_name)}")

    if missing_name:
        print(f"\nFirst 10 entities missing name:")
        for entity_ref in missing_name[:10]:
            print(f"  - {entity_ref}")

    # Write fixed data
    data["@graph"] = new_graph

    print(f"\nWriting to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print("Done!")
    print(f"\nSummary:")
    print(f"  Input entities: {len(graph)}")
    print(f"  Output entities: {len(new_graph)}")
    print(f"  Relationships converted: {relationships_added}")
    print(f"  EmailAddresses fixed: {email_fixed}")
    print(f"  Entities removed: {len(entities_to_remove)}")


if __name__ == "__main__":
    input_file = "/home/jsell/code/kartograph-kg-iteration/extraction/working/schema_guided_full_extraction.jsonld"
    output_file = "/home/jsell/code/kartograph-kg-iteration/extraction/working/schema_guided_full_extraction_fixed.jsonld"

    fix_extraction_data(input_file, output_file)
