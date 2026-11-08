import datetime
import tomllib
from pathlib import Path

import pytest

from timewarp import config as config_module
from timewarp.config import Config
from timewarp.core import SpecialOffset


def test_default_path_uses_override(monkeypatch, tmp_path):
    path = tmp_path / 'custom.toml'
    monkeypatch.setenv('TIMEWARP_CONFIG', str(path))
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'xdg'))

    assert config_module.default_path() == path


def test_default_path_uses_xdg_config_home(monkeypatch, tmp_path):
    monkeypatch.delenv('TIMEWARP_CONFIG', raising=False)
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'xdg'))

    assert config_module.default_path() == tmp_path / 'xdg' / 'timewarp' / 'config.toml'


def test_default_path_falls_back_to_home(monkeypatch, tmp_path):
    monkeypatch.delenv('TIMEWARP_CONFIG', raising=False)
    monkeypatch.delenv('XDG_CONFIG_HOME', raising=False)
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))

    assert config_module.default_path() == tmp_path / '.config' / 'timewarp' / 'config.toml'


def test_load_missing_file_returns_empty_config(tmp_path):
    path = tmp_path / 'missing.toml'

    config = Config.load(path)

    assert config.path == path
    assert not config.journals


def test_load_malformed_file_returns_empty_config(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text('not = [valid', encoding='utf-8')

    assert not Config.load(config_path).journals


def test_load_ignores_invalid_entries(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '[journals."/valid"]\n'
        'last_opened = "2024-06-16"\n'
        '[journals."/invalid-date"]\n'
        'last_opened = "yesterday"\n'
        '[journals."/invalid-type"]\n'
        'last_opened = 42\n'
        '[journals."/missing-date"]\n'
        'other = "value"\n'
        '[journals]\n'
        '"/scalar" = "not a table"\n',
        encoding='utf-8',
    )

    assert Config.load(config_path).journals == {Path('/valid'): datetime.date(2024, 6, 16)}


def test_load_parses_special_offsets(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '[journals."/valid"]\n'
        'last_opened = "2024-06-16"\n'
        '[[special_offsets]]\n'
        'label = "1 month"\n'
        'target = "2024-06-16"\n'
        'reference = "2024-05-16"\n'
        '[[special_offsets]]\n'
        'label = "3 months"\n'
        'target = "2024-06-16"\n'
        'reference = "2024-03-16"\n',
        encoding='utf-8',
    )

    assert Config.load(config_path).special_offsets == [
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
        SpecialOffset('3 months', datetime.date(2024, 6, 16), datetime.date(2024, 3, 16)),
    ]


def test_load_parses_inline_special_offsets(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        'special_offsets = [\n'
        '    { label = "1 month", target = "2024-06-16", reference = "2024-05-16" },\n'
        ']\n',
        encoding='utf-8',
    )

    assert Config.load(config_path).special_offsets == [
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    ]


def test_load_parses_special_offsets_without_journals(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '[[special_offsets]]\n'
        'label = "1 month"\n'
        'target = "2024-06-16"\n'
        'reference = "2024-05-16"\n',
        encoding='utf-8',
    )

    assert Config.load(config_path).special_offsets == [
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    ]


def test_load_ignores_invalid_special_offsets(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        '[[special_offsets]]\n'
        'label = ""\n'
        'target = "2024-06-16"\n'
        'reference = "2024-05-16"\n'
        '[[special_offsets]]\n'
        'label = 42\n'
        'target = "2024-06-16"\n'
        'reference = "2024-05-16"\n'
        '[[special_offsets]]\n'
        'label = "missing target"\n'
        'reference = "2024-05-16"\n'
        '[[special_offsets]]\n'
        'label = "invalid date"\n'
        'target = "yesterday"\n'
        'reference = "2024-05-16"\n'
        '[[special_offsets]]\n'
        'label = "not later"\n'
        'target = "2024-05-16"\n'
        'reference = "2024-06-16"\n'
        '[[special_offsets]]\n'
        'label = "valid"\n'
        'target = "2024-06-16"\n'
        'reference = "2024-05-16"\n',
        encoding='utf-8',
    )

    assert Config.load(config_path).special_offsets == [
        SpecialOffset('valid', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    ]


def test_load_ignores_non_list_special_offsets(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text('special_offsets = "not a list"\n', encoding='utf-8')

    assert not Config.load(config_path).special_offsets


def test_load_ignores_non_table_special_offsets(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text('special_offsets = ["not a table"]\n', encoding='utf-8')

    assert not Config.load(config_path).special_offsets


def test_load_ignores_non_table_journals(config_path):
    config_path.parent.mkdir(parents=True)
    config_path.write_text('journals = "not a table"\n', encoding='utf-8')

    assert not Config.load(config_path).journals


def test_save_and_load_round_trip(config_path, tmp_path):
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    config = Config(config_path)
    config.set_last_opened(first, datetime.date(2024, 6, 16))
    config.set_last_opened(second, datetime.date(2023, 1, 2))

    config.save()

    loaded = Config.load(config_path)
    assert loaded.last_opened(first) == datetime.date(2024, 6, 16)
    assert loaded.last_opened(second) == datetime.date(2023, 1, 2)
    assert loaded.journals == config.journals


def test_save_and_load_round_trip_includes_special_offsets(config_path):
    offsets = [
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
        SpecialOffset('3 months', datetime.date(2024, 6, 16), datetime.date(2024, 3, 16)),
    ]
    config = Config(config_path)
    config.special_offsets = offsets

    config.save()

    assert Config.load(config_path).special_offsets == offsets


def test_saving_last_opened_preserves_special_offsets(config_path, tmp_path):
    offsets = [SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16))]
    config = Config(config_path)
    config.special_offsets = offsets
    config.set_last_opened(tmp_path / 'first', datetime.date(2024, 6, 16))
    config.save()

    config = Config.load(config_path)
    config.set_last_opened(tmp_path / 'second', datetime.date(2023, 1, 2))
    config.save()

    assert Config.load(config_path).special_offsets == offsets


def test_saving_one_journal_preserves_the_others(config_path, tmp_path):
    config = Config.load(config_path)
    config.set_last_opened(tmp_path / 'first', datetime.date(2024, 6, 16))
    config.save()

    config = Config.load(config_path)
    config.set_last_opened(tmp_path / 'second', datetime.date(2023, 1, 2))
    config.save()

    loaded = Config.load(config_path)
    assert loaded.last_opened(tmp_path / 'first') == datetime.date(2024, 6, 16)
    assert loaded.last_opened(tmp_path / 'second') == datetime.date(2023, 1, 2)


def test_save_creates_parent_directories(config_path):
    assert not config_path.parent.exists()

    Config(config_path).save()

    assert config_path.is_file()
    assert tomllib.loads(config_path.read_text(encoding='utf-8')) == {'journals': {}}


def test_save_removes_temporary_file_on_failure(config_path, mocker):
    mocker.patch('timewarp.config.os.replace', side_effect=OSError('disk full'))

    with pytest.raises(OSError, match='disk full'):
        Config(config_path).save()

    assert not list(config_path.parent.glob('*.tmp'))


def test_last_opened_normalizes_paths(config_path, monkeypatch, tmp_path):
    journal = tmp_path / 'journal'
    journal.mkdir()
    monkeypatch.chdir(tmp_path)
    config = Config(config_path)

    config.set_last_opened(Path('journal'), datetime.date(2024, 6, 16))

    assert config.last_opened(journal) == datetime.date(2024, 6, 16)
