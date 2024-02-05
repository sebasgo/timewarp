"""TUI for Time Warp."""

import argparse
import os
import sys
from pathlib import Path


from textual.app import App
from textual.app import Binding
from textual.app import ComposeResult
from textual.widgets import Footer
from textual.widgets import Label
from textual.widgets import ListItem
from textual.widgets import ListView
from textual.widgets import MarkdownViewer

from .core import AppState
from .core import date_str
from .core import scan


class TimeWarpApp(App):

    CSS_PATH = 'timewarp.tcss'

    BINDINGS = [
        Binding(key='q', action='quit', description='Quit'),
    ]

    directory: Path

    def __init__(self, directory):
        super().__init__()
        self.state = AppState()
        self.directory = directory
        scan(self.state, self.directory)

    def compose(self) -> ComposeResult:
        items = [ListItem(Label(date_str(e.date))) for e in self.state.journal_entries]
        yield ListView(classes='column', *items)
        yield MarkdownViewer(show_table_of_contents=False, classes='column')
        yield Footer()


def dir_path_arg(path: str) -> Path:
    path = Path(path)
    if path.is_dir():
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', type=dir_path_arg, help='path to journal directory')
    args = parser.parse_args()
    app = TimeWarpApp(args.dir)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
