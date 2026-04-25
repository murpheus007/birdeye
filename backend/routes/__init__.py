"""Route blueprint exports."""

from routes.analysis import analysis_bp
from routes.auth import auth_bp
from routes.alerts import alerts_bp
from routes.discovery import discovery_bp
from routes.user_wallet import user_wallet_bp

__all__ = ["discovery_bp", "analysis_bp", "auth_bp", "alerts_bp", "user_wallet_bp"]
