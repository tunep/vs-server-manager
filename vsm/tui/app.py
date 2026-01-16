"""Main TUI application for Vintage Story Server Manager."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .. import __version__
from .tabs import BackupsTab, ConsoleTab, LogsTab, SchedulerTab, StatusTab
from .screens import ConfigScreen


class VSMApp(App):
    """Vintage Story Server Manager TUI Application."""

    TITLE = "Vintage Story Server Manager"
    SUB_TITLE = f"v{__version__}"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "show_config", "Config"),
        Binding("r", "refresh", "Refresh"),
        Binding("1", "switch_tab('status')", "Status", show=False),
        Binding("2", "switch_tab('logs')", "Logs", show=False),
        Binding("3", "switch_tab('backups')", "Backups", show=False),
        Binding("4", "switch_tab('scheduler')", "Scheduler", show=False),
        Binding("5", "switch_tab('console')", "Console", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Status", id="status"):
                yield StatusTab()
            with TabPane("Logs", id="logs"):
                yield LogsTab()
            with TabPane("Backups", id="backups"):
                yield BackupsTab()
            with TabPane("Scheduler", id="scheduler"):
                yield SchedulerTab()
            with TabPane("Console", id="console"):
                yield ConsoleTab()
        yield Footer()

    def action_show_config(self) -> None:
        """Show the configuration screen."""
        self.push_screen(ConfigScreen())

    def action_refresh(self) -> None:
        """Refresh the current tab."""
        tabs = self.query_one(TabbedContent)
        active_tab = tabs.active
        if active_tab == "status":
            self.query_one(StatusTab).refresh_status()
        elif active_tab == "logs":
            pass  # Logs auto-refresh
        elif active_tab == "backups":
            self.query_one(BackupsTab).refresh_backups()
        elif active_tab == "scheduler":
            self.query_one(SchedulerTab).refresh_status()

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to a specific tab."""
        tabs = self.query_one(TabbedContent)
        tabs.active = tab_id
