"""TUI for Time Warp."""

import datetime
from pathlib import Path


from textual import log
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
    TITLE = 'Timewarp'

    BINDINGS = [
        Binding(key='q', action='quit', description='Quit'),
        Binding(key='h', action='set_date("prev_day")', description='Prev Day'),
        Binding(key='t', action='set_date("cur_day")', description='Today'),
        Binding(key='l', action='set_date("next_day")', description='Next Day'),
    ]

    directory: Path
    date = reactive(datetime.date.today, init=False)
    date_entries: list
    view: MarkdownViewer

    def __init__(self, directory):
        super().__init__()
        self.state = AppState()
        self.date_entries = []
        self.directory = directory
        scan(self.state, self.directory)

    def compose(self) -> ComposeResult:
        list = ListView(id='list', classes='column')
        list.border_title = date_str(self.date)
        self.view = MarkdownViewer(show_table_of_contents=False, classes='column')
        yield list
        yield self.view
        yield Footer()

    async def on_mount(self):
        await self.action_update_date_entries()

    def watch_date(self, old_date: datetime.date, new_date: datetime.date) -> None:
        self.query_one('#list').border_title = date_str(new_date)

    async def action_set_date(self, direction):
        if direction == 'next_day':
            self.date += datetime.timedelta(days=1)
        elif direction == 'prev_day':
            self.date -= datetime.timedelta(days=1)
        else:
            self.date = datetime.date.today()
        await self.action_update_date_entries()

    async def action_update_date_entries(self):
        day, month = self.date.day, self.date.month
        entry_list = self.query_one('#list')
        self.date_entries = []
        items = []
        entry_list.clear()
        for entry in self.state.journal_entries:
            if entry.date.day == day and entry.date.month == month:
                self.date_entries.append(entry)
                items.append(ListItem(Label(date_str(entry.date))))
        entry_list.clear()
        entry_list.extend(items)
        for i, entry in enumerate(self.date_entries):
            if entry.date.year <= self.date.year:
                entry_list.index = i
                break

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        index = event.list_view.index
        log('list highlight event', index=index)
        if index is not None:
            journal_entry = self.date_entries[index]
            log('loading', path=journal_entry.path)
            await self.view.document.load(journal_entry.path)
