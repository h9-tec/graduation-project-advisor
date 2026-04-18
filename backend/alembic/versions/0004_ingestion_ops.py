"""ingestion_runs + dead_letter

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-18 16:20:00

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import JSONB

        return JSONB()
    return sa.JSON()


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import UUID

        return UUID(as_uuid=True)
    return sa.String(36)


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("total_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedded_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dead_lettered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(), nullable=True),
    )
    op.create_index("ix_ir_source", "ingestion_runs", ["source"])
    op.create_index("ix_ir_status", "ingestion_runs", ["status"])

    op.create_table(
        "dead_letter",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("payload", _json_type(), nullable=False),
        sa.Column("error", sa.String(), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dl_source", "dead_letter", ["source"])
    op.create_index("ix_dl_stage", "dead_letter", ["stage"])
    op.create_index("ix_dl_external_id", "dead_letter", ["external_id"])
    op.create_index("ix_dl_resolved_at", "dead_letter", ["resolved_at"])


def downgrade() -> None:
    op.drop_index("ix_dl_resolved_at", table_name="dead_letter")
    op.drop_index("ix_dl_external_id", table_name="dead_letter")
    op.drop_index("ix_dl_stage", table_name="dead_letter")
    op.drop_index("ix_dl_source", table_name="dead_letter")
    op.drop_table("dead_letter")
    op.drop_index("ix_ir_status", table_name="ingestion_runs")
    op.drop_index("ix_ir_source", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
