from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm

from core.embeddings.encoder import VECTOR_DIM
from core.settings import get_settings

COLLECTION = "project_candidates"


@lru_cache(maxsize=1)
def get_qdrant() -> AsyncQdrantClient:
    settings = get_settings()
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        timeout=15,
    )


async def ensure_collection() -> None:
    """Create the project_candidates collection if missing. Idempotent."""
    client = get_qdrant()
    existing = await client.get_collections()
    names = {c.name for c in existing.collections}
    if COLLECTION in names:
        return

    await client.create_collection(
        collection_name=COLLECTION,
        vectors_config=qm.VectorParams(size=VECTOR_DIM, distance=qm.Distance.COSINE),
    )

    # indexed payload fields for fast filtering
    for field_name, schema in [
        ("domains", qm.PayloadSchemaType.KEYWORD),
        ("ai_keywords", qm.PayloadSchemaType.KEYWORD),
        ("difficulty_estimated", qm.PayloadSchemaType.KEYWORD),
        ("difficulty_level", qm.PayloadSchemaType.INTEGER),
        ("has_code", qm.PayloadSchemaType.BOOL),
        ("published_year", qm.PayloadSchemaType.INTEGER),
        ("source", qm.PayloadSchemaType.KEYWORD),
        ("source_type", qm.PayloadSchemaType.KEYWORD),
        ("quality_score", qm.PayloadSchemaType.FLOAT),
    ]:
        await client.create_payload_index(
            collection_name=COLLECTION, field_name=field_name, field_schema=schema
        )


async def upsert_candidate(
    *,
    candidate_id: uuid.UUID,
    vector: list[float],
    payload: dict[str, Any],
) -> None:
    client = get_qdrant()
    await client.upsert(
        collection_name=COLLECTION,
        points=[
            qm.PointStruct(
                id=str(candidate_id),
                vector=vector,
                payload=payload,
            )
        ],
    )


async def upsert_batch(
    items: list[tuple[uuid.UUID, list[float], dict[str, Any]]],
) -> None:
    if not items:
        return
    client = get_qdrant()
    await client.upsert(
        collection_name=COLLECTION,
        points=[
            qm.PointStruct(id=str(cid), vector=v, payload=p)
            for cid, v, p in items
        ],
    )


async def count_points() -> int:
    client = get_qdrant()
    info = await client.get_collection(COLLECTION)
    return info.points_count or 0
