from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


@dataclass(frozen=True)
class AudioSynthesisResult:
    content: bytes
    duration_seconds: int
    mime_type: str = "audio/mpeg"
    metadata: dict[str, Any] = field(default_factory=dict)


class TtsClient(Protocol):
    def synthesize(self, text: str, language: Optional[str] = None) -> AudioSynthesisResult:
        """Generate one audio segment from text."""
