"""feedback table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-18 16:05:00

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
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
        "feedbacks",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("card_id", sa.String(128), nullable=False),
        sa.Column("reaction", sa.String(8), nullable=False),
        sa.Column("profile_snapshot", _json_type(), nullable=False),
        sa.Column("card_snapshot", _json_type(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_fb_session_id", "feedbacks", ["session_id"])
    op.create_index("ix_fb_card_id", "feedbacks", ["card_id"])
    op.create_index("ix_fb_reaction", "feedbacks", ["reaction"])


def downgrade() -> None:
    op.drop_index("ix_fb_reaction", table_name="feedbacks")
    op.drop_index("ix_fb_card_id", table_name="feedbacks")
    op.drop_index("ix_fb_session_id", table_name="feedbacks")
    op.drop_table("feedbacks")
