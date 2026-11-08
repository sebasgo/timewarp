# pylint: disable=redefined-outer-name
import datetime
from pathlib import Path

import pytest

from timewarp.app import TimeWarpApp


@pytest.fixture
def journal_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / 'config' / 'config.toml'


@pytest.fixture
def write_entry(journal_dir: Path):
    def _write_entry(date: datetime.date, text: str = '# Entry\n') -> Path:
        path = journal_dir / f'{date.isoformat()}.md'
        path.write_text(text, encoding='utf-8')
        return path

    return _write_entry


@pytest.fixture
def make_app(journal_dir: Path, config_path: Path):
    def _make_app(
        today: datetime.date,
        editor: str = 'vim',
        path: Path | None = None,
        debug: bool = False,
    ) -> TimeWarpApp:
        return TimeWarpApp(
            journal_dir,
            today=lambda: today,
            editor=editor,
            config_path=path or config_path,
            debug=debug,
        )

    return _make_app
