"""Rich-based progress display for extraction."""

import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text


class ETAColumn(ProgressColumn):
    """Custom column to display estimated time remaining."""

    def __init__(self, progress_display: "ProgressDisplay"):
        super().__init__()
        self.progress_display = progress_display

    def render(self, task: Task) -> Text:
        """Render the ETA."""
        eta = self.progress_display._calculate_eta()
        if eta:
            return Text(f"• {eta} remaining", style="bold yellow")
        else:
            return Text("• calculating ETA...", style="dim")


class ProgressDisplay:
    """
    Beautiful progress display using Rich library.

    Shows:
    - Overall chunk progress
    - Current chunk details (files, size)
    - Agent activity (tool usage, thinking)
    - Entity extraction counts
    - Validation errors
    """

    def __init__(
        self,
        total_chunks: int,
        verbose: bool = False,
        data_dir: Path | None = None,
        orchestrator: Any = None,
        num_workers: int = 1,
    ):
        """
        Initialize progress display.

        Args:
            total_chunks: Total number of chunks to process
            verbose: Show verbose agent activity
            data_dir: Optional data directory being processed (for display)
            orchestrator: Optional orchestrator reference for worker state tracking
            num_workers: Number of parallel workers (for accurate ETA calculation)
        """
        self.console = Console()
        self.verbose = verbose
        self.total_chunks = total_chunks
        self.data_dir = data_dir
        self.orchestrator = orchestrator
        self.num_workers = num_workers

        # Create progress bars
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            ETAColumn(self),  # Custom ETA column
            console=self.console,
        )

        self.chunk_task: TaskID | None = None
        self.current_chunk_info: dict[str, Any] = {}

        # ETA tracking
        self.chunk_start_times: list[float] = []  # Start time of each chunk
        self.chunk_durations: list[float] = []  # Duration of completed chunks
        self.current_chunk_start: float | None = None  # Start time of current chunk
        self.chunks_completed: int = 0
        self.current_file: str | None = None  # Currently processing file
        self.agent_activity: list[str] = []
        self.stats: dict[str, int | float] = {
            "entities": 0,
            "relationships": 0,
            "validation_errors": 0,
            "average_degree": 0.0,
            "graph_density": 0.0,
            "running_cost_usd": 0.0,
            "running_input_tokens": 0,
            "running_output_tokens": 0,
        }
        self.all_entities: list[Any] = []  # Track all entities for graph metrics

        self.live: Live | None = None

    def start(self) -> None:
        """Start the live display."""
        # Remove console handlers from root logger to prevent interference with Rich Live
        # This allows initial startup messages to be shown, but stops logging output
        # once the progress display takes over
        import logging

        root_logger = logging.getLogger()
        # Remove only StreamHandler instances (keep file handlers)
        handlers_to_remove = [
            h
            for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.FileHandler)
        ]
        for handler in handlers_to_remove:
            root_logger.removeHandler(handler)

        self.chunk_task = self.progress.add_task(
            "Processing chunks", total=self.total_chunks
        )

        # Start live display
        # Use high refresh rate (20 Hz) to prevent visual artifacts during rapid updates
        # When chunks complete, multiple updates happen in quick succession which can
        # cause terminal display corruption with lower refresh rates
        self.live = Live(
            self._build_display(),
            console=self.console,
            refresh_per_second=20,
        )
        self.live.start()

    def stop(self) -> None:
        """Stop the live display."""
        if self.live:
            self.live.stop()

    def update_chunk(
        self,
        chunk_num: int,
        chunk_id: str,
        files: list[Path],
        size_mb: float,
    ) -> None:
        """
        Update current chunk being processed.

        Args:
            chunk_num: Current chunk number (1-indexed)
            chunk_id: Chunk identifier
            files: Files in this chunk
            size_mb: Total size of files in MB
        """
        self.current_chunk_info = {
            "num": chunk_num,
            "id": chunk_id,
            "files": files,
            "size_mb": size_mb,
        }
        self.current_file = None  # Reset current file for new chunk
        self.agent_activity = []  # Reset activity for new chunk

        # Track chunk start time for ETA calculation
        self.current_chunk_start = time.time()

        if self.live:
            self.live.update(self._build_display())

    def set_initial_progress(self, chunks_completed: int) -> None:
        """
        Set initial chunk progress when resuming from checkpoint.

        This updates the progress bar to reflect chunks already processed,
        without recording fake chunk durations.

        Args:
            chunks_completed: Number of chunks already completed
        """
        if self.chunk_task is not None and chunks_completed > 0:
            # Update progress bar to show chunks already done
            self.progress.update(self.chunk_task, completed=chunks_completed)
            self.chunks_completed = chunks_completed

        if self.live:
            self.live.update(self._build_display())

    def advance_chunk(self) -> None:
        """Advance to next chunk."""
        if self.chunk_task is not None:
            self.progress.advance(self.chunk_task)

        # Record chunk duration for ETA calculation
        if self.current_chunk_start is not None:
            duration = time.time() - self.current_chunk_start
            self.chunk_durations.append(duration)
            self.chunks_completed += 1
            self.current_chunk_start = None  # Reset for next chunk

        if self.live:
            self.live.update(self._build_display())

    def set_current_file(self, file_path: Path | str | None) -> None:
        """
        Set the currently processing file.

        Args:
            file_path: Path to the file being processed, or None to clear
        """
        if file_path:
            # Extract just the filename
            if isinstance(file_path, Path):
                self.current_file = file_path.name
            else:
                self.current_file = Path(file_path).name
        else:
            self.current_file = None

        if self.live:
            self.live.update(self._build_display())

    def log_agent_activity(
        self, activity: str, activity_type: str = "info", detail: str | None = None
    ) -> None:
        """
        Log agent activity (only shown in verbose mode).

        Args:
            activity: Activity description
            activity_type: Type of activity (info, tool, thinking, result, file)
            detail: Optional detail text to show in dim/grey style (e.g., tool parameters)
        """
        if self.verbose:
            # Handle file activity specially - update current file
            if activity_type == "file":
                # Extract filename from activity like "Reading file: /path/to/file.yaml"
                if ":" in activity:
                    file_part = activity.split(":", 1)[1].strip()
                    self.set_current_file(file_part)
                return

            # Keep only last 10 activities
            if len(self.agent_activity) >= 10:
                self.agent_activity.pop(0)

            # Format based on type
            if activity_type == "tool":
                icon = "🔧"
            elif activity_type == "thinking":
                icon = "💭"
            elif activity_type == "result":
                icon = "✅"
            else:
                icon = "ℹ️ "

            # Build formatted string with optional detail in grey
            if detail:
                # Use Rich markup for styling
                formatted = f"{icon} {activity} [dim]{detail}[/dim]"
            else:
                formatted = f"{icon} {activity}"

            self.agent_activity.append(formatted)

            if self.live:
                self.live.update(self._build_display())

    def update_stats(
        self,
        entities: list[Any] | None = None,
        validation_errors: int = 0,
        cost_usd: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """
        Update extraction statistics.

        Args:
            entities: List of entities extracted (to count and analyze)
            validation_errors: Number of validation errors (incremental)
            cost_usd: Cost for this chunk in USD (incremental)
            input_tokens: Input tokens for this chunk (incremental)
            output_tokens: Output tokens for this chunk (incremental)
        """
        if entities:
            # Add entities to tracking
            self.all_entities.extend(entities)
            self.stats["entities"] += len(entities)

            # Count relationships in the new entities
            new_relationships = self._count_relationships(entities)
            self.stats["relationships"] += new_relationships

            # Recalculate graph metrics
            self._update_graph_metrics()

        self.stats["validation_errors"] += validation_errors
        self.stats["running_cost_usd"] += cost_usd
        self.stats["running_input_tokens"] += input_tokens
        self.stats["running_output_tokens"] += output_tokens

        if self.live:
            self.live.update(self._build_display())

    def _calculate_eta(self) -> str | None:
        """
        Calculate estimated time remaining based on completed chunks.

        Accounts for parallel execution by dividing remaining work by number of workers.

        Returns:
            Formatted ETA string (e.g., "~0:02:30") or None if not enough data
        """
        if not self.chunk_durations or self.chunks_completed == 0:
            return None

        # Calculate average chunk duration
        avg_duration = sum(self.chunk_durations) / len(self.chunk_durations)

        # Calculate remaining chunks
        remaining_chunks = self.total_chunks - self.chunks_completed

        if remaining_chunks <= 0:
            return None

        # Estimate remaining time accounting for parallel workers
        # Calculate number of batches remaining (ceil division)
        import math

        remaining_batches = math.ceil(remaining_chunks / self.num_workers)
        estimated_seconds = avg_duration * remaining_batches

        # Format as HH:MM:SS
        hours = int(estimated_seconds // 3600)
        minutes = int((estimated_seconds % 3600) // 60)
        seconds = int(estimated_seconds % 60)

        if hours > 0:
            return f"~{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"~{minutes}:{seconds:02d}"

    def _count_relationships(self, entities: list[Any]) -> int:
        """
        Count relationships (edges) in entities.

        A relationship is a property whose value is:
        - A dict with "@id" key (entity reference)
        - A list of such dicts (multiple references)

        Args:
            entities: List of Entity objects

        Returns:
            Number of relationships found
        """
        total_relationships = 0

        for entity in entities:
            # Get properties dict
            properties = getattr(entity, "properties", {})

            for key, value in properties.items():
                # Skip reserved keys
                if key.startswith("@"):
                    continue

                # Check if value is an entity reference
                if isinstance(value, dict) and "@id" in value:
                    total_relationships += 1

                # Check if value is a list of entity references
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and "@id" in item:
                            total_relationships += 1

        return total_relationships

    def _update_graph_metrics(self) -> None:
        """Update graph connectivity metrics."""
        n = self.stats["entities"]
        r = self.stats["relationships"]

        # Average Degree: total edges / total nodes
        if n > 0:
            self.stats["average_degree"] = r / n
        else:
            self.stats["average_degree"] = 0.0

        # Graph Density: actual edges / possible edges
        # For a directed graph: density = edges / (n * (n-1))
        # For an undirected graph: density = (2 * edges) / (n * (n-1))
        # We'll use directed graph formula
        if n > 1:
            possible_edges = n * (n - 1)
            self.stats["graph_density"] = r / possible_edges
        else:
            self.stats["graph_density"] = 0.0

    def _check_rate_limit_status(self) -> dict[str, Any]:
        """
        Check if globally rate limited.

        Returns:
            Dictionary with {"limited": bool, "remaining": float}
        """
        try:
            from kg_extractor.llm.agent_client import AgentClient

            if AgentClient._rate_limited_until:
                remaining = AgentClient._rate_limited_until - time.time()
                if remaining > 0:
                    return {"limited": True, "remaining": remaining}
        except Exception:
            pass

        return {"limited": False, "remaining": 0}

    def _build_worker_panel(self) -> Panel | None:
        """
        Build worker panel showing current worker activity.

        Returns:
            Rich Panel with worker status, or None if no orchestrator
        """
        if not self.orchestrator:
            return None

        # Get rate limit status
        rate_limit_status = self._check_rate_limit_status()

        # Get worker states from orchestrator
        worker_states = self.orchestrator.get_worker_states()

        if not worker_states and not rate_limit_status["limited"]:
            # No workers active and not rate limited
            return None

        # Build panel content
        if rate_limit_status["limited"]:
            # Show rate limit warning
            remaining = rate_limit_status["remaining"]
            panel_content = (
                f"[bold yellow]⚠ RATE LIMITED[/bold yellow] - "
                f"All workers paused (resuming in [bold]{remaining:.1f}s[/bold])\n"
            )

            # Show waiting workers
            for wid in sorted(worker_states.keys()):
                panel_content += f"  [dim]⊗ Worker {wid+1}[/dim]: Waiting for rate limit clearance...\n"

        else:
            # Show normal worker activity
            # Count active vs completed workers
            active_count = sum(
                1
                for state in worker_states.values()
                if state.get("status", "active") == "active"
            )
            completed_count = sum(
                1
                for state in worker_states.values()
                if state.get("status", "active") == "completed"
            )

            # Build header with worker summary
            total_workers = len(worker_states)
            if completed_count > 0:
                panel_content = (
                    f"[bold]Workers:[/bold] {active_count}/{total_workers} active, "
                    f"{completed_count} completed this cycle\n\n"
                )
            else:
                panel_content = (
                    f"[bold]Workers:[/bold] {active_count}/{total_workers} active\n\n"
                )

            for wid in sorted(worker_states.keys()):
                state = worker_states.get(wid, {})
                status = state.get("status", "active")
                chunk_id = state.get("chunk_id", "?")
                files_count = state.get("files_count", 0)
                size_mb = state.get("size_mb", 0)
                activity = state.get("activity", "Processing...")
                detail = state.get("detail", "")

                # Build worker line with status indicator
                if status == "completed":
                    # Completed worker - show checkmark
                    line = f"  [bold green]✓[/bold green] Worker {wid+1}: [cyan]{chunk_id}[/cyan] "
                    line += f"[dim]({files_count} files, {size_mb:.1f} MB)[/dim]"
                    line += " → [green]Completed[/green]"

                    # Show entity and relationship counts if available
                    entity_count = state.get("entity_count", 0)
                    relationship_count = state.get("relationship_count", 0)
                    if entity_count > 0 or relationship_count > 0:
                        line += f" [dim]({entity_count} entities, {relationship_count} relationships)[/dim]"
                else:
                    # Active worker - show green dot
                    line = f"  [bold green]●[/bold green] Worker {wid+1}: [cyan]{chunk_id}[/cyan] "
                    line += f"[dim]({files_count} files, {size_mb:.1f} MB)[/dim]"

                    # Add activity
                    if activity:
                        # Truncate long activities
                        if len(activity) > 50:
                            activity = activity[:47] + "..."
                        line += f" → {activity}"

                panel_content += line + "\n"

        return Panel(
            panel_content.rstrip(),
            title="[bold magenta]Parallel Execution[/bold magenta]",
            border_style="magenta",
        )

    def _build_display(self) -> Panel:
        """Build the complete display panel."""
        # Main progress bar
        components = [self.progress]

        # Current chunk info - ONLY for non-parallel mode
        # In parallel mode, this info doesn't make sense (20 workers = 20 chunks)
        # The worker panel shows per-worker chunk info instead
        # Determine if we're in parallel mode by checking for active workers
        worker_states = (
            self.orchestrator.get_worker_states() if self.orchestrator else {}
        )

        if not worker_states:
            # Sequential mode - show current chunk info
            chunk_table = Table.grid(padding=(0, 2))
            chunk_table.add_column(style="bold cyan")
            chunk_table.add_column()

            if self.current_chunk_info:
                files = self.current_chunk_info.get("files", [])
                file_count = len(files)

                chunk_table.add_row("Chunk:", self.current_chunk_info.get("id", ""))
                chunk_table.add_row("Files/Chunk:", str(file_count))
                chunk_table.add_row(
                    "Size:", f"{self.current_chunk_info.get('size_mb', 0):.2f} MB"
                )

                # In verbose mode, always reserve space for optional rows (consistent height)
                if self.verbose:
                    # Current file row (always present in verbose, may be empty)
                    current_file_display = (
                        Text(self.current_file, style="bold yellow")
                        if self.current_file
                        else ""
                    )
                    chunk_table.add_row("Current File:", current_file_display)

                    # Files list row (always present in verbose, may be empty)
                    if files:
                        filenames = [f.name for f in files]
                        # Show first 5 filenames, then "... and N more" if needed
                        if len(filenames) <= 5:
                            files_display = ", ".join(filenames)
                        else:
                            files_display = (
                                ", ".join(filenames[:5])
                                + f" ... and {len(filenames) - 5} more"
                            )
                        chunk_table.add_row("Files:", Text(files_display, style="dim"))
                    else:
                        chunk_table.add_row("Files:", "")
            else:
                # Placeholder rows to maintain height even when no chunk info
                chunk_table.add_row("Chunk:", "")
                chunk_table.add_row("Files/Chunk:", "")
                chunk_table.add_row("Size:", "")
                if self.verbose:
                    chunk_table.add_row("Current File:", "")
                    chunk_table.add_row("Files:", "")

            components.append(chunk_table)

        # Statistics - Two column layout
        # Left column: Entity/Graph stats
        left_stats = Table.grid(padding=(0, 2))
        left_stats.add_column(style="bold green")
        left_stats.add_column()

        left_stats.add_row("Entities:", str(self.stats["entities"]))
        left_stats.add_row("Relationships:", str(self.stats["relationships"]))

        # Show graph metrics in verbose mode
        if self.verbose:
            left_stats.add_row("Average Degree:", f"{self.stats['average_degree']:.2f}")
            left_stats.add_row(
                "Graph Density:",
                (
                    f"{self.stats['graph_density']:.4f}"
                    if self.stats["graph_density"] > 0
                    else "0.0000"
                ),
            )

        left_stats.add_row(
            "Validation Errors:",
            (
                Text(str(self.stats["validation_errors"]), style="red bold")
                if self.stats["validation_errors"] > 0
                else Text("0", style="green")
            ),
        )

        # Right column: Cost/Token stats
        right_stats = Table.grid(padding=(0, 2))
        right_stats.add_column(style="bold cyan")
        right_stats.add_column()

        # Always show running cost (even when $0.0000)
        running_cost = self.stats["running_cost_usd"]
        right_stats.add_row(
            "Running Cost:",
            Text(f"${running_cost:.4f}", style="bold yellow"),
        )

        # Show token counts
        input_tokens = self.stats["running_input_tokens"]
        output_tokens = self.stats["running_output_tokens"]
        right_stats.add_row("Input Tokens:", f"{input_tokens:,}")
        right_stats.add_row("Output Tokens:", f"{output_tokens:,}")

        # Combine left and right stats in a container
        stats_container = Table.grid(padding=(0, 4))
        stats_container.add_column()  # Left column
        stats_container.add_column()  # Right column
        stats_container.add_row(left_stats, right_stats)

        components.append(stats_container)

        # Worker panel (multi-worker mode)
        worker_panel = self._build_worker_panel()
        if worker_panel:
            components.append(worker_panel)

        # Agent activity (verbose mode only)
        # Always show in verbose mode to maintain consistent panel height
        if self.verbose:
            if self.agent_activity:
                activity_text = "\n".join(self.agent_activity[-5:])  # Last 5 activities
            else:
                # Show placeholder to maintain consistent height
                activity_text = "[dim]Waiting for agent activity...[/dim]"
            components.append(
                Panel(
                    activity_text,
                    title="[bold magenta]Agent Activity[/bold magenta]",
                    border_style="magenta",
                )
            )

        # Build final layout
        layout = Table.grid()
        layout.add_column()
        for component in components:
            layout.add_row(component)

        # Build subtitle with data directory if available
        subtitle = None
        if self.data_dir:
            # Show relative path if possible, otherwise just the name
            try:
                from pathlib import Path

                cwd = Path.cwd()
                try:
                    rel_path = self.data_dir.relative_to(cwd)
                    subtitle = f"[dim]{rel_path}[/dim]"
                except ValueError:
                    # Not relative to cwd, show name
                    subtitle = f"[dim]{self.data_dir.name}[/dim]"
            except Exception:
                subtitle = f"[dim]{self.data_dir}[/dim]"

        return Panel(
            layout,
            title="[bold blue]Knowledge Graph Extraction[/bold blue]",
            subtitle=subtitle,
            border_style="blue",
        )

    def print_success(
        self,
        total_entities: int,
        total_chunks: int,
        duration: float,
    ) -> None:
        """
        Print success message.

        Args:
            total_entities: Total entities extracted
            total_chunks: Total chunks processed
            duration: Total duration in seconds
        """
        self.console.print()

        # Build success message
        message_parts = [
            "[bold green]✓ Extraction Complete![/bold green]\n",
            f"Chunks Processed: [cyan]{total_chunks}[/cyan]",
            f"Entities Extracted: [cyan]{total_entities}[/cyan]",
            f"Relationships: [cyan]{self.stats['relationships']}[/cyan]",
        ]

        # Add graph metrics in verbose mode
        if self.verbose:
            message_parts.extend(
                [
                    f"Average Degree: [cyan]{self.stats['average_degree']:.2f}[/cyan]",
                    f"Graph Density: [cyan]{self.stats['graph_density']:.4f}[/cyan]",
                ]
            )

        message_parts.extend(
            [
                f"Validation Errors: [{'red' if self.stats['validation_errors'] > 0 else 'green'}]{self.stats['validation_errors']}[/]",
                f"Duration: [cyan]{duration:.2f}s[/cyan]",
            ]
        )

        # Add total cost if available
        if self.stats["running_cost_usd"] > 0:
            message_parts.append(
                f"Total Cost: [yellow]${self.stats['running_cost_usd']:.4f}[/yellow]"
            )

        self.console.print(
            Panel(
                "\n".join(message_parts),
                title="[bold green]Success[/bold green]",
                border_style="green",
            )
        )

    def print_error(self, error: str) -> None:
        """
        Print error message.

        Args:
            error: Error message
        """
        self.console.print()
        self.console.print(
            Panel(
                f"[bold red]✗ Extraction Failed[/bold red]\n\n{error}",
                title="[bold red]Error[/bold red]",
                border_style="red",
            )
        )
