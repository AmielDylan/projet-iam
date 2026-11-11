"""Application configuration module."""
import base64
import hashlib
import os
from urllib.parse import urlparse
from typing import Optional


def parse_mysql_url(url: str) -> dict:
    """Parse MySQL URL into connection parameters."""
    parsed = urlparse(url)
    return {
        'host': parsed.hostname or '127.0.0.1',
        'port': parsed.port or 3306,
        'user': parsed.username or 'root',
        'password': parsed.password or '',
        'database': parsed.path.lstrip('/') or 'projet_ipa'
    }


def development_key(purpose: str) -> str:
    """Fixed key for development and tests only; production must set real keys."""
    digest = hashlib.sha256(f'digiremed-development-{purpose}'.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode()


class Config:
    """Base configuration class."""

    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database configuration - supports Railway's MYSQL_URL or individual vars
    @property
    def DB_HOST(self) -> str:
        if os.environ.get('MYSQL_URL'):
            return parse_mysql_url(os.environ['MYSQL_URL'])['host']
        return os.environ.get('MYSQLHOST') or os.environ.get('DB_HOST', '127.0.0.1')

    @property
    def DB_PORT(self) -> int:
        if os.environ.get('MYSQL_URL'):
            return parse_mysql_url(os.environ['MYSQL_URL'])['port']
        return int(os.environ.get('MYSQLPORT') or os.environ.get('DB_PORT', 3306))

    @property
    def DB_USER(self) -> str:
        if os.environ.get('MYSQL_URL'):
            return parse_mysql_url(os.environ['MYSQL_URL'])['user']
        return os.environ.get('MYSQLUSER') or os.environ.get('DB_USER', 'root')

    @property
    def DB_PASSWORD(self) -> str:
        if os.environ.get('MYSQL_URL'):
            return parse_mysql_url(os.environ['MYSQL_URL'])['password']
        return os.environ.get('MYSQLPASSWORD') or os.environ.get('DB_PASSWORD', '')

    @property
    def DB_NAME(self) -> str:
        if os.environ.get('MYSQL_URL'):
            return parse_mysql_url(os.environ['MYSQL_URL'])['database']
        return os.environ.get('MYSQLDATABASE') or os.environ.get('DB_NAME', 'projet_ipa')

    # Connection pool settings
    DB_POOL_SIZE: int = int(os.environ.get('DB_POOL_SIZE', 5))
    DB_POOL_NAME: str = os.environ.get('DB_POOL_NAME', 'iam_pool')

    # Application settings
    AUTOCOMPLETE_LIMIT: int = int(os.environ.get('AUTOCOMPLETE_LIMIT', 6))
    MAX_IDENTITY_DOCUMENT_BYTES: int = int(os.environ.get('MAX_IDENTITY_DOCUMENT_BYTES', 5 * 1024 * 1024))
    SMTP_HOST: str = os.environ.get('SMTP_HOST', '')
    SMTP_PORT: int = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER: str = os.environ.get('SMTP_USER', '')
    SMTP_PASSWORD: str = os.environ.get('SMTP_PASSWORD', '')
    SMTP_FROM: str = os.environ.get('SMTP_FROM', '')
    SMTP_TLS: bool = os.environ.get('SMTP_TLS', 'true').lower() not in {'0', 'false', 'no'}

    # Health data encryption at rest (see app/services/vault.py)
    @property
    def DATA_ENCRYPTION_KEYS(self) -> str:
        return os.environ.get('DATA_ENCRYPTION_KEYS') or f"dev:{development_key('encryption')}"

    @property
    def DATA_INDEX_KEY(self) -> str:
        return os.environ.get('DATA_INDEX_KEY') or development_key('index')


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG: bool = True
    TESTING: bool = False


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG: bool = False
    TESTING: bool = False

    @property
    def SECRET_KEY(self) -> str:
        key = os.environ.get('SECRET_KEY')
        if not key:
            raise ValueError('SECRET_KEY must be set in production')
        return key

    @property
    def DATA_ENCRYPTION_KEYS(self) -> str:
        keys = os.environ.get('DATA_ENCRYPTION_KEYS')
        if not keys:
            raise ValueError('DATA_ENCRYPTION_KEYS must be set in production')
        return keys

    @property
    def DATA_INDEX_KEY(self) -> str:
        key = os.environ.get('DATA_INDEX_KEY')
        if not key:
            raise ValueError('DATA_INDEX_KEY must be set in production')
        return key


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG: bool = True
    TESTING: bool = True

    @property
    def DB_NAME(self) -> str:
        return 'projet_ipa_test'


def get_config(env: Optional[str] = None) -> Config:
    """Get configuration based on environment."""
    env = env or os.environ.get('FLASK_ENV') or os.environ.get('RAILWAY_ENVIRONMENT', 'development')

    # Railway sets RAILWAY_ENVIRONMENT=production
    if env == 'production' or os.environ.get('RAILWAY_ENVIRONMENT'):
        return ProductionConfig()

    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
    }

    config_class = configs.get(env, DevelopmentConfig)
    return config_class()
