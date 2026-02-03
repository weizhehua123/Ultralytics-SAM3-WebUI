from __future__ import annotations

import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass
class CachedEmbedding:
    embedding_id: str
    created_at: float
    expires_at: float
    features: Any
    src_shape: tuple[int, int]

    @staticmethod
    def new(*, features: Any, src_shape: tuple[int, int], ttl_sec: int) -> "CachedEmbedding":
        now = time.time()
        return CachedEmbedding(
            embedding_id=uuid.uuid4().hex,
            created_at=now,
            expires_at=now + max(1, int(ttl_sec)),
            features=features,
            src_shape=src_shape,
        )


class EmbeddingCache:
    def __init__(self, max_size: int):
        self._max_size = max_size
        self._data: "OrderedDict[str, CachedEmbedding]" = OrderedDict()

    def get(self, embedding_id: str) -> CachedEmbedding | None:
        self._purge_expired()
        item = self._data.get(embedding_id)
        if item is None:
            return None
        self._data.move_to_end(embedding_id)
        return item

    def put(self, item: CachedEmbedding) -> None:
        self._purge_expired()
        self._data[item.embedding_id] = item
        self._data.move_to_end(item.embedding_id)
        while len(self._data) > self._max_size:
            self._data.popitem(last=False)

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._data.items() if v.expires_at <= now]
        for k in expired:
            self._data.pop(k, None)


_cache: EmbeddingCache | None = None


def get_embedding_cache() -> EmbeddingCache:
    global _cache
    if _cache is None:
        from ..core.config import get_settings

        settings = get_settings()
        _cache = EmbeddingCache(max_size=settings.embedding_cache_size)
    return _cache
