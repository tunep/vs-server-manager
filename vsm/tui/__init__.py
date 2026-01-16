"""TUI entry point for Vintage Story Server Manager."""

from .app import VSMApp


def main():
    """Launch the TUI application."""
    app = VSMApp()
    app.run()


__all__ = ["main", "VSMApp"]
