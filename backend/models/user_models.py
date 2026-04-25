"""SQLAlchemy models for users and alert rules."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


class User(db.Model):
    """Tracks a user wallet and notification destination."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    discord_webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    discord_user_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    alert_rules: Mapped[list["AlertRule"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "wallet_address": self.wallet_address,
            "discord_webhook_url": self.discord_webhook_url,
            "discord_user_id": self.discord_user_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AlertRule(db.Model):
    """Stores market radar alerts: price breakouts, volume spikes, whale watch."""

    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Human-readable token metadata stored at creation time
    token_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    token_logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Human-readable description of the alert condition
    alert_description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Alert lifecycle status: 'active' or 'triggered'
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    
    # Price breakout: alert if price crosses this threshold
    target_price: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    
    # Volume spike: alert if 1h volume exceeds threshold
    volume_threshold_usd: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)

    # Volume spike percentage trigger configured from terminal modal
    volume_spike_percent_threshold: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Whale watch: alert if price change% exceeds threshold
    price_change_percent_threshold: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    
    # DIY risk assessment: false = disabled, true = include local Solana RPC checks
    include_risk_assessment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Notification destination configured per alert: webhook or dm
    delivery_channel: Mapped[str] = mapped_column(String(16), default="webhook", nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="alert_rules")
    notifications: Mapped[list["NotificationHistory"]] = relationship(
        back_populates="alert_rule",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "token_address": self.token_address,
            "token_name": self.token_name,
            "token_logo_url": self.token_logo_url,
            "alert_description": self.alert_description,
            "status": self.status,
            "target_price": float(self.target_price) if self.target_price is not None else None,
            "volume_threshold_usd": float(self.volume_threshold_usd) if self.volume_threshold_usd is not None else None,
            "volume_spike_percent_threshold": float(self.volume_spike_percent_threshold)
            if self.volume_spike_percent_threshold is not None
            else None,
            "price_change_percent_threshold": float(self.price_change_percent_threshold) if self.price_change_percent_threshold is not None else None,
            "include_risk_assessment": self.include_risk_assessment,
            "delivery_channel": self.delivery_channel,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class NotificationHistory(db.Model):
    """Tracks outbound alert delivery attempts for idempotency and audit."""

    __tablename__ = "notification_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alert_rule_id: Mapped[int] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_address: Mapped[str] = mapped_column(String(64), nullable=False)
    condition_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    alert_rule: Mapped[AlertRule] = relationship(back_populates="notifications")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "alert_rule_id": self.alert_rule_id,
            "token_address": self.token_address,
            "condition_key": self.condition_key,
            "status": self.status,
            "detail": self.detail,
            "sent_at": self.sent_at.isoformat(),
        }


class WatchlistItem(db.Model):
    """Stores user-selected tokens for persistent command center watchlists."""

    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="watchlist_items")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "token_address": self.token_address,
            "token_name": self.token_name,
            "symbol": self.symbol,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
