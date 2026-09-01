from __future__ import annotations

import re
from typing import Match

_HL_PATTERN = re.compile(r"<hl\b[^>]*>(?P<content>.*?)</hl>", re.DOTALL | re.IGNORECASE)
_H2_BLOCK_SPLIT_PATTERN = re.compile(r"(<h2\b[^>]*>.*?</h2>)", re.DOTALL | re.IGNORECASE)
_H2_BLOCK_FULL_PATTERN = re.compile(r"<h2\b[^>]*>.*?</h2>", re.DOTALL | re.IGNORECASE)
_HL_PLACEHOLDER_PATTERN = re.compile(r"__HL_PLACEHOLDER_(\d+)__")
_LEAD_PATTERN = re.compile(r"<lead\b[^>]*>.*?</lead>", re.DOTALL | re.IGNORECASE)
_CONTENTS_PATTERN = re.compile(r"<contents\b[^>]*>(?P<contents_body>.*?)</contents>", re.DOTALL | re.IGNORECASE)
_CONTENTS_ENTRY_PATTERN = re.compile(r"\{(?P<text>[^}]+)\}\s*\(\s*#(?P<anchor>\w+)\s*\)", re.DOTALL | re.IGNORECASE)
_EMPTY_AUTHOR_PATTERN = re.compile(
    r"<author>\s*<description>\s*</description>\s*</author>",
    re.DOTALL | re.IGNORECASE,
)

_AUTHOR_LINK_PATTERN = re.compile(
    r"<p>\s*\{(?P<name>[^{}\n]{1,80})\}\((?P<link>[^)\s]+)\)\s*</p>\s*"
    r"<p>\s*(?P<description>.*?)\s*</p>",
    re.DOTALL | re.IGNORECASE,
)
_AUTHOR_NAME_PATTERN = re.compile(
    r"<p>\s*(?P<name>[^<>\n]{1,80})\s*</p>\s*<p>\s*(?P<description>.*?)\s*</p>",
    re.DOTALL | re.IGNORECASE,
)
_SOCIAL_ID_PATTERN = re.compile(r"user(?P<user_id>\d+)\b", re.IGNORECASE)
_NAME_TOKEN_PATTERN = re.compile(r"^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё'-]*$")

_POSITIVE_MARKERS = ("👍", "positive", "plus", "плюсы", "плюс")
_NEGATIVE_MARKERS = ("👎", "negative", "minus", "минусы", "минус")


# English ordinal words for IDs: one, two, three, ...
_EN_NUMBERS = [
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty",
]


def _english_number(n: int) -> str:
    """Return English word for 1-based index: 1->one, 2->two, ..."""
    if n <= 0:
        raise ValueError(f"Expected positive integer, got {n}")
    if n <= 20:
        return _EN_NUMBERS[n - 1]
    # For numbers > 20, fall back to numeric string
    return str(n)


def _strip_html_tags(html: str) -> str:
    """Remove all HTML tags and normalize whitespace to plain text."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _assign_content_ids_to_headers(text: str) -> str:
    """
    If the text contains a <contents>...</contents> TOC block, assign ids to the
    matching <h2> headers.

    Each TOC entry has the form: {header text}(#anchor)

    Strategy:
    1. If the header text inside {} matches the <h2> content (as plain text),
       assign sequential English-word ids: one, two, three, ...
    2. If the texts do not match, use the anchor from the TOC entry as the id,
       assigning them sequentially to h2 headers in order.
    """
    contents_match = _CONTENTS_PATTERN.search(text)
    if not contents_match:
        return text

    contents_body = contents_match.group("contents_body")

    # Parse all entries from the TOC: extract text and anchor
    entries = _CONTENTS_ENTRY_PATTERN.findall(contents_body)
    if not entries:
        return text

    # entries is list of (text, anchor) tuples
    toc_header_texts: list[str] = []
    toc_anchors: list[str] = []
    for entry_text, anchor in entries:
        plain = _strip_html_tags(entry_text)
        toc_header_texts.append(plain)
        toc_anchors.append(anchor)

    # Find all <h2> tags in the document (outside of contents — contents has no h2)
    h2_matches: list[Match[str]] = list(_H2_BLOCK_FULL_PATTERN.finditer(text))
    if not h2_matches:
        return text

    # Try to match by text first
    toc_index = 0
    h2_id_map: dict[int, str] = {}

    for h2_idx, h2_match in enumerate(h2_matches):
        h2_plain = _strip_html_tags(h2_match.group(0))

        if toc_index < len(toc_header_texts) and h2_plain == toc_header_texts[toc_index]:
            # Text matches — assign sequential id
            id_value = _english_number(toc_index + 1)
            h2_id_map[h2_idx] = id_value
            toc_index += 1

    # If at least one h2 was matched by text, use text-based matching
    if h2_id_map:
        pass  # keep the text-based mapping
    else:
        # No text matches — fallback: assign anchors sequentially to h2 headers
        h2_id_map.clear()
        for i, h2_match in enumerate(h2_matches):
            if i < len(toc_anchors):
                h2_id_map[i] = toc_anchors[i]

    if not h2_id_map:
        return text

    # Rebuild the string with ids injected into matching h2 tags
    result_parts: list[str] = []
    last_end = 0

    for h2_idx, h2_match in enumerate(h2_matches):
        if h2_idx not in h2_id_map:
            continue

        # Append everything before this h2 match
        result_parts.append(text[last_end:h2_match.start()])

        # Insert id into the opening tag: <h2 ... > -> <h2 id="xxx" ... >
        h2_tag = h2_match.group(0)
        id_value = h2_id_map[h2_idx]

        h2_with_id = re.sub(
            r"(<h2)(\b[^>]*>)",
            rf'\1 id="{id_value}"\2',
            h2_tag,
            count=1,
            flags=re.IGNORECASE,
        )
        result_parts.append(h2_with_id)
        last_end = h2_match.end()

    # Append the rest
    result_parts.append(text[last_end:])

    return "".join(result_parts)


def _replace_emoji_in_h2_headers(text: str) -> str:
    """
    Replace ➕ emoji at the start of h2 content with <image src="plus-icon" />
    and ➖ emoji with <image src="minus-icon" />.

    Example:
      <h2>➕ Good stuff</h2>
      -> <h2>\n    <image src="plus-icon" />\nGood stuff\n</h2>

      <h2>➖ Bad stuff</h2>
      -> <h2>\n    <image src="minus-icon" />\nBad stuff\n</h2>
    """
    def replace_h2(match: Match[str]) -> str:
        full_tag = match.group(0)
        # Extract opening tag and content
        open_match = re.match(r'(<h2\b[^>]*>)(.*?)(</h2>)', full_tag, re.DOTALL | re.IGNORECASE)
        if not open_match:
            return full_tag

        opening = open_match.group(1)
        content = open_match.group(2)
        closing = open_match.group(3)

        # Check if content starts with ➕ or ➖ (possibly with leading whitespace)
        plus_match = re.match(r'^(\s*)➕(.+)$', content, re.DOTALL)
        if plus_match:
            rest = plus_match.group(2).strip()
            return f'{opening}\n<image src="plus-icon" />\n{rest}\n{closing}'

        minus_match = re.match(r'^(\s*)➖(.+)$', content, re.DOTALL)
        if minus_match:
            rest = minus_match.group(2).strip()
            return f'{opening}\n<image src="minus-icon" />\n{rest}\n{closing}'

        return full_tag

    return _H2_BLOCK_FULL_PATTERN.sub(replace_h2, text)


def process_html(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("Input must be a string.")
    if not text.strip():
        return text

    processed = text.replace("\r\n", "\n").replace("\r", "\n")

    # Assign IDs to h2 headers based on contents TOC
    processed = _assign_content_ids_to_headers(processed)

    # Replace ➕/➖ emojis in h2 headers with image tags
    processed = _replace_emoji_in_h2_headers(processed)

    processed, hl_contents = _extract_hl_blocks(processed)
    processed = _replace_primary_author_before_lead(processed)
    processed = _replace_author_with_social_id(processed)
    processed = _replace_author_with_name(processed)
    processed = _restore_hl_blocks(processed, hl_contents)
    processed = _remove_empty_author_blocks(processed)
    processed = _normalize_spacing(processed)
    return processed.strip()


def _extract_hl_blocks(text: str) -> tuple[str, list[str]]:
    hl_contents: list[str] = []

    def save_hl(match: Match[str]) -> str:
        hl_contents.append(match.group("content"))
        return f"__HL_PLACEHOLDER_{len(hl_contents) - 1}__"

    return _HL_PATTERN.sub(save_hl, text), hl_contents


def _replace_primary_author_before_lead(text: str) -> str:
    lead_match = _LEAD_PATTERN.search(text)
    if not lead_match:
        return text

    before_lead = text[: lead_match.start()]
    after_lead = text[lead_match.start() :]

    link_match = _AUTHOR_LINK_PATTERN.search(before_lead)
    if link_match:
        return _move_primary_author_to_top(before_lead, after_lead, link_match)

    name_match = _AUTHOR_NAME_PATTERN.search(before_lead)
    if name_match and _is_probable_author_name(" ".join(name_match.group("name").split())):
        return _move_primary_author_to_top(before_lead, after_lead, name_match)

    return text


def _move_primary_author_to_top(
    before_lead: str,
    after_lead: str,
    match: Match[str],
) -> str:
    description = match.group("description").strip()
    if not description:
        return before_lead + after_lead

    replacement = (
        "<author>\n"
        f"    <description>{description}</description>\n"
        "</author>"
    )

    remaining_before_lead = before_lead[: match.start()] + before_lead[match.end() :]
    filled_existing_author, replacements = _EMPTY_AUTHOR_PATTERN.subn(
        replacement,
        remaining_before_lead,
        count=1,
    )
    if replacements > 0:
        merged = f"{filled_existing_author}{after_lead}".strip()
        return merged

    remaining = (remaining_before_lead + after_lead).strip()
    if not remaining:
        return replacement
    return f"{replacement}\n\n{remaining}"


def _remove_empty_author_blocks(text: str) -> str:
    return _EMPTY_AUTHOR_PATTERN.sub("", text)


def _replace_author_with_social_id(text: str) -> str:
    def replace(match: Match[str]) -> str:
        link = match.group("link")
        description = match.group("description").strip()
        user_match = _SOCIAL_ID_PATTERN.search(link)
        if not user_match or not description:
            return match.group(0)

        user_id = user_match.group("user_id")
        return (
            f'<author prop="additional" social_id="{user_id}">\n'
            f"    <description>{description}</description>\n"
            f"</author>"
        )

    return _AUTHOR_LINK_PATTERN.sub(replace, text)


def _replace_author_with_name(text: str) -> str:
    def replace(match: Match[str]) -> str:
        name = " ".join(match.group("name").split())
        description = match.group("description").strip()
        if not _is_probable_author_name(name) or not description:
            return match.group(0)

        return (
            f'<author name="{name}" prop="additional" img="">\n'
            f"    <description>{description}</description>\n"
            f"</author>"
        )

    return _AUTHOR_NAME_PATTERN.sub(replace, text)


def _is_probable_author_name(value: str) -> bool:
    if not value or len(value) > 80:
        return False
    if value[-1] in ".!?;:,":
        return False

    tokens = value.split(" ")
    if len(tokens) > 4:
        return False

    for token in tokens:
        if not _NAME_TOKEN_PATTERN.fullmatch(token):
            return False
        if not token[0].isupper():
            return False

    return True


def _restore_hl_blocks(text: str, hl_contents: list[str]) -> str:
    parts = _H2_BLOCK_SPLIT_PATTERN.split(text)
    if not parts:
        return text

    current_surface = "positive"
    restored_parts: list[str] = []

    for part in parts:
        if not part:
            continue

        if _H2_BLOCK_FULL_PATTERN.fullmatch(part):
            current_surface = _surface_from_header(part, current_surface)
            restored_parts.append(part)
            continue

        def restore_placeholder(match: Match[str]) -> str:
            index = int(match.group(1))
            if index >= len(hl_contents):
                return match.group(0)

            cleaned_content = _normalize_hl_content(hl_contents[index])
            if not cleaned_content:
                return f'<bubble surface="{current_surface}"></bubble>'

            return (
                f'<bubble surface="{current_surface}">\n'
                f"{cleaned_content}\n"
                f"</bubble>"
            )

        restored_parts.append(_HL_PLACEHOLDER_PATTERN.sub(restore_placeholder, part))

    return "".join(restored_parts)


def _surface_from_header(h2_html: str, current_surface: str) -> str:
    plain_header = re.sub(r"<[^>]+>", " ", h2_html).lower()
    if any(marker in plain_header for marker in _NEGATIVE_MARKERS):
        return "negative"
    if any(marker in plain_header for marker in _POSITIVE_MARKERS):
        return "positive"
    return current_surface


def _normalize_hl_content(content: str) -> str:
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    return "\n\n".join(lines)


def _normalize_spacing(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"</author>\s*<h2", r"</author>\n\n<h2", text, flags=re.IGNORECASE)
    text = re.sub(r"</bubble>\s*<h2", r"</bubble>\n\n<h2", text, flags=re.IGNORECASE)
    text = re.sub(r"</h2>\s*<author", r"</h2>\n\n<author", text, flags=re.IGNORECASE)
    text = re.sub(r"</h2>\s*<p", r"</h2>\n\n<p", text, flags=re.IGNORECASE)
    return text
