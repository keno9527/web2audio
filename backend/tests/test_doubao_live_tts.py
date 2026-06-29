from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.runtime import build_tts_client  # noqa: E402


pytestmark = pytest.mark.skipif(
    os.environ.get("W2A_RUN_REAL_DOUBAO_TTS") != "1",
    reason="set W2A_RUN_REAL_DOUBAO_TTS=1 to run real Doubao TTS debug case",
)


def test_real_doubao_tts_generates_audio_from_local_config() -> None:
    client = build_tts_client(Settings(tts_mode="doubao"))

    result = client.synthesize("web2audio 文字转语音真实调试。", language="zh")

    assert result.content
    assert len(result.content) > 1024
    assert result.duration_seconds >= 1
    assert result.mime_type in {"audio/mpeg", "audio/wav", "audio/pcm", "audio/ogg"}
    assert result.metadata["provider"] == "doubao"
    assert result.metadata["connect_id"]
    assert result.metadata["session_id"]

    output_path = os.environ.get("W2A_DOUBAO_TTS_OUTPUT")
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(result.content)
        print(f"wrote Doubao TTS audio debug file: {path}")
