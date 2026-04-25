"""
Database service for Discord bot
"""
import os
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations"""
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.engine = create_engine(self.db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
    
    def get_guild_config(self, guild_id: int):
        """Get configuration for a guild"""
        try:
            session = self.get_session()
            # Implementation here
            return None
        except Exception as e:
            logger.error(f"Error getting guild config: {e}")
            return None
    
    def save_guild_config(self, guild_id: int, config: dict):
        """Save guild configuration"""
        try:
            session = self.get_session()
            # Implementation here
            session.commit()
        except Exception as e:
            logger.error(f"Error saving guild config: {e}")
            if session:
                session.rollback()

    def list_active_alert_rules(self):
        """Return active alert rules joined with user notification details."""
        query = text(
            """
            SELECT
                ar.id AS rule_id,
                ar.user_id,
                ar.token_address,
                ar.target_price,
                ar.volume_spike_percent_threshold,
                ar.price_change_percent_threshold,
                COALESCE(ar.delivery_channel, 'webhook') AS delivery_channel,
                ar.is_active,
                COALESCE(ar.status, 'active') AS status,
                ar.alert_description,
                u.wallet_address,
                u.discord_webhook_url,
                u.discord_user_id
            FROM alert_rules ar
            JOIN users u ON u.id = ar.user_id
            WHERE ar.is_active = TRUE
              AND (ar.status IS NULL OR ar.status = 'active')
            """
        )

        session = self.get_session()
        try:
            rows = session.execute(query).mappings().all()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing active alert rules: {e}")
            return []
        finally:
            session.close()

    def has_recent_notification(self, alert_rule_id: int, token_address: str, condition_key: str, hours: int = 4) -> bool:
        """Return True if same alert was sent in the given lookback window."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = text(
            """
            SELECT 1
            FROM notification_history
            WHERE alert_rule_id = :alert_rule_id
              AND token_address = :token_address
              AND condition_key = :condition_key
              AND status = 'success'
              AND sent_at >= :cutoff
            LIMIT 1
            """
        )

        session = self.get_session()
        try:
            row = session.execute(
                query,
                {
                    "alert_rule_id": alert_rule_id,
                    "token_address": token_address,
                    "condition_key": condition_key,
                    "cutoff": cutoff,
                },
            ).first()
            return row is not None
        except Exception as e:
            logger.error(f"Error checking notification idempotency: {e}")
            return False
        finally:
            session.close()

    def log_notification_attempt(
        self,
        alert_rule_id: int,
        token_address: str,
        condition_key: str,
        status: str,
        detail: str | None = None,
    ):
        """Write delivery status to notification_history table."""
        query = text(
            """
            INSERT INTO notification_history (alert_rule_id, token_address, condition_key, status, detail)
            VALUES (:alert_rule_id, :token_address, :condition_key, :status, :detail)
            """
        )

        session = self.get_session()
        try:
            session.execute(
                query,
                {
                    "alert_rule_id": alert_rule_id,
                    "token_address": token_address,
                    "condition_key": condition_key,
                    "status": status,
                    "detail": detail,
                },
            )
            session.commit()
        except Exception as e:
            logger.error(f"Error logging notification attempt: {e}")
            session.rollback()
        finally:
            session.close()

    def get_wallet_by_discord_user_id(self, discord_user_id: str) -> str | None:
        """Return wallet address for a Discord user, or None when not linked."""
        query = text(
            """
            SELECT wallet_address
            FROM users
            WHERE discord_user_id = :discord_user_id
            LIMIT 1
            """
        )

        session = self.get_session()
        try:
            row = session.execute(query, {"discord_user_id": discord_user_id}).first()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error finding wallet by discord user id: {e}")
            return None
        finally:
            session.close()

    def get_user_id_by_wallet(self, wallet_address: str) -> int | None:
        """Return the user id for a wallet address, or None when not linked."""
        query = text(
            """
            SELECT id
            FROM users
            WHERE wallet_address = :wallet_address
            LIMIT 1
            """
        )

        session = self.get_session()
        try:
            row = session.execute(query, {"wallet_address": wallet_address}).first()
            return int(row[0]) if row else None
        except Exception as e:
            logger.error(f"Error finding user id by wallet: {e}")
            return None
        finally:
            session.close()

    def get_discord_user_id_by_user_id(self, user_id: int) -> str | None:
        """Return discord_user_id for a user id, or None when unavailable."""
        query = text(
            """
            SELECT discord_user_id
            FROM users
            WHERE id = :user_id
            LIMIT 1
            """
        )

        session = self.get_session()
        try:
            row = session.execute(query, {"user_id": user_id}).first()
            if not row or not row[0]:
                return None
            return str(row[0])
        except Exception as e:
            logger.error(f"Error finding discord user id by user id: {e}")
            return None
        finally:
            session.close()

    def list_watchlist_by_wallet(self, wallet_address: str) -> list[dict]:
        """Return watchlist items for a wallet."""
        query = text(
            """
            SELECT
                wi.token_address,
                wi.token_name,
                wi.symbol,
                wi.created_at
            FROM watchlist_items wi
            JOIN users u ON u.id = wi.user_id
            WHERE u.wallet_address = :wallet_address
            ORDER BY wi.created_at DESC
            LIMIT 25
            """
        )

        session = self.get_session()
        try:
            rows = session.execute(query, {"wallet_address": wallet_address}).mappings().all()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing watchlist by wallet: {e}")
            return []
        finally:
            session.close()

    def mark_alert_triggered(self, alert_rule_id: int) -> None:
        """Update a single alert rule's status to 'triggered' so it stops firing."""
        query = text(
            """
            UPDATE alert_rules
            SET status = 'triggered', updated_at = NOW()
            WHERE id = :alert_rule_id
            """
        )
        session = self.get_session()
        try:
            session.execute(query, {"alert_rule_id": alert_rule_id})
            session.commit()
        except Exception as e:
            logger.error(f"Error marking alert as triggered: {e}")
            session.rollback()
        finally:
            session.close()

    def list_alerts_by_wallet(self, wallet_address: str) -> list[dict]:
        """Return active alerts for a wallet."""
        query = text(
            """
            SELECT
                ar.id,
                ar.token_address,
                ar.token_name,
                ar.alert_description,
                ar.status,
                ar.target_price,
                ar.volume_spike_percent_threshold,
                ar.price_change_percent_threshold,
                ar.delivery_channel,
                ar.is_active,
                ar.created_at
            FROM alert_rules ar
            JOIN users u ON u.id = ar.user_id
            WHERE u.wallet_address = :wallet_address
              AND ar.is_active = TRUE
            ORDER BY ar.created_at DESC
            LIMIT 25
            """
        )

        session = self.get_session()
        try:
            rows = session.execute(query, {"wallet_address": wallet_address}).mappings().all()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing alerts by wallet: {e}")
            return []
        finally:
            session.close()
