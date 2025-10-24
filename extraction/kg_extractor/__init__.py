"""
Production Knowledge Graph Extraction System.

A domain-agnostic system for extracting knowledge graphs from diverse data sources
using Claude Agent SDK. Features checkpointing, resumability, comprehensive metrics,
and configurable extraction strategies.

Key components:
- Orchestrator: Coordinates the extraction workflow
- Agents: Claude Agent SDK integration for entity extraction
- Deduplication: Strategies for merging duplicate entities
- Validation: Entity and relationship validation
- Prompts: YAML-based Jinja2 prompt templates
"""

__version__ = "0.1.0"

__all__ = [
    "__version__",
]
