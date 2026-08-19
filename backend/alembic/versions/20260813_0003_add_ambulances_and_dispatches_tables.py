"""add ambulances and dispatches tables

Revision ID: 0003_add_ambulances_and_dispatches_tables
Revises: 0002_add_hospitals_table
Create Date: 2026-08-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_add_ambulances_dispatches"
down_revision: Union[str, None] = "0002_add_hospitals_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ambulances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ambulance_code", sa.String(100), nullable=False, unique=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("current_latitude", sa.Float(), nullable=True),
        sa.Column("current_longitude", sa.Float(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'available'")),
        sa.Column("last_location_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ambulances_ambulance_code", "ambulances", ["ambulance_code"], unique=True)

    op.create_table(
        "dispatches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("ambulance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ambulances.id"), nullable=False),
        sa.Column("dispatched_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'dispatched'")),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("dispatches")
    op.drop_index("ix_ambulances_ambulance_code", table_name="ambulances")
    op.drop_table("ambulances")
