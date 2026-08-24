"""add agency_units and agency_dispatches tables

Revision ID: 0006_agency_units_dispatches
Revises: 0005_emergency_contacts
Create Date: 2026-08-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_agency_units_dispatches"
down_revision: Union[str, None] = "0005_emergency_contacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create agency_units table
    op.create_table(
        "agency_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agency_type", sa.String(50), nullable=False),
        sa.Column("unit_code", sa.String(100), nullable=False, unique=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("current_latitude", sa.Float(), nullable=True),
        sa.Column("current_longitude", sa.Float(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="available"),
        sa.Column("last_location_update", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_agency_units_unit_code", "agency_units", ["unit_code"], unique=True)

    # 2. Create agency_dispatches table
    op.create_table(
        "agency_dispatches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("agency_unit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agency_units.id"), nullable=False),
        sa.Column("dispatched_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("agency_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("agency_dispatches")
    op.drop_index("ix_agency_units_unit_code", table_name="agency_units")
    op.drop_table("agency_units")
