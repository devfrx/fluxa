"""fluxa CLI."""

import typer
from rich import print as rprint
from fluxa.ui.app import FluxaApp
from fluxa.utils.logger import setup_logger

app = typer.Typer()


@app.command()
def chat() -> None:
    """Avvia l'interfaccia di chat (TUI)."""
    # Configura il logger prima di tutto
    setup_logger()

    # Avvia l'app Textual
    tui = FluxaApp()
    tui.run()


@app.command()
def version() -> None:
    """Mostra la versione."""
    rprint("[bold blue]Fluxa[/bold blue] v0.1.0")


if __name__ == "__main__":
    app()