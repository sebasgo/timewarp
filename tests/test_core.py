import datetime
from pathlib import Path

import pytest

from timewarp import core


def make_entry(year: int, month: int, day: int) -> core.JournalEntry:
    return core.JournalEntry(datetime.date(year, month, day), Path(f'{year}-{month:02d}-{day:02d}.md'))


def test_scan_returns_valid_entries_sorted_newest_first(journal_dir, write_entry):
    newest = write_entry(datetime.date(2024, 2, 29))
    middle = write_entry(datetime.date(2013, 10, 21))
    oldest = write_entry(datetime.date(1986, 6, 16))

    assert core.scan(journal_dir) == [
        core.JournalEntry(datetime.date(2024, 2, 29), newest),
        core.JournalEntry(datetime.date(2013, 10, 21), middle),
        core.JournalEntry(datetime.date(1986, 6, 16), oldest),
    ]


def test_scan_ignores_invalid_names_and_directories(journal_dir, write_entry):
    valid = write_entry(datetime.date(2024, 2, 29))
    (journal_dir / '2000-13-01.md').write_text('invalid month', encoding='utf-8')
    (journal_dir / '2023-02-29.md').write_text('invalid day', encoding='utf-8')
    (journal_dir / 'other.md').write_text('not a journal entry', encoding='utf-8')
    (journal_dir / 'notes-2024-01-01.md').write_text('not a journal entry', encoding='utf-8')
    (journal_dir / '2024-02-29.md.bak').write_text('not a journal entry', encoding='utf-8')
    (journal_dir / '2024-02-29xmd').write_text('not a journal entry', encoding='utf-8')
    nested = journal_dir / 'sub'
    nested.mkdir()
    (nested / '2013-10-21.md').write_text('nested', encoding='utf-8')

    assert core.scan(journal_dir) == [core.JournalEntry(datetime.date(2024, 2, 29), valid)]


def test_scan_empty_directory(journal_dir):
    assert not core.scan(journal_dir)


def test_date_str():
    assert core.date_str(datetime.date(2024, 2, 9)) == '09.02.2024'


def test_day_month_str():
    assert core.day_month_str(datetime.date(2024, 2, 9)) == '09.02.'


def test_entries_for_date_matches_day_and_month_across_years():
    entries = [
        make_entry(2024, 6, 16),
        make_entry(2023, 6, 16),
        make_entry(2023, 6, 17),
    ]

    assert core.entries_for_date(entries, datetime.date(2022, 6, 16)) == [
        make_entry(2024, 6, 16),
        make_entry(2023, 6, 16),
    ]


def test_special_entries_for_date_applies_offsets_and_labels():
    entries = [
        make_entry(2024, 6, 16),
        make_entry(2024, 5, 16),
        make_entry(2024, 3, 16),
    ]
    offsets = [
        core.SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
        core.SpecialOffset('3 months', datetime.date(2024, 6, 16), datetime.date(2024, 3, 16)),
    ]

    assert core.special_entries_for_date(
        entries, datetime.date(2024, 6, 16), offsets, current_year=2024
    ) == [
        core.SpecialEntry('1 month', entries[1]),
        core.SpecialEntry('3 months', entries[2]),
    ]


def test_special_entries_for_date_skips_dates_without_entry():
    entries = [make_entry(2024, 6, 16)]
    offsets = [core.SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16))]

    assert not core.special_entries_for_date(
        entries, datetime.date(2024, 6, 16), offsets, current_year=2024
    )


def test_special_entries_for_date_without_offsets():
    assert not core.special_entries_for_date(
        [make_entry(2024, 6, 16)], datetime.date(2024, 6, 16), [], current_year=2024
    )


def test_special_entries_for_date_applies_full_offset():
    entries = [make_entry(2023, 3, 1)]
    offsets = [core.SpecialOffset('1 year', datetime.date(2024, 3, 1), datetime.date(2023, 3, 1))]

    assert core.special_entries_for_date(
        entries, datetime.date(2024, 3, 1), offsets, current_year=2024
    ) == [core.SpecialEntry('1 year', entries[0])]


def test_special_entries_for_date_projects_viewed_date_into_current_year():
    entries = [
        make_entry(2023, 6, 9),
        make_entry(2026, 6, 9),
    ]
    offsets = [core.SpecialOffset('example', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16))]
    viewed = datetime.date(2023, 7, 10)

    assert core.special_entries_for_date(entries, viewed, offsets, current_year=2023) == [
        core.SpecialEntry('example', entries[0]),
    ]
    assert core.special_entries_for_date(entries, viewed, offsets, current_year=2026) == [
        core.SpecialEntry('example', entries[1]),
    ]


def test_special_entries_for_date_clamps_leap_day_when_projecting():
    entries = [make_entry(2023, 2, 27)]
    offsets = [core.SpecialOffset('leap', datetime.date(2024, 3, 1), datetime.date(2024, 2, 29))]

    assert core.special_entries_for_date(
        entries, datetime.date(2024, 2, 29), offsets, current_year=2023
    ) == [core.SpecialEntry('leap', entries[0])]


def test_selected_index_uses_newest_entry_not_newer_than_date():
    entries = [make_entry(2024, 6, 16), make_entry(2022, 6, 16), make_entry(2020, 6, 16)]

    assert core.selected_index(entries, datetime.date(2025, 6, 16)) == 0
    assert core.selected_index(entries, datetime.date(2023, 6, 16)) == 1
    assert core.selected_index(entries, datetime.date(2020, 6, 16)) == 2
    assert core.selected_index(entries, datetime.date(2019, 6, 16)) is None
    assert core.selected_index([], datetime.date(2024, 6, 16)) is None


def test_target_date_moves_one_day():
    def today():
        return datetime.date(2024, 6, 16)

    assert core.target_date(datetime.date(2024, 6, 16), 'next_day', today) == datetime.date(2024, 6, 17)
    assert core.target_date(datetime.date(2024, 6, 16), 'prev_day', today) == datetime.date(2024, 6, 15)
    assert core.target_date(datetime.date(2020, 1, 1), 'cur_day', today) == datetime.date(2024, 6, 16)


def test_target_date_crosses_year_boundaries():
    assert core.target_date(datetime.date(2024, 12, 31), 'next_day') == datetime.date(2025, 1, 1)
    assert core.target_date(datetime.date(2024, 1, 1), 'prev_day') == datetime.date(2023, 12, 31)


def test_target_date_handles_leap_day():
    assert core.target_date(datetime.date(2024, 2, 28), 'next_day') == datetime.date(2024, 2, 29)
    assert core.target_date(datetime.date(2024, 2, 29), 'next_day') == datetime.date(2024, 3, 1)


def test_target_date_rejects_unknown_direction():
    with pytest.raises(ValueError, match='unknown direction'):
        core.target_date(datetime.date(2024, 6, 16), 'sideways')
