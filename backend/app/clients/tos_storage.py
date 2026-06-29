from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class TosStorageConfig:
    access_key_id: str
    access_key_secret: str
    endpoint: str
    region: str
    bucket: str
    object_prefix: str = "web2audio"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "TosStorageConfig":
        return cls(
            access_key_id=str(data.get("access_key_id") or ""),
            access_key_secret=str(data.get("access_key_secret") or ""),
            endpoint=str(data.get("endpoint") or "tos-cn-beijing.volces.com"),
            region=str(data.get("region") or "cn-beijing"),
            bucket=str(data.get("bucket") or ""),
            object_prefix=str(data.get("object_prefix") or "web2audio"),
        )

    def validate(self) -> None:
        missing = []
        for field_name in (
            "access_key_id",
            "access_key_secret",
            "endpoint",
            "region",
            "bucket",
        ):
            if not getattr(self, field_name):
                missing.append(field_name)
        if missing:
            raise ValueError(f"tos config missing required fields: {', '.join(missing)}")


class TosStorage:
    def __init__(self, config: TosStorageConfig, tos_client: Optional[object] = None) -> None:
        config.validate()
        self.config = config
        self._client = tos_client

    def _tos_client(self) -> object:
        if self._client is None:
            import tos

            self._client = tos.TosClientV2(
                self.config.access_key_id,
                self.config.access_key_secret,
                self.config.endpoint,
                self.config.region,
            )
        return self._client

    def put_object(self, key: str, content: bytes, content_type: str) -> str:
        client = self._tos_client()
        client.put_object(
            self.config.bucket,
            key,
            content=content,
            content_type=content_type,
        )
        return key
