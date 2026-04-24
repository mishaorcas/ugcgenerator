from __future__ import annotations

import re
from typing import Match

_HL_PATTERN = re.compile(r"<hl\b[^>]*>(?P<content>.*?)</hl>", re.DOTALL | re.IGNORECASE)
_H2_BLOCK_SPLIT_PATTERN = re.compile(r"(<h2\b[^>]*>.*?</h2>)", re.DOTALL | re.IGNORECASE)
_H2_BLOCK_FULL_PATTERN = re.compile(r"<h2\b[^>]*>.*?</h2>", re.DOTALL | re.IGNORECASE)
_HL_PLACEHOLDER_PATTERN = re.compile(r"__HL_PLACEHOLDER_(\d+)__")

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


def process_html(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("Input must be a string.")
    if not text.strip():
        return text

    processed = text.replace("\r\n", "\n").replace("\r", "\n")
    processed, hl_contents = _extract_hl_blocks(processed)
    processed = _replace_author_with_social_id(processed)
    processed = _replace_author_with_name(processed)
    processed = _restore_hl_blocks(processed, hl_contents)
    processed = _normalize_spacing(processed)
    return processed.strip()


def _extract_hl_blocks(text: str) -> tuple[str, list[str]]:
    hl_contents: list[str] = []

    def save_hl(match: Match[str]) -> str:
        hl_contents.append(match.group("content"))
        return f"__HL_PLACEHOLDER_{len(hl_contents) - 1}__"

    return _HL_PATTERN.sub(save_hl, text), hl_contents


def _replace_author_with_social_id(text: str) -> str:
    def replace(match: Match[str]) -> str:
        link = match.group("link")
        description = match.group("description").strip()
        user_match = _SOCIAL_ID_PATTERN.search(link)
        if not user_match or not description:
            return match.group(0)

        user_id = user_match.group("user_id")
        return (
            f'<author-ugc prop="additional" social_id="{user_id}">\n'
            f"    <description>{description}</description>\n"
            f"</author-ugc>"
        )

    return _AUTHOR_LINK_PATTERN.sub(replace, text)


def _replace_author_with_name(text: str) -> str:
    def replace(match: Match[str]) -> str:
        name = " ".join(match.group("name").split())
        description = match.group("description").strip()
        if not _is_probable_author_name(name) or not description:
            return match.group(0)

        return (
            f'<author-ugc name="{name}" prop="additional" img="">\n'
            f"    <description>{description}</description>\n"
            f"</author-ugc>"
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
                return f'<hl isbuble="true" surface="{current_surface}"></hl>'

            return (
                f'<hl isbuble="true" surface="{current_surface}">\n'
                f"{cleaned_content}\n"
                f"</hl>"
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
    text = re.sub(r"</author-ugc>\s*<h2", r"</author-ugc>\n\n<h2", text, flags=re.IGNORECASE)
    text = re.sub(r"</hl>\s*<h2", r"</hl>\n\n<h2", text, flags=re.IGNORECASE)
    text = re.sub(r"</h2>\s*<author-ugc", r"</h2>\n\n<author-ugc", text, flags=re.IGNORECASE)
    text = re.sub(r"</h2>\s*<p", r"</h2>\n\n<p", text, flags=re.IGNORECASE)
    return text
