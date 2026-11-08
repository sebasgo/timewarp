import contextlib
import datetime

from timewarp.app import TimeWarpApp


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
