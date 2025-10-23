#!/usr/bin/env python3
"""
Full-scale Claude CLI-based extraction.

Calls Claude CLI for each file, providing schema paths as file references.
Claude reads the schemas directly - no need to embed them in prompts.
"""

import json
import subprocess
import yaml
from pathlib import Path
from typing import Optional

# Directories
APP_INTERFACE = Path("/home/jsell/code/sandbox/cartograph/app-interface")
SCHEMAS_DIR = Path("/home/jsell/code/sandbox/cartograph/qontract-schemas")
WORKING_DIR = Path("/home/jsell/code/kartograph-kg-iteration/extraction/working")


def get_schema_path(file_path: Path) -> Optional[Path]:
    """Extract $schema reference from YAML and find schema file."""
    try:
        with open(file_path) as f:
            data = yaml.safe_load(f)

        if not data or not isinstance(data, dict):
            return None

        schema_ref = data.get("$schema")
        if not schema_ref:
            return None

        # Schema ref is usually like: /app-interface/app-1.yml
        # Convert to actual file path
        schema_file = SCHEMAS_DIR / schema_ref.lstrip("/")

        if schema_file.exists():
            return schema_file

        return None
    except Exception as e:
        print(f"⚠️  Could not determine schema for {file_path}: {e}")
        return None


def build_extraction_prompt(
    file_path: Path, schema_path: Optional[Path], entity_summary: dict
) -> str:
    """Build extraction prompt with file path references."""

    schema_instruction = ""
    if schema_path:
        schema_instruction = f"""
### Schema Available

The schema for this file is located at:
**{schema_path}**

Read this schema file to understand:
- Entity type (usually from filename like "app-1.yml" → App entity)
- Required vs optional fields
- Field types and validation rules
- Relationship patterns ($ref fields)

The schema defines the FORMAL structure, but you should also:
- Extract ALL fields present (maximum fidelity)
- Discover pattern-based entities (emails, URLs, etc.)
- Apply nested entity extraction where appropriate
"""
    else:
        schema_instruction = """
### No Formal Schema

This file doesn't have a $schema reference. Use AI reasoning to:
- Infer entity type from file path and content
- Discover all fields and relationships
- Apply pattern-based entity discovery
"""

    prompt = f"""# Knowledge Graph Entity Extraction

## Your Task

Extract ALL entities and relationships from this file.

**File to extract**: {file_path}

**Additional context**:
- Repository: app-interface (infrastructure configuration)
- Schemas directory: {SCHEMAS_DIR}
- Already extracted: {entity_summary['total_entities']} entities across {entity_summary['total_types']} types

{schema_instruction}

## CRITICAL Requirements

### Output Format (REQUIRED)

Return ONLY valid JSON (no markdown, no code blocks) in this exact structure:

```json
{{
  "entities": [
    {{
      "@id": "urn:entitytype:unique-identifier",
      "@type": "EntityTypeName",
      "name": "human-readable-name",
      "otherField": "value",
      "relationshipField": {{"@id": "urn:othertype:target"}}
    }}
  ],
  "discovered_types": ["EntityTypeName"],
  "extraction_notes": "Brief notes"
}}
```

### PROHIBITED Patterns (CRITICAL - MUST NOT DO)

❌ DO NOT create @type="Relationship" entities
   - Relationships are predicates ON entities, not separate entities
   - Use: {{"repoUrl": {{"@id": "urn:repo:foo"}}}}
   - NOT: {{"@type": "Relationship", "from": "...", "to": "..."}}

❌ DO NOT use invalid type names
   - ONLY letters and numbers, must start with letter
   - NO: /, [, ], ., :, -, space, +, @
   - YES: "Service", "CodeRepository", "EmailAddress"
   - NO: "rhdh/backstage.io/...", "Parameters[0]", "acceptance-criteria"

❌ DO NOT skip name fields
   - ALL entities MUST have "name" field
   - Use email/url/path as name if no explicit name
   - Use URN last segment as fallback

❌ DO NOT create indexed types for arrays
   - NO: "Items[0]", "Parameters[1]"
   - YES: "Item", "Parameter" (generic types)

### Entity Discovery Process

1. **Read the file** at {file_path}
2. **Read the schema** at {schema_path if schema_path else 'N/A'} (if available)
3. **Identify PRIMARY entity** (from schema or file structure)
4. **Extract ALL fields** from primary entity (maximum fidelity)
5. **Discover nested entities** (3+ properties, independent identity)
6. **Discover pattern entities** (emails, URLs, Slack channels, $refs)
7. **Generate valid URNs** (lowercase, hyphens)
8. **Ensure all have name field**
9. **Express relationships as predicates** (not separate entities)

### Nested Entity Extraction

Extract nested objects as separate entities IF:
- Has 3+ meaningful properties
- Has independent identity/lifecycle
- Would be queried independently

Example nested object that should be extracted:
```yaml
serviceOwners:
  - name: "John Doe"
    email: "jdoe@example.com"
    role: "Tech Lead"
```

Becomes User entity + reference:
```json
{{
  "@id": "urn:user:jdoe",
  "@type": "User",
  "name": "John Doe",
  "email": "jdoe@example.com",
  "role": "Tech Lead"
}}
```

### Pattern-Based Discovery

Discover entities from value patterns:
- Email: user@example.com → EmailAddress entity
- GitHub URL: https://github.com/org/repo → CodeRepository entity
- Slack: #team-channel → SlackChannel entity
- File refs: $ref: /path/file.yml → resolve to target entity URN

## Additional Resources

You can read other files if needed:
- Schema directory: {SCHEMAS_DIR}
- Related files in app-interface (for $ref resolution)

Use your file reading capabilities to get full context!

Now extract from {file_path} and return JSON only.
"""
    return prompt


def call_claude_cli(prompt: str) -> Optional[dict]:
    """Call Claude CLI with file path references."""

    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                "--dangerously-skip-permissions",
                "--output-format",
                "json",
                prompt,
            ],
            capture_output=True,
            text=True,
            timeout=180,  # 3 min per file
        )

        if result.returncode != 0:
            return None

        # Parse Claude CLI JSON output
        output = json.loads(result.stdout)

        # Extract response text from LAST assistant message (Claude uses tools first)
        assistant_messages = [
            item for item in output if item.get("type") == "assistant"
        ]

        if not assistant_messages:
            return None

        # Get the last assistant message (final response after tool use)
        last_message = assistant_messages[-1]
        message = last_message.get("message", {})
        content = message.get("content", [])

        for block in content:
            if block.get("type") == "text":
                text = block.get("text", "").strip()

                # Remove markdown code blocks if present
                if text.startswith("```"):
                    lines = text.split("\n")
                    # Find first line without ``` and last line without ```
                    start = 1 if lines[0].startswith("```") else 0
                    end = -1 if lines[-1].startswith("```") else len(lines)
                    text = "\n".join(lines[start:end])

                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    # Text might contain explanation before JSON
                    # Try to find JSON in the text
                    import re

                    json_match = re.search(r"\{[\s\S]*\}", text)
                    if json_match:
                        return json.loads(json_match.group(0))
                    return None

        return None

    except subprocess.TimeoutExpired:
        print(f"    ⏱️  Timeout")
        return None
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return None


def validate_entities(entities: list) -> dict:
    """Validate extracted entities against standards."""
    import re

    validation = {
        "total": len(entities),
        "relationship_entities": 0,
        "missing_name": [],
        "invalid_types": [],
        "valid": True,
    }

    for entity in entities:
        # Check for Relationship entities
        if entity.get("@type") == "Relationship":
            validation["relationship_entities"] += 1
            validation["valid"] = False

        # Check name field
        if not entity.get("name"):
            validation["missing_name"].append(entity.get("@id", "unknown"))
            validation["valid"] = False

        # Check type name format
        type_name = entity.get("@type", "")
        if not re.match(r"^[A-Za-z][A-Za-z0-9]*$", type_name):
            validation["invalid_types"].append(type_name)
            validation["valid"] = False

    return validation


def main():
    """Run full-scale extraction."""

    print("=" * 80)
    print("CLAUDE CLI FULL-SCALE EXTRACTION")
    print("=" * 80)

    # Find all YAML files
    all_files = list(APP_INTERFACE.glob("data/**/*.yml"))
    print(f"\n📂 Found {len(all_files)} YAML files in app-interface")

    # Entity summary for context
    entity_summary = {"total_entities": 0, "total_types": 0}

    all_entities = []
    all_types = set()
    failed_files = []

    # Process files
    for i, file_path in enumerate(all_files, 1):
        print(f"\n[{i}/{len(all_files)}] {file_path.relative_to(APP_INTERFACE)}")

        # Get schema path
        schema_path = get_schema_path(file_path)
        if schema_path:
            print(f"    📋 Schema: {schema_path.relative_to(SCHEMAS_DIR)}")

        # Build prompt
        prompt = build_extraction_prompt(file_path, schema_path, entity_summary)

        # Call Claude
        print(f"    🤖 Extracting...", end=" ", flush=True)
        result = call_claude_cli(prompt)

        if not result or "entities" not in result:
            print("❌ Failed")
            failed_files.append(file_path)
            continue

        entities = result["entities"]

        # Validate
        validation = validate_entities(entities)

        if not validation["valid"]:
            print(f"❌ Validation failed")
            if validation["relationship_entities"]:
                print(
                    f"       Relationship entities: {validation['relationship_entities']}"
                )
            if validation["missing_name"]:
                print(f"       Missing names: {len(validation['missing_name'])}")
            if validation["invalid_types"]:
                print(f"       Invalid types: {validation['invalid_types'][:3]}")
            failed_files.append(file_path)
            continue

        # Success
        print(f"✅ {len(entities)} entities")

        # Track discovered types
        for entity in entities:
            all_types.add(entity["@type"])

        all_entities.extend(entities)

        # Update summary
        entity_summary["total_entities"] = len(all_entities)
        entity_summary["total_types"] = len(all_types)

        # Progress checkpoint every 100 files
        if i % 100 == 0:
            print(
                f"\n📊 Progress: {len(all_entities)} entities, {len(all_types)} types"
            )

    # Final summary
    print(f"\n{'=' * 80}")
    print("EXTRACTION COMPLETE")
    print(f"{'=' * 80}")
    print(f"Files processed: {len(all_files)}")
    print(f"Files failed: {len(failed_files)}")
    print(f"Total entities: {len(all_entities)}")
    print(f"Entity types discovered: {len(all_types)}")
    print(f"\nEntity types: {sorted(all_types)}")

    # Save output
    output_file = WORKING_DIR / "claude_cli_full_extraction.jsonld"
    output_data = {
        "@context": {"@vocab": "http://example.org/vocab#"},
        "@graph": all_entities,
    }

    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\n💾 Saved to: {output_file}")

    # Save failed files list
    if failed_files:
        failed_file = WORKING_DIR / "claude_cli_failed_files.txt"
        with open(failed_file, "w") as f:
            for path in failed_files:
                f.write(f"{path}\n")
        print(f"⚠️  Failed files saved to: {failed_file}")


if __name__ == "__main__":
    main()
