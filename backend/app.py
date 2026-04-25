"""
Solana Trading Dashboard - Flask Backend
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from extensions import db, create_redis_client
from models.user_models import AlertRule, User
from routes.alerts import alerts_bp
from routes.analysis import analysis_bp
from routes.auth import auth_bp
from routes.discovery import discovery_bp
from routes.user_wallet import user_wallet_bp

# Load environment variables
load_dotenv()

def create_app() -> Flask:
    """Application factory used by Gunicorn and local dev."""
    app = Flask(__name__)

    # Core configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///birdeye.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'change-me-in-production')
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Birdeye gateway configuration
    app.config['BIRDEYE_API_BASE_URL'] = os.getenv('BIRDEYE_API_BASE_URL', 'https://public-api.birdeye.so')
    app.config['BIRDEYE_API_KEY'] = os.getenv('BIRDEYE_API_KEY')
    app.config['BIRDEYE_CACHE_TTL_SECONDS'] = int(os.getenv('BIRDEYE_CACHE_TTL_SECONDS', '300'))
    app.config['BIRDEYE_TIMEOUT_SECONDS'] = int(os.getenv('BIRDEYE_TIMEOUT_SECONDS', '15'))

    CORS(app, supports_credentials=True)
    db.init_app(app)

    birdeye_api_key = (app.config.get('BIRDEYE_API_KEY') or '').strip()
    if not birdeye_api_key or birdeye_api_key.lower().startswith('your_'):
        raise RuntimeError(
            'BIRDEYE_API_KEY is required at startup and must be a real key with endpoint access.'
        )

    # Initialize Redis and continue even if it is temporarily unavailable.
    try:
        redis_client = create_redis_client()
        redis_client.ping()
        app.extensions['redis_client'] = redis_client
    except Exception:
        app.extensions['redis_client'] = None

    # Register modular API blueprints.
    app.register_blueprint(discovery_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(user_wallet_bp)

    register_core_routes(app)
    return app


def register_core_routes(app: Flask):
    """Register non-domain core routes and handlers."""


    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        redis_ready = app.extensions.get('redis_client') is not None
        return jsonify({
            'status': 'healthy',
            'service': 'birdeye-backend',
            'redis_connected': redis_ready,
        }), 200


    @app.route('/api/v1/health', methods=['GET'])
    def api_health():
        """API health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'version': '1.0.0',
            'service': 'Solana Trading Dashboard API',
            'registered_models': ['Users', 'AlertRules'],
        }), 200


    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({'error': 'Endpoint not found'}), 404


    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        return jsonify({'error': 'Internal server error'}), 500


app = create_app()


if __name__ == '__main__':
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(
        host=os.getenv('API_HOST', '0.0.0.0'),
        port=int(os.getenv('API_PORT', 5000)),
        debug=debug
    )
