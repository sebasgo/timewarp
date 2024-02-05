import datetime
from pathlib import Path

import pytest

from timewarp import core


@pytest.fixture(name='state')
def state_fixture():
    return core.AppState()


def test_scan(state, mocker):
    directory = Path('/foo/bar')
    files = [
        directory / '2024-02-29.md',
        directory / '1986-06-16.md',
        directory / 'other.md',
        directory / 'sub' / '2013-10-21.md',
        directory / '2000-13-01.md',
    ]
    with mocker.patch('pathlib.Path.glob', return_value=files):
        core.scan(state, directory)
    assert state.journal_entries == [
        core.JournalEntry(datetime.date(1986, 6, 16), files[1]),
        core.JournalEntry(datetime.date(2013, 10, 21), files[3]),
        core.JournalEntry(datetime.date(2024, 2, 29), files[0]),
    ]
