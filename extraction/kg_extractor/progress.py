"""Rich-based progress display for extraction."""

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text


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

    def __init__(self, total_chunks: int, verbose: bool = False):
        """
        Initialize progress display.

        Args:
            total_chunks: Total number of chunks to process
            verbose: Show verbose agent activity
        """
        self.console = Console()
        self.verbose = verbose
        self.total_chunks = total_chunks

        # Create progress bars
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=self.console,
        )

        self.chunk_task: TaskID | None = None
        self.current_chunk_info: dict[str, Any] = {}
        self.agent_activity: list[str] = []
        self.stats: dict[str, int | float] = {
            "entities": 0,
            "relationships": 0,
            "validation_errors": 0,
            "average_degree": 0.0,
            "graph_density": 0.0,
        }
        self.all_entities: list[Any] = []  # Track all entities for graph metrics

        self.live: Live | None = None

    def start(self) -> None:
        """Start the live display."""
        self.chunk_task = self.progress.add_task(
            "Processing chunks", total=self.total_chunks
        )

        # Start live display
        self.live = Live(
            self._build_display(), console=self.console, refresh_per_second=4
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
        self.agent_activity = []  # Reset activity for new chunk

        if self.live:
            self.live.update(self._build_display())

    def advance_chunk(self) -> None:
        """Advance to next chunk."""
        if self.chunk_task is not None:
            self.progress.advance(self.chunk_task)

        if self.live:
            self.live.update(self._build_display())

    def log_agent_activity(self, activity: str, activity_type: str = "info") -> None:
        """
        Log agent activity (only shown in verbose mode).

        Args:
            activity: Activity description
            activity_type: Type of activity (info, tool, thinking, result)
        """
        if self.verbose:
            # Keep only last 10 activities
            if len(self.agent_activity) >= 10:
                self.agent_activity.pop(0)

            # Format based on type
            if activity_type == "tool":
                formatted = f"🔧 {activity}"
            elif activity_type == "thinking":
                formatted = f"💭 {activity}"
            elif activity_type == "result":
                formatted = f"✅ {activity}"
            else:
                formatted = f"ℹ️  {activity}"

            self.agent_activity.append(formatted)

            if self.live:
                self.live.update(self._build_display())

    def update_stats(
        self,
        entities: list[Any] | None = None,
        validation_errors: int = 0,
    ) -> None:
        """
        Update extraction statistics.

        Args:
            entities: List of entities extracted (to count and analyze)
            validation_errors: Number of validation errors (incremental)
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

        if self.live:
            self.live.update(self._build_display())

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

    def _build_display(self) -> Panel:
        """Build the complete display panel."""
        # Main progress bar
        components = [self.progress]

        # Current chunk info
        if self.current_chunk_info:
            chunk_table = Table.grid(padding=(0, 2))
            chunk_table.add_column(style="bold cyan")
            chunk_table.add_column()

            files = self.current_chunk_info.get("files", [])
            file_count = len(files)

            chunk_table.add_row("Chunk:", self.current_chunk_info.get("id", ""))
            chunk_table.add_row("Files/Chunk:", str(file_count))
            chunk_table.add_row(
                "Size:", f"{self.current_chunk_info.get('size_mb', 0):.2f} MB"
            )

            # Show filenames (just names, not full paths)
            if files and self.verbose:
                filenames = [f.name for f in files]
                # Show first 5 filenames, then "... and N more" if needed
                if len(filenames) <= 5:
                    files_display = ", ".join(filenames)
                else:
                    files_display = (
                        ", ".join(filenames[:5]) + f" ... and {len(filenames) - 5} more"
                    )
                chunk_table.add_row("Files:", Text(files_display, style="dim"))

            components.append(chunk_table)

        # Statistics
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_column(style="bold green")
        stats_table.add_column()

        stats_table.add_row("Entities:", str(self.stats["entities"]))
        stats_table.add_row("Relationships:", str(self.stats["relationships"]))

        # Show graph metrics in verbose mode
        if self.verbose:
            stats_table.add_row(
                "Average Degree:", f"{self.stats['average_degree']:.2f}"
            )
            stats_table.add_row(
                "Graph Density:",
                (
                    f"{self.stats['graph_density']:.4f}"
                    if self.stats["graph_density"] > 0
                    else "0.0000"
                ),
            )

        stats_table.add_row(
            "Validation Errors:",
            (
                Text(str(self.stats["validation_errors"]), style="red bold")
                if self.stats["validation_errors"] > 0
                else Text("0", style="green")
            ),
        )

        components.append(stats_table)

        # Agent activity (verbose mode only)
        if self.verbose and self.agent_activity:
            activity_text = "\n".join(self.agent_activity[-5:])  # Last 5 activities
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

        return Panel(
            layout,
            title="[bold blue]Knowledge Graph Extraction[/bold blue]",
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
