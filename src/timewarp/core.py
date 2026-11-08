"""Domain logic for Time Warp."""

import calendar
import datetime
import re
from dataclasses import dataclass
from operator import attrgetter
from pathlib import Path
from typing import Callable
from typing import Iterable
from typing import Sequence

_JOURNAL_FILE_PATTERN = re.compile(r'^([0-9]{4})-([0-9]{2})-([0-9]{2})\.md$')


def date_in_year(date: datetime.date, year: int) -> datetime.date:
    """Return ``date`` in ``year``, clamping leap days if necessary."""
    day = min(date.day, calendar.monthrange(year, date.month)[1])
    return datetime.date(year, date.month, day)


@dataclass(frozen=True)
class JournalEntry:
    date: datetime.date
    path: Path


@dataclass(frozen=True)
class SpecialOffset:
    label: str
    target: datetime.date
    reference: datetime.date

    @property
    def offset(self) -> datetime.timedelta:
        return self.target - self.reference

    def special_date(self, date: datetime.date, current_year: int) -> datetime.date:
        """Return the entry date for ``date`` projected into ``current_year``."""
        return date_in_year(date, current_year) - self.offset


@dataclass(frozen=True)
class SpecialEntry:
    label: str
    entry: JournalEntry


def scan(directory: Path) -> list[JournalEntry]:
    journal_entries = []
    for path in directory.glob(pattern='*.md'):
        matches = _JOURNAL_FILE_PATTERN.match(path.name)
        if matches is None:
            continue
        try:
            date = datetime.date(int(matches[1]), int(matches[2]), int(matches[3]))
        except ValueError:
            continue
        journal_entries.append(JournalEntry(date, path))
    journal_entries.sort(key=attrgetter('date'), reverse=True)
    return journal_entries


def date_str(date: datetime.date) -> str:
    return date.strftime('%d.%m.%Y')


def day_month_str(date: datetime.date) -> str:
    return date.strftime('%d.%m.')


def entries_for_date(entries: Iterable[JournalEntry], date: datetime.date) -> list[JournalEntry]:
    """Return all entries for the day and month of ``date``."""
    return [entry for entry in entries if entry.date.day == date.day and entry.date.month == date.month]


def special_entries_for_date(
    entries: Iterable[JournalEntry],
    date: datetime.date,
    offsets: Iterable[SpecialOffset],
    current_year: int,
) -> list[SpecialEntry]:
    """Return labelled entries for offsets applied to ``date`` in ``current_year``."""
    entries_by_date = {entry.date: entry for entry in entries}
    special_entries = []
    for offset in offsets:
        entry = entries_by_date.get(offset.special_date(date, current_year))
        if entry is not None:
            special_entries.append(SpecialEntry(offset.label, entry))
    return special_entries


def selected_index(entries: Sequence[JournalEntry], date: datetime.date) -> int | None:
    """Return the index of the newest entry that is not newer than ``date``."""
    for index, entry in enumerate(entries):
        if entry.date.year <= date.year:
            return index
    return None


def target_date(
    current: datetime.date,
    direction: str,
    today: Callable[[], datetime.date] | None = None,
) -> datetime.date:
    """Calculate the date to navigate to from ``current``."""
    if direction == 'next_day':
        return current + datetime.timedelta(days=1)
    if direction == 'prev_day':
        return current - datetime.timedelta(days=1)
    if direction == 'cur_day':
        return (today or datetime.date.today)()
    raise ValueError(f'unknown direction: {direction!r}')
