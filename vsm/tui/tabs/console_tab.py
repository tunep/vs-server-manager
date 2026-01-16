"""Console tab for VSM TUI."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Input, RichLog

from ...config import load_config
from ...server import command as server_command
from ..workers import run_blocking


class ConsoleTab(Container):
    """Server console tab."""

    def compose(self) -> ComposeResult:
        """Create the console tab layout."""
        yield RichLog(id="console-output", highlight=True, markup=True)
        with Horizontal(id="console-input-container"):
            yield Input(
                placeholder="Enter server command...",
                id="console-input",
            )
            yield Button("Send", id="console-send", variant="primary")

    def on_mount(self) -> None:
        """Initialize console."""
        log = self.query_one("#console-output", RichLog)
        log.write("[dim]Server console ready. Enter commands below.[/dim]")
        log.write("[dim]Common commands: list clients, announce <msg>, genbackup[/dim]")
        log.write("")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle send button."""
        if event.button.id == "console-send":
            await self._send_command()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter key in input."""
        if event.input.id == "console-input":
            await self._send_command()

    async def _send_command(self) -> None:
        """Send the current command."""
        input_widget = self.query_one("#console-input", Input)
        cmd = input_widget.value.strip()

        if not cmd:
            return

        log = self.query_one("#console-output", RichLog)
        log.write(f"[green]> {cmd}[/green]")

        input_widget.value = ""

        try:
            config = load_config()
            result = await run_blocking(server_command, cmd, config)
            if result:
                for line in result.strip().splitlines():
                    log.write(f"  {line}")
            else:
                log.write("  [dim](no output)[/dim]")
        except Exception as e:
            log.write(f"  [red]Error: {e}[/red]")

        log.write("")
