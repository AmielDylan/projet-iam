"""Schema migrator: apply SQL migrations from 010 onward at application start.

Migrations 001 to 008 were applied by hand on existing databases. From 010
on, each file runs once and is recorded in `schema_migrations`, so a deploy
brings its tables with it. Files must stay idempotent so that a database
migrated by hand is not harmed.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.services.database import DatabasePool


FIRST_AUTOMATIC = 10
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


class SchemaMigrator:
    @staticmethod
    def apply_pending(directory: Path | str = MIGRATIONS_DIR) -> list[str]:
        """Apply the migration files not yet recorded; return their names."""
        files = sorted(
            path for path in Path(directory).glob("*.sql")
            if re.match(r"^\d{3}_", path.name) and int(path.name[:3]) >= FIRST_AUTOMATIC
        )
        applied: list[str] = []
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS `schema_migrations` (
                    `name` VARCHAR(190) PRIMARY KEY,
                    `applied_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute("SELECT name FROM schema_migrations")
            done = {row[0] for row in cursor.fetchall()}
            for path in files:
                if path.name in done:
                    continue
                for statement in split_statements(path.read_text(encoding="utf-8")):
                    cursor.execute(statement)
                cursor.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
                applied.append(path.name)
        return applied


def split_statements(sql: str) -> list[str]:
    """Split a SQL file into statements, honouring DELIMITER blocks."""
    statements: list[str] = []
    delimiter = ";"
    buffer: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not buffer and (not stripped or stripped.startswith("--")):
            continue
        if stripped.upper().startswith("DELIMITER "):
            delimiter = stripped.split(None, 1)[1]
            continue
        buffer.append(line)
        if stripped.endswith(delimiter):
            text = "\n".join(buffer).strip()
            statements.append(text[: -len(delimiter)].strip())
            buffer = []
    if "\n".join(buffer).strip():
        statements.append("\n".join(buffer).strip())
    return [_dedent(statement) for statement in statements if statement]


def _dedent(statement: str) -> str:
    lines = statement.splitlines()
    if len(lines) == 1:
        return lines[0].strip()
    return "\n".join(line.rstrip() for line in lines).strip()
