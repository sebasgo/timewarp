=========
Time Warp
=========

Return to days begone.


Features
--------

* TODO

Setting up a New Development Environment
----------------------------------------

1.  Obtain the source code::

        git clone git@github.com:sebasgo/timewarp.git
        cd timewarp

2.  Install a new Python |venv|_::

        python3 -m venv venv
        source venv/bin/activate
        pip install -e ".[dev]"


    Using ``venv`` is not strictly necessary, but recommended to isolate
    the procect dependencies from the ones of other projects. In the
    ``pip`` step, the development dependencies to run the tests and
    generate the HTML documentation are installed as well. By passing
    the flag ``-e`` the package is installed in editable mode. Changes
    to the source code don't have to be installed to become effective
    when running ``venv/bin/timewarp``.

.. |venv| replace:: ``venv``
.. _venv: https://docs.python.org/3/library/venv.html

Running Time Warp
-----------------

After the setup of the development environment, the project can be run
from the project directory with::

    timewarp /path/to/journal/files

This requires the virtual environment to be activated. In new shells,
this step has to be repeated once from the project folder with::

    source venv/bin/activate


Configuration
-------------

Time Warp stores per-journal state in a TOML configuration file. By
default it lives at ``$XDG_CONFIG_HOME/timewarp/config.toml`` (usually
``~/.config/timewarp/config.toml``). The location can be overridden with
the ``TIMEWARP_CONFIG`` environment variable or the ``--config`` option::

    timewarp --config /path/to/config.toml /path/to/journal/files

Currently the configuration remembers the last opened date for each
journal directory::

    [journals."/path/to/journal/files"]
    last_opened = "2024-06-16"

Additional journal entries can be shown at arbitrary offsets. Each
offset is defined by a label and two dates::

    [[special_offsets]]
    label = "one month ago"
    target = "2024-07-01"
    reference = "2024-06-01"

The offset is the difference between the target and reference dates. It
is applied to the viewed day and month projected into the current year.

Special entries appear in the left list below the regular entries,
separated by a divider and identified by their label. They are skipped
when no journal file exists for the computed date.

Use ``--debug`` to show a log below the Markdown viewer. It lists the
configured offsets and the dates looked up for the current year::

    timewarp --debug /path/to/journal/files


Obsidian Links
--------------

Journal files may use Obsidian's internal link syntax. Time Warp renders
``[[2024-06-16]]`` and ``[[2024-06-16|label]]`` as links and follows them
when clicked. Heading references such as ``[[2024-06-16#Heading]]`` and
``[[#Heading]]`` jump to the matching heading.

Only links to dated journal entries are followed; other targets are ignored.
Block references (``[[2024-06-16#^block]]``) are not supported. Links inside
code are left untouched, and the journal files are never modified.


Running the Tests
-----------------

The tests are run with `pytest`_. After setting up the development
environment, run them from the project directory with::

    python -m pytest

The suite includes unit tests for the journal logic as well as headless
integration tests for the Textual user interface. Coverage is collected
automatically and must stay at or above 90%. To generate an HTML report
instead, use::

    python -m pytest --cov-report=html

Alternatively, with `uv`_ installed, no manual virtual environment is
required::

    uv sync --extra dev
    uv run --extra dev pytest

.. _pytest: https://pytest.org
.. _uv: https://docs.astral.sh/uv/

