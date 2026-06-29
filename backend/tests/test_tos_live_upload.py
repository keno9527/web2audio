from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.tos_storage import TosStorage  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.runtime import build_audio_storage  # noqa: E402


def test_upload_local_mp3_to_real_tos() -> None:
    if os.getenv("W2A_RUN_REAL_TOS_UPLOAD") != "1":
        pytest.skip("set W2A_RUN_REAL_TOS_UPLOAD=1 to upload a local MP3 to real TOS")

    input_path = Path(os.getenv("W2A_TOS_UPLOAD_INPUT", "/tmp/web2audio-doubao-debug.mp3"))
    if not input_path.exists():
        pytest.skip(f"TOS upload input file does not exist: {input_path}")

    storage = build_audio_storage(Settings(storage_mode="tos"))
    assert isinstance(storage, TosStorage)

    content = input_path.read_bytes()
    run_id = os.getenv("W2A_TOS_UPLOAD_RUN_ID") or uuid4().hex[:12]
    object_prefix = storage.config.object_prefix.strip("/")
    object_key = os.getenv("W2A_TOS_UPLOAD_KEY") or (
        f"{object_prefix}/debug/live-upload/{run_id}/{input_path.name}"
    )

    uploaded_key = storage.put_object(object_key, content, "audio/mpeg")
    assert uploaded_key == object_key

    client = storage._tos_client()
    assert client.does_object_exist(storage.config.bucket, object_key) is True
    metadata = client.head_object(storage.config.bucket, object_key)
    assert metadata.status_code == 200
    assert metadata.content_length == len(content)

    print("tos_bucket:", storage.config.bucket)
    print("tos_region:", storage.config.region)
    print("tos_object_key:", object_key)
    print("tos_content_length:", metadata.content_length)

    if os.getenv("W2A_TOS_KEEP_OBJECT") != "1":
        client.delete_object(storage.config.bucket, object_key)
        assert client.does_object_exist(storage.config.bucket, object_key) is False
