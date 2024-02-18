"""Main module."""

import datetime
import re
from dataclasses import dataclass
from dataclasses import field
from operator import attrgetter
from pathlib import Path


@dataclass(frozen=True)
class JournalEntry:
    date: datetime.date
    path: Path

@dataclass
class AppState:
    journal_entries: list[JournalEntry] = field(default_factory=list, init=False)


def scan(state: AppState, directory: Path):
    state.journal_entries = []
    for path in directory.glob(pattern='*.md'):
        if (matches := re.match(r'([0-9]{4})-([0-9]{2})-([0-9]{2}).md', path.name)) is not None:
            try:
                date = datetime.date(int(matches[1]), int(matches[2]), int(matches[3]))
            except ValueError:
                continue
            entry = JournalEntry(date, path)
            state.journal_entries.append(entry)
    state.journal_entries.sort(key=attrgetter('date'), reverse=True)


def date_str(date: datetime.date) -> str:
    return date.strftime('%d.%m.%Y')
