"""TUI for Time Warp."""

import argparse
import datetime
import sys
from pathlib import Path


from textual.app import App
from textual.app import Binding
from textual.app import ComposeResult
from textual.reactive import reactive
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
        Binding(key='h', action='set_date("prev_day")', description='Prev Day'),
        Binding(key='t', action='set_date("cur_day")', description='Today'),
        Binding(key='l', action='set_date("next_day")', description='Next Day'),
    ]

    directory: Path
    date = reactive(datetime.date.today, init=False)

    def __init__(self, directory):
        super().__init__()
        self.state = AppState()
        self.directory = directory
        scan(self.state, self.directory)

    def compose(self) -> ComposeResult:
        items = [ListItem(Label(date_str(e.date))) for e in self.state.journal_entries]
        list = ListView(id='list', classes='column', *items)
        list.border_title = date_str(self.date)
        yield list
        yield MarkdownViewer(show_table_of_contents=False, classes='column')
        yield Footer()

    def watch_date(self, old_date: datetime.date, new_date: datetime.date) -> None:
        self.query_one('#list').border_title = date_str(new_date)

    def action_set_date(self, direction):
        if direction == 'next_day':
            self.date += datetime.timedelta(days=1)
        elif direction == 'prev_day':
            self.date -= datetime.timedelta(days=1)
        else:
            self.date = datetime.date.today()


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
