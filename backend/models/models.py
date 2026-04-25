"""
Database models for trading data
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid


class BaseModel:
    """Base model with common fields"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Token(BaseModel):
    """Token model"""
    __tablename__ = 'tokens'
    
    mint_address = Column(String(255), unique=True, nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    decimals = Column(Integer, default=6)
    logo_url = Column(String(255))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'mint_address': self.mint_address,
            'symbol': self.symbol,
            'name': self.name,
            'decimals': self.decimals,
            'logo_url': self.logo_url,
            'created_at': self.created_at.isoformat(),
        }


class PriceFeed(BaseModel):
    """Price feed data"""
    __tablename__ = 'price_feeds'
    __table_args__ = (
        Index('idx_token_timestamp', 'token_id', 'timestamp'),
    )
    
    token_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume_24h = Column(Float)
    market_cap = Column(Float)
    price_change_24h = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'token_id': str(self.token_id),
            'price': self.price,
            'volume_24h': self.volume_24h,
            'market_cap': self.market_cap,
            'price_change_24h': self.price_change_24h,
            'timestamp': self.timestamp.isoformat(),
        }
