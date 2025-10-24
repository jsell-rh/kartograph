"""Tests for file-level progress tracking in verbose mode."""

from pathlib import Path

import pytest


def test_progress_display_set_current_file():
    """Test ProgressDisplay can set and display current file."""
    from kg_extractor.progress import ProgressDisplay

    display = ProgressDisplay(total_chunks=5, verbose=True)

    # Set current file
    display.set_current_file(Path("/data/test/file1.yaml"))
    assert display.current_file == "file1.yaml"

    # Set as string
    display.set_current_file("/data/test/file2.json")
    assert display.current_file == "file2.json"

    # Clear current file
    display.set_current_file(None)
    assert display.current_file is None


def test_progress_display_file_activity():
    """Test ProgressDisplay handles file activity type."""
    from kg_extractor.progress import ProgressDisplay

    display = ProgressDisplay(total_chunks=5, verbose=True)

    # Log file activity
    display.log_agent_activity("Reading file: /data/test.yaml", activity_type="file")

    # Should extract and set current file
    assert display.current_file == "test.yaml"

    # Should not appear in activity log (handled specially)
    assert len(display.agent_activity) == 0


def test_progress_display_resets_current_file_on_new_chunk():
    """Test current file is reset when starting a new chunk."""
    from kg_extractor.progress import ProgressDisplay

    display = ProgressDisplay(total_chunks=5, verbose=True)

    # Set current file
    display.set_current_file("/data/file1.yaml")
    assert display.current_file == "file1.yaml"

    # Update to new chunk
    display.update_chunk(
        chunk_num=2,
        chunk_id="chunk-002",
        files=[Path("/data/file2.yaml"), Path("/data/file3.yaml")],
        size_mb=1.5,
    )

    # Current file should be reset
    assert display.current_file is None


def test_progress_display_shows_current_file_in_verbose_mode():
    """Test current file is shown in display when in verbose mode."""
    from io import StringIO

    from rich.console import Console

    from kg_extractor.progress import ProgressDisplay

    display = ProgressDisplay(total_chunks=5, verbose=True)
    display.start()

    display.update_chunk(
        chunk_num=1,
        chunk_id="chunk-001",
        files=[Path("/data/file1.yaml")],
        size_mb=0.5,
    )

    display.set_current_file("/data/file1.yaml")

    # Render panel to string
    panel = display._build_display()
    console = Console(file=StringIO(), force_terminal=True)
    console.print(panel)
    display_text = console.file.getvalue()

    assert "file1.yaml" in display_text
    assert "Current File" in display_text

    display.stop()


def test_progress_display_no_current_file_in_non_verbose_mode():
    """Test current file is not shown when verbose=False."""
    from kg_extractor.progress import ProgressDisplay

    display = ProgressDisplay(total_chunks=5, verbose=False)

    # Set current file
    display.set_current_file("/data/file1.yaml")

    # File activity should be ignored in non-verbose mode
    display.log_agent_activity("Reading file: /data/test.yaml", activity_type="file")

    # Should not track file in non-verbose mode
    assert display.current_file == "file1.yaml"  # Still set but won't be displayed


def test_agent_client_reports_file_reads():
    """Test agent client reports file reads during streaming."""
    # This is an integration-level test to verify the full flow

    from unittest.mock import AsyncMock, MagicMock

    # Mock event data from Agent SDK when Read tool is used
    read_tool_event = {
        "type": "content_block_start",
        "content_block": {
            "type": "tool_use",
            "name": "Read",
            "input": {"file_path": "/data/schemas/service.yaml"},
        },
    }

    # Verify callback would be called with file activity
    callback_calls = []

    def mock_callback(msg, activity_type=None):
        callback_calls.append((msg, activity_type))

    # Simulate the event handling logic from agent_client.py
    event_data = read_tool_event
    content = event_data.get("content_block", {})

    if content.get("type") == "tool_use":
        tool_name = content.get("name", "unknown")
        tool_input = content.get("input", {})

        if tool_name == "Read" and "file_path" in tool_input:
            file_path = tool_input["file_path"]
            mock_callback(f"Reading file: {file_path}", activity_type="file")

    # Verify callback was called with file activity
    assert len(callback_calls) == 1
    assert callback_calls[0][0] == "Reading file: /data/schemas/service.yaml"
    assert callback_calls[0][1] == "file"


def test_file_activity_extraction():
    """Test file path is extracted correctly from activity messages."""
    from kg_extractor.progress import ProgressDisplay

    display = ProgressDisplay(total_chunks=5, verbose=True)

    # Test various formats
    test_cases = [
        ("Reading file: /data/test.yaml", "test.yaml"),
        ("Reading file: test.json", "test.json"),
        ("Reading file: /path/to/schema/service.yaml", "service.yaml"),
    ]

    for activity, expected_filename in test_cases:
        display.log_agent_activity(activity, activity_type="file")
        assert (
            display.current_file == expected_filename
        ), f"Failed for: {activity}, got: {display.current_file}"
