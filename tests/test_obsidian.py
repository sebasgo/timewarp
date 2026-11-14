import datetime

from timewarp import obsidian


def children(markdown: str):
    parser = obsidian.markdown_parser()
    result = []
    for token in parser.parse(markdown):
        if token.type == 'inline':
            result.extend(token.children or [])
    return result


def links(markdown: str):
    return [child for child in children(markdown) if child.type == 'link_open']


def obsidian_links(markdown: str):
    return [link for link in links(markdown) if link.attrs['href'].startswith(obsidian.SCHEME)]


def text_contents(markdown: str):
    return [child.content for child in children(markdown) if child.type == 'text']


def test_basic_wikilink_becomes_obsidian_link():
    [link] = obsidian_links('See [[2024-06-16]].')
    assert link.attrs == {'href': 'obsidian:2024-06-16'}
    assert '2024-06-16' in text_contents('See [[2024-06-16]].')


def test_wikilink_alias_is_used_as_text():
    markdown = 'See [[2024-06-16|yesterday]].'
    [link] = obsidian_links(markdown)
    assert link.attrs == {'href': 'obsidian:2024-06-16'}
    assert 'yesterday' in text_contents(markdown)
    assert '[[2024-06-16|yesterday]]' not in text_contents(markdown)


def test_wikilink_keeps_heading_anchor():
    [link] = obsidian_links('[[2024-06-16#Some Heading]]')
    assert link.attrs == {'href': 'obsidian:2024-06-16#Some Heading'}


def test_wikilink_can_target_heading_in_current_document():
    [link] = obsidian_links('[[#Some Heading]]')
    assert link.attrs == {'href': 'obsidian:#Some Heading'}


def test_wikilink_accepts_md_suffix_and_folder():
    [link] = obsidian_links('[[journal/2024-06-16.md]]')
    assert link.attrs == {'href': 'obsidian:journal/2024-06-16.md'}


def test_wikilinks_are_not_parsed_in_code():
    assert not obsidian_links('`[[Note]]`')
    assert not obsidian_links('```\n[[Note]]\n```')


def test_malformed_and_empty_wikilinks_are_left_alone():
    assert not obsidian_links('[[Note')
    assert not obsidian_links('[[]]')
    assert not obsidian_links('[[Note\nAlias]]')


def test_wikilink_alias_works_in_tables_with_escaped_pipe():
    markdown = '| A |\n|---|\n| [[2024-06-16\\|yesterday]] |'
    [link] = obsidian_links(markdown)
    assert link.attrs == {'href': 'obsidian:2024-06-16'}
    assert 'yesterday' in text_contents(markdown)


def test_parse_href():
    assert obsidian.parse_href('obsidian:Note#Heading') == ('Note', 'Heading')
    assert obsidian.parse_href('obsidian:#Heading') == ('', 'Heading')
    assert obsidian.parse_href('obsidian:Note') == ('Note', '')
    assert obsidian.parse_href('https://example.com') is None


def test_linked_date():
    expected = datetime.date(2024, 6, 16)
    assert obsidian.linked_date('2024-06-16') == expected
    assert obsidian.linked_date('2024-06-16.md') == expected
    assert obsidian.linked_date('journal/2024-06-16.md') == expected
    assert obsidian.linked_date('notes') is None
    assert obsidian.linked_date('2024-13-01') is None


def test_heading_anchor():
    assert obsidian.heading_anchor('Some Heading') == 'some-heading'
    assert obsidian.heading_anchor('some-heading') == 'some-heading'
    assert obsidian.heading_anchor('') == ''
    assert obsidian.heading_anchor('^block-id') == ''
