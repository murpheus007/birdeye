"""Add status, alert_description, token_name, token_logo_url to alert_rules

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alert_rules",
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
    )
    op.add_column(
        "alert_rules",
        sa.Column("alert_description", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "alert_rules",
        sa.Column("token_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "alert_rules",
        sa.Column("token_logo_url", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("alert_rules", "token_logo_url")
    op.drop_column("alert_rules", "token_name")
    op.drop_column("alert_rules", "alert_description")
    op.drop_column("alert_rules", "status")
