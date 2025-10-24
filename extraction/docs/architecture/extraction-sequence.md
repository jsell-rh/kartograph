# Knowledge Graph Extraction - Sequence Diagram

This diagram shows the complete flow from CLI invocation to JSON-LD output.

```mermaid
sequenceDiagram
    actor User
    participant CLI as extractor.py<br/>(main)
    participant Config as ExtractionConfig
    participant Orch as ExtractionOrchestrator
    participant FS as DiskFileSystem
    participant Chunker as HybridChunker
    participant Agent as ExtractionAgent
    participant LLM as AgentClient
    participant SDK as ClaudeSDKClient
    participant Validator as EntityValidator
    participant Dedup as URNDeduplicator
    participant Output as JSONLDGraph

    User->>CLI: uv run python extractor.py<br/>--data-dir ./docs<br/>--output-file output.jsonld

    Note over CLI: 1. Configuration Phase
    CLI->>CLI: parse_args()
    CLI->>Config: build_config_from_args(args)
    Config->>Config: Load from .env + env vars + CLI flags
    Config-->>CLI: ExtractionConfig
    CLI->>CLI: setup_logging(config)

    Note over CLI,Output: 2. Component Initialization
    CLI->>FS: DiskFileSystem()
    CLI->>Chunker: HybridChunker(config)
    CLI->>Dedup: URNDeduplicator(config)
    CLI->>LLM: AgentClient(auth_config, model)
    LLM->>SDK: ClaudeSDKClient(options)
    CLI->>Validator: EntityValidator(config)
    CLI->>Agent: ExtractionAgent(llm_client, validator)
    CLI->>Orch: ExtractionOrchestrator(components)

    Note over Orch,Output: 3. Extraction Phase
    CLI->>Orch: extract()
    Orch->>FS: load_files(data_dir)
    FS-->>Orch: List[FileContent]

    Orch->>Chunker: create_chunks(files)
    Chunker->>Chunker: Group by directory<br/>+ size-based splitting
    Chunker-->>Orch: List[Chunk]

    Note over Orch: For each chunk (parallel possible)
    loop For each chunk
        Orch->>Agent: extract(chunk, schemas)
        Agent->>Agent: Build extraction prompt
        Agent->>LLM: extract_entities(files, schema_dir)

        LLM->>LLM: Build tool-based prompt
        LLM->>SDK: _ensure_connected()
        SDK->>SDK: connect()
        LLM->>SDK: query(prompt)

        Note over SDK: Claude Agent processes with tools<br/>(Read, Grep, Glob)
        SDK->>SDK: Multi-step reasoning<br/>Read files, analyze schemas<br/>Extract entities

        LLM->>SDK: receive_response()
        SDK-->>LLM: AsyncIterator[ResultMessage]
        LLM->>LLM: Extract result.result
        LLM-->>Agent: {"entities": [...], "metadata": {...}}

        Agent->>Agent: Parse JSON response
        Agent->>Agent: Convert to Entity objects

        loop For each entity
            Agent->>Validator: validate(entity)
            Validator->>Validator: Check URN format
            Validator->>Validator: Check type validity
            Validator->>Validator: Check required fields
            Validator-->>Agent: ValidationResult
        end

        alt Validation failed
            Agent->>Agent: Log errors, filter invalid
        end

        Agent-->>Orch: List[Entity]
        Orch->>Orch: Log progress: X/N chunks
    end

    Note over Dedup: 4. Deduplication Phase
    Orch->>Dedup: deduplicate(all_entities)
    Dedup->>Dedup: Group by URN
    Dedup->>Dedup: Merge duplicate predicates
    Dedup-->>Orch: DeduplicationResult

    Note over Output: 5. Output Phase
    Orch-->>CLI: OrchestrationResult<br/>(entities, metrics)
    CLI->>CLI: Log metrics:<br/>chunks, entities, duration

    CLI->>Output: JSONLDGraph()
    CLI->>Output: add_entities(entities)
    loop For each entity
        Output->>Output: entity.to_jsonld()
    end

    CLI->>Output: save(output_file)
    Output->>Output: Build JSON-LD structure<br/>{"@context": {...}, "@graph": [...]}
    Output->>Output: Write to file

    Output-->>User: ✅ output.jsonld<br/>81 entities, 0 errors
```

## Key Patterns

### 1. Configuration Priority (Highest to Lowest)

```
CLI Flags > Environment Variables > .env File > Defaults
```

### 2. Chunk Processing

- Files grouped by directory structure
- Size-based splitting when directories exceed limits
- Configurable: `chunk_size_mb`, `max_files_per_chunk`

### 3. Agent-Based Extraction

- Claude Agent SDK with tools (Read, Grep, Glob)
- Multi-step reasoning and file access
- Prompt instructs agent to discover entities through analysis

### 4. Validation Points

- **During Extraction**: EntityValidator checks each entity
- **URN Format**: `urn:type:identifier`
- **Type Validity**: Alphanumeric, starts with capital
- **Required Fields**: @id, @type, name
- **No Relationship Entities**: Must use predicates

### 5. Deduplication Strategy

- **URN-based**: Group entities by URN
- **Merge Strategy**: `merge_predicates` (default)
  - Combines all predicates from duplicates
  - Preserves all relationships

## Metrics Tracked

```python
ExtractionMetrics:
  - total_chunks: int
  - chunks_processed: int
  - entities_extracted: int
  - validation_errors: int
  - duration_seconds: float
```

## Error Handling

1. **Retry Logic**: LLM calls retry up to 3 times with exponential backoff
2. **Validation Errors**: Logged but don't stop extraction
3. **Chunk Failures**: Continue with remaining chunks
4. **Connection Issues**: SDK auto-reconnects

## Performance

- **Parallel Chunks**: Configurable (future enhancement)
- **Streaming**: SDK uses async streaming for responses
- **Checkpointing**: Support for `--resume` flag
- **Example**: 81 entities from 3 chunks in 158.65s (~53s per chunk)
