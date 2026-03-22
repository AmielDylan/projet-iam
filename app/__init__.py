"""Application factory module."""
import os
import logging
from typing import Optional

from flask import Flask

from app.config import get_config, Config
from app.services.database import DatabasePool
from app.api import api_bp
from app.web import web_bp
from app.errors import register_error_handlers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(config: Optional[Config] = None) -> Flask:
    """
    Application factory for creating Flask application instances.

    Args:
        config: Optional configuration object. If not provided,
                configuration is loaded based on FLASK_ENV.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )

    # Load configuration
    if config is None:
        config = get_config()

    # Apply configuration
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['DEBUG'] = getattr(config, 'DEBUG', False)
    app.config['TESTING'] = getattr(config, 'TESTING', False)

    # Store config for later use
    app.config['APP_CONFIG'] = config

    # Debug: Log database configuration
    logger.info(f"MYSQL_URL env: {os.environ.get('MYSQL_URL', 'NOT SET')[:50]}...")
    logger.info(f"DB_HOST: {config.DB_HOST}")
    logger.info(f"DB_PORT: {config.DB_PORT}")
    logger.info(f"DB_USER: {config.DB_USER}")
    logger.info(f"DB_NAME: {config.DB_NAME}")

    # Initialize database pool
    DatabasePool.initialize(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        pool_size=config.DB_POOL_SIZE,
        pool_name=config.DB_POOL_NAME
    )

    # Register blueprints
    app.register_blueprint(api_bp)
    app.register_blueprint(web_bp)

    # Register error handlers
    register_error_handlers(app)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register teardown
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Clean up on application context teardown."""
        pass  # Connection pool handles this

    return app
