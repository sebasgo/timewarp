"""TUI for Time Warp."""

import datetime
import os
import shlex
import subprocess
from pathlib import Path
from typing import Callable


from textual.app import App
from textual.app import Binding
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Label
from textual.widgets import ListItem
from textual.widgets import ListView
from textual.widgets import MarkdownViewer

from .core import JournalEntry
from .core import date_str
from .core import entries_for_date
from .core import scan
from .core import selected_index
from .core import target_date

# TODO: dummy entries for missing dates (so one can edit them)
# TODO: link parsing and following


class TimeWarpApp(App):  # pylint: disable=too-many-instance-attributes

    CSS_PATH = 'timewarp.tcss'
    TITLE = 'Timewarp'

    BINDINGS = [
        Binding(key='q', action='quit', description='Quit'),
        Binding(key='h', action='set_date("prev_day")', description='Prev Day'),
        Binding(key='t', action='set_date("cur_day")', description='Today'),
        Binding(key='l', action='set_date("next_day")', description='Next Day'),
        Binding(key='k', action='set_date("prev_year")', description='Prev Year'),
        Binding(key='j', action='set_date("next_year")', description='Next Year'),
        Binding(key='e', action='edit()', description='Edit'),
        Binding(key='r', action='refresh()', description='Refresh'),
    ]

    directory: Path
    date = reactive(datetime.date.today, init=False)
    entries: list[JournalEntry]
    date_entries: list[JournalEntry]
    current_entry: JournalEntry | None
    list: ListView
    view: MarkdownViewer
    refresh_timer: Timer

    def __init__(
        self,
        directory: Path,
        today: Callable[[], datetime.date] = datetime.date.today,
        editor: str | None = None,
    ):
        super().__init__()
        self.entries = []
        self.date_entries = []
        self.current_entry = None
        self.directory = directory
        self._today = today
        self.editor = editor or os.environ.get('EDITOR', 'vim')

    def compose(self) -> ComposeResult:
        self.list = ListView(id='list', classes='column')
        self.list.border_title = date_str(self.date)
        self.view = MarkdownViewer(show_table_of_contents=False, classes='column')
        yield Header(icon='📅')
        yield self.list
        yield self.view
        yield Footer()

    async def on_mount(self):
        self.date = self._today()
        self.view.focus()
        self.refresh_timer = self.set_interval(60, self.action_refresh, name='background_refresh')
        self.entries = scan(self.directory)
        await self.action_update_date_entries()

    def watch_date(self, _old_date: datetime.date, new_date: datetime.date) -> None:
        self.query_one('#list').border_title = date_str(new_date)

    async def action_set_date(self, direction):
        self.date = target_date(self.date, direction, self.entries, today=self._today)
        await self.action_update_date_entries()

    async def action_update_date_entries(self):
        date_entries = entries_for_date(self.entries, self.date)
        if date_entries != self.date_entries:
            self.date_entries = date_entries
            items = [ListItem(Label(date_str(entry.date))) for entry in date_entries]
            await self.list.clear()
            await self.list.extend(items)
        self.list.index = selected_index(self.date_entries, self.date)

    async def action_edit(self):
        if self.current_entry is not None:
            with self.suspend():
                subprocess.call([*shlex.split(self.editor), str(self.current_entry.path)])

    async def action_refresh(self):
        self.refresh_timer.reset()
        self.entries = scan(self.directory)
        await self.action_update_date_entries()

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        index = event.list_view.index
        if index is not None and 0 <= index < len(self.date_entries):
            self.current_entry = self.date_entries[index]
            await self.view.document.load(self.current_entry.path)
        else:
            self.current_entry = None
