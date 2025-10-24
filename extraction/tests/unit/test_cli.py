"""Unit tests for CLI entry point."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_cli_minimal_args():
    """Test CLI with minimal required arguments."""
    from extractor import parse_args

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        args = parse_args(["--data-dir", str(data_dir)])

        assert args.data_dir == data_dir
        assert args.output_file == Path("knowledge_graph.jsonld")
        assert args.resume is False


def test_cli_all_args():
    """Test CLI with all arguments specified."""
    from extractor import parse_args

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()
        output_file = Path(tmpdir) / "output.jsonld"

        args = parse_args(
            [
                "--data-dir",
                str(data_dir),
                "--output-file",
                str(output_file),
                "--resume",
                "--auth-method",
                "api_key",
                "--api-key",
                "test-key",  # pragma: allowlist secret
                "--log-level",
                "DEBUG",
            ]
        )

        assert args.data_dir == data_dir
        assert args.output_file == output_file
        assert args.resume is True
        assert args.auth_method == "api_key"
        assert args.api_key == "test-key"  # pragma: allowlist secret
        assert args.log_level == "DEBUG"


def test_cli_missing_required_args():
    """Test CLI fails without required arguments."""
    from extractor import parse_args

    with pytest.raises(SystemExit):
        parse_args([])


def test_cli_auth_api_key():
    """Test CLI with API key authentication."""
    from extractor import parse_args

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        args = parse_args(
            [
                "--data-dir",
                str(data_dir),
                "--auth-method",
                "api_key",
                "--api-key",
                "test-key",  # pragma: allowlist secret
            ]
        )

        assert args.auth_method == "api_key"
        assert args.api_key == "test-key"  # pragma: allowlist secret


def test_cli_auth_vertex_ai():
    """Test CLI with Vertex AI authentication."""
    from extractor import parse_args

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        args = parse_args(
            [
                "--data-dir",
                str(data_dir),
                "--auth-method",
                "vertex_ai",
                "--vertex-project-id",
                "test-project",
                "--vertex-region",
                "us-central1",
            ]
        )

        assert args.auth_method == "vertex_ai"
        assert args.vertex_project_id == "test-project"
        assert args.vertex_region == "us-central1"


def test_build_config_from_args():
    """Test building ExtractionConfig from parsed args."""
    from extractor import build_config_from_args, parse_args
    from kg_extractor.config import ExtractionConfig

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        args = parse_args(
            [
                "--data-dir",
                str(data_dir),
                "--auth-method",
                "api_key",
                "--api-key",
                "test-key",  # pragma: allowlist secret
            ]
        )

        config = build_config_from_args(args, cwd=Path(tmpdir))

        assert isinstance(config, ExtractionConfig)
        assert config.data_dir == data_dir
        assert config.auth.auth_method == "api_key"
        assert config.auth.api_key == "test-key"  # pragma: allowlist secret


def test_config_priority_flags_over_env_vars(monkeypatch):
    """Test CLI flags override environment variables."""
    from extractor import build_config_from_args, parse_args

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        # Set environment variables
        monkeypatch.setenv("EXTRACTOR_AUTH__AUTH_METHOD", "api_key")
        monkeypatch.setenv(
            "EXTRACTOR_AUTH__API_KEY", "env-var-key"
        )  # pragma: allowlist secret
        monkeypatch.setenv("EXTRACTOR_LOGGING__LOG_LEVEL", "DEBUG")

        args = parse_args(
            [
                "--data-dir",
                str(data_dir),
                "--auth-method",
                "api_key",
                "--api-key",
                "cli-flag-key",  # pragma: allowlist secret
                "--log-level",
                "ERROR",
            ]
        )

        config = build_config_from_args(args, cwd=Path(tmpdir))

        # CLI flags should override environment variables
        assert config.auth.api_key == "cli-flag-key"  # pragma: allowlist secret
        assert config.logging.log_level == "ERROR"


def test_setup_logging():
    """Test logging setup."""
    from extractor import setup_logging
    from kg_extractor.config import LoggingConfig

    config = LoggingConfig(log_level="DEBUG")
    setup_logging(config)

    import logging

    logger = logging.getLogger("kg_extractor")
    assert logger.level == logging.DEBUG


def test_setup_logging_with_file():
    """Test logging setup with file output."""
    from extractor import setup_logging
    from kg_extractor.config import LoggingConfig

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "test.log"
        config = LoggingConfig(log_level="INFO", log_file=log_file)
        setup_logging(config)

        import logging

        logger = logging.getLogger("kg_extractor")
        logger.info("Test message")

        # Verify log file was created
        assert log_file.exists()


@pytest.mark.asyncio
async def test_cli_main_success():
    """Test CLI main function with successful extraction."""
    from extractor import main
    from kg_extractor.deduplication.models import (
        DeduplicationMetrics,
        DeduplicationResult,
    )
    from kg_extractor.models import Entity, ExtractionMetrics

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()
        (data_dir / "test.yaml").write_text("test: data")

        output_file = Path(tmpdir) / "output.jsonld"

        # Mock the orchestrator
        with patch("extractor.ExtractionOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock orchestrator result
            from kg_extractor.orchestrator import OrchestrationResult

            mock_result = OrchestrationResult(
                entities=[Entity(id="urn:Service:test", type="Service", name="Test")],
                metrics=ExtractionMetrics(
                    total_chunks=1,
                    chunks_processed=1,
                    entities_extracted=1,
                    validation_errors=0,
                    duration_seconds=1.0,
                ),
            )
            mock_orchestrator.extract.return_value = mock_result

            # Mock the JSON-LD writer
            with patch("extractor.write_jsonld") as mock_write:
                exit_code = await main(
                    [
                        "--data-dir",
                        str(data_dir),
                        "--output-file",
                        str(output_file),
                        "--auth-method",
                        "api_key",
                        "--api-key",
                        "test-key",  # pragma: allowlist secret
                    ]
                )

                assert exit_code == 0
                mock_orchestrator.extract.assert_called_once()
                mock_write.assert_called_once()


@pytest.mark.asyncio
async def test_cli_main_extraction_failure():
    """Test CLI main function with extraction failure."""
    from extractor import main

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        # Mock the orchestrator to raise exception
        with patch("extractor.ExtractionOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator
            mock_orchestrator.extract.side_effect = Exception("Extraction failed")

            exit_code = await main(
                [
                    "--data-dir",
                    str(data_dir),
                    "--auth-method",
                    "api_key",
                    "--api-key",
                    "test-key",  # pragma: allowlist secret
                ]
            )

            assert exit_code == 1


@pytest.mark.asyncio
async def test_cli_main_invalid_config():
    """Test CLI main function with invalid configuration."""
    from extractor import main

    # Non-existent data directory should fail
    exit_code = await main(
        [
            "--data-dir",
            "/nonexistent/directory",
            "--auth-method",
            "api_key",
            "--api-key",
            "test-key",  # pragma: allowlist secret
        ]
    )

    assert exit_code == 1


def test_cli_log_prompts_flag():
    """Test --log-prompts flag is properly parsed and passed to config."""
    from extractor import build_config_from_args, parse_args

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data"
        data_dir.mkdir()

        args = parse_args(
            [
                "--data-dir",
                str(data_dir),
                "--log-prompts",
                "--auth-method",
                "api_key",
                "--api-key",
                "test-key",  # pragma: allowlist secret
            ]
        )

        assert args.log_prompts is True

        # Build config and verify it's passed through
        config = build_config_from_args(args)
        assert config.logging.log_llm_prompts is True
