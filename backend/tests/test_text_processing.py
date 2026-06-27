from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.text_processing import prepare_article_text  # noqa: E402


def test_prepare_article_text_cleans_detects_language_and_segments() -> None:
    raw_text = (
        "  第一段  内容足够长。\r\n"
        "\r\n"
        "第二段\t内容也足够长。\n"
        "\u00a0\n"
        "第三段结尾。  "
    )

    prepared = prepare_article_text(raw_text, language_hint="zh-CN", max_segment_chars=14)

    assert prepared.cleaned_text == "第一段 内容足够长。\n第二段 内容也足够长。\n第三段结尾。"
    assert prepared.language == "zh"
    assert prepared.segments == [
        "第一段 内容足够长。",
        "第二段 内容也足够长。",
        "第三段结尾。",
    ]


def test_prepare_article_text_rejects_too_short_body() -> None:
    prepared = prepare_article_text("太短", language_hint="zh", min_chars=10)

    assert prepared.cleaned_text == "太短"
    assert prepared.language == "zh"
    assert prepared.segments == []
    assert prepared.error_code == "text_too_short"
