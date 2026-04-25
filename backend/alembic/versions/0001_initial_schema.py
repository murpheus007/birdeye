"""Consolidated initial schema: users, alert_rules, notification_history, watchlist_items

Revision ID: 0001
Revises:
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wallet_address", sa.String(length=64), nullable=False),
        sa.Column("discord_webhook_url", sa.String(length=2048), nullable=True),
        sa.Column("discord_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_wallet_address", "users", ["wallet_address"], unique=True)

    # ── alert_rules ────────────────────────────────────────────────────────
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_address", sa.String(length=64), nullable=False),
        sa.Column("target_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("security_threshold", sa.Integer(), nullable=True),
        sa.Column("volume_threshold_usd", sa.Numeric(20, 2), nullable=True),
        sa.Column("price_change_percent_threshold", sa.Numeric(10, 2), nullable=True),
        sa.Column("include_risk_assessment", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("volume_spike_percent_threshold", sa.Numeric(10, 2), nullable=True),
        sa.Column("delivery_channel", sa.String(length=16), nullable=False, server_default="webhook"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_alert_rules_user_id", "alert_rules", ["user_id"], unique=False)
    op.create_index("ix_alert_rules_token_address", "alert_rules", ["token_address"], unique=False)

    # ── notification_history ───────────────────────────────────────────────
    op.create_table(
        "notification_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_rule_id", sa.Integer(), sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_address", sa.String(length=64), nullable=False),
        sa.Column("condition_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notification_history_alert_rule_id", "notification_history", ["alert_rule_id"], unique=False)
    op.create_index("ix_notification_history_sent_at", "notification_history", ["sent_at"], unique=False)

    # ── watchlist_items ────────────────────────────────────────────────────
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_address", sa.String(length=64), nullable=False),
        sa.Column("token_name", sa.String(length=255), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_watchlist_items_user_id", "watchlist_items", ["user_id"], unique=False)
    op.create_index("ix_watchlist_items_token_address", "watchlist_items", ["token_address"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_watchlist_items_token_address", table_name="watchlist_items")
    op.drop_index("ix_watchlist_items_user_id", table_name="watchlist_items")
    op.drop_table("watchlist_items")

    op.drop_index("ix_notification_history_sent_at", table_name="notification_history")
    op.drop_index("ix_notification_history_alert_rule_id", table_name="notification_history")
    op.drop_table("notification_history")

    op.drop_index("ix_alert_rules_token_address", table_name="alert_rules")
    op.drop_index("ix_alert_rules_user_id", table_name="alert_rules")
    op.drop_table("alert_rules")

    op.drop_index("ix_users_wallet_address", table_name="users")
    op.drop_table("users")
