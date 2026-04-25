"""Shared Flask extensions."""
import os

import redis
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def create_redis_client():
    """Build a Redis client from REDIS_URL."""
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    return redis.from_url(redis_url, decode_responses=True)
