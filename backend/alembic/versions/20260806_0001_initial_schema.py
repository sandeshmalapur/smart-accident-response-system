"""initial schema: users, devices, sensor_readings, incidents, alerts

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-06

Table order matches DATABASE_SCHEMA.md's Migration Plan (respects FK
dependencies): users -> devices -> sensor_readings -> incidents -> alerts.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')  # for gen_random_uuid()

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="operator"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("device_code", sa.String(100), nullable=False, unique=True),
        sa.Column("device_type", sa.String(50), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "sensor_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("accel_x", sa.Float(), nullable=False),
        sa.Column("accel_y", sa.Float(), nullable=False),
        sa.Column("accel_z", sa.Float(), nullable=False),
        sa.Column("gyro_x", sa.Float(), nullable=True),
        sa.Column("gyro_y", sa.Float(), nullable=True),
        sa.Column("gyro_z", sa.Float(), nullable=True),
        sa.Column("gas_level", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_sensor_readings_device_id_recorded_at", "sensor_readings", ["device_id", "recorded_at"]
    )

    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column(
            "sensor_reading_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sensor_readings.id"),
            nullable=False,
        ),
        sa.Column("incident_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(50), nullable=True),
        sa.Column("severity_score", sa.Float(), nullable=True),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_incidents_device_id_created_at", "incidents", ["device_id", "created_at"])
    op.create_index("ix_incidents_status", "incidents", ["status"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("delivery_status", sa.String(50), nullable=False, server_default="mocked"),
    )


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_device_id_created_at", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_sensor_readings_device_id_recorded_at", table_name="sensor_readings")
    op.drop_table("sensor_readings")
    op.drop_table("devices")
    op.drop_table("users")
