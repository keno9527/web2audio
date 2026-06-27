from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


DEFAULT_MIN_CHARS = 20
DEFAULT_MAX_SEGMENT_CHARS = 4000


@dataclass(frozen=True)
class PreparedArticleText:
    cleaned_text: str
    language: Optional[str]
    segments: list[str]
    error_code: Optional[str] = None


def clean_article_text(raw_text: str) -> str:
    text = str(raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\t", " ")
    lines = []
    for line in text.split("\n"):
        normalized = re.sub(r" {2,}", " ", line).strip()
        if normalized:
            lines.append(normalized)
    return "\n".join(lines)


def normalize_language(language_hint: Optional[str], cleaned_text: str) -> Optional[str]:
    if language_hint:
        language = language_hint.strip().lower().replace("_", "-").split("-")[0]
        if language in {"zh", "en"}:
            return language
    if re.search(r"[\u4e00-\u9fff]", cleaned_text):
        return "zh"
    if re.search(r"[A-Za-z]", cleaned_text):
        return "en"
    return None


def split_segments(cleaned_text: str, max_segment_chars: int = DEFAULT_MAX_SEGMENT_CHARS) -> list[str]:
    if max_segment_chars <= 0:
        raise ValueError("max_segment_chars must be positive")

    segments: list[str] = []
    current = ""
    for paragraph in cleaned_text.split("\n"):
        if not paragraph:
            continue
        if len(paragraph) > max_segment_chars:
            if current:
                segments.append(current)
                current = ""
            segments.extend(
                paragraph[index : index + max_segment_chars]
                for index in range(0, len(paragraph), max_segment_chars)
            )
            continue
        candidate = paragraph if not current else f"{current}\n{paragraph}"
        if len(candidate) <= max_segment_chars:
            current = candidate
        else:
            if current:
                segments.append(current)
            current = paragraph
    if current:
        segments.append(current)
    return segments


def prepare_article_text(
    raw_text: str,
    language_hint: Optional[str] = None,
    min_chars: int = DEFAULT_MIN_CHARS,
    max_segment_chars: int = DEFAULT_MAX_SEGMENT_CHARS,
) -> PreparedArticleText:
    cleaned_text = clean_article_text(raw_text)
    language = normalize_language(language_hint, cleaned_text)
    if len(cleaned_text) < min_chars:
        return PreparedArticleText(
            cleaned_text=cleaned_text,
            language=language,
            segments=[],
            error_code="text_too_short",
        )
    return PreparedArticleText(
        cleaned_text=cleaned_text,
        language=language,
        segments=split_segments(cleaned_text, max_segment_chars=max_segment_chars),
    )
