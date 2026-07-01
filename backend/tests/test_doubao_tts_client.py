from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.clients.doubao import (  # noqa: E402
    DoubaoTtsClient,
    DoubaoTtsConfig,
    _DoubaoEvent,
    _DoubaoMsgFlag,
    _DoubaoMsgType,
    _DoubaoWsMessage,
)


class FakeWebSocket:
    def __init__(self, responses: list[bytes]) -> None:
        self.responses = responses
        self.sent: list[bytes] = []

    async def __aenter__(self) -> "FakeWebSocket":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    async def send(self, data: bytes) -> None:
        self.sent.append(data)

    async def recv(self) -> bytes:
        if not self.responses:
            raise AssertionError("no fake websocket response left")
        return self.responses.pop(0)


class RecordingWebSocketFactory:
    def __init__(self, websocket: FakeWebSocket) -> None:
        self.websocket = websocket
        self.calls: list[tuple[str, Mapping[str, str], float]] = []

    def __call__(self, url: str, headers: Mapping[str, str], timeout: float) -> FakeWebSocket:
        self.calls.append((url, dict(headers), timeout))
        return self.websocket


def server_message(
    event: _DoubaoEvent,
    payload: bytes = b"{}",
    *,
    session_id: str = "",
    msg_type: _DoubaoMsgType = _DoubaoMsgType.FullServerResponse,
) -> bytes:
    return _DoubaoWsMessage(
        type=msg_type,
        flag=_DoubaoMsgFlag.WithEvent,
        event=event,
        session_id=session_id,
        payload=payload,
    ).marshal()


def decode_payload(message: _DoubaoWsMessage) -> dict[str, Any]:
    return json.loads(message.payload.decode("utf-8"))


def test_doubao_config_defaults_to_volcengine_bidirectional_websocket() -> None:
    config = DoubaoTtsConfig.from_mapping(
        {
            "api_key": "test-key",
            "resource_id": "seed-tts-2.0",
            "speaker": "zh_female_test",
        }
    )

    assert config.base_url == "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
    assert config.resource_id == "seed-tts-2.0"
    assert config.speaker == "zh_female_test"


def test_doubao_websocket_client_sends_volcengine_event_sequence_and_headers() -> None:
    session_id = "session-1"
    fake_ws = FakeWebSocket(
        [
            server_message(_DoubaoEvent.ConnectionStarted, b'{"ok":true}'),
            server_message(_DoubaoEvent.SessionStarted, b'{"ok":true}', session_id=session_id),
            server_message(
                _DoubaoEvent.TTSResponse,
                b"audio-chunk",
                session_id=session_id,
                msg_type=_DoubaoMsgType.AudioOnlyServer,
            ),
            server_message(
                _DoubaoEvent.SessionFinished,
                b'{"usage":{"text_words":5}}',
                session_id=session_id,
            ),
            server_message(_DoubaoEvent.ConnectionFinished, b'{"ok":true}'),
        ]
    )
    factory = RecordingWebSocketFactory(fake_ws)
    config = DoubaoTtsConfig.from_mapping(
        {
            "api_key": "test-key",
            "resource_id": "seed-tts-2.0",
            "speaker": "zh_female_test",
            "audio_format": "mp3",
            "sample_rate": 24000,
            "bit_rate": 128000,
            "speech_rate": 12,
            "loudness_rate": -5,
        }
    )
    client = DoubaoTtsClient(
        config,
        websocket_factory=factory,
        connect_id_factory=lambda: "connect-1",
        session_id_factory=lambda: session_id,
    )

    result = client.synthesize("你好，世界", language="zh")

    assert result.content == b"audio-chunk"
    assert result.mime_type == "audio/mpeg"
    assert result.duration_seconds >= 1
    assert result.metadata == {
        "provider": "doubao",
        "connect_id": "connect-1",
        "session_id": session_id,
        "usage": {"text_words": 5},
    }
    assert factory.calls == [
        (
            "wss://openspeech.bytedance.com/api/v3/tts/bidirection",
            {
                "X-Api-Key": "test-key",
                "X-Api-Resource-Id": "seed-tts-2.0",
                "X-Api-Connect-Id": "connect-1",
            },
            60.0,
        )
    ]

    sent_messages = [_DoubaoWsMessage.from_bytes(data) for data in fake_ws.sent]
    assert [message.event for message in sent_messages] == [
        _DoubaoEvent.StartConnection,
        _DoubaoEvent.StartSession,
        _DoubaoEvent.TaskRequest,
        _DoubaoEvent.FinishSession,
        _DoubaoEvent.FinishConnection,
    ]
    assert decode_payload(sent_messages[0]) == {}
    assert decode_payload(sent_messages[1]) == {
        "req_params": {
            "speaker": "zh_female_test",
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000,
                "bit_rate": 128000,
            },
            "speech_rate": 12,
            "loudness_rate": -5,
            "explicit_language": "zh-cn",
        }
    }
    assert decode_payload(sent_messages[2]) == {
        "req_params": {
            "text": "你好，世界",
            "speaker": "zh_female_test",
            "audio_params": {
                "format": "mp3",
                "sample_rate": 24000,
                "bit_rate": 128000,
            },
            "speech_rate": 12,
            "loudness_rate": -5,
            "explicit_language": "zh-cn",
        }
    }
    assert decode_payload(sent_messages[3]) == {}
    assert decode_payload(sent_messages[4]) == {}


def test_doubao_websocket_client_reports_failed_provider_event() -> None:
    session_id = "session-2"
    fake_ws = FakeWebSocket(
        [
            server_message(_DoubaoEvent.ConnectionStarted),
            server_message(_DoubaoEvent.SessionStarted, session_id=session_id),
            server_message(
                _DoubaoEvent.SessionFailed,
                b'{"message":"speaker not found"}',
                session_id=session_id,
            ),
        ]
    )
    factory = RecordingWebSocketFactory(fake_ws)
    client = DoubaoTtsClient(
        DoubaoTtsConfig.from_mapping(
            {
                "api_key": "test-key",
                "resource_id": "seed-tts-2.0",
                "speaker": "missing-speaker",
            }
        ),
        websocket_factory=factory,
        connect_id_factory=lambda: "connect-2",
        session_id_factory=lambda: session_id,
    )

    with pytest.raises(RuntimeError, match="SessionFailed.*speaker not found"):
        client.synthesize("你好")


def test_doubao_config_rejects_legacy_ark_http_endpoint() -> None:
    config = DoubaoTtsConfig.from_mapping(
        {
            "api_key": "test-key",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "resource_id": "seed-tts-2.0",
            "speaker": "zh_female_test",
        }
    )

    with pytest.raises(ValueError, match="WebSocket URL"):
        config.validate()
