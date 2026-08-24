"""add device emergency contact fields and incident_tracking_tokens table

Revision ID: 0005_emergency_contacts
Revises: 0004_add_welfare_checks
Create Date: 2026-08-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005_emergency_contacts"

down_revision: Union[str, None] = "0004_add_welfare_checks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add emergency contact columns to devices table
    op.add_column("devices", sa.Column("owner_name", sa.String(255), nullable=True))
    op.add_column("devices", sa.Column("emergency_contact_name", sa.String(255), nullable=True))
    op.add_column("devices", sa.Column("emergency_contact_phone", sa.String(50), nullable=True))

    # 2. Create incident_tracking_tokens table
    op.create_table(
        "incident_tracking_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("token", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incident_tracking_tokens_token", "incident_tracking_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_incident_tracking_tokens_token", table_name="incident_tracking_tokens")
    op.drop_table("incident_tracking_tokens")
    op.drop_column("devices", "emergency_contact_phone")
    op.drop_column("devices", "emergency_contact_name")
    op.drop_column("devices", "owner_name")
