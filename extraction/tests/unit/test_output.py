"""Unit tests for JSON-LD output."""

import json
import tempfile
from pathlib import Path

import pytest


def test_jsonld_context_defaults():
    """Test JSONLDContext with default values."""
    from kg_extractor.output import JSONLDContext

    context = JSONLDContext()

    assert "@vocab" in context.context
    assert context.context["@vocab"] == "http://schema.org/"


def test_jsonld_context_custom():
    """Test JSONLDContext with custom values."""
    from kg_extractor.output import JSONLDContext

    custom_context = {
        "@vocab": "https://example.com/vocab/",
        "custom": "https://custom.com/",
    }
    context = JSONLDContext(context=custom_context)

    assert context.context == custom_context


def test_jsonld_graph_empty():
    """Test empty JSONLDGraph."""
    from kg_extractor.output import JSONLDGraph

    graph = JSONLDGraph()

    assert graph.entity_count == 0
    assert len(graph.types) == 0
    assert graph.graph == []


def test_jsonld_graph_add_entity():
    """Test adding single entity to graph."""
    from kg_extractor.models import Entity
    from kg_extractor.output import JSONLDGraph

    graph = JSONLDGraph()
    entity = Entity(id="urn:Service:api1", type="Service", name="API 1")

    graph.add_entity(entity)

    assert graph.entity_count == 1
    assert "Service" in graph.types
    assert graph.graph[0]["@id"] == "urn:Service:api1"
    assert graph.graph[0]["@type"] == "Service"
    assert graph.graph[0]["name"] == "API 1"


def test_jsonld_graph_add_entities():
    """Test adding multiple entities to graph."""
    from kg_extractor.models import Entity
    from kg_extractor.output import JSONLDGraph

    graph = JSONLDGraph()
    entities = [
        Entity(id="urn:Service:api1", type="Service", name="API 1"),
        Entity(id="urn:User:user1", type="User", name="User 1"),
    ]

    graph.add_entities(entities)

    assert graph.entity_count == 2
    assert "Service" in graph.types
    assert "User" in graph.types


def test_jsonld_graph_to_jsonld_string():
    """Test converting graph to JSON-LD string."""
    from kg_extractor.models import Entity
    from kg_extractor.output import JSONLDGraph

    graph = JSONLDGraph()
    entity = Entity(id="urn:Service:api1", type="Service", name="API 1")
    graph.add_entity(entity)

    jsonld_string = graph.to_jsonld_string()

    # Parse to verify valid JSON
    data = json.loads(jsonld_string)
    assert "@context" in data
    assert "@graph" in data
    assert len(data["@graph"]) == 1
    assert data["@graph"][0]["@id"] == "urn:Service:api1"


def test_jsonld_graph_save():
    """Test saving graph to file."""
    from kg_extractor.models import Entity
    from kg_extractor.output import JSONLDGraph

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test.jsonld"

        graph = JSONLDGraph()
        entity = Entity(id="urn:Service:api1", type="Service", name="API 1")
        graph.add_entity(entity)

        graph.save(output_file)

        # Verify file exists and contains valid JSON-LD
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "@context" in data
        assert "@graph" in data


def test_jsonld_graph_load():
    """Test loading graph from file."""
    from kg_extractor.output import JSONLDGraph

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.jsonld"

        # Create test file
        test_data = {
            "@context": {"@vocab": "http://schema.org/"},
            "@graph": [
                {
                    "@id": "urn:Service:api1",
                    "@type": "Service",
                    "name": "API 1",
                }
            ],
        }
        input_file.write_text(json.dumps(test_data))

        # Load graph
        graph = JSONLDGraph.load(input_file)

        assert graph.entity_count == 1
        assert "Service" in graph.types
        assert graph.graph[0]["@id"] == "urn:Service:api1"


def test_jsonld_graph_roundtrip():
    """Test save and load roundtrip."""
    from kg_extractor.models import Entity
    from kg_extractor.output import JSONLDGraph

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.jsonld"

        # Create and save graph
        graph1 = JSONLDGraph()
        entities = [
            Entity(id="urn:Service:api1", type="Service", name="API 1"),
            Entity(id="urn:User:user1", type="User", name="User 1"),
        ]
        graph1.add_entities(entities)
        graph1.save(file_path)

        # Load graph
        graph2 = JSONLDGraph.load(file_path)

        # Verify same content
        assert graph2.entity_count == graph1.entity_count
        assert graph2.types == graph1.types
        assert graph2.graph == graph1.graph


def test_jsonld_graph_with_properties():
    """Test graph with entities that have additional properties."""
    from kg_extractor.models import Entity
    from kg_extractor.output import JSONLDGraph

    graph = JSONLDGraph()
    entity = Entity(
        id="urn:Service:api1",
        type="Service",
        name="API 1",
        properties={
            "description": "Test API",
            "version": "1.0",
        },
    )
    graph.add_entity(entity)

    # Verify properties are included in JSON-LD
    assert graph.graph[0]["description"] == "Test API"
    assert graph.graph[0]["version"] == "1.0"


def test_jsonld_graph_custom_context():
    """Test graph with custom context."""
    from kg_extractor.models import Entity
    from kg_extractor.output import JSONLDContext, JSONLDGraph

    custom_context = JSONLDContext(
        context={
            "@vocab": "https://custom.com/vocab/",
            "myns": "https://my.namespace.com/",
        }
    )
    graph = JSONLDGraph(context=custom_context)
    entity = Entity(id="urn:Service:api1", type="Service", name="API 1")
    graph.add_entity(entity)

    jsonld_string = graph.to_jsonld_string()
    data = json.loads(jsonld_string)

    assert data["@context"]["@vocab"] == "https://custom.com/vocab/"
    assert data["@context"]["myns"] == "https://my.namespace.com/"


def test_jsonld_graph_types_property():
    """Test types property returns unique entity types."""
    from kg_extractor.models import Entity
    from kg_extractor.output import JSONLDGraph

    graph = JSONLDGraph()
    entities = [
        Entity(id="urn:Service:api1", type="Service", name="API 1"),
        Entity(id="urn:Service:api2", type="Service", name="API 2"),
        Entity(id="urn:User:user1", type="User", name="User 1"),
    ]
    graph.add_entities(entities)

    types = graph.types
    assert len(types) == 2
    assert "Service" in types
    assert "User" in types


def test_jsonld_graph_indent():
    """Test JSON-LD string indentation."""
    from kg_extractor.models import Entity
    from kg_extractor.output import JSONLDGraph

    graph = JSONLDGraph()
    entity = Entity(id="urn:Service:api1", type="Service", name="API 1")
    graph.add_entity(entity)

    # Test different indentation
    jsonld_compact = graph.to_jsonld_string(indent=0)
    jsonld_pretty = graph.to_jsonld_string(indent=4)

    # Compact should be shorter
    assert len(jsonld_compact) < len(jsonld_pretty)

    # Both should parse to same data
    assert json.loads(jsonld_compact) == json.loads(jsonld_pretty)
