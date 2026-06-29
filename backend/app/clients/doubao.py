from __future__ import annotations

import asyncio
import base64
import io
import json
import struct
import uuid
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Mapping, Optional

import websockets

from app.clients.tts import AudioSynthesisResult


DOUBAO_BIDIRECTIONAL_TTS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
DOUBAO_RESOURCE_IDS = {"seed-tts-2.0", "seed-icl-2.0"}


class _DoubaoMsgType(IntEnum):
    FullClientRequest = 0b0001
    FullServerResponse = 0b1001
    AudioOnlyServer = 0b1011
    Error = 0b1111


class _DoubaoMsgFlag(IntEnum):
    NoSeq = 0
    PositiveSeq = 0b0001
    NegativeSeq = 0b0011
    WithEvent = 0b0100


class _DoubaoSerialization(IntEnum):
    Raw = 0
    JSON = 0b0001


class _DoubaoCompression(IntEnum):
    None_ = 0


class _DoubaoEvent(IntEnum):
    StartConnection = 1
    FinishConnection = 2
    ConnectionStarted = 50
    ConnectionFailed = 51
    ConnectionFinished = 52
    StartSession = 100
    CancelSession = 101
    FinishSession = 102
    SessionStarted = 150
    SessionCanceled = 151
    SessionFinished = 152
    SessionFailed = 153
    UsageResponse = 154
    TaskRequest = 200
    TTSResponse = 352
    TTSSubtitle = 364
    TTSSentenceStart = 350
    TTSSentenceEnd = 351


@dataclass
class _DoubaoWsMessage:
    type: _DoubaoMsgType
    flag: _DoubaoMsgFlag = _DoubaoMsgFlag.NoSeq
    event: Optional[_DoubaoEvent] = None
    session_id: str = ""
    connect_id: str = ""
    sequence: int = 0
    error_code: int = 0
    payload: bytes = b""
    serialization: _DoubaoSerialization = _DoubaoSerialization.JSON
    compression: _DoubaoCompression = _DoubaoCompression.None_

    def marshal(self) -> bytes:
        buffer = io.BytesIO()
        buffer.write(
            bytes(
                [
                    0x11,
                    (int(self.type) << 4) | int(self.flag),
                    (int(self.serialization) << 4) | int(self.compression),
                    0x00,
                ]
            )
        )

        if self.flag == _DoubaoMsgFlag.WithEvent:
            if self.event is None:
                raise ValueError("doubao websocket event is required")
            buffer.write(struct.pack(">i", int(self.event)))
            self._write_session_id(buffer)

        if self.flag in {_DoubaoMsgFlag.PositiveSeq, _DoubaoMsgFlag.NegativeSeq}:
            buffer.write(struct.pack(">i", self.sequence))

        if self.type == _DoubaoMsgType.Error:
            buffer.write(struct.pack(">I", self.error_code))

        payload_size = len(self.payload)
        buffer.write(struct.pack(">I", payload_size))
        buffer.write(self.payload)
        return buffer.getvalue()

    @classmethod
    def from_bytes(cls, data: bytes) -> "_DoubaoWsMessage":
        if len(data) < 4:
            raise ValueError(f"doubao websocket message is too short: {len(data)} bytes")

        buffer = io.BytesIO(data)
        version_and_header_size = buffer.read(1)[0]
        header_size = version_and_header_size & 0b00001111
        type_and_flag = buffer.read(1)[0]
        serialization_and_compression = buffer.read(1)[0]
        buffer.read(max(0, header_size * 4 - 3))

        msg = cls(
            type=_DoubaoMsgType(type_and_flag >> 4),
            flag=_DoubaoMsgFlag(type_and_flag & 0b00001111),
            serialization=_DoubaoSerialization(serialization_and_compression >> 4),
            compression=_DoubaoCompression(serialization_and_compression & 0b00001111),
        )

        if msg.flag in {_DoubaoMsgFlag.PositiveSeq, _DoubaoMsgFlag.NegativeSeq}:
            sequence = buffer.read(4)
            if sequence:
                msg.sequence = struct.unpack(">i", sequence)[0]

        if msg.type == _DoubaoMsgType.Error:
            error_code = buffer.read(4)
            if error_code:
                msg.error_code = struct.unpack(">I", error_code)[0]

        if msg.flag == _DoubaoMsgFlag.WithEvent:
            event = buffer.read(4)
            if event:
                event_value = struct.unpack(">i", event)[0]
                msg.event = _safe_event(event_value)
            msg._read_session_id(buffer)
            msg._read_connect_id(buffer)

        payload_size = buffer.read(4)
        if payload_size:
            size = struct.unpack(">I", payload_size)[0]
            if size:
                msg.payload = buffer.read(size)
        return msg

    def _write_session_id(self, buffer: io.BytesIO) -> None:
        if self.event in {
            _DoubaoEvent.StartConnection,
            _DoubaoEvent.FinishConnection,
            _DoubaoEvent.ConnectionStarted,
            _DoubaoEvent.ConnectionFailed,
            _DoubaoEvent.ConnectionFinished,
        }:
            return
        encoded = self.session_id.encode("utf-8")
        buffer.write(struct.pack(">I", len(encoded)))
        buffer.write(encoded)

    def _read_session_id(self, buffer: io.BytesIO) -> None:
        if self.event in {
            _DoubaoEvent.StartConnection,
            _DoubaoEvent.FinishConnection,
            _DoubaoEvent.ConnectionStarted,
            _DoubaoEvent.ConnectionFailed,
            _DoubaoEvent.ConnectionFinished,
        }:
            return
        size_bytes = buffer.read(4)
        if not size_bytes:
            return
        size = struct.unpack(">I", size_bytes)[0]
        if size:
            self.session_id = buffer.read(size).decode("utf-8")

    def _read_connect_id(self, buffer: io.BytesIO) -> None:
        if self.event not in {
            _DoubaoEvent.ConnectionStarted,
            _DoubaoEvent.ConnectionFailed,
            _DoubaoEvent.ConnectionFinished,
        }:
            return
        size_bytes = buffer.read(4)
        if not size_bytes:
            return
        size = struct.unpack(">I", size_bytes)[0]
        if size:
            self.connect_id = buffer.read(size).decode("utf-8")


@dataclass(frozen=True)
class DoubaoTtsConfig:
    api_key: str
    resource_id: str
    speaker: str
    base_url: str = DOUBAO_BIDIRECTIONAL_TTS_URL
    audio_format: str = "mp3"
    sample_rate: int = 24000
    bit_rate: int = 128000
    speech_rate: int = 0
    loudness_rate: int = 0
    request_model: str = ""
    timeout: float = 60.0
    estimated_seconds_per_char: float = 0.2
    require_usage_tokens: bool = False
    extra_req_params: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DoubaoTtsConfig":
        resource_id = str(data.get("resource_id") or data.get("model") or "")
        speaker = str(data.get("speaker") or data.get("voice") or "")
        extra_req_params = data.get("extra_req_params") or {}
        if not isinstance(extra_req_params, Mapping):
            raise ValueError("doubao config extra_req_params must be an object")
        return cls(
            api_key=str(data.get("api_key") or ""),
            resource_id=resource_id,
            speaker=speaker,
            base_url=str(data.get("base_url") or DOUBAO_BIDIRECTIONAL_TTS_URL),
            audio_format=str(data.get("audio_format") or data.get("format") or "mp3"),
            sample_rate=int(data.get("sample_rate") or 24000),
            bit_rate=int(data.get("bit_rate") or 128000),
            speech_rate=int(data.get("speech_rate") or 0),
            loudness_rate=int(data.get("loudness_rate") or 0),
            request_model=str(data.get("request_model") or ""),
            timeout=float(data.get("timeout") or 60),
            estimated_seconds_per_char=float(data.get("estimated_seconds_per_char") or 0.2),
            require_usage_tokens=bool(data.get("require_usage_tokens") or False),
            extra_req_params=dict(extra_req_params),
        )

    def validate(self) -> None:
        missing = []
        if not self.api_key:
            missing.append("api_key")
        if not self.resource_id:
            missing.append("resource_id")
        if not self.speaker:
            missing.append("speaker")
        errors = []
        if missing:
            errors.append(f"missing required fields: {', '.join(missing)}")
        if not self.base_url.startswith(("ws://", "wss://")):
            errors.append("base_url must be a WebSocket URL")
        if self.resource_id and self.resource_id not in DOUBAO_RESOURCE_IDS:
            allowed = ", ".join(sorted(DOUBAO_RESOURCE_IDS))
            errors.append(f"resource_id must be one of: {allowed}")
        if errors:
            raise ValueError(f"doubao config invalid: {'; '.join(errors)}")


class DoubaoTtsClient:
    def __init__(
        self,
        config: DoubaoTtsConfig,
        websocket_factory: Optional[Callable[[str, Mapping[str, str], float], Any]] = None,
        connect_id_factory: Optional[Callable[[], str]] = None,
        session_id_factory: Optional[Callable[[], str]] = None,
    ) -> None:
        config.validate()
        self.config = config
        self._websocket_factory = websocket_factory or _default_websocket_factory
        self._connect_id_factory = connect_id_factory or _new_uuid
        self._session_id_factory = session_id_factory or _new_uuid

    def synthesize(self, text: str, language: Optional[str] = None) -> AudioSynthesisResult:
        if not text:
            raise ValueError("doubao synthesize text must not be empty")
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._synthesize_async(text, language))
        raise RuntimeError("DoubaoTtsClient.synthesize cannot run inside an active event loop")

    async def _synthesize_async(
        self,
        text: str,
        language: Optional[str],
    ) -> AudioSynthesisResult:
        connect_id = self._connect_id_factory()
        session_id = self._session_id_factory()
        headers = self._headers(connect_id)
        connection = self._websocket_factory(self.config.base_url, headers, self.config.timeout)
        if hasattr(connection, "__await__"):
            connection = await connection

        chunks: list[bytes] = []
        async with connection as websocket:
            await self._send(websocket, _DoubaoEvent.StartConnection, b"{}")
            await self._expect(websocket, _DoubaoEvent.ConnectionStarted)

            await self._send(
                websocket,
                _DoubaoEvent.StartSession,
                _json_bytes({"req_params": self._req_params(language)}),
                session_id=session_id,
            )
            await self._expect(websocket, _DoubaoEvent.SessionStarted)

            await self._send(
                websocket,
                _DoubaoEvent.TaskRequest,
                _json_bytes({"req_params": self._req_params(language, text=text)}),
                session_id=session_id,
            )
            await self._send(websocket, _DoubaoEvent.FinishSession, b"{}", session_id=session_id)
            response_metadata: dict[str, Any] = {}
            audio_chunks, response_metadata = await self._receive_audio_until_finished(websocket)
            chunks.extend(audio_chunks)

            await self._send(websocket, _DoubaoEvent.FinishConnection, b"{}")
            try:
                await self._expect(websocket, _DoubaoEvent.ConnectionFinished)
            except Exception:
                pass

        if not chunks:
            raise RuntimeError("doubao TTS returned no audio")
        return AudioSynthesisResult(
            content=b"".join(chunks),
            duration_seconds=max(1, int(round(len(text) * self.config.estimated_seconds_per_char))),
            mime_type=_mime_type_for_format(self.config.audio_format),
            metadata={
                "provider": "doubao",
                "connect_id": connect_id,
                "session_id": session_id,
                **response_metadata,
            },
        )

    def _headers(self, connect_id: str) -> dict[str, str]:
        headers = {
            "X-Api-Key": self.config.api_key,
            "X-Api-Resource-Id": self.config.resource_id,
            "X-Api-Connect-Id": connect_id,
        }
        if self.config.require_usage_tokens:
            headers["X-Control-Require-Usage-Tokens-Return"] = "*"
        return headers

    def _req_params(self, language: Optional[str], text: str = "") -> dict[str, Any]:
        req_params: dict[str, Any] = {
            "speaker": self.config.speaker,
            "audio_params": {
                "format": self.config.audio_format,
                "sample_rate": self.config.sample_rate,
                "bit_rate": self.config.bit_rate,
            },
        }
        if text:
            req_params["text"] = text
        if self.config.request_model:
            req_params["model"] = self.config.request_model
        if self.config.speech_rate:
            req_params["speech_rate"] = self.config.speech_rate
        if self.config.loudness_rate:
            req_params["loudness_rate"] = self.config.loudness_rate
        explicit_language = _normalize_language(language)
        if explicit_language:
            req_params["explicit_language"] = explicit_language
        req_params.update(self.config.extra_req_params)
        return req_params

    async def _receive_audio_until_finished(self, websocket: Any) -> tuple[list[bytes], dict[str, Any]]:
        chunks: list[bytes] = []
        while True:
            message = await _receive_message(websocket)
            if message.type == _DoubaoMsgType.Error:
                raise RuntimeError(_format_provider_error(message))
            if message.event in {_DoubaoEvent.ConnectionFailed, _DoubaoEvent.SessionFailed}:
                raise RuntimeError(_format_provider_error(message))
            if message.event == _DoubaoEvent.SessionFinished:
                return chunks, _session_finished_metadata(message)
            if message.type == _DoubaoMsgType.AudioOnlyServer and message.payload:
                chunks.append(message.payload)
                if message.flag == _DoubaoMsgFlag.NegativeSeq:
                    return chunks, {}
                continue
            if message.event == _DoubaoEvent.TTSResponse:
                audio = _extract_audio_payload(message)
                if audio:
                    chunks.append(audio)

    async def _expect(self, websocket: Any, event: _DoubaoEvent) -> _DoubaoWsMessage:
        message = await _receive_message(websocket)
        if message.type == _DoubaoMsgType.Error:
            raise RuntimeError(_format_provider_error(message))
        if message.event != event:
            raise RuntimeError(
                f"doubao TTS expected {event.name}, got {_event_name(message.event)}: "
                f"{_payload_text(message.payload)}"
            )
        return message

    async def _send(
        self,
        websocket: Any,
        event: _DoubaoEvent,
        payload: bytes,
        *,
        session_id: str = "",
    ) -> None:
        await websocket.send(
            _DoubaoWsMessage(
                type=_DoubaoMsgType.FullClientRequest,
                flag=_DoubaoMsgFlag.WithEvent,
                event=event,
                session_id=session_id,
                payload=payload,
            ).marshal()
        )


def _default_websocket_factory(url: str, headers: Mapping[str, str], timeout: float) -> Any:
    return websockets.connect(
        url,
        additional_headers=dict(headers),
        open_timeout=timeout,
        ping_timeout=timeout,
        close_timeout=timeout,
    )


async def _receive_message(websocket: Any) -> _DoubaoWsMessage:
    data = await websocket.recv()
    if not isinstance(data, bytes):
        raise ValueError(f"doubao websocket returned non-binary message: {type(data)!r}")
    return _DoubaoWsMessage.from_bytes(data)


def _json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _extract_audio_payload(message: _DoubaoWsMessage) -> bytes:
    if message.type == _DoubaoMsgType.AudioOnlyServer:
        return message.payload
    payload = _json_payload(message.payload)
    audio = payload.get("audio") or payload.get("data")
    if isinstance(audio, str):
        try:
            return base64.b64decode(audio)
        except ValueError:
            return audio.encode("utf-8")
    return b""


def _json_payload(payload: bytes) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _format_provider_error(message: _DoubaoWsMessage) -> str:
    payload = _json_payload(message.payload)
    detail = (
        payload.get("message")
        or payload.get("error")
        or payload.get("reason")
        or _payload_text(message.payload)
    )
    event = _event_name(message.event)
    if message.type == _DoubaoMsgType.Error:
        return f"doubao TTS Error({message.error_code}) {event}: {detail}"
    return f"doubao TTS {event}: {detail}"


def _session_finished_metadata(message: _DoubaoWsMessage) -> dict[str, Any]:
    payload = _json_payload(message.payload)
    metadata: dict[str, Any] = {}
    usage = payload.get("usage")
    if isinstance(usage, Mapping):
        metadata["usage"] = dict(usage)
    return metadata


def _payload_text(payload: bytes) -> str:
    return payload.decode("utf-8", "ignore")


def _event_name(event: Optional[_DoubaoEvent]) -> str:
    return event.name if isinstance(event, _DoubaoEvent) else str(event)


def _safe_event(value: int) -> Optional[_DoubaoEvent]:
    try:
        return _DoubaoEvent(value)
    except ValueError:
        return None


def _normalize_language(language: Optional[str]) -> str:
    if not language:
        return ""
    value = language.lower().replace("_", "-")
    if value in {"zh", "cn", "zh-hans"}:
        return "zh-cn"
    return value


def _mime_type_for_format(audio_format: str) -> str:
    normalized = audio_format.lower()
    if normalized == "mp3":
        return "audio/mpeg"
    if normalized == "wav":
        return "audio/wav"
    if normalized == "pcm":
        return "audio/pcm"
    if normalized == "ogg_opus":
        return "audio/ogg"
    return "application/octet-stream"


def _new_uuid() -> str:
    return uuid.uuid4().hex
