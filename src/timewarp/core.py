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


@dataclass(frozen=True)
class JournalEntry:
    date: datetime.date
    path: Path


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


def entries_for_date(entries: Iterable[JournalEntry], date: datetime.date) -> list[JournalEntry]:
    """Return all entries for the day and month of ``date``."""
    return [entry for entry in entries if entry.date.day == date.day and entry.date.month == date.month]


def selected_index(entries: Sequence[JournalEntry], date: datetime.date) -> int | None:
    """Return the index of the newest entry that is not newer than ``date``."""
    for index, entry in enumerate(entries):
        if entry.date.year <= date.year:
            return index
    return None


def target_date(
    current: datetime.date,
    direction: str,
    entries: Sequence[JournalEntry],
    today: Callable[[], datetime.date] | None = None,
) -> datetime.date:
    """Calculate the date to navigate to from ``current``."""
    if direction == 'next_day':
        return current + datetime.timedelta(days=1)
    if direction == 'prev_day':
        return current - datetime.timedelta(days=1)
    if direction == 'cur_day':
        return (today or datetime.date.today)()
    if direction == 'next_year':
        return _shift_year(current, 1, entries)
    if direction == 'prev_year':
        return _shift_year(current, -1, entries)
    raise ValueError(f'unknown direction: {direction!r}')


def _shift_year(current: datetime.date, offset: int, entries: Sequence[JournalEntry]) -> datetime.date:
    if not entries:
        return current
    years = [entry.date.year for entry in entries]
    if offset > 0 and current.year >= max(years):
        return current
    if offset < 0 and current.year <= min(years):
        return current

    year = current.year + offset
    # A leap day does not exist in every year, so clamp to the last day of the month.
    day = min(current.day, calendar.monthrange(year, current.month)[1])
    return datetime.date(year, current.month, day)
