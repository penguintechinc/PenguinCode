"""
PenguinCode CLI - Main entry point for the chat and server modes.
"""

import asyncio
import os
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from penguincode.config.settings import load_settings
from penguincode.core import start_repl
from penguincode.core.session import SessionManager

app = typer.Typer(
    name="penguincode",
    help="PenguinCode CLI - AI-powered coding assistant using Ollama",
    no_args_is_help=True,
)

console = Console()


@app.command()
def chat(
    project_dir: str = typer.Option(
        ".",
        "--project",
        "-p",
        help="Project directory to work with",
    ),
    config_path: str = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to config.yaml",
    ),
) -> None:
    """Start an interactive chat session."""
    # Run the REPL in async context
    asyncio.run(start_repl(project_dir, config_path))


@app.command()
def serve(
    port: int = typer.Option(
        8420,
        "--port",
        "-p",
        help="Port to serve on",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        "-h",
        help="Host to bind to",
    ),
) -> None:
    """Start the PenguinCode server (for VS Code extension integration)."""
    console.print(f"[cyan]Starting PenguinCode Server[/cyan]")
    console.print(f"Listening on http://{host}:{port}")

    # TODO: Implement FastAPI server
    # This will be implemented by the server/app.py module
    console.print("[yellow]Server mode not yet implemented[/yellow]")


@app.command()
def config(
    action: str = typer.Argument(
        "show",
        help="Action: show, set",
    ),
    key: str = typer.Option(
        None,
        "--key",
        "-k",
        help="Configuration key (for set action)",
    ),
    value: str = typer.Option(
        None,
        "--value",
        "-v",
        help="Configuration value (for set action)",
    ),
    config_path: str = typer.Option(
        "config.yaml",
        "--config",
        "-c",
        help="Path to config.yaml",
    ),
) -> None:
    """Manage configuration."""
    if action == "show":
        try:
            settings = load_settings(config_path)
            console.print("\n[bold cyan]PenguinCode Configuration[/bold cyan]\n")

            # Display key settings
            table = Table(title="Ollama Settings", show_header=True, header_style="bold cyan")
            table.add_column("Setting", style="green")
            table.add_column("Value", style="yellow")
            table.add_row("API URL", settings.ollama.api_url)
            table.add_row("Timeout", f"{settings.ollama.timeout}s")
            console.print(table)

            # Display model assignments
            table = Table(title="\nModel Roles", show_header=True, header_style="bold cyan")
            table.add_column("Role", style="green")
            table.add_column("Model", style="yellow")
            table.add_row("Planning", settings.models.planning)
            table.add_row("Orchestration", settings.models.orchestration)
            table.add_row("Research", settings.models.research)
            table.add_row("Execution", settings.models.execution)
            console.print(table)

            console.print(f"\n[dim]Config file: {config_path}[/dim]\n")

        except FileNotFoundError:
            console.print(f"[red]Config file not found: {config_path}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error loading config: {str(e)}[/red]")
            raise typer.Exit(1)

    elif action == "set":
        if not key or value is None:
            console.print("[red]Error: --key and --value required for set action[/red]")
            raise typer.Exit(1)

        console.print(f"[cyan]Setting {key} = {value}[/cyan]")
        console.print("[yellow]Config update not fully implemented yet[/yellow]")
        console.print("[dim]Hint: Edit config.yaml directly for now[/dim]")

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        raise typer.Exit(1)


@app.command()
def history(
    project_dir: str = typer.Option(
        ".",
        "--project",
        "-p",
        help="Project directory",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Number of sessions to show",
    ),
) -> None:
    """Show session history."""
    try:
        session_manager = SessionManager(project_dir)
        sessions = session_manager.list_sessions(limit=limit)

        if not sessions:
            console.print("[yellow]No sessions found[/yellow]")
            return

        console.print("\n[bold cyan]Session History[/bold cyan]\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Session ID", style="green")
        table.add_column("Created", style="yellow")
        table.add_column("Messages", style="blue")

        for session in sessions:
            table.add_row(
                session["session_id"],
                session["created_at"],
                str(session["message_count"]),
            )

        console.print(table)
        console.print(f"\n[dim]Project: {Path(project_dir).resolve()}[/dim]\n")

    except Exception as e:
        console.print(f"[red]Error loading history: {str(e)}[/red]")
        raise typer.Exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
