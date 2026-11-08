import contextlib
import datetime

from timewarp.app import TimeWarpApp
from timewarp.config import Config
from timewarp.core import SpecialOffset


async def test_startup_lists_entries_for_today(make_app, write_entry):
    today = datetime.date(2024, 6, 16)
    newest = write_entry(today, '# Today\n')
    older = write_entry(datetime.date(2023, 6, 16), '# Older\n')
    write_entry(datetime.date(2024, 7, 1), '# Other day\n')

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.date == today
        assert [entry.path for entry in app.date_entries] == [newest, older]
        assert app.list.index == 0
        assert app.list.border_title == '16.06.2024'
        assert app.current_entry == app.date_entries[0]


async def test_day_navigation_updates_entries(make_app, write_entry):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press('l')
        await pilot.pause()
        assert app.date == datetime.date(2024, 6, 17)
        assert app.date_entries == []
        assert app.list.index is None
        assert app.current_entry is None

        await pilot.press('h')
        await pilot.pause()
        assert app.date == today
        assert len(app.date_entries) == 1
        assert app.list.index == 0


async def test_today_binding_returns_to_injected_today(make_app, write_entry):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press('l')
        await pilot.pause()
        assert app.date == datetime.date(2024, 6, 17)

        await pilot.press('t')
        await pilot.pause()
        assert app.date == today


async def test_year_navigation_is_clamped_to_entry_range(make_app, write_entry):
    today = datetime.date(2022, 6, 16)
    write_entry(datetime.date(2024, 6, 16), '# 2024\n')
    write_entry(datetime.date(2022, 6, 16), '# 2022\n')

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.list.index == 1

        await pilot.press('j')
        await pilot.pause()
        assert app.date == datetime.date(2023, 6, 16)
        assert app.list.index == 1

        await pilot.press('j')
        await pilot.pause()
        assert app.date == datetime.date(2024, 6, 16)
        assert app.list.index == 0

        await pilot.press('j')
        await pilot.pause()
        assert app.date == datetime.date(2024, 6, 16)

        await pilot.press('k')
        await pilot.pause()
        assert app.date == datetime.date(2023, 6, 16)
        assert app.list.index == 1

        await pilot.press('k')
        await pilot.pause()
        assert app.date == datetime.date(2022, 6, 16)

        await pilot.press('k')
        await pilot.pause()
        assert app.date == datetime.date(2022, 6, 16)


async def test_previous_year_from_leap_day_does_not_crash(make_app, write_entry):
    today = datetime.date(2024, 2, 29)
    write_entry(today, '# Leap day\n')
    write_entry(datetime.date(2023, 2, 28), '# Not a leap year\n')

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press('k')
        await pilot.pause()

        assert app.date == datetime.date(2023, 2, 28)
        assert app.list.index == 0


async def test_highlighting_entry_loads_markdown(make_app, write_entry):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n\nToday text.\n')
    second = write_entry(datetime.date(2023, 6, 16), '# Older\n\nOlder text.\n')

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        app.list.index = 1
        await pilot.pause()

        assert app.current_entry.path == second
        blocks = [block.render().plain for block in app.view.document.query('MarkdownBlock')]
        assert any('Older text.' in text for text in blocks)


async def test_refresh_picks_up_new_entries(make_app, journal_dir):
    today = datetime.date(2024, 6, 16)

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.date_entries == []

        path = journal_dir / '2024-06-16.md'
        path.write_text('# New entry\n', encoding='utf-8')

        await app.action_refresh()
        await pilot.pause()

        assert [entry.path for entry in app.date_entries] == [path]
        assert app.list.index == 0


async def test_edit_opens_configured_editor(make_app, write_entry, mocker):
    today = datetime.date(2024, 6, 16)
    path = write_entry(today, '# Today\n')
    app = make_app(today, editor='myeditor --wait')
    call = mocker.patch('timewarp.app.subprocess.call')
    mocker.patch.object(TimeWarpApp, 'suspend', side_effect=contextlib.nullcontext)

    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.current_entry is not None

        await app.action_edit()

    call.assert_called_once_with(['myeditor', '--wait', str(path)])


async def test_edit_does_nothing_without_current_entry(make_app, mocker):
    app = make_app(datetime.date(2024, 6, 16))
    call = mocker.patch('timewarp.app.subprocess.call')

    async with app.run_test() as pilot:
        await pilot.pause()
        app.current_entry = None

        await app.action_edit()

    call.assert_not_called()


async def test_startup_restores_last_opened_date(make_app, write_entry, journal_dir, config_path):
    today = datetime.date(2024, 6, 16)
    restored = datetime.date(2023, 5, 10)
    write_entry(today, '# Today\n')
    restored_path = write_entry(restored, '# Restored\n')
    config = Config(config_path)
    config.set_last_opened(journal_dir, restored)
    config.save()

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.date == restored
        assert [entry.path for entry in app.date_entries] == [restored_path]
        assert app.list.border_title == '10.05.2023'


async def test_startup_ignores_corrupt_config(make_app, config_path):
    today = datetime.date(2024, 6, 16)
    config_path.parent.mkdir(parents=True)
    config_path.write_text('not = [valid', encoding='utf-8')

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.date == today


async def test_date_change_is_persisted(make_app, write_entry, journal_dir, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press('l')
        await pilot.pause()

    assert Config.load(config_path).last_opened(journal_dir) == datetime.date(2024, 6, 17)


async def test_date_change_is_restored_in_a_new_app(make_app, write_entry):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press('l')
        await pilot.pause()

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.date == datetime.date(2024, 6, 17)


async def test_save_failure_does_not_crash(make_app, write_entry, mocker):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    mocker.patch.object(Config, 'save', side_effect=OSError('read-only'))

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press('l')
        await pilot.pause()

        assert app.date == datetime.date(2024, 6, 17)


def configure_special_offsets(config_path, *offsets):
    config = Config(config_path)
    config.special_offsets = list(offsets)
    config.save()


async def test_special_entries_are_listed_after_a_disabled_divider(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    special_path = write_entry(datetime.date(2024, 5, 16), '# Special\n')
    configure_special_offsets(
        config_path,
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    )

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert [special.entry.path for special in app.special_entries] == [special_path]
        items = list(app.list.children)
        assert len(items) == 3
        assert not items[0].disabled
        assert items[1].disabled
        assert not items[2].disabled
        assert items[2].children[0].renderable.plain == '1 month'


async def test_missing_special_entries_are_skipped(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    configure_special_offsets(
        config_path,
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    )

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.special_entries == []
        assert len(app.list.children) == 1


async def test_special_entries_without_regular_entries(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    special_path = write_entry(datetime.date(2024, 5, 16), '# Special\n')
    configure_special_offsets(
        config_path,
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    )

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.date_entries == []
        assert [special.entry.path for special in app.special_entries] == [special_path]
        items = list(app.list.children)
        assert len(items) == 2
        assert items[0].disabled
        assert not items[1].disabled


async def test_selecting_special_entry_loads_markdown(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    special_path = write_entry(datetime.date(2024, 5, 16), '# Special\n\nSpecial text.\n')
    configure_special_offsets(
        config_path,
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    )

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        app.list.index = len(app.date_entries) + 1
        await pilot.pause()

        assert app.current_entry.path == special_path
        blocks = [block.render().plain for block in app.view.document.query('MarkdownBlock')]
        assert any('Special text.' in text for text in blocks)


async def test_special_entries_use_viewed_date_in_current_year(
    make_app, write_entry, config_path, journal_dir
):
    today = datetime.date(2026, 2, 20)
    viewed = datetime.date(2023, 7, 10)
    write_entry(viewed, '# Viewed\n')
    special_path = write_entry(datetime.date(2026, 6, 9), '# Special\n')
    config = Config(config_path)
    config.set_last_opened(journal_dir, viewed)
    config.special_offsets = [
        SpecialOffset('example', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    ]
    config.save()

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.date == viewed
        assert [special.entry.path for special in app.special_entries] == [special_path]


async def test_day_navigation_reprojects_special_entry(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    first_special = write_entry(datetime.date(2024, 5, 16), '# May 16\n')
    next_special = write_entry(datetime.date(2024, 5, 17), '# May 17\n')
    configure_special_offsets(
        config_path,
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    )

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert [special.entry.path for special in app.special_entries] == [first_special]

        await pilot.press('l')
        await pilot.pause()

        assert app.date == datetime.date(2024, 6, 17)
        assert [special.entry.path for special in app.special_entries] == [next_special]


async def test_year_navigation_does_not_change_special_entry(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    write_entry(datetime.date(2025, 6, 16), '# Next year\n')
    special_path = write_entry(datetime.date(2024, 5, 16), '# May 16\n')
    configure_special_offsets(
        config_path,
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    )

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press('j')
        await pilot.pause()

        assert app.date == datetime.date(2025, 6, 16)
        assert [special.entry.path for special in app.special_entries] == [special_path]


async def test_keyboard_navigation_skips_the_divider(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    write_entry(datetime.date(2024, 5, 16), '# Special\n')
    configure_special_offsets(
        config_path,
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    )

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        app.list.index = 0
        app.list.action_cursor_down()
        await pilot.pause()

        assert app.list.index == 2


async def test_date_change_keeps_special_offsets_in_config(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    offsets = [SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16))]
    configure_special_offsets(config_path, *offsets)

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press('l')
        await pilot.pause()

    assert Config.load(config_path).special_offsets == offsets


def debug_log_text(app) -> str:
    assert app.debug_log is not None
    return '\n'.join(line.text for line in app.debug_log.lines)


async def test_debug_log_is_absent_by_default(make_app, write_entry):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')

    app = make_app(today)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.debug_log is None
        assert len(app.query('#debug-log')) == 0


async def test_debug_log_is_below_the_markdown_viewer(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    configure_special_offsets(
        config_path,
        SpecialOffset('example', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    )

    app = make_app(today, debug=True)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert app.debug_log is not None
        assert app.debug_log.parent is app.view.parent
        assert list(app.debug_log.parent.children) == [app.view, app.debug_log]


async def test_debug_logs_configured_offsets(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    write_entry(datetime.date(2024, 5, 16), '# Special\n')
    configure_special_offsets(
        config_path,
        SpecialOffset('example', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    )

    app = make_app(today, debug=True)
    async with app.run_test() as pilot:
        await pilot.pause()

        log = debug_log_text(app)
        assert 'Configured special offsets:' in log
        assert 'example: target=2024-06-16, reference=2024-05-16,' in log
        assert 'offset=31 days' in log
        assert 'Special entries for 2024-06-16 projected to 2024-06-16:' in log
        assert 'looking for 2024-05-16 (found)' in log


async def test_debug_logs_no_offsets_configured(make_app, write_entry):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')

    app = make_app(today, debug=True)
    async with app.run_test() as pilot:
        await pilot.pause()

        log = debug_log_text(app)
        assert 'No special offsets configured.' in log
        assert 'Special entries for 2024-06-16 projected to 2024-06-16:' in log
        assert 'none' in log


async def test_debug_logs_special_targets_on_navigation(make_app, write_entry, config_path):
    today = datetime.date(2024, 6, 16)
    write_entry(today, '# Today\n')
    write_entry(datetime.date(2024, 5, 17), '# May 17\n')
    configure_special_offsets(
        config_path,
        SpecialOffset('1 month', datetime.date(2024, 6, 16), datetime.date(2024, 5, 16)),
    )

    app = make_app(today, debug=True)
    async with app.run_test() as pilot:
        await pilot.pause()

        assert 'looking for 2024-05-16 (missing)' in debug_log_text(app)

        await pilot.press('l')
        await pilot.pause()

        log = debug_log_text(app)
        assert 'Special entries for 2024-06-17 projected to 2024-06-17:' in log
        assert 'looking for 2024-05-17 (found)' in log
