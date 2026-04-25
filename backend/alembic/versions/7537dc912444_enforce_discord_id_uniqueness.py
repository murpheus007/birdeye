"""enforce_discord_id_uniqueness

Revision ID: 7537dc912444
Revises: 0003
Create Date: 2026-04-25 18:06:35.547352
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7537dc912444'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Clean up duplicates by keeping the most recently updated record for each Discord ID
    op.execute("""
        DELETE FROM users 
        WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY discord_user_id ORDER BY updated_at DESC) as rnum
                FROM users
                WHERE discord_user_id IS NOT NULL
            ) t
            WHERE t.rnum > 1
        )
    """)
    
    # 2. Add the unique constraint
    op.create_unique_constraint("uq_users_discord_user_id", "users", ["discord_user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_discord_user_id", "users", type_="unique")
