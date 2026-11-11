"""Medication catalog services (analysis lives in app/services/analysis.py)."""
from __future__ import annotations

from typing import Any

from mysql.connector import Error

from app.services.database import DatabasePool


class MedicationCatalogService:
    """Search and analyze the V3 enriched medication catalog."""

    @staticmethod
    def search(query: str, limit: int = 12) -> list[dict[str, Any]]:
        """Search medication catalog by trade name, substance, or normalized specialty."""
        query = (query or "").strip()
        if not query:
            return []

        pattern = f"%{query}%"
        starts_pattern = f"{query}%"
        sql = """
            SELECT
                id,
                nom_medicament,
                dosage,
                concentration,
                forme_galenique,
                presentation,
                volume,
                quantite_unites,
                quantite_boites,
                substances,
                specialite,
                iam_specialite_id,
                match_status
            FROM medication_catalog
            WHERE nom_medicament LIKE %s
               OR substances LIKE %s
               OR specialite LIKE %s
            ORDER BY
                CASE
                    WHEN nom_medicament LIKE %s THEN 0
                    WHEN specialite LIKE %s THEN 1
                    ELSE 2
                END,
                nom_medicament ASC
            LIMIT %s
        """
        try:
            rows = DatabasePool.execute_query(
                sql,
                (pattern, pattern, pattern, starts_pattern, starts_pattern, limit),
                dictionary=True,
            )
        except Error:
            return []

        results = [MedicationCatalogService._serialize_catalog_row(row) for row in rows]
        if not results:
            MedicationCatalogService.log_search_miss(query)
        return results

    @staticmethod
    def get(medication_id: int) -> dict[str, Any] | None:
        """Return a medication catalog row by id."""
        try:
            rows = DatabasePool.execute_query(
                """
                SELECT
                    id,
                    nom_medicament,
                    dosage,
                    concentration,
                    forme_galenique,
                    presentation,
                    volume,
                    quantite_unites,
                    quantite_boites,
                    substances,
                    specialite,
                    iam_specialite_id,
                    match_status
                FROM medication_catalog
                WHERE id = %s
                LIMIT 1
                """,
                (medication_id,),
                dictionary=True,
            )
        except Error:
            return None

        if not rows:
            return None
        return MedicationCatalogService._serialize_catalog_row(rows[0])

    @staticmethod
    def log_search_miss(query: str) -> None:
        """Log an unmatched prescription search for future data enrichment."""
        try:
            with DatabasePool.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO medication_search_miss (query, source) VALUES (%s, %s)",
                    (query[:255], "ordonnance"),
                )
        except Error:
            pass

    @staticmethod
    def _serialize_catalog_row(row: dict[str, Any]) -> dict[str, Any]:
        substances = row.get("substances") or ""
        return {
            "id": row.get("id"),
            "name": row.get("nom_medicament") or "",
            "dosage": row.get("dosage") or "",
            "concentration": row.get("concentration") or "",
            "form": row.get("forme_galenique") or "",
            "presentation": row.get("presentation") or "",
            "volume": row.get("volume") or "",
            "box_units": float(row["quantite_unites"]) if row.get("quantite_unites") is not None else None,
            "box_count": float(row["quantite_boites"]) if row.get("quantite_boites") is not None else None,
            "substances": MedicationCatalogService.split_substances(substances),
            "substances_label": substances,
            "specialite": row.get("specialite") or "",
            "is_known": bool(row.get("iam_specialite_id")),
            "match_status": row.get("match_status") or "unmatched",
        }

    @staticmethod
    def split_substances(value: str | None) -> list[str]:
        """Split pipe-separated DCI/substance labels."""
        if not value:
            return []
        return [part.strip() for part in value.split("|") if part and part.strip()]
