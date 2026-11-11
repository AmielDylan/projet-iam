"""Integration tests against a real MySQL 8.

Run them with a throwaway server, for example:
    docker run -d --rm --name iam-it -e MYSQL_ROOT_PASSWORD=test -p 127.0.0.1:33099:3306 mysql:8.0
    TEST_MYSQL_URL=mysql://root:test@127.0.0.1:33099 .venv/bin/python -m pytest tests/integration

Without TEST_MYSQL_URL they are skipped. The database is rebuilt like a
production start: hand-run migrations 007 and 008, then the startup steps.
"""
import os
from pathlib import Path

import mysql.connector
import pytest

from app.config import parse_mysql_url
from app.services.database import DatabasePool
from app.services.schema import split_statements

DATABASE = 'digiremed_it'
ROOT = Path(__file__).resolve().parents[2]


def pytest_collection_modifyitems(config, items):
    if os.environ.get('TEST_MYSQL_URL'):
        return
    skip = pytest.mark.skip(reason='TEST_MYSQL_URL not set')
    for item in items:
        if 'integration' in str(item.fspath):
            item.add_marker(skip)


@pytest.fixture(scope='session')
def database():
    params = parse_mysql_url(os.environ['TEST_MYSQL_URL'])
    admin = mysql.connector.connect(host=params['host'], port=params['port'],
                                    user=params['user'], password=params['password'])
    cursor = admin.cursor()
    cursor.execute(f'DROP DATABASE IF EXISTS {DATABASE}')
    cursor.execute(f'CREATE DATABASE {DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    cursor.execute(f'USE {DATABASE}')
    # Minimal ANSM thesaurus table (the real one comes from an external dump).
    cursor.execute('CREATE TABLE substances (id INT PRIMARY KEY AUTO_INCREMENT, substances VARCHAR(255) NOT NULL)')
    for name in ('006_medication_catalog.sql', '007_auth_prescriber_patients.sql',
                 '008_prescriber_requests_establishments.sql'):
        for statement in split_statements((ROOT / 'migrations' / name).read_text(encoding='utf-8')):
            cursor.execute(statement)
    admin.commit()
    admin.close()

    DatabasePool.close()
    DatabasePool.initialize(host=params['host'], port=params['port'], user=params['user'],
                            password=params['password'], database=DATABASE,
                            pool_size=3, pool_name='iam_it_pool')

    from app.services.auth import AuthService
    from app.services.patient import PatientService
    from app.services.schema import SchemaMigrator

    AuthService.ensure_schema()
    PatientService.ensure_schema()
    SchemaMigrator.apply_pending()
    yield DatabasePool
    DatabasePool.close()


@pytest.fixture
def db(database):
    """Each test starts from empty data tables (schema kept)."""
    with DatabasePool.get_cursor() as cursor:
        cursor.execute('SET FOREIGN_KEY_CHECKS = 0')
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s AND table_type = 'BASE TABLE' AND table_name <> 'schema_migrations'",
            (DATABASE,),
        )
        for (table,) in cursor.fetchall():
            cursor.execute(f'TRUNCATE TABLE `{table}`')
        cursor.execute('SET FOREIGN_KEY_CHECKS = 1')
    return database


@pytest.fixture
def prescriber(db):
    return make_user(db, 'prescriber', 'awa.prescriptrice@example.org')


@pytest.fixture
def other_prescriber(db):
    return make_user(db, 'prescriber', 'kossi.prescripteur@example.org')


def make_user(db, role, email):
    with DatabasePool.get_cursor() as cursor:
        cursor.execute(
            "INSERT INTO iam_users (email, password_hash, role, status, first_name, last_name, profession) "
            "VALUES (%s, 'x', %s, 'approved', 'Test', 'User', 'Médecin')",
            (email, role),
        )
        return cursor.lastrowid
