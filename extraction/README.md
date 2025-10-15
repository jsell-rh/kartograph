# Knowledge Graph Extraction

This directory contains tools and methodology for extracting knowledge graphs from structured repositories.

## Overview

Kartograph uses AI assistants (like Claude Code) to analyze repositories and extract knowledge graphs representing entities, relationships, and metadata. The extracted graphs are exported in JSON-LD format for loading into graph databases.

## Components

### 1. PROCESS.md - Extraction Methodology

Complete step-by-step guide for AI assistants to extract knowledge graphs from any structured repository (Kubernetes manifests, Terraform configs, API specifications, etc.).

**[→ Read the full extraction process](./PROCESS.md)**

### 2. Loader Scripts

Python scripts to load JSON-LD knowledge graphs into graph databases:

- **load_dgraph.py** - Load graphs into Dgraph (primary database)
- **load_neo4j.py** - Load graphs into Neo4j

## Quick Start

### Extract a Knowledge Graph

Use Claude Code to extract entities from your repository following the PROCESS.md methodology:

1. Claude Code analyzes your repository structure
2. Identifies entities (services, namespaces, deployments, etc.)
3. Extracts relationships between entities
4. Validates the graph structure
5. Exports to JSON-LD format

### Load into Dgraph

```bash
# Port-forward to your Dgraph instance (if using Kubernetes)
kubectl port-forward svc/dgraph-alpha 8080:8080

# Load the graph (from extraction directory)
cd extraction
python load_dgraph.py \
  --input working/knowledge_graph.jsonld \
  --dgraph-url http://localhost:8080
```

The script will:

- Generate Dgraph schema from JSON-LD types
- Convert JSON-LD to N-Quads format
- Use `dgraph live` to load data (via Docker)
- Validate successful loading

### Load into Neo4j

```bash
# Load into Neo4j instance (from extraction directory)
cd extraction
python load_neo4j.py \
  --input working/knowledge_graph.jsonld \
  --neo4j-uri bolt://localhost:7687 \
  --username neo4j \
  --password your-password
```

## JSON-LD Format

All knowledge graphs use JSON-LD for interchange. Example structure:

```json
{
  "@context": {
    "@vocab": "https://kartograph.example.com/schema#",
    "name": "https://schema.org/name",
    "description": "https://schema.org/description"
  },
  "@graph": [
    {
      "@id": "urn:service:api-gateway",
      "@type": "Service",
      "name": "api-gateway",
      "namespace": { "@id": "urn:namespace:production" },
      "dependsOn": [{ "@id": "urn:service:auth-service" }]
    }
  ]
}
```

## URN Pattern

All entities use URNs for consistent identification:

- Services: `urn:service:name`
- Namespaces: `urn:namespace:name`
- Deployments: `urn:deployment:name`
- ConfigMaps: `urn:configmap:name`
- Custom types: `urn:type:identifier`

## Requirements

### Python Dependencies

```bash
# For load_dgraph.py
pip install requests

# For load_neo4j.py
pip install neo4j requests
```

### External Tools

**For Dgraph loader:**

- Docker (to run `dgraph live` command)
- Access to Dgraph instance (HTTP endpoint)

**For Neo4j loader:**

- Access to Neo4j instance (Bolt endpoint)

## Loader Script Options

### load_dgraph.py

```bash
# Run from extraction directory
python load_dgraph.py --help

Options:
  --input PATH          Path to JSON-LD file relative to extraction/ (required)
                        Example: working/knowledge_graph.jsonld
  --dgraph-url URL      Dgraph Alpha HTTP endpoint (default: http://localhost:8080)
  --batch-size N        Batch size for mutations (default: 1000)
  --help                Show help message
```

### load_neo4j.py

```bash
# Run from extraction directory
python load_neo4j.py --help

Options:
  --input PATH          Path to JSON-LD file relative to extraction/ (required)
                        Example: working/knowledge_graph.jsonld
  --neo4j-uri URI       Neo4j Bolt URI (default: bolt://localhost:7687)
  --username USER       Neo4j username (default: neo4j)
  --password PASS       Neo4j password (required)
  --help                Show help message
```

## Supported Repository Types

The PROCESS.md methodology works with any structured repository:

- **Kubernetes/OpenShift** - Services, deployments, configmaps, namespaces
- **Terraform** - Resources, modules, providers
- **Ansible** - Playbooks, roles, tasks
- **OpenAPI/Swagger** - Endpoints, schemas, operations
- **CloudFormation** - Stacks, resources, parameters
- **Docker Compose** - Services, networks, volumes
- **Custom formats** - Any structured data with entities and relationships

## Examples

### Loading Kubernetes Knowledge Graph

```bash
# 1. Extract graph using Claude Code
# (Claude follows PROCESS.md to create extraction/working/knowledge_graph.jsonld)

# 2. Load into Dgraph running in Kubernetes
cd app
make port-forward-dgraph  # Opens port 8081

# In another terminal
cd extraction
python load_dgraph.py \
  --input working/knowledge_graph.jsonld \
  --dgraph-url http://localhost:8081
```

### Custom Extraction

You can customize the extraction process by:

1. Defining custom entity types in your JSON-LD context
2. Creating domain-specific relationship patterns
3. Adding validation rules for your use case
4. Extending the schema as needed

See PROCESS.md for detailed customization guidance.

## Troubleshooting

### Dgraph Connection Failed

```
Error: Failed to connect to Dgraph at http://localhost:8080
```

**Solutions:**

- Verify Dgraph is running: `curl http://localhost:8080/health`
- Check port-forwarding: `kubectl get pods -l app=dgraph`
- Try different port: `--dgraph-url http://localhost:8081`

### Docker Not Found

```
Error: docker command not found
```

**Solutions:**

- Install Docker: <https://docs.docker.com/get-docker/>
- Or use Podman: Replace `docker` with `podman` in load_dgraph.py

### Invalid JSON-LD Format

```
Error: Invalid JSON-LD - missing @graph array
```

**Solutions:**

- Ensure JSON-LD has `@graph` array
- Validate structure: All entities need `@id` and `@type`
- Check JSON syntax: Use `jq` or JSON validator

## Next Steps

After loading your knowledge graph:

1. **Query with AI** - Use the Kartograph app for natural language queries
2. **Visualize** - Explore relationships interactively in the web UI
3. **Integrate** - Connect via MCP server for programmatic access

See the [app documentation](../app/) for deployment and usage.

## Contributing

Improvements to the extraction methodology or loader scripts are welcome. Common enhancements:

- Additional database loaders (Neptune, JanusGraph, etc.)
- Performance optimizations for large graphs
- Schema inference improvements
- Validation rule libraries for common domains

## License

MIT License - see [LICENSE](../LICENSE)
