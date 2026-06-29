from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import (  # noqa: E402
    AUDIO_PENDING,
    PLAYER_PENDING,
    TEXT_READY,
    ArticleAudioItem,
    ArticleTtsSegment,
)
from app.text_jobs import process_article_text  # noqa: E402


TOKEN = "test-token"
REPO_ROOT = Path(__file__).resolve().parents[2]


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def extract_payload_from_extension() -> dict[str, str]:
    script = r"""
const { extractArticleFromDocument } = require('./extension/content.js');

function element(textContent, attrs = {}) {
  return {
    textContent,
    getAttribute(name) {
      return attrs[name] ?? null;
    },
  };
}

const meta = {
  'meta[property="og:title"]': element('', { content: '网页正文链路测试标题' }),
  'meta[property="og:site_name"]': element('', { content: '测试站点' }),
  'meta[name="author"]': element('', { content: '测试作者' }),
  'meta[property="article:published_time"]': element('', {
    content: '2026-06-29T10:00:00Z',
  }),
  'meta[property="og:image"]': element('', {
    content: 'https://example.com/cover.png',
  }),
};

const doc = {
  title: '浏览器标题备用值',
  location: { href: 'https://example.com/articles/webpage-text-db-chain' },
  documentElement: { lang: 'zh-CN' },
  querySelector(selector) {
    if (selector === 'article') {
      return element('  第一段  从网页提取的正文。\n\n第二段 会被清洗并写入数据库。\n\n第三段 用于验证 TTS 分段。');
    }
    return meta[selector] ?? null;
  },
};

process.stdout.write(JSON.stringify(extractArticleFromDocument(doc)));
"""
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_webpage_extraction_submission_and_text_processing_persist_to_db(
    mysql_app_factory,
) -> None:
    payload = extract_payload_from_extension()
    app = mysql_app_factory(TOKEN)
    client = TestClient(app)

    created = client.post("/api/articles", json=payload, headers=auth_headers())
    assert created.status_code == 201
    article_id = created.json()["article_id"]

    with app.state.session_factory() as session:
        result = process_article_text(session, article_id, max_segment_chars=18)
        article = session.scalar(
            select(ArticleAudioItem).where(ArticleAudioItem.article_id == article_id)
        )
        segments = session.scalars(
            select(ArticleTtsSegment)
            .where(ArticleTtsSegment.article_id == article_id)
            .order_by(ArticleTtsSegment.segment_index)
        ).all()

    assert result.processed is True
    assert result.segment_count == 3
    assert article is not None
    assert article.source_url == "https://example.com/articles/webpage-text-db-chain"
    assert article.title == "网页正文链路测试标题"
    assert article.site_name == "测试站点"
    assert article.author == "测试作者"
    assert article.language == "zh"
    assert article.text_status == TEXT_READY
    assert article.audio_status == AUDIO_PENDING
    assert article.player_sync_status == PLAYER_PENDING
    assert article.text_content == (
        "第一段 从网页提取的正文。\n"
        "第二段 会被清洗并写入数据库。\n"
        "第三段 用于验证 TTS 分段。"
    )
    assert article.text_char_count == len(article.text_content)
    assert [segment.segment_index for segment in segments] == [0, 1, 2]
    assert [segment.text_content for segment in segments] == [
        "第一段 从网页提取的正文。",
        "第二段 会被清洗并写入数据库。",
        "第三段 用于验证 TTS 分段。",
    ]
    assert [segment.tts_status for segment in segments] == [
        AUDIO_PENDING,
        AUDIO_PENDING,
        AUDIO_PENDING,
    ]
