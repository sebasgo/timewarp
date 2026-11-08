"""Configuration handling for Time Warp."""

import datetime
import os
import tempfile
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

try:  # pragma: no cover
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

import tomli_w

from .core import SpecialOffset


def default_path() -> Path:
    """Return the path of the user's configuration file."""
    override = os.environ.get('TIMEWARP_CONFIG')
    if override:
        return Path(override).expanduser()
    config_home = os.environ.get('XDG_CONFIG_HOME')
    base = Path(config_home).expanduser() if config_home else Path.home() / '.config'
    return base / 'timewarp' / 'config.toml'


def _journal_key(directory: Path) -> Path:
    return directory.expanduser().resolve()


def _parse_date(value: object) -> datetime.date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def _parse_special_offsets(value: object) -> list[SpecialOffset]:
    if not isinstance(value, list):
        return []
    offsets = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = item.get('label')
        target = _parse_date(item.get('target'))
        reference = _parse_date(item.get('reference'))
        if not isinstance(label, str) or not label.strip():
            continue
        if target is None or reference is None or target <= reference:
            continue
        offsets.append(SpecialOffset(label, target, reference))
    return offsets


@dataclass
class Config:
    path: Path
    journals: dict[Path, datetime.date] = field(default_factory=dict)
    special_offsets: list[SpecialOffset] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> 'Config':
        """Load the configuration from ``path``, ignoring malformed contents."""
        config = cls(path)
        try:
            data = tomllib.loads(path.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            return config

        journals = data.get('journals')
        if isinstance(journals, dict):
            for key, values in journals.items():
                if not isinstance(values, dict):
                    continue
                date = _parse_date(values.get('last_opened'))
                if date is not None:
                    config.journals[Path(key)] = date
        config.special_offsets = _parse_special_offsets(data.get('special_offsets'))
        return config

    def save(self) -> None:
        """Write the configuration to disk atomically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, object] = {
            'journals': {
                str(directory): {'last_opened': date.isoformat()}
                for directory, date in self.journals.items()
            }
        }
        if self.special_offsets:
            data['special_offsets'] = [
                {
                    'label': offset.label,
                    'target': offset.target.isoformat(),
                    'reference': offset.reference.isoformat(),
                }
                for offset in self.special_offsets
            ]
        text = tomli_w.dumps(data)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=self.path.parent,
                prefix=f'.{self.path.name}.',
                suffix='.tmp',
                delete=False,
            ) as file:
                file.write(text)
                temp_path = Path(file.name)
            os.replace(temp_path, self.path)
            temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def last_opened(self, directory: Path) -> datetime.date | None:
        return self.journals.get(_journal_key(directory))

    def set_last_opened(self, directory: Path, date: datetime.date) -> None:
        self.journals[_journal_key(directory)] = date
