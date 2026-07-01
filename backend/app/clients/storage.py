from __future__ import annotations

from typing import Protocol


class AudioStorage(Protocol):
    def put_object(self, key: str, content: bytes, content_type: str) -> str:
        """Persist an audio object and return the storage key used by downstream systems."""
