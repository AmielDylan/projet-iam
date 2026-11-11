"""Referential versions: which ANSM thesaurus and which catalog an analysis used.

Every import records a version (scripts/import_medication_catalog.py for the
catalog, scripts/record_referential.py for the thesaurus). Issued ordonnances
freeze the versions current at issuance.
"""
from __future__ import annotations

from typing import Any

from app.services.database import DatabasePool


KINDS = ("thesaurus", "catalog")


class ReferentialService:
    @staticmethod
    def record(kind: str, label: str, published_on: str | None = None) -> None:
        if kind not in KINDS:
            raise ValueError(f"Référentiel inconnu : {kind}")
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                "INSERT INTO referential_versions (kind, label, published_on) VALUES (%s, %s, %s)",
                (kind, label.strip()[:190], published_on or None),
            )

    @staticmethod
    def current() -> dict[str, Any]:
        """Latest version of each referential, or None when never recorded."""
        current: dict[str, Any] = {kind: None for kind in KINDS}
        rows = DatabasePool.execute_query(
            """
            SELECT r.kind, r.label, r.published_on, r.imported_at
            FROM referential_versions r
            JOIN (SELECT kind, MAX(id) AS id FROM referential_versions GROUP BY kind) latest ON latest.id = r.id
            """,
            dictionary=True,
        )
        for row in rows:
            current[row["kind"]] = {
                "label": row["label"],
                "published_on": row["published_on"].isoformat() if row["published_on"] else None,
                "imported_at": row["imported_at"].isoformat() if row["imported_at"] else None,
            }
        return current
