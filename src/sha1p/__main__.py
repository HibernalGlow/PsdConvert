#!/usr/bin/env python3
"""SHA1 Processor CLI"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import List, Optional
from .core import process_directories
from .input_path import get_paths

app = typer.Typer()
console = Console()


@app.command()
def main(
    paths: Optional[List[str]] = typer.Argument(None, help="Directories to process"),
    sha1_length: int = typer.Option(-1, help="Length of SHA1 to append (-1 for no truncation)"),
    max_images: int = typer.Option(3, help="Maximum number of images to process per directory"),
    enable_rename: bool = typer.Option(True, help="Enable file renaming"),
):
    """
    Process images in directories to rename first image with SHA1.
    """
    # Handle Typer's ArgumentInfo when no paths provided
    try:
        len(paths)
    except TypeError:
        paths = None

    if paths is None:
        # Interactive mode
        console.print(Panel.fit(
            Text("SHA1 Processor - Interactive Mode", style="bold blue"),
            title="Welcome"
        ))
        console.print("No paths provided. Entering interactive mode...\n")
        paths = get_paths()
        if not paths:
            console.print("[red]No valid paths provided. Exiting.[/red]")
            raise typer.Exit(1)

    console.print(f"[green]Processing {len(paths)} path(s)...[/green]")

    for path in paths:
        console.print(f"[blue]Processing: {path}[/blue]")
        try:
            process_directories(path, sha1_length, max_images, enable_rename)
            console.print(f"[green]✓ Completed: {path}[/green]")
        except Exception as e:
            console.print(f"[red]✗ Error processing {path}: {e}[/red]")

    console.print("[bold green]All processing complete![/bold green]")


if __name__ == "__main__":
    app()