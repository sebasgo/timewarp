"""Main module."""

import datetime
import re
from dataclasses import dataclass
from operator import attrgetter
from pathlib import Path


@dataclass(frozen=True)
class JournalEntry:
    date: datetime.date
    path: Path


def scan(directory: Path):
    journal_entries = []
    for path in directory.glob(pattern='*.md'):
        if (matches := re.match(r'([0-9]{4})-([0-9]{2})-([0-9]{2}).md', path.name)) is not None:
            try:
                date = datetime.date(int(matches[1]), int(matches[2]), int(matches[3]))
            except ValueError:
                continue
            entry = JournalEntry(date, path)
            journal_entries.append(entry)
    journal_entries.sort(key=attrgetter('date'), reverse=True)
    return journal_entries


def date_str(date: datetime.date) -> str:
    return date.strftime('%d.%m.%Y')
