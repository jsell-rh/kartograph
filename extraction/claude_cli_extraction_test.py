#!/usr/bin/env python3
"""
Test Claude CLI-based extraction approach.

Calls Claude CLI for each file to extract entities through AI reasoning.
Compares results to previous schema-guided extraction.
"""

import json
import subprocess
import yaml
from pathlib import Path

# Directories
APP_INTERFACE = Path("/home/jsell/code/sandbox/cartograph/app-interface")
SCHEMAS_DIR = Path("/home/jsell/code/sandbox/cartograph/qontract-schemas")
WORKING_DIR = Path("/home/jsell/code/kartograph-kg-iteration/extraction/working")

# Load previous extraction for comparison
PREVIOUS_EXTRACTION = WORKING_DIR / "schema_guided_full_extraction_fixed.jsonld"


def build_extraction_prompt(file_path: Path, context: dict) -> str:
    """Build detailed prompt for Claude CLI extraction."""

    prompt = f"""# Knowledge Graph Entity Extraction

## Your Task
Extract ALL entities and relationships from this file using AI reasoning.

**File**: {file_path}

**Repository Context**:
- Domain: Infrastructure configuration (app-interface)
- Available schemas: {len(context['schemas'])} JSON schemas in qontract-schemas/
- Related entities already extracted: {context['entity_count']} total

## Critical Requirements (MUST FOLLOW)

### 1. Output Format
Return ONLY valid JSON (no markdown, no explanations) in this structure:

```json
{{
  "entities": [
    {{
      "@id": "urn:entitytype:unique-identifier",
      "@type": "EntityTypeName",
      "name": "human-readable-name",
      "field1": "value1",
      "field2": {{"@id": "urn:othertype:referenced-entity"}},
      "arrayField": [
        {{"@id": "urn:type:item1"}},
        {{"@id": "urn:type:item2"}}
      ]
    }}
  ],
  "discovered_types": ["EntityTypeName", "OtherType"],
  "extraction_notes": "Brief notes about patterns you discovered"
}}
```

### 2. Entity Extraction Rules

**DISCOVER entity types from the data** - don't use a hardcoded list. Ask:
- "What things does this data describe?" (services, users, namespaces, repos, etc.)
- "What would someone want to query?" (queryability test)
- "What has independent identity?" (not just attributes)

**For EACH entity you must**:
- Generate URN: `urn:entitytype:unique-id` (lowercase, hyphens for spaces)
- Provide @type: Valid identifier (letters/numbers only, no /, [, ], ., :, -)
- Provide name: Human-readable name (REQUIRED - use fallbacks if needed)
- Extract ALL fields from source (maximum fidelity)
- Express relationships as predicates with {{"@id": "..."}} references

### 3. PROHIBITED Patterns (CRITICAL)

❌ DO NOT create entities with @type="Relationship"
  - Relationships are predicates ON entities, not separate entities

❌ DO NOT use invalid type names:
  - No: /, [, ], ., :, -, space, +, @
  - YES: "Service", "CodeRepository", "EmailAddress"
  - NO: "rhdh/backstage.io/...", "Parameters[0]", "acceptance-criteria"

❌ DO NOT skip name fields:
  - ALL entities MUST have "name"
  - Use email/url/path as name if no explicit name field
  - Use URN last segment as fallback

❌ DO NOT create indexed types:
  - NO: "Items[0]", "Parameters[1]"
  - YES: "Item", "Parameter" (generic, reusable)

### 4. Nested Entity Extraction

Extract nested objects as separate entities IF:
- Has 3+ meaningful properties
- Has independent identity/lifecycle
- Would be queried independently

Example:
```yaml
serviceOwners:
  - name: "John Doe"
    email: "jdoe@example.com"
    role: "Tech Lead"
```

Extract as User entity:
```json
{{
  "@id": "urn:user:jdoe",
  "@type": "User",
  "name": "John Doe",
  "email": "jdoe@example.com",
  "role": "Tech Lead"
}}
```

Then reference from service:
```json
{{
  "@id": "urn:service:myservice",
  "serviceOwners": [{{"@id": "urn:user:jdoe"}}]
}}
```

### 5. Pattern-Based Entity Discovery

Discover entities from VALUE PATTERNS:
- Email addresses: `user@example.com` → EmailAddress entity
- URLs: `https://github.com/org/repo` → CodeRepository entity
- Slack channels: `#team-channel` → SlackChannel entity
- File references: `$ref: /path/to/file.yml` → resolve to target entity

### 6. Schema Guidance (if available)

Schema for this file: {context['schema_hint']}

Use schema to:
- Understand entity type
- Identify required vs optional fields
- Find relationship fields ($ref patterns)

But DON'T be limited by schema - discover additional patterns!

## Examples

### Good Entity
```json
{{
  "@id": "urn:service:myapp",
  "@type": "Service",
  "name": "myapp",
  "description": "My application service",
  "grafanaUrl": "https://grafana.example.com/d/myapp",
  "slackChannel": "#myapp-team",
  "repoUrl": {{"@id": "urn:coderepository:org/myapp"}},
  "serviceOwners": [
    {{"@id": "urn:user:jdoe"}},
    {{"@id": "urn:user:asmith"}}
  ]
}}
```

### Bad Entity (DO NOT DO THIS)
```json
{{
  "@id": "urn:relationship:service-to-repo",
  "@type": "Relationship",  // ❌ WRONG - relationships are predicates
  "from": "urn:service:myapp",
  "to": "urn:repo:org/myapp",
  "relationshipType": "repoUrl"
}}
```

## Your Reasoning Process

1. Read the file and understand its structure
2. Identify the PRIMARY entity (from $schema typically)
3. Extract ALL fields from primary entity
4. Identify nested objects that should be separate entities
5. Discover pattern-based entities (emails, URLs, etc.)
6. Generate valid URNs and type names
7. Ensure all entities have name field
8. Express relationships as predicates
9. Return JSON

Focus on DISCOVERING patterns and entities, not just following templates!
"""

    return prompt


def call_claude_cli(prompt: str, file_content: str) -> dict:
    """Call Claude CLI to extract entities."""

    full_prompt = f"""{prompt}

## File Content

```yaml
{file_content}
```

Extract entities and return JSON."""

    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                "--dangerously-skip-permissions",
                "--output-format",
                "json",
                full_prompt,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            print(f"❌ Claude CLI error: {result.stderr}")
            return None

        # Parse the JSON output
        # Claude CLI with --output-format json returns array of message objects
        output = json.loads(result.stdout)

        # Extract the actual response text
        for item in output:
            if item.get("type") == "assistant":
                message = item.get("message", {})
                content = message.get("content", [])
                for block in content:
                    if block.get("type") == "text":
                        text = block.get("text", "")
                        # Try to parse as JSON
                        try:
                            # Remove markdown code blocks if present
                            text = text.strip()
                            if text.startswith("```"):
                                lines = text.split("\n")
                                text = "\n".join(lines[1:-1])
                            return json.loads(text)
                        except json.JSONDecodeError:
                            print(f"⚠️  Could not parse Claude response as JSON")
                            print(f"Response: {text[:200]}...")
                            return None

        return None

    except subprocess.TimeoutExpired:
        print(f"❌ Claude CLI timeout")
        return None
    except Exception as e:
        print(f"❌ Error calling Claude CLI: {e}")
        return None


def test_extraction():
    """Test Claude CLI extraction on sample files."""

    print("=" * 80)
    print("CLAUDE CLI EXTRACTION TEST")
    print("=" * 80)

    # Select 3 diverse sample files
    sample_files = [
        APP_INTERFACE / "data/services/app-interface/app.yml",
        APP_INTERFACE / "data/common/users/jsmith.yml",
        APP_INTERFACE / "data/teams/app-sre/escalation-policies/general.yml",
    ]

    # Load previous extraction for comparison
    print("\n📂 Loading previous extraction for comparison...")
    with open(PREVIOUS_EXTRACTION) as f:
        previous = json.load(f)
    previous_entities = previous["@graph"]
    print(f"   Previous extraction: {len(previous_entities)} entities")

    # Build context
    schemas = list(SCHEMAS_DIR.glob("**/*.yml"))
    context = {
        "schemas": schemas,
        "entity_count": len(previous_entities),
        "schema_hint": "Check $schema field in YAML",
    }

    all_extracted = []

    for file_path in sample_files:
        if not file_path.exists():
            print(f"\n⚠️  File not found: {file_path}")
            continue

        print(f"\n{'=' * 80}")
        print(f"📄 Processing: {file_path.relative_to(APP_INTERFACE)}")
        print(f"{'=' * 80}")

        # Read file
        with open(file_path) as f:
            file_content = f.read()

        # Build prompt
        prompt = build_extraction_prompt(file_path, context)

        # Call Claude
        print("🤖 Calling Claude CLI for extraction...")
        result = call_claude_cli(prompt, file_content)

        if result:
            entities = result.get("entities", [])
            discovered_types = result.get("discovered_types", [])
            notes = result.get("extraction_notes", "")

            print(f"\n✅ Extracted {len(entities)} entities")
            print(f"   Entity types: {', '.join(discovered_types)}")
            print(f"   Notes: {notes}")

            # Validate
            print("\n🔍 Validation:")
            has_relationship = any(e.get("@type") == "Relationship" for e in entities)
            print(
                f"   ❌ Relationship entities: {'YES - FAIL' if has_relationship else 'NO - PASS'}"
            )

            missing_name = [e.get("@id") for e in entities if not e.get("name")]
            print(
                f"   {'❌' if missing_name else '✅'} Name coverage: {len(entities) - len(missing_name)}/{len(entities)}"
            )
            if missing_name:
                print(f"      Missing: {missing_name}")

            invalid_types = []
            import re

            for e in entities:
                type_name = e.get("@type", "")
                if not re.match(r"^[A-Za-z][A-Za-z0-9]*$", type_name):
                    invalid_types.append(type_name)
            print(
                f"   {'❌' if invalid_types else '✅'} Type names valid: {len(entities) - len(invalid_types)}/{len(entities)}"
            )
            if invalid_types:
                print(f"      Invalid: {invalid_types}")

            # Show entities
            print(f"\n📦 Entities extracted:")
            for entity in entities:
                print(
                    f"   - {entity.get('@type')}: {entity.get('@id')} (name: {entity.get('name')})"
                )

            # Compare to previous extraction
            file_str = str(file_path)
            previous_for_file = [
                e for e in previous_entities if e.get("file_path") == file_str
            ]
            print(f"\n📊 Comparison to previous extraction:")
            print(f"   Previous: {len(previous_for_file)} entities from this file")
            print(f"   This run: {len(entities)} entities")

            all_extracted.extend(entities)
        else:
            print("❌ Extraction failed")

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total entities extracted: {len(all_extracted)}")
    print(f"Entity types: {set(e.get('@type') for e in all_extracted)}")

    # Save results
    output_file = WORKING_DIR / "claude_cli_test_results.json"
    with open(output_file, "w") as f:
        json.dump({"@context": {}, "@graph": all_extracted}, f, indent=2)
    print(f"\n💾 Saved to: {output_file}")


if __name__ == "__main__":
    test_extraction()
