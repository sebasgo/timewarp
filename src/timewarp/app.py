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
from textual.containers import Vertical
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Label
from textual.widgets import ListItem
from textual.widgets import ListView
from textual.widgets import RichLog

from .config import Config
from .config import default_path
from .core import JournalEntry
from .core import SpecialEntry
from .core import date_in_year
from .core import date_str
from .core import day_month_str
from .core import entries_for_date
from .core import scan
from .core import selected_index
from .core import special_entries_for_date
from .core import target_date
from .obsidian import JournalViewer
from .obsidian import ObsidianLinkClicked
from .obsidian import heading_anchor
from .obsidian import linked_date
from .obsidian import markdown_parser
from .obsidian import parse_href

# TODO: dummy entries for missing dates (so one can edit them)


class TimeWarpApp(App):  # pylint: disable=too-many-instance-attributes

    CSS_PATH = 'timewarp.tcss'
    TITLE = 'Timewarp'

    BINDINGS = [
        Binding(key='q', action='quit', description='Quit'),
        Binding(key='h', action='set_date("prev_day")', description='Prev Day'),
        Binding(key='t', action='set_date("cur_day")', description='Today'),
        Binding(key='l', action='set_date("next_day")', description='Next Day'),
        Binding(key='k', action='select_prev_entry', description='Prev Entry'),
        Binding(key='j', action='select_next_entry', description='Next Entry'),
        Binding(key='e', action='edit()', description='Edit'),
        Binding(key='r', action='refresh()', description='Refresh'),
    ]

    directory: Path
    date = reactive(datetime.date.today, init=False)
    entries: list[JournalEntry]
    date_entries: list[JournalEntry]
    special_entries: list[SpecialEntry]
    current_entry: JournalEntry | None
    list: ListView
    view: JournalViewer
    debug_log: RichLog | None
    refresh_timer: Timer
    _pending_anchor: str

    def __init__(  # pylint: disable=too-many-arguments
        self,
        directory: Path,
        today: Callable[[], datetime.date] = datetime.date.today,
        editor: str | None = None,
        config_path: Path | None = None,
        debug: bool = False,
    ):
        super().__init__()
        self.entries = []
        self.date_entries = []
        self.special_entries = []
        self._list_entries: list[JournalEntry | None] = []
        self.current_entry = None
        self.directory = directory
        self._today = today
        self.editor = editor or os.environ.get('EDITOR', 'vim')
        self.config = Config.load(config_path or default_path())
        self._initial_date = self.config.last_opened(directory) or today()
        self.debug_enabled = debug
        self.debug_log = None
        self._pending_anchor = ''

    def compose(self) -> ComposeResult:
        self.list = ListView(id='list', classes='column')
        self.list.border_title = day_month_str(self._initial_date)
        self.view = JournalViewer(
            show_table_of_contents=False,
            parser_factory=markdown_parser,
        )
        yield Header(icon='📅')
        yield self.list
        with Vertical(id='content'):
            yield self.view
            if self.debug_enabled:
                self.debug_log = RichLog(
                    id='debug-log',
                    max_lines=500,
                    wrap=True,
                    min_width=1,
                )
                yield self.debug_log
        yield Footer()

    async def on_mount(self):
        self.date = self._initial_date
        self.view.focus()
        self.refresh_timer = self.set_interval(60, self.action_refresh, name='background_refresh')
        self.entries = scan(self.directory)
        await self.action_update_date_entries()
        self.call_after_refresh(self._log_startup_debug)

    def _log_startup_debug(self) -> None:
        self._log_config_offsets()
        self._log_special_targets()

    def watch_date(self, _old_date: datetime.date, new_date: datetime.date) -> None:
        self.query_one('#list').border_title = day_month_str(new_date)
        if self.config.last_opened(self.directory) != new_date:
            self.config.set_last_opened(self.directory, new_date)
            try:
                self.config.save()
            except OSError:
                self.log.warning('could not save configuration to %s', self.config.path)

    def _log_debug(self, message: str) -> None:
        assert self.debug_log is not None
        self.debug_log.write(message)

    def _log_config_offsets(self) -> None:
        if self.debug_log is None:
            return
        if not self.config.special_offsets:
            self._log_debug('No special offsets configured.')
            return
        self._log_debug('Configured special offsets:')
        for offset in self.config.special_offsets:
            self._log_debug(
                f'  {offset.label}: target={offset.target.isoformat()}, '
                f'reference={offset.reference.isoformat()}, offset={offset.offset.days} days'
            )

    def _log_special_targets(self) -> None:
        if self.debug_log is None:
            return
        current_year = self._today().year
        projected_date = date_in_year(self.date, current_year)
        self._log_debug(
            f'Special entries for {self.date.isoformat()} projected to {projected_date.isoformat()}:'
        )
        if not self.config.special_offsets:
            self._log_debug('  none')
            return
        entry_dates = {entry.date for entry in self.entries}
        for offset in self.config.special_offsets:
            special_date = offset.special_date(self.date, current_year)
            status = 'found' if special_date in entry_dates else 'missing'
            self._log_debug(f'  {offset.label}: looking for {special_date.isoformat()} ({status})')

    async def action_set_date(self, direction):
        selection = self._capture_selection()
        self.date = target_date(self.date, direction, today=self._today)
        self._log_special_targets()
        await self.action_update_date_entries(selection)

    def _capture_selection(self) -> tuple[str | None, int | None] | None:
        """Return the selected special label and year, if there is a selection."""
        index = self.list.index
        if index is None or not 0 <= index < len(self._list_entries):
            return None
        regular_count = len(self.date_entries)
        if index < regular_count:
            return None, self.date_entries[index].date.year
        if index == regular_count:
            return None
        special_index = index - regular_count - 1
        if 0 <= special_index < len(self.special_entries):
            special = self.special_entries[special_index]
            return special.label, special.entry.date.year
        return None

    def _selection_index(self, selection: tuple[str | None, int | None] | None) -> int | None:
        """Return the index that best preserves ``selection`` in the current list."""
        special_label, year = selection if selection is not None else (None, None)
        if special_label is not None:
            for offset, special in enumerate(self.special_entries):
                if special.label == special_label:
                    return len(self.date_entries) + 1 + offset
        if year is not None:
            for index, entry in enumerate(self.date_entries):
                if entry.date.year == year:
                    return index
        return selected_index(self.date_entries, self.date)

    async def action_update_date_entries(
        self, selection: tuple[str | None, int | None] | None = None
    ) -> bool:
        date_entries = entries_for_date(self.entries, self.date)
        special_entries = special_entries_for_date(
            self.entries,
            self.date,
            self.config.special_offsets,
            current_year=self._today().year,
        )
        rebuilt = False
        if date_entries != self.date_entries or special_entries != self.special_entries:
            rebuilt = True
            self.date_entries = date_entries
            self.special_entries = special_entries
            items = [ListItem(Label(date_str(entry.date))) for entry in date_entries]
            list_entries: list[JournalEntry | None] = list(date_entries)
            if special_entries:
                items.append(ListItem(Label('─' * 8, markup=False, classes='divider'), disabled=True))
                list_entries.append(None)
                items.extend(ListItem(Label(special.label, markup=False)) for special in special_entries)
                list_entries.extend(special.entry for special in special_entries)
            self._list_entries = list_entries
            # Batch the clear/extend so no frame is painted while the new
            # ListItems exist without their Label children (which would
            # briefly render as the "ListItem" CSS identifier).
            with self.app.batch_update():
                await self.list.clear()
                await self.list.extend(items)
        self.list.index = self._selection_index(selection)
        return rebuilt

    def action_select_next_entry(self) -> None:
        self.list.action_cursor_down()

    def action_select_prev_entry(self) -> None:
        self.list.action_cursor_up()

    async def action_edit(self):
        if self.current_entry is not None:
            with self.suspend():
                subprocess.call([*shlex.split(self.editor), str(self.current_entry.path)])

    async def action_refresh(self):
        selection = self._capture_selection()
        self.refresh_timer.reset()
        self.entries = scan(self.directory)
        await self.action_update_date_entries(selection)

    async def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        index = event.list_view.index
        if index is not None and 0 <= index < len(self._list_entries):
            self.current_entry = self._list_entries[index]
        else:
            self.current_entry = None
        if self.current_entry is not None:
            location = str(self.current_entry.path)
            anchor, self._pending_anchor = self._pending_anchor, ''
            if anchor:
                location = f'{location}#{anchor}'
            await self.view.document.load(Path(location))

    async def on_obsidian_link_clicked(self, event: ObsidianLinkClicked) -> None:
        event.stop()
        await self._follow_obsidian_link(event.href)

    async def _follow_obsidian_link(self, href: str) -> None:
        parsed = parse_href(href)
        if parsed is None:
            return
        target, anchor = parsed
        if not target:
            heading = heading_anchor(anchor)
            if heading:
                self.view.document.goto_anchor(heading)
            return
        date = linked_date(target)
        if date is None:
            self.notify(f'{target} is not a journal entry.', severity='warning')
            return
        entry = next((entry for entry in self.entries if entry.date == date), None)
        if entry is None:
            self.notify(f'No journal entry for {date.isoformat()}.', severity='warning')
            return
        self._pending_anchor = heading_anchor(anchor)
        previous_index = self.list.index
        self.date = date
        rebuilt = await self.action_update_date_entries((None, date.year))
        if not rebuilt and self.list.index == previous_index:
            # No Highlighted message is emitted when the index does not
            # change, so show the linked entry (and anchor) ourselves.
            self.current_entry = entry
            pending_anchor, self._pending_anchor = self._pending_anchor, ''
            location = str(entry.path)
            if pending_anchor:
                location = f'{location}#{pending_anchor}'
            await self.view.document.load(Path(location))
