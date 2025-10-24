# Knowledge Graph Extractor - Usage Guide

## Quick Start

```bash
# Basic extraction
uv run python extractor.py --data-dir ./data --output-file output.jsonld

# With verbose progress display
uv run python extractor.py --data-dir ./data --verbose

# CI/automated mode with JSON logging
uv run python extractor.py --data-dir ./data --json-logging --verbose
```

## Display Modes

### 1. Standard Mode (Default)

```bash
uv run python extractor.py --data-dir ./docs
```

**Output:**

```
2025-10-23 14:32:36,687 - kg_extractor - INFO - Starting knowledge graph extraction
2025-10-23 14:32:36,687 - kg_extractor - INFO - Data directory: docs
2025-10-23 14:32:36,687 - kg_extractor - INFO - Output file: knowledge_graph.jsonld
2025-10-23 14:32:36,687 - kg_extractor - INFO - Beginning extraction...
2025-10-23 14:35:56,706 - kg_extractor - INFO - Progress: 1/3 - Processed chunk chunk-000
2025-10-23 14:37:16,764 - kg_extractor - INFO - Progress: 2/3 - Processed chunk chunk-001
2025-10-23 14:37:35,515 - kg_extractor - INFO - Progress: 3/3 - Processed chunk chunk-002
2025-10-23 14:37:35,515 - kg_extractor - INFO - Extraction complete!
2025-10-23 14:37:35,515 - kg_extractor - INFO -   Total chunks: 3
2025-10-23 14:37:35,515 - kg_extractor - INFO -   Chunks processed: 3
2025-10-23 14:37:35,515 - kg_extractor - INFO -   Entities extracted: 81
2025-10-23 14:37:35,515 - kg_extractor - INFO -   Validation errors: 0
2025-10-23 14:37:35,515 - kg_extractor - INFO -   Duration: 158.65s
```

**Features:**

- Simple INFO-level logs
- Chunk progress updates
- Final metrics summary

### 2. Verbose Mode (Interactive)

```bash
uv run python extractor.py --data-dir ./docs --verbose
```

**Output:**

```
┌─ Knowledge Graph Extraction ─────────────────────────────────────┐
│ ⠹ Processing chunks ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2/3 • 1m23s │
│                                                                   │
│ Chunk:  chunk-001                                                │
│ Files:  15                                                       │
│ Size:   2.34 MB                                                  │
│                                                                   │
│ Entities:          45                                            │
│ Validation Errors: 0                                             │
│                                                                   │
│ ┌─ Agent Activity ─────────────────────────────────────────────┐ │
│ │ 🔧 Using tool: Read                                          │ │
│ │ 💭 Thinking: Analyzing schema structure for entities...     │ │
│ │ 🔧 Using tool: Grep                                          │ │
│ │ 💭 Thinking: Extracting Service entities from data files... │ │
│ │ ✅ Result: Extracted 12 Service entities                     │ │
│ └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

**Features:**

- Beautiful rich terminal UI
- Live progress bars with spinner
- Current chunk details (ID, file count, size)
- Real-time entity/error counts
- **Agent activity panel** showing:
  - 🔧 Tool usage (Read, Grep, Glob)
  - 💭 Agent thinking/reasoning
  - ✅ Results and completions
- Success/error panels on completion

**Best for:**

- Interactive terminal sessions
- Development and debugging
- Understanding what the agent is doing in real-time

### 3. JSON Logging Mode (CI/Automated)

```bash
uv run python extractor.py --data-dir ./docs --json-logging
```

**Output:**

```json
{"timestamp": "2025-10-23 14:32:36,687", "level": "INFO", "logger": "kg_extractor", "message": "Starting knowledge graph extraction"}
{"timestamp": "2025-10-23 14:32:36,687", "level": "INFO", "logger": "kg_extractor", "message": "Data directory: docs"}
{"timestamp": "2025-10-23 14:35:56,706", "level": "INFO", "logger": "kg_extractor", "message": "Progress: 1/3 - Processed chunk chunk-000"}
{"timestamp": "2025-10-23 14:37:35,515", "level": "INFO", "logger": "kg_extractor", "message": "Extraction complete!"}
```

**Features:**

- Structured JSON logs
- Machine-readable format
- No ANSI escape codes
- Easy parsing for log aggregation

**Best for:**

- CI/CD pipelines
- Log aggregation systems (Splunk, ELK, etc.)
- Automated monitoring

### 4. Verbose JSON Logging Mode (CI + Debugging)

```bash
uv run python extractor.py --data-dir ./docs --json-logging --verbose
```

**Output:**

```json
{"timestamp": "2025-10-23 14:32:36,687", "level": "INFO", "logger": "kg_extractor", "message": "Starting knowledge graph extraction"}
{"timestamp": "2025-10-23 14:32:37,123", "level": "DEBUG", "logger": "kg_extractor", "message": "Agent activity: Using tool: Read", "activity_type": "tool"}
{"timestamp": "2025-10-23 14:32:38,456", "level": "DEBUG", "logger": "kg_extractor", "message": "Agent activity: Thinking: Analyzing schema structure...", "activity_type": "thinking"}
{"timestamp": "2025-10-23 14:35:56,706", "level": "INFO", "logger": "kg_extractor", "message": "Progress: 1/3 - Processed chunk chunk-000"}
```

**Features:**

- Structured JSON logs
- DEBUG-level agent activity events
- Structured `activity_type` field for filtering
- No rich terminal UI (CI-compatible)

**Best for:**

- CI/CD pipelines with debugging enabled
- Troubleshooting extraction issues in automated environments
- Post-mortem analysis with log aggregation

## Command-Line Options

### Required Arguments

- `--data-dir PATH`: Directory containing data files to extract from

### Output Options

- `--output-file PATH`: Output JSON-LD file path (default: `knowledge_graph.jsonld`)
- `--resume`: Resume from latest checkpoint

### Authentication

- `--auth-method {vertex_ai,api_key}`: Authentication method (default: `vertex_ai`)
- `--api-key KEY`: Anthropic API key (for api_key auth)
- `--vertex-project-id ID`: Google Cloud project ID (for vertex_ai auth)
- `--vertex-region REGION`: Google Cloud region (default: `us-central1`)
- `--vertex-credentials-file PATH`: Path to Google Cloud credentials file

### Chunking

- `--chunking-strategy {hybrid,directory,size,count}`: Chunking strategy (default: `hybrid`)
- `--chunk-size-mb SIZE`: Target chunk size in MB (default: 10)
- `--max-files-per-chunk COUNT`: Maximum files per chunk (default: 100)

### Deduplication

- `--dedup-strategy {urn,agent,hybrid}`: Deduplication strategy (default: `urn`)
- `--urn-merge-strategy {first,last,merge_predicates}`: How to merge duplicate URNs (default: `merge_predicates`)

### Logging

- `--log-level {DEBUG,INFO,WARNING,ERROR}`: Logging level (default: `INFO`)
- `--log-file PATH`: Log file path (logs to stdout if not specified)
- `--json-logging`: Use JSON-formatted logs (for CI/automated environments)
- `--verbose`, `-v`: Enable verbose mode with rich progress display and agent activity

## Configuration Priority

Configuration is loaded from multiple sources with the following priority (highest to lowest):

1. **CLI flags** (e.g., `--api-key`, `--verbose`)
2. **Environment variables** (e.g., `EXTRACTOR_AUTH__API_KEY`)
3. **.env file** (automatically loaded from current directory)
4. **Defaults**

### Example .env File

```bash
# Authentication
EXTRACTOR_AUTH__AUTH_METHOD=api_key
EXTRACTOR_AUTH__API_KEY=sk-ant-...

# Chunking
EXTRACTOR_CHUNKING__TARGET_SIZE_MB=20
EXTRACTOR_CHUNKING__MAX_FILES_PER_CHUNK=50

# Logging
EXTRACTOR_LOGGING__LOG_LEVEL=DEBUG
EXTRACTOR_LOGGING__VERBOSE=true
```

### Example Environment Variables

```bash
export EXTRACTOR_AUTH__API_KEY=sk-ant-...
export EXTRACTOR_LOGGING__VERBOSE=true
uv run python extractor.py --data-dir ./docs
```

## Output Format

The extractor produces JSON-LD format compatible with graph databases:

```json
{
  "@context": {
    "@vocab": "http://schema.org/",
    "urn": "@id"
  },
  "@graph": [
    {
      "@id": "urn:Service:payment-api",
      "@type": "Service",
      "name": "Payment API",
      "description": "Handles payment processing",
      "language": "Python",
      "ownedBy": {"@id": "urn:Team:payments"}
    },
    {
      "@id": "urn:Team:payments",
      "@type": "Team",
      "name": "Payments Team",
      "slackChannel": "#team-payments"
    }
  ]
}
```

## Examples

### Local Development with Verbose Mode

```bash
# Create .env file
cat > .env <<EOF
EXTRACTOR_AUTH__API_KEY=sk-ant-...
EXTRACTOR_LOGGING__VERBOSE=true
EOF

# Run with beautiful progress display
uv run python extractor.py \
  --data-dir ./app-interface/data \
  --output-file knowledge_graph.jsonld
```

### CI/CD Pipeline

```bash
# GitHub Actions / GitLab CI
export EXTRACTOR_AUTH__API_KEY=${{ secrets.ANTHROPIC_API_KEY }}
uv run python extractor.py \
  --data-dir ./data \
  --output-file output.jsonld \
  --json-logging \
  --log-level INFO
```

### Debugging in CI

```bash
# Enable verbose agent activity in JSON format
export EXTRACTOR_AUTH__API_KEY=${{ secrets.ANTHROPIC_API_KEY }}
uv run python extractor.py \
  --data-dir ./data \
  --output-file output.jsonld \
  --json-logging \
  --verbose \
  --log-level DEBUG
```

### Container Deployment

```dockerfile
FROM python:3.13
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
ENV EXTRACTOR_AUTH__AUTH_METHOD=vertex_ai
ENV EXTRACTOR_LOGGING__JSON_LOGGING=true
CMD ["uv", "run", "python", "extractor.py", "--data-dir", "/data"]
```

## Performance Tuning

### Adjust Chunk Size

```bash
# Larger chunks = fewer LLM calls but more tokens per call
uv run python extractor.py \
  --data-dir ./data \
  --chunk-size-mb 50 \
  --max-files-per-chunk 500
```

### Parallel Processing (Future)

Currently, chunks are processed sequentially. Parallel processing is planned for a future release.

## Troubleshooting

### Extraction is slow

- **Increase chunk size**: `--chunk-size-mb 20`
- **Check file count**: Large numbers of small files create many chunks
- **Use verbose mode**: See what the agent is doing: `--verbose`

### Validation errors

- **Check schema files**: Ensure schema directory is provided
- **Review error messages**: Validation errors are logged with details
- **Adjust validation rules**: Configure in ValidationConfig

### Out of memory

- **Reduce chunk size**: `--chunk-size-mb 5`
- **Reduce files per chunk**: `--max-files-per-chunk 50`

### Authentication errors

- **Verify API key**: Check `EXTRACTOR_AUTH__API_KEY` or `--api-key`
- **Check Vertex AI setup**: Ensure project ID and credentials are correct
- **Test connection**: Run with `--log-level DEBUG` to see auth details
