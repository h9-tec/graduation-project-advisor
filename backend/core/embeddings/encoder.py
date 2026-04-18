from __future__ import annotations

import asyncio
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from core.settings import get_settings

VECTOR_DIM = 384  # paraphrase-multilingual-MiniLM-L12-v2 output size
MAX_SEQ_LEN = 512


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the multilingual MiniLM model. Downloads on first call (~90 MB)."""
    settings = get_settings()
    model = SentenceTransformer(settings.embedding_model)
    model.max_seq_length = MAX_SEQ_LEN
    return model


def embed_sync(text: str) -> list[float]:
    """Synchronous encode — for ingestion scripts / CLI."""
    vec = get_model().encode(text, normalize_embeddings=True, show_progress_bar=False)
    return vec.tolist()


def embed_batch_sync(texts: list[str]) -> list[list[float]]:
    """Batched sync encode — use this in ingestion for speed."""
    vecs = get_model().encode(
        texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32
    )
    return [v.tolist() for v in vecs]


async def embed(text: str) -> list[float]:
    """Async wrapper — offloads the CPU work to a thread so the event loop stays free."""
    return await asyncio.to_thread(embed_sync, text)


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Batched async wrapper."""
    return await asyncio.to_thread(embed_batch_sync, texts)
