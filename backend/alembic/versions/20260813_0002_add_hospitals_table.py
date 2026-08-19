"""add hospitals table and nearest_hospital_id to incidents

Revision ID: 0002_add_hospitals_table
Revises: 0001_initial_schema
Create Date: 2026-08-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_add_hospitals_table"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hospitals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.add_column(
        "incidents",
        sa.Column(
            "nearest_hospital_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hospitals.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("incidents", "nearest_hospital_id")
    op.drop_table("hospitals")
