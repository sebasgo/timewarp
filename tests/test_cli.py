import argparse
import sys

import pytest

from timewarp import __main__ as cli


def test_dir_path_arg_accepts_directory(tmp_path):
    assert cli.dir_path_arg(str(tmp_path)) == tmp_path


def test_dir_path_arg_rejects_file(tmp_path):
    path = tmp_path / 'not-a-directory'
    path.write_text('', encoding='utf-8')

    with pytest.raises(argparse.ArgumentTypeError, match='is not a valid path'):
        cli.dir_path_arg(str(path))


def test_main_runs_app_with_directory(tmp_path, mocker):
    app_class = mocker.patch.object(cli, 'TimeWarpApp')
    mocker.patch.object(sys, 'argv', ['timewarp', str(tmp_path)])

    assert cli.main() == 0

    app_class.assert_called_once_with(tmp_path)
    app_class.return_value.run.assert_called_once_with()


def test_main_requires_directory(mocker):
    mocker.patch.object(sys, 'argv', ['timewarp'])

    with pytest.raises(SystemExit) as error:
        cli.main()

    assert error.value.code == 2


def test_main_rejects_missing_directory(tmp_path, mocker):
    mocker.patch.object(sys, 'argv', ['timewarp', str(tmp_path / 'missing')])

    with pytest.raises(SystemExit) as error:
        cli.main()

    assert error.value.code == 2
