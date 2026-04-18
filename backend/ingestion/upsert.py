from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.db.models import ProjectCandidate
from core.embeddings.encoder import embed_batch_sync
from core.embeddings.qdrant_client import ensure_collection, upsert_batch
from core.settings import get_settings
from ingestion.normalize import NormalizedCandidate, content_hash, embedding_text


def _engine() -> Any:
    settings = get_settings()
    return create_async_engine(settings.database_url, future=True)


async def _find_existing(
    session: AsyncSession, c: NormalizedCandidate
) -> ProjectCandidate | None:
    if c.arxiv_id:
        q = select(ProjectCandidate).where(ProjectCandidate.arxiv_id == c.arxiv_id)
        r = (await session.execute(q)).scalar_one_or_none()
        if r is not None:
            return r
    if c.github_url:
        q = select(ProjectCandidate).where(ProjectCandidate.github_url == c.github_url)
        return (await session.execute(q)).scalar_one_or_none()
    return None


def _payload(pc: ProjectCandidate) -> dict[str, Any]:
    """Qdrant payload — duplicates the display fields so card rendering
    doesn't need a Postgres round trip."""
    return {
        "source": pc.source,
        "source_type": pc.source_type,
        "title": pc.title,
        "arxiv_id": pc.arxiv_id,
        "github_url": pc.github_url,
        "project_page_url": pc.project_page_url,
        "domains": pc.domains,
        "ai_keywords": pc.ai_keywords,
        "difficulty_estimated": pc.difficulty_estimated,
        "difficulty_level": pc.difficulty_level,
        "has_code": pc.has_code,
        "stars": pc.stars,
        "upvotes_daily": pc.upvotes_daily,
        "quality_score": pc.quality_score,
        "published_year": pc.published_at.year if pc.published_at else None,
        "summary": (pc.ai_summary or pc.abstract or "")[:1200],
    }


async def ingest(candidates: list[NormalizedCandidate]) -> dict[str, int]:
    """Upsert candidates to Postgres, embed, upsert to Qdrant."""
    if not candidates:
        return {"total": 0, "new": 0, "updated": 0, "embedded": 0, "qdrant_upserted": 0}

    settings = get_settings()
    engine = _engine()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    await ensure_collection()

    new_count = 0
    updated_count = 0
    need_embed: list[ProjectCandidate] = []

    async with sessionmaker() as session:
        for c in candidates:
            existing = await _find_existing(session, c)
            new_hash = content_hash(c)

            if existing is None:
                pc = ProjectCandidate(
                    id=uuid.uuid4(),
                    source=c.source,
                    source_type=c.source_type,
                    arxiv_id=c.arxiv_id,
                    github_url=c.github_url,
                    title=c.title,
                    abstract=c.abstract,
                    readme_summary=c.readme_summary,
                    ai_summary=c.ai_summary,
                    domains=c.domains or [],
                    ai_keywords=c.ai_keywords or [],
                    difficulty_estimated=c.difficulty_estimated,
                    difficulty_level=c.difficulty_level,
                    has_code=c.has_code,
                    stars=c.stars,
                    upvotes_daily=c.upvotes_daily,
                    citations=c.citations,
                    quality_score=c.quality_score,
                    project_page_url=c.project_page_url,
                    organization=c.organization,
                    code_language=c.code_language,
                    published_at=c.published_at,
                    submitted_on_daily_at=c.submitted_on_daily_at,
                    raw_metadata=c.raw_metadata or {},
                    content_hash=new_hash,
                )
                session.add(pc)
                new_count += 1
                need_embed.append(pc)
            else:
                # update fields that can legitimately change
                existing.stars = c.stars
                existing.upvotes_daily = max(existing.upvotes_daily, c.upvotes_daily)
                existing.quality_score = max(existing.quality_score, c.quality_score)
                if c.ai_keywords:
                    existing.ai_keywords = c.ai_keywords
                if c.ai_summary and not existing.ai_summary:
                    existing.ai_summary = c.ai_summary
                if c.project_page_url and not existing.project_page_url:
                    existing.project_page_url = c.project_page_url
                if c.github_url and not existing.github_url:
                    existing.github_url = c.github_url
                    existing.has_code = True
                if existing.content_hash != new_hash:
                    existing.content_hash = new_hash
                    existing.embedded_at = None
                    need_embed.append(existing)
                updated_count += 1

        await session.commit()

        # embed + Qdrant upsert in one batch
        if need_embed:
            texts = [embedding_text_from_pc(pc) for pc in need_embed]
            vectors = embed_batch_sync(texts)
            now = datetime.now(tz=timezone.utc)
            for pc, vec in zip(need_embed, vectors):
                pc.embedded_at = now
                pc.embedding_model_name = settings.embedding_model
                pc.qdrant_synced = True
            await session.commit()

            await upsert_batch(
                [(pc.id, vec, _payload(pc)) for pc, vec in zip(need_embed, vectors)]
            )
            logger.info(f"Embedded + upserted {len(need_embed)} points to Qdrant")

    await engine.dispose()
    return {
        "total": len(candidates),
        "new": new_count,
        "updated": updated_count,
        "embedded": len(need_embed),
        "qdrant_upserted": len(need_embed),
    }


def embedding_text_from_pc(pc: ProjectCandidate) -> str:
    body = pc.abstract or pc.ai_summary or pc.readme_summary or ""
    return f"{pc.title}\n\n{body}".strip()
