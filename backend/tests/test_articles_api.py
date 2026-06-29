from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TOKEN = "test-token"
ARTICLE_URL = "https://mp.weixin.qq.com/s/sVgTl03Hh3zaNFBh7X-ckQ"


def make_client(mysql_app_factory) -> TestClient:
    app = mysql_app_factory(TOKEN)
    return TestClient(app)


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def article_payload() -> dict[str, str]:
    return {
        "source_url": ARTICLE_URL,
        "title": "示例文章标题",
        "text_content": "这是一篇用于测试 Chrome 插件提交入口的文章正文，长度足够通过第一版服务端校验。",
        "site_name": "微信公众平台",
        "author": "作者",
        "published_at": "2026-06-27T08:00:00Z",
        "cover_url": "https://example.com/cover.jpg",
        "language_hint": "zh",
    }


def test_health_endpoint_reports_ok(mysql_app_factory) -> None:
    client = make_client(mysql_app_factory)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_post_article_creates_task_and_detail_can_be_queried(mysql_app_factory) -> None:
    client = make_client(mysql_app_factory)

    response = client.post("/api/articles", json=article_payload(), headers=auth_headers())

    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    assert body["article_id"].startswith("art_")
    assert body["source_url"] == ARTICLE_URL
    assert body["status"] == "submitted"
    assert body["text_status"] == "queued"
    assert body["audio_status"] == "pending"
    assert body["player_sync_status"] == "pending"
    assert body["submitted_at"].endswith("Z")

    detail = client.get(f"/api/articles/{body['article_id']}", headers=auth_headers())

    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["article_id"] == body["article_id"]
    assert detail_body["source_url"] == ARTICLE_URL
    assert detail_body["title"] == "示例文章标题"
    assert detail_body["site_name"] == "微信公众平台"
    assert detail_body["language"] == "zh"
    assert detail_body["status"] == "submitted"


def test_post_article_is_idempotent_by_exact_source_url(mysql_app_factory) -> None:
    client = make_client(mysql_app_factory)

    first = client.post("/api/articles", json=article_payload(), headers=auth_headers())
    second = client.post("/api/articles", json=article_payload(), headers=auth_headers())
    listed = client.get("/api/articles", headers=auth_headers())

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["article_id"] == first.json()["article_id"]
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["article_id"] == first.json()["article_id"]


def test_list_articles_supports_status_and_source_url_filters(mysql_app_factory) -> None:
    client = make_client(mysql_app_factory)
    created = client.post("/api/articles", json=article_payload(), headers=auth_headers())

    response = client.get(
        "/api/articles",
        params={"status": "submitted", "source_url": ARTICLE_URL},
        headers=auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] == 1
    assert body["items"][0]["article_id"] == created.json()["article_id"]


def test_articles_api_requires_bearer_token(mysql_app_factory) -> None:
    client = make_client(mysql_app_factory)

    response = client.post("/api/articles", json=article_payload())

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_post_article_rejects_invalid_payload(mysql_app_factory) -> None:
    client = make_client(mysql_app_factory)
    payload = article_payload() | {"source_url": "ftp://example.com/a", "unexpected": True}

    response = client.post("/api/articles", json=payload, headers=auth_headers())

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
