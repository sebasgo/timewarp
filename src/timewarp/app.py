"""TUI for Time Warp."""

import datetime
import subprocess
from pathlib import Path


from textual.app import App
from textual.app import Binding
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Footer
from textual.widgets import Label
from textual.widgets import ListItem
from textual.widgets import ListView
from textual.widgets import MarkdownViewer

from .core import JournalEntry
from .core import date_str
from .core import scan

# TODO: dummy entries for missing dates (so one can edit them)
# TODO: link parsing and following


class TimeWarpApp(App):

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

    def __init__(self, directory):
        super().__init__()
        self.entries = []
        self.date_entries = []
        self.directory = directory

    def compose(self) -> ComposeResult:
        self.list = ListView(id='list', classes='column')
        self.list.border_title = date_str(self.date)
        self.view = MarkdownViewer(show_table_of_contents=False, classes='column')
        yield self.list
        yield self.view
        yield Footer()

    async def on_mount(self):
        self.view.focus()
        self.refresh_timer = self.set_interval(60, self.action_refresh, name='background_refresh')
        self.entries = scan(self.directory)
        await self.action_update_date_entries()

    def watch_date(self, old_date: datetime.date, new_date: datetime.date) -> None:
        self.query_one('#list').border_title = date_str(new_date)

    async def action_set_date(self, direction):
        if direction == 'next_day':
            self.date += datetime.timedelta(days=1)
        elif direction == 'prev_day':
            self.date -= datetime.timedelta(days=1)
        elif direction == 'next_year':
            if not self.date_entries or self.date.year >= self.date_entries[0].date.year:
                return
            self.date = datetime.date(self.date.year + 1, self.date.month, self.date.day)
        elif direction == 'prev_year':
            if not self.date_entries or self.date.year <= self.date_entries[-1].date.year:
                return
            self.date = datetime.date(self.date.year - 1, self.date.month, self.date.day)
        else:
            self.date = datetime.date.today()
        await self.action_update_date_entries()

    async def action_update_date_entries(self):
        day, month = self.date.day, self.date.month
        date_entries = []
        items = []
        for entry in self.entries:
            if entry.date.day == day and entry.date.month == month:
                date_entries.append(entry)
                items.append(ListItem(Label(date_str(entry.date))))
        if date_entries != self.date_entries:
            self.date_entries = date_entries
            await self.list.clear()
            await self.list.extend(items)
        for i, entry in enumerate(self.date_entries):
            if entry.date.year <= self.date.year:
                self.list.index = i
                break

    async def action_edit(self):
        if self.current_entry is not None:
            with self.suspend():
                subprocess.call(['vim', str(self.current_entry.path)])

    async def action_refresh(self):
        self.refresh_timer.reset()
        self.entries = scan(self.directory)
        await self.action_update_date_entries()

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        index = event.list_view.index
        if index is not None:
            self.current_entry = self.date_entries[index]
            await self.view.document.load(self.current_entry.path)
        else:
            self.current_entry = None
