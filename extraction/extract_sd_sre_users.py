#!/usr/bin/env python3
"""
Extract User entities from sd-sre user YAML files
"""

import json
import yaml
from pathlib import Path
from typing import List, Dict, Any


def extract_user_entity(file_path: Path) -> Dict[str, Any]:
    """Extract a User entity from a YAML file"""
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    org_username = data.get("org_username", "")
    entity_id = f"urn:User:{org_username}"

    entity = {
        "@id": entity_id,
        "@type": "User",
        "name": data.get("name", ""),
        "org_username": org_username,
    }

    # Add optional fields if they exist
    if "github_username" in data:
        entity["github_username"] = data["github_username"]

    if "quay_username" in data:
        entity["quay_username"] = data["quay_username"]

    if "tag_on_cluster_updates" in data:
        entity["tag_on_cluster_updates"] = data["tag_on_cluster_updates"]

    if "public_gpg_key" in data:
        entity["public_gpg_key"] = data["public_gpg_key"]

    # Extract role relationships
    if "roles" in data and data["roles"]:
        roles = []
        for role_ref in data["roles"]:
            if isinstance(role_ref, dict) and "$ref" in role_ref:
                ref_path = role_ref["$ref"]
                # Extract role name from path
                if ref_path.endswith(".yml") or ref_path.endswith(".yaml"):
                    role_name = Path(ref_path).stem
                    roles.append({"@id": f"urn:Role:{role_name}"})

        if roles:
            entity["has_role"] = roles

    return entity


def main():
    users_dir = Path(
        "/home/jsell/code/sandbox/cartograph/app-interface/data/teams/sd-sre/users"
    )

    # Get all .yml files
    user_files = sorted(users_dir.glob("*.yml"))

    entities = []
    for file_path in user_files:
        try:
            entity = extract_user_entity(file_path)
            entities.append(entity)
        except Exception as e:
            print(f"Error processing {file_path}: {e}", file=__import__("sys").stderr)

    # Create output
    output = {
        "entities": entities,
        "metadata": {
            "entity_count": len(entities),
            "types_discovered": ["User"],
            "files_processed": len(user_files),
        },
    }

    # Print JSON output
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
