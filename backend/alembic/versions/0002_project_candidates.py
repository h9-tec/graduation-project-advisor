"""project candidates table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-18 14:50:00

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import JSONB

        return JSONB()
    return sa.JSON()


def _string_array() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import ARRAY

        return ARRAY(sa.String())
    return sa.JSON()


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import UUID

        return UUID(as_uuid=True)
    return sa.String(36)


def upgrade() -> None:
    op.create_table(
        "project_candidates",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("arxiv_id", sa.String(32), nullable=True),
        sa.Column("github_url", sa.String(512), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("abstract", sa.String(), nullable=True),
        sa.Column("readme_summary", sa.String(), nullable=True),
        sa.Column("ai_summary", sa.String(), nullable=True),
        sa.Column("domains", _string_array(), nullable=False),
        sa.Column("ai_keywords", _string_array(), nullable=False),
        sa.Column("difficulty_estimated", sa.String(16), nullable=True),
        sa.Column("difficulty_level", sa.Integer(), nullable=True),
        sa.Column("has_code", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("upvotes_daily", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("citations", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("project_page_url", sa.String(512), nullable=True),
        sa.Column("organization", sa.String(256), nullable=True),
        sa.Column("code_language", sa.String(64), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("submitted_on_daily_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_github_push", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_metadata", _json_type(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding_model_name", sa.String(128), nullable=True),
        sa.Column(
            "qdrant_synced", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )

    op.create_index("ix_pc_source", "project_candidates", ["source"])
    op.create_index("ix_pc_source_type", "project_candidates", ["source_type"])
    op.create_index("ix_pc_arxiv_id", "project_candidates", ["arxiv_id"])
    op.create_index("ix_pc_github_url", "project_candidates", ["github_url"])
    op.create_index("ix_pc_has_code", "project_candidates", ["has_code"])
    op.create_index("ix_pc_difficulty_level", "project_candidates", ["difficulty_level"])
    op.create_index(
        "ix_pc_difficulty_estimated", "project_candidates", ["difficulty_estimated"]
    )
    op.create_index("ix_pc_content_hash", "project_candidates", ["content_hash"])
    op.create_index("ix_pc_embedded_at", "project_candidates", ["embedded_at"])
    op.create_index("ix_pc_qdrant_synced", "project_candidates", ["qdrant_synced"])


def downgrade() -> None:
    op.drop_index("ix_pc_qdrant_synced", table_name="project_candidates")
    op.drop_index("ix_pc_embedded_at", table_name="project_candidates")
    op.drop_index("ix_pc_content_hash", table_name="project_candidates")
    op.drop_index("ix_pc_difficulty_estimated", table_name="project_candidates")
    op.drop_index("ix_pc_difficulty_level", table_name="project_candidates")
    op.drop_index("ix_pc_has_code", table_name="project_candidates")
    op.drop_index("ix_pc_github_url", table_name="project_candidates")
    op.drop_index("ix_pc_arxiv_id", table_name="project_candidates")
    op.drop_index("ix_pc_source_type", table_name="project_candidates")
    op.drop_index("ix_pc_source", table_name="project_candidates")
    op.drop_table("project_candidates")
