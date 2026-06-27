from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.main import (
    AUDIO_PENDING,
    TEXT_FAILED,
    TEXT_PROCESSING,
    TEXT_READY,
    ArticleAudioItem,
    ArticleTtsSegment,
    make_business_id,
    utc_now_naive,
)
from app.text_processing import prepare_article_text


@dataclass(frozen=True)
class TextProcessingResult:
    processed: bool
    article_id: str
    text_status: int
    segment_count: int = 0
    error_code: Optional[str] = None


def process_article_text(
    session: Session,
    article_id: str,
    *,
    min_chars: int = 20,
    max_segment_chars: int = 4000,
) -> TextProcessingResult:
    article = session.scalar(
        select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
    )
    if article is None:
        return TextProcessingResult(
            processed=False,
            article_id=article_id,
            text_status=TEXT_FAILED,
            error_code="article_not_found",
        )

    now = utc_now_naive()
    article.text_status = TEXT_PROCESSING
    article.updated_at = now
    session.flush()

    prepared = prepare_article_text(
        article.text_content or "",
        language_hint=article.language,
        min_chars=min_chars,
        max_segment_chars=max_segment_chars,
    )
    article.text_content = prepared.cleaned_text
    article.text_char_count = len(prepared.cleaned_text)
    article.language = prepared.language
    article.updated_at = utc_now_naive()

    session.execute(
        delete(ArticleTtsSegment).where(ArticleTtsSegment.article_id == article.article_id)
    )

    if prepared.error_code is not None:
        article.text_status = TEXT_FAILED
        session.commit()
        return TextProcessingResult(
            processed=False,
            article_id=article.article_id,
            text_status=TEXT_FAILED,
            error_code=prepared.error_code,
        )

    for index, segment_text in enumerate(prepared.segments):
        segment_now = utc_now_naive()
        session.add(
            ArticleTtsSegment(
                segment_id=make_business_id("seg"),
                article_id=article.article_id,
                segment_index=index,
                text_content=segment_text,
                text_char_count=len(segment_text),
                tts_status=AUDIO_PENDING,
                created_at=segment_now,
                updated_at=segment_now,
            )
        )

    article.text_status = TEXT_READY
    session.commit()
    return TextProcessingResult(
        processed=True,
        article_id=article.article_id,
        text_status=TEXT_READY,
        segment_count=len(prepared.segments),
    )
