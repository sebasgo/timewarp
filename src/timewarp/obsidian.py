"""Obsidian-style internal links for the Markdown viewer."""

import datetime
from pathlib import PurePath

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from textual._slug import slug
from textual.message import Message
from textual.widgets import MarkdownViewer

SCHEME = 'obsidian:'


def _parse_wikilink(state: StateInline, silent: bool) -> bool:
    """Turn an Obsidian ``[[target|alias]]`` into a regular link token."""
    source = state.src
    start = state.pos
    if source[start:start + 2] != '[[':
        return False
    end = source.find(']]', start + 2)
    if end < 0:
        return False
    content = source[start + 2:end]
    if not content.strip() or '\n' in content:
        return False
    target, separator, alias = content.partition('|')
    target = target.strip()
    label = alias.strip() if separator and alias.strip() else target
    if silent:
        state.pos = end + 2
        return True
    link = state.push('link_open', 'a', 1)
    link.attrs = {'href': f'{SCHEME}{target}'}
    state.push('text', '', 0).content = label
    state.push('link_close', 'a', -1)
    state.pos = end + 2
    return True


def obsidian_links(md: MarkdownIt) -> None:
    """Install the Obsidian wiki link rule on ``md``."""
    md.inline.ruler.before('link', 'obsidian_link', _parse_wikilink)


def markdown_parser() -> MarkdownIt:
    """Return a Markdown parser that understands Obsidian internal links."""
    return MarkdownIt('gfm-like').use(obsidian_links)


def parse_href(href: str) -> tuple[str, str] | None:
    """Split an ``obsidian:`` link into target and anchor."""
    if not href.startswith(SCHEME):
        return None
    target, _, anchor = href[len(SCHEME):].partition('#')
    return target.strip(), anchor.strip()


def linked_date(target: str) -> datetime.date | None:
    """Return the journal date named by ``target``, if there is one."""
    name = PurePath(target).name
    if name.lower().endswith('.md'):
        name = name[:-3]
    try:
        return datetime.date.fromisoformat(name)
    except ValueError:
        return None


def heading_anchor(anchor: str) -> str:
    """Convert an Obsidian heading reference to a Textual heading anchor.

    Block references are not supported and are ignored.
    """
    if not anchor or anchor.startswith('^'):
        return ''
    return slug(anchor)


class ObsidianLinkClicked(Message):
    """An Obsidian internal link was followed in the viewer."""

    def __init__(self, href: str) -> None:
        super().__init__()
        self.href = href


class JournalViewer(MarkdownViewer):
    """Markdown viewer that hands Obsidian links back to the application."""

    async def go(self, location: str | PurePath) -> None:
        href = str(location)
        if href.startswith(SCHEME):
            self.post_message(ObsidianLinkClicked(href))
        else:
            await super().go(location)
