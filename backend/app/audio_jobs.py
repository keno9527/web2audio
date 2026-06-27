from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

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
class AudioSynthesisResult:
    content: bytes
    duration_seconds: int
    mime_type: str = "audio/mpeg"


class FakeTtsClient:
    def __init__(self, duration_seconds_per_char: float = 0.2) -> None:
        self.duration_seconds_per_char = duration_seconds_per_char
        self.requests: list[str] = []

    def synthesize(self, text: str, language: Optional[str] = None) -> AudioSynthesisResult:
        self.requests.append(text)
        duration = max(1, int(round(len(text) * self.duration_seconds_per_char)))
        payload = f"FAKE-MP3[{language or 'unknown'}]:{text}".encode("utf-8")
        return AudioSynthesisResult(content=payload, duration_seconds=duration)


class FakeTosStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def put_object(self, key: str, content: bytes, content_type: str) -> str:
        self.objects[key] = content
        self.content_types[key] = content_type
        return key


@dataclass(frozen=True)
class AudioProcessingResult:
    generated: bool
    article_id: str
    audio_status: int
    segment_count: int = 0
    storage_key: Optional[str] = None
    duration_seconds: Optional[int] = None
    error_code: Optional[str] = None


def process_article_audio(
    session: Session,
    article_id: str,
    *,
    tts_client: FakeTtsClient,
    storage: FakeTosStorage,
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

    total_duration = 0
    segment_payloads: list[bytes] = []
    try:
        for segment in segments:
            segment.tts_status = AUDIO_PROCESSING
            segment.updated_at = utc_now_naive()
            session.flush()

            synthesized = tts_client.synthesize(segment.text_content, language=article.language)
            segment_key = (
                f"web2audio/articles/{article.article_id}/segments/{segment.segment_id}.mp3"
            )
            segment.audio_storage_key = storage.put_object(
                segment_key,
                synthesized.content,
                synthesized.mime_type,
            )
            segment.duration_seconds = synthesized.duration_seconds
            segment.tts_status = AUDIO_READY
            segment.updated_at = utc_now_naive()
            total_duration += synthesized.duration_seconds
            segment_payloads.append(synthesized.content)
    except Exception:
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
            error_code="tts_generation_failed",
        )

    final_key = f"web2audio/articles/{article.article_id}/final.mp3"
    final_payload = b"\n".join(segment_payloads)
    article.audio_storage_key = storage.put_object(final_key, final_payload, "audio/mpeg")
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
