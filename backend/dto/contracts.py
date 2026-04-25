"""DTO contracts for backend API responses."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class TokenSummaryDTO(BaseModel):
    """Response model for token summary cards."""

    token_address: str
    token_name: str
    symbol: str | None = None
    current_price: float | None = None
    security_rating: int | None = None


class PortfolioTokenDTO(BaseModel):
    """Single token holding details in a wallet portfolio."""

    token_address: str
    symbol: str | None = None
    amount: float = 0.0
    usd_value: float = 0.0


class WalletPortfolioDTO(BaseModel):
    """Response model for wallet portfolio overview."""

    wallet_address: str
    total_value_usd: float = 0.0
    token_count: int = 0
    tokens: List[PortfolioTokenDTO] = Field(default_factory=list)
