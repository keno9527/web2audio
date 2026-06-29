from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clients.love_song import LoveSongClient
from app.love_song_contract import (
    ARTICLE_AUDIO_CONTENT_TYPE,
    WEB2AUDIO_EXTERNAL_SOURCE,
    TosAssetRegistrationRequest,
)
from app.main import (
    AUDIO_READY,
    PLAYER_FAILED,
    PLAYER_PROCESSING,
    PLAYER_READY,
    ArticleAudioItem,
    utc_now_naive,
)


@dataclass(frozen=True)
class PlayerSyncResult:
    synced: bool
    article_id: str
    player_sync_status: int
    track_id: Optional[str] = None
    asset_id: Optional[str] = None
    playlist_id: Optional[str] = None
    error_code: Optional[str] = None


def build_tos_registration_request(article: ArticleAudioItem) -> TosAssetRegistrationRequest:
    return TosAssetRegistrationRequest(
        external_source=WEB2AUDIO_EXTERNAL_SOURCE,
        external_id=article.article_id,
        content_type=ARTICLE_AUDIO_CONTENT_TYPE,
        title=article.title,
        subtitle=article.site_name,
        cover_url=article.cover_url,
        duration_seconds=article.duration_seconds or 0,
        storage_key=article.audio_storage_key or "",
        mime_type="audio/mpeg",
    )


def process_player_sync(
    session: Session,
    article_id: str,
    *,
    love_song_client: LoveSongClient,
    playlist_id: str,
) -> PlayerSyncResult:
    article = session.scalar(
        select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
    )
    if article is None:
        return PlayerSyncResult(
            synced=False,
            article_id=article_id,
            player_sync_status=PLAYER_FAILED,
            error_code="article_not_found",
        )

    if (
        article.audio_status != AUDIO_READY
        or not article.audio_storage_key
        or not article.duration_seconds
    ):
        article.player_sync_status = PLAYER_FAILED
        article.updated_at = utc_now_naive()
        session.commit()
        return PlayerSyncResult(
            synced=False,
            article_id=article.article_id,
            player_sync_status=PLAYER_FAILED,
            error_code="audio_not_ready",
        )

    article.player_sync_status = PLAYER_PROCESSING
    article.updated_at = utc_now_naive()
    session.flush()

    try:
        registered = love_song_client.register_tos_asset(
            build_tos_registration_request(article)
        )
        love_song_client.append_track_to_playlist(playlist_id, registered.track_id)
    except Exception:
        article.player_sync_status = PLAYER_FAILED
        article.updated_at = utc_now_naive()
        session.commit()
        return PlayerSyncResult(
            synced=False,
            article_id=article.article_id,
            player_sync_status=PLAYER_FAILED,
            error_code="love_song_sync_failed",
        )

    article.love_song_track_id = registered.track_id
    article.love_song_asset_id = registered.asset_id
    article.love_song_playlist_id = playlist_id
    article.player_sync_status = PLAYER_READY
    article.player_synced_at = utc_now_naive()
    article.updated_at = article.player_synced_at
    session.commit()

    return PlayerSyncResult(
        synced=True,
        article_id=article.article_id,
        player_sync_status=PLAYER_READY,
        track_id=registered.track_id,
        asset_id=registered.asset_id,
        playlist_id=playlist_id,
    )
