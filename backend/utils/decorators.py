"""
Utility functions
"""
from functools import wraps
from flask import jsonify
import logging

logger = logging.getLogger(__name__)


def error_handler(f):
    """Decorator for error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            return jsonify({'error': 'Internal server error'}), 500
    return decorated_function


def validate_pagination(page: int = 1, limit: int = 20) -> tuple:
    """Validate pagination parameters"""
    page = max(1, page)
    limit = max(1, min(limit, 100))  # Cap at 100
    offset = (page - 1) * limit
    return page, limit, offset
