"""Backfill alert_rules schema drift and legacy table compatibility.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-24
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # If only the legacy quoted table exists, rename it to the canonical snake_case table.
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public."AlertRules"') IS NOT NULL
               AND to_regclass('public.alert_rules') IS NULL THEN
                EXECUTE 'ALTER TABLE public."AlertRules" RENAME TO alert_rules';
            END IF;
        END
        $$;
        """
    )

    # If both tables exist, copy missing rows into alert_rules and keep a backup table for safety.
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public."AlertRules"') IS NOT NULL
               AND to_regclass('public.alert_rules') IS NOT NULL THEN
                INSERT INTO public.alert_rules (
                    id,
                    user_id,
                    token_address,
                    target_price,
                    is_active,
                    created_at,
                    updated_at
                )
                SELECT
                    legacy.id,
                    legacy.user_id,
                    legacy.token_address,
                    legacy.target_price,
                    COALESCE(legacy.is_active, TRUE),
                    NOW(),
                    NOW()
                FROM public."AlertRules" legacy
                LEFT JOIN public.alert_rules current_rules ON current_rules.id = legacy.id
                WHERE current_rules.id IS NULL;

                IF to_regclass('public.alert_rules_legacy_backup') IS NULL THEN
                    EXECUTE 'ALTER TABLE public."AlertRules" RENAME TO alert_rules_legacy_backup';
                END IF;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        ALTER TABLE public.alert_rules
            ADD COLUMN IF NOT EXISTS volume_spike_percent_threshold NUMERIC(10, 2),
            ADD COLUMN IF NOT EXISTS price_change_percent_threshold NUMERIC(10, 2),
            ADD COLUMN IF NOT EXISTS delivery_channel VARCHAR(16) DEFAULT 'webhook',
            ADD COLUMN IF NOT EXISTS status VARCHAR(16) DEFAULT 'active',
            ADD COLUMN IF NOT EXISTS alert_description VARCHAR(512);
        """
    )

    # Ensure defaults are present and existing null rows are backfilled for command compatibility.
    op.execute(
        """
        ALTER TABLE public.alert_rules
            ALTER COLUMN delivery_channel SET DEFAULT 'webhook',
            ALTER COLUMN status SET DEFAULT 'active';

        UPDATE public.alert_rules
        SET delivery_channel = 'webhook'
        WHERE delivery_channel IS NULL;

        UPDATE public.alert_rules
        SET status = 'active'
        WHERE status IS NULL;
        """
    )


def downgrade() -> None:
    # Best-effort downgrade: keep all row data, remove only columns added by this migration.
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('public.alert_rules') IS NOT NULL THEN
                ALTER TABLE public.alert_rules
                    DROP COLUMN IF EXISTS alert_description,
                    DROP COLUMN IF EXISTS status,
                    DROP COLUMN IF EXISTS delivery_channel,
                    DROP COLUMN IF EXISTS price_change_percent_threshold,
                    DROP COLUMN IF EXISTS volume_spike_percent_threshold;
            END IF;

            IF to_regclass('public.alert_rules_legacy_backup') IS NOT NULL
               AND to_regclass('public."AlertRules"') IS NULL THEN
                EXECUTE 'ALTER TABLE public.alert_rules_legacy_backup RENAME TO "AlertRules"';
            END IF;
        END
        $$;
        """
    )
