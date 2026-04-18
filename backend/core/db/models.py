from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, Date, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator

from core.db.base import Base


class _UUIDType(TypeDecorator[uuid.UUID]):
    """UUID as native uuid on Postgres, 36-char string on SQLite."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: uuid.UUID | str | None, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> uuid.UUID | None:
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class _JSONType(TypeDecorator[Any]):
    """JSONB on Postgres, JSON on SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_JSONB())
        return dialect.type_descriptor(JSON())


class _StringArrayType(TypeDecorator[list[str]]):
    """Array-of-text on Postgres, JSON list on SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_ARRAY(String()))
        return dialect.type_descriptor(JSON())


class ProjectCandidate(Base):
    """A normalized record for a paper, a repo, or a paper+repo pair.

    One row per unique candidate. Dedup keys: arxiv_id, github_url, or
    (normalized_title, first_author) fuzzy match when neither is present.
    """

    __tablename__ = "project_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        _UUIDType(), primary_key=True, default=uuid.uuid4
    )

    # source tagging
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # "hf_daily_papers" | "arxiv" | "github_trending" | "awesome_list"
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # "paper_with_code" | "paper_only" | "repo_only"

    # dedup keys (nullable; at least one must be present)
    arxiv_id: Mapped[str | None] = mapped_column(
        String(32), nullable=True, index=True, unique=False
    )
    github_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True, unique=False
    )

    # content
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    abstract: Mapped[str | None] = mapped_column(String, nullable=True)
    readme_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(String, nullable=True)

    # enrichment (from source when possible; LLM-generated otherwise)
    domains: Mapped[list[str]] = mapped_column(
        _StringArrayType(), nullable=False, default=list
    )
    ai_keywords: Mapped[list[str]] = mapped_column(
        _StringArrayType(), nullable=False, default=list
    )
    difficulty_estimated: Mapped[str | None] = mapped_column(
        String(16), nullable=True, index=True
    )
    difficulty_level: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )

    # signals
    has_code: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    stars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    upvotes_daily: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    citations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # extras
    project_page_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(256), nullable=True)
    code_language: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # dates
    published_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    submitted_on_daily_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_github_push: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # bookkeeping
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(
        _JSONType(), nullable=False, default=dict
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )  # SHA-256 of (title + abstract + readme_summary) — triggers re-embed on change

    # embedding status
    embedded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    embedding_model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # outbox flag for Qdrant sync retry
    qdrant_synced: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<ProjectCandidate id={self.id} source={self.source} "
            f"arxiv={self.arxiv_id} github={self.github_url}>"
        )
