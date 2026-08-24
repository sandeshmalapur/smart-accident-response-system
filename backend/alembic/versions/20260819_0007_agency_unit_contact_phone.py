"""add contact_phone to agency_units

Revision ID: 0007_agency_unit_contact_phone
Revises: 0006_agency_units_dispatches
Create Date: 2026-08-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_agency_unit_contact_phone"
down_revision: Union[str, None] = "0006_agency_units_dispatches"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agency_units", sa.Column("contact_phone", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("agency_units", "contact_phone")
