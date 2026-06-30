from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Session, declarative_base

from app.core.config import (
    DEFAULT_AUTH_TOKEN,
    DEFAULT_DATABASE_URL,
    DEFAULT_OWNER_USER_ID,
    Settings,
    settings as default_settings,
)
from app.db.session import create_engine_and_session_factory
from app.observability import configure_logging, log_pipeline_event

TEXT_QUEUED = 0
TEXT_PROCESSING = 1
TEXT_READY = 2
TEXT_FAILED = 3

AUDIO_PENDING = 0
AUDIO_PROCESSING = 1
AUDIO_READY = 2
AUDIO_FAILED = 3

PLAYER_PENDING = 0
PLAYER_PROCESSING = 1
PLAYER_READY = 2
PLAYER_FAILED = 3

TEXT_STATUS_LABELS = {
    TEXT_QUEUED: "queued",
    TEXT_PROCESSING: "processing",
    TEXT_READY: "ready",
    TEXT_FAILED: "failed",
}
AUDIO_STATUS_LABELS = {
    AUDIO_PENDING: "pending",
    AUDIO_PROCESSING: "processing",
    AUDIO_READY: "ready",
    AUDIO_FAILED: "failed",
}
PLAYER_STATUS_LABELS = {
    PLAYER_PENDING: "pending",
    PLAYER_PROCESSING: "processing",
    PLAYER_READY: "ready",
    PLAYER_FAILED: "failed",
}
VISIBLE_STATUSES = {"submitted", "processing", "playable", "failed"}

Base = declarative_base()


class ArticleAudioItem(Base):
    __tablename__ = "article_audio_items"
    __table_args__ = (
        UniqueConstraint("article_id", name="uq_article_audio_items_article_id"),
        UniqueConstraint(
            "owner_user_id",
            "source_url_hash",
            name="uq_article_audio_items_owner_source_hash",
        ),
        CheckConstraint(
            "text_status IN (0, 1, 2, 3)",
            name="ck_article_audio_items_text_status",
        ),
        CheckConstraint(
            "audio_status IN (0, 1, 2, 3)",
            name="ck_article_audio_items_audio_status",
        ),
        CheckConstraint(
            "player_sync_status IN (0, 1, 2, 3)",
            name="ck_article_audio_items_player_sync_status",
        ),
        Index(
            "idx_article_audio_items_owner_status",
            "owner_user_id",
            "text_status",
            "audio_status",
            "player_sync_status",
            "updated_at",
        ),
        Index("idx_article_audio_items_love_song_track_id", "love_song_track_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(String(64), nullable=False)
    owner_user_id = Column(String(64), nullable=False)
    source_url = Column(String(2048), nullable=False)
    source_url_hash = Column(String(64), nullable=False)
    site_name = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    title = Column(String(512), nullable=False)
    published_at = Column(DateTime, nullable=True)
    cover_url = Column(String(1024), nullable=True)
    language = Column(String(16), nullable=True)
    text_content = Column(Text, nullable=True)
    text_char_count = Column(Integer, nullable=False, default=0)
    text_status = Column(SmallInteger, nullable=False, default=TEXT_QUEUED)
    audio_status = Column(SmallInteger, nullable=False, default=AUDIO_PENDING)
    player_sync_status = Column(SmallInteger, nullable=False, default=PLAYER_PENDING)
    audio_storage_key = Column(String(1024), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    love_song_track_id = Column(String(64), nullable=True)
    love_song_asset_id = Column(String(64), nullable=True)
    love_song_playlist_id = Column(String(64), nullable=True)
    submitted_at = Column(DateTime, nullable=False)
    audio_ready_at = Column(DateTime, nullable=True)
    player_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ArticleTtsSegment(Base):
    __tablename__ = "article_tts_segments"
    __table_args__ = (
        UniqueConstraint("segment_id", name="uq_article_tts_segments_segment_id"),
        UniqueConstraint(
            "article_id",
            "segment_index",
            name="uq_article_tts_segments_article_index",
        ),
        CheckConstraint(
            "tts_status IN (0, 1, 2, 3)",
            name="ck_article_tts_segments_tts_status",
        ),
        Index(
            "idx_article_tts_segments_article_status",
            "article_id",
            "tts_status",
            "segment_index",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(String(64), nullable=False)
    article_id = Column(
        String(64),
        ForeignKey(
            "article_audio_items.article_id",
            name="fk_article_tts_segments_article_id",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    segment_index = Column(Integer, nullable=False)
    text_content = Column(Text, nullable=False)
    text_char_count = Column(Integer, nullable=False, default=0)
    tts_status = Column(SmallInteger, nullable=False, default=AUDIO_PENDING)
    audio_storage_key = Column(String(1024), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ArticleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=512)
    text_content: str = Field(min_length=20, max_length=300000)
    site_name: Optional[str] = Field(default=None, max_length=255)
    author: Optional[str] = Field(default=None, max_length=255)
    published_at: Optional[datetime] = None
    cover_url: Optional[str] = Field(default=None, max_length=1024)
    language_hint: Optional[str] = Field(default=None, max_length=16)

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must be http or https")
        return value


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_business_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:20]}"


def source_hash(source_url: str) -> str:
    return hashlib.sha256(source_url.encode("utf-8")).hexdigest()


def normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def iso_z(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def visible_status(article: ArticleAudioItem) -> str:
    if (
        article.text_status == TEXT_FAILED
        or article.audio_status == AUDIO_FAILED
        or article.player_sync_status == PLAYER_FAILED
    ):
        return "failed"
    if article.player_sync_status == PLAYER_READY:
        return "playable"
    if article.text_status == TEXT_QUEUED:
        return "submitted"
    return "processing"


def article_response(article: ArticleAudioItem, created: Optional[bool] = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "article_id": article.article_id,
        "source_url": article.source_url,
        "title": article.title,
        "status": visible_status(article),
        "text_status": TEXT_STATUS_LABELS[article.text_status],
        "audio_status": AUDIO_STATUS_LABELS[article.audio_status],
        "player_sync_status": PLAYER_STATUS_LABELS[article.player_sync_status],
        "submitted_at": iso_z(article.submitted_at),
    }
    if created is not None:
        body["created"] = created
    return body


def article_detail_response(article: ArticleAudioItem) -> dict[str, Any]:
    body = article_response(article)
    body.update(
        {
            "site_name": article.site_name,
            "author": article.author,
            "published_at": iso_z(article.published_at),
            "cover_url": article.cover_url,
            "language": article.language,
            "duration_seconds": article.duration_seconds,
            "love_song_track_id": article.love_song_track_id,
            "love_song_asset_id": article.love_song_asset_id,
            "love_song_playlist_id": article.love_song_playlist_id,
            "updated_at": iso_z(article.updated_at),
        }
    )
    return body


def api_error(
    status_code: int,
    code: str,
    message: str,
    details: Optional[dict[str, Any]] = None,
):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def validation_error_details(exc: RequestValidationError) -> dict[str, Any]:
    return {
        "errors": [
            {
                "type": error.get("type"),
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg"),
            }
            for error in exc.errors()
        ]
    }


def create_app(
    database_url: Optional[str] = None,
    auth_token: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> FastAPI:
    runtime_settings = settings or default_settings
    overrides: dict[str, str] = {}
    if database_url is not None:
        overrides["database_url"] = database_url
    if auth_token is not None:
        overrides["auth_token"] = auth_token
    if overrides:
        runtime_settings = runtime_settings.model_copy(update=overrides)

    configure_logging(runtime_settings.log_level)
    engine, session_factory = create_engine_and_session_factory(
        runtime_settings.resolve_database_url()
    )
    Base.metadata.create_all(engine)

    app = FastAPI(title=runtime_settings.app_name)
    app.state.settings = runtime_settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return api_error(422, "validation_failed", "Request is invalid.", validation_error_details(exc))

    def get_db():
        with session_factory() as session:
            yield session

    def require_auth(authorization: Optional[str] = Header(default=None)) -> None:
        expected = f"Bearer {runtime_settings.auth_token}"
        if authorization != expected:
            raise UnauthorizedError

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: "UnauthorizedError") -> JSONResponse:
        return api_error(401, "unauthorized", "Authentication is required.")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/articles")
    def create_article(
        request: ArticleCreateRequest,
        response: Response,
        _: None = Depends(require_auth),
        db: Session = Depends(get_db),
    ) -> dict[str, Any]:
        existing = db.scalar(
            select(ArticleAudioItem).where(
                ArticleAudioItem.owner_user_id == runtime_settings.owner_user_id,
                ArticleAudioItem.source_url_hash == source_hash(request.source_url),
            )
        )
        if existing is not None:
            log_pipeline_event(
                "article_task_duplicate",
                "article_submission",
                article_id=existing.article_id,
                owner_user_id=existing.owner_user_id,
                source_url_hash=existing.source_url_hash,
                status=visible_status(existing),
                text_status=TEXT_STATUS_LABELS[existing.text_status],
                audio_status=AUDIO_STATUS_LABELS[existing.audio_status],
                player_sync_status=PLAYER_STATUS_LABELS[existing.player_sync_status],
            )
            response.status_code = 200
            return article_response(existing, created=False)

        now = utc_now_naive()
        article = ArticleAudioItem(
            article_id=make_business_id("art"),
            owner_user_id=runtime_settings.owner_user_id,
            source_url=request.source_url,
            source_url_hash=source_hash(request.source_url),
            site_name=request.site_name,
            author=request.author,
            title=request.title,
            published_at=normalize_datetime(request.published_at),
            cover_url=request.cover_url,
            language=request.language_hint,
            text_content=request.text_content,
            text_char_count=len(request.text_content),
            text_status=TEXT_QUEUED,
            audio_status=AUDIO_PENDING,
            player_sync_status=PLAYER_PENDING,
            submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        log_pipeline_event(
            "article_task_created",
            "article_submission",
            article_id=article.article_id,
            owner_user_id=article.owner_user_id,
            source_url_hash=article.source_url_hash,
            text_status=TEXT_STATUS_LABELS[article.text_status],
            audio_status=AUDIO_STATUS_LABELS[article.audio_status],
            player_sync_status=PLAYER_STATUS_LABELS[article.player_sync_status],
            text_char_count=article.text_char_count,
        )
        log_pipeline_event(
            "article_waiting_for_worker",
            "article_submission",
            article_id=article.article_id,
            next_stage="text_processing",
            worker_trigger="external_or_manual",
        )
        response.status_code = 201
        return article_response(article, created=True)

    @app.get("/api/articles/{article_id}")
    def get_article(
        article_id: str,
        _: None = Depends(require_auth),
        db: Session = Depends(get_db),
    ):
        article = db.scalar(
            select(ArticleAudioItem).where(
                ArticleAudioItem.owner_user_id == runtime_settings.owner_user_id,
                ArticleAudioItem.article_id == article_id,
            )
        )
        if article is None:
            return api_error(404, "article_not_found", "Article was not found.")
        return article_detail_response(article)

    @app.get("/api/articles")
    def list_articles(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
        status: Optional[str] = None,
        source_url: Optional[str] = None,
        _: None = Depends(require_auth),
        db: Session = Depends(get_db),
    ):
        if status is not None and status not in VISIBLE_STATUSES:
            return api_error(422, "validation_failed", "Request is invalid.")

        statement = select(ArticleAudioItem).where(
            ArticleAudioItem.owner_user_id == runtime_settings.owner_user_id
        )
        if source_url:
            statement = statement.where(ArticleAudioItem.source_url == source_url)

        rows = db.scalars(statement.order_by(ArticleAudioItem.submitted_at.desc())).all()
        filtered = [row for row in rows if status is None or visible_status(row) == status]
        start = (page - 1) * page_size
        end = start + page_size
        items = [article_detail_response(row) for row in filtered[start:end]]
        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": len(filtered),
        }

    return app


class UnauthorizedError(Exception):
    pass
