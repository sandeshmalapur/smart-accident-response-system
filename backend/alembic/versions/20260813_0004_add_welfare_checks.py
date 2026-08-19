"""add welfare_checks table

Revision ID: 0004_add_welfare_checks
Revises: 0003_add_ambulances_dispatches
Create Date: 2026-08-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_add_welfare_checks"
down_revision: Union[str, None] = "0003_add_ambulances_dispatches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "welfare_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'awaiting_response'")),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response", sa.String(50), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("welfare_checks")
