from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.storage import AudioStorage
from app.clients.tts import TtsClient
from app.main import (
    AUDIO_FAILED,
    AUDIO_PENDING,
    AUDIO_PROCESSING,
    AUDIO_READY,
    TEXT_READY,
    ArticleAudioItem,
    ArticleTtsSegment,
    utc_now_naive,
)


@dataclass(frozen=True)
class AudioProcessingResult:
    generated: bool
    article_id: str
    audio_status: int
    segment_count: int = 0
    storage_key: Optional[str] = None
    duration_seconds: Optional[int] = None
    error_code: Optional[str] = None
    error_detail: Optional[str] = None


def process_article_audio(
    session: Session,
    article_id: str,
    *,
    tts_client: TtsClient,
    storage: AudioStorage,
) -> AudioProcessingResult:
    article = session.scalar(
        select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
    )
    if article is None:
        return AudioProcessingResult(
            generated=False,
            article_id=article_id,
            audio_status=AUDIO_FAILED,
            error_code="article_not_found",
        )

    if article.text_status != TEXT_READY:
        article.audio_status = AUDIO_FAILED
        article.updated_at = utc_now_naive()
        session.commit()
        return AudioProcessingResult(
            generated=False,
            article_id=article.article_id,
            audio_status=AUDIO_FAILED,
            error_code="text_not_ready",
        )

    segments = session.scalars(
        select(ArticleTtsSegment)
        .where(ArticleTtsSegment.article_id == article.article_id)
        .order_by(ArticleTtsSegment.segment_index)
    ).all()
    if not segments:
        article.audio_status = AUDIO_FAILED
        article.updated_at = utc_now_naive()
        session.commit()
        return AudioProcessingResult(
            generated=False,
            article_id=article.article_id,
            audio_status=AUDIO_FAILED,
            error_code="segments_missing",
        )

    article.audio_status = AUDIO_PROCESSING
    article.updated_at = utc_now_naive()
    session.flush()

    def fail_audio(error_code: str, exc: Exception) -> AudioProcessingResult:
        article.audio_status = AUDIO_FAILED
        article.updated_at = utc_now_naive()
        for segment in segments:
            if segment.tts_status == AUDIO_PROCESSING:
                segment.tts_status = AUDIO_FAILED
                segment.updated_at = utc_now_naive()
        session.commit()
        return AudioProcessingResult(
            generated=False,
            article_id=article.article_id,
            audio_status=AUDIO_FAILED,
            error_code=error_code,
            error_detail=str(exc),
        )

    total_duration = 0
    segment_payloads: list[bytes] = []
    for segment in segments:
        segment.tts_status = AUDIO_PROCESSING
        segment.updated_at = utc_now_naive()
        session.flush()

        try:
            synthesized = tts_client.synthesize(segment.text_content, language=article.language)
        except Exception as exc:
            return fail_audio("tts_generation_failed", exc)

        segment_key = f"web2audio/articles/{article.article_id}/segments/{segment.segment_id}.mp3"
        try:
            segment.audio_storage_key = storage.put_object(
                segment_key,
                synthesized.content,
                synthesized.mime_type,
            )
        except Exception as exc:
            return fail_audio("audio_storage_failed", exc)

        segment.duration_seconds = synthesized.duration_seconds
        segment.tts_status = AUDIO_READY
        segment.updated_at = utc_now_naive()
        total_duration += synthesized.duration_seconds
        segment_payloads.append(synthesized.content)

    final_key = f"web2audio/articles/{article.article_id}/final.mp3"
    final_payload = b"\n".join(segment_payloads)
    try:
        article.audio_storage_key = storage.put_object(final_key, final_payload, "audio/mpeg")
    except Exception as exc:
        return fail_audio("audio_storage_failed", exc)
    article.duration_seconds = total_duration
    article.audio_status = AUDIO_READY
    article.audio_ready_at = utc_now_naive()
    article.updated_at = article.audio_ready_at
    session.commit()

    return AudioProcessingResult(
        generated=True,
        article_id=article.article_id,
        audio_status=AUDIO_READY,
        segment_count=len(segments),
        storage_key=article.audio_storage_key,
        duration_seconds=article.duration_seconds,
    )
