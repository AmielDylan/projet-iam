"""Medication catalog services (analysis lives in app/services/analysis.py)."""
from __future__ import annotations

import re
from typing import Any

from mysql.connector import Error

from app.services.database import DatabasePool


# Forms that do not identify the product: none, or GEL (written for gels and for gélules alike).
UNRELIABLE_FORMS = {"", "GEL"}


class MedicationCatalogService:
    """Search and analyze the V3 enriched medication catalog."""

    @staticmethod
    def search(query: str, limit: int = 12) -> list[dict[str, Any]]:
        """Search medication catalog by trade name, substance, or normalized specialty."""
        query = (query or "").strip()
        if not query:
            return []

        # Every word must appear in the name, the dosage, the DCI or the specialty:
        # "doliprane 1000" finds DOLIPRANE 1000MG, "paracetamol 1000" finds every 1 g paracetamol.
        words = [word for word in query.split() if word][:6]
        haystack = "CONCAT_WS(' ', nom_medicament, dosage, substances, specialite)"
        conditions = []
        word_params: list[str] = []
        for word in words:
            variants = dosage_variants(word)
            if variants == [word]:
                conditions.append(f"{haystack} LIKE %s")
                word_params.append(f"%{word}%")
            else:
                # A dosage must start a number: "1G" matches "1G" or "1G | 5,4G", never "81G".
                conditions.append("(" + " OR ".join([f"{haystack} REGEXP %s"] * len(variants)) + ")")
                word_params += [f"(^|[^0-9.,]){re.escape(variant)}" for variant in variants]
        conditions = " AND ".join(conditions)
        starts_pattern = f"{words[0]}%"
        sql = f"""
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
            WHERE {conditions}
            ORDER BY
                CASE
                    WHEN nom_medicament LIKE %s THEN 0
                    WHEN specialite LIKE %s THEN 1
                    ELSE 2
                END,
                nom_medicament ASC,
                dosage ASC
            LIMIT %s
        """
        try:
            rows = DatabasePool.execute_query(
                sql,
                (*word_params, starts_pattern, starts_pattern, limit),
                dictionary=True,
            )
        except Error:
            return []

        results = [MedicationCatalogService._serialize_catalog_row(row) for row in rows]
        if not results:
            MedicationCatalogService.log_search_miss(query)
        MedicationCatalogService._add_labels(results)
        return results

    @staticmethod
    def _add_labels(results: list[dict[str, Any]]) -> None:
        """Give `label` (the full product name) to results that name, dosage and form cannot tell apart.

        The catalog files DOLIPRANE 1G CPR 8 and DOLIPRANE 1G CPR EFF 8 both as DOLIPRANE, 1G, COMPRIMÉ,
        and writes no form or the ambiguous GEL (gel or gélule) for many products: those carry their
        full name, on screen and on the printed ordonnance, so that the pharmacist delivers the right one.
        """
        for item in results:
            item["label"] = item["specialite"] if item["form"].upper() in UNRELIABLE_FORMS else ""
        names = sorted({item["name"] for item in results if item["name"] and not item["label"]})
        if not names:
            return
        try:
            rows = DatabasePool.execute_query(
                f"""
                SELECT nom_medicament, IFNULL(dosage, ''), IFNULL(forme_galenique, '')
                FROM medication_catalog
                WHERE nom_medicament IN ({', '.join(['%s'] * len(names))})
                GROUP BY nom_medicament, IFNULL(dosage, ''), IFNULL(forme_galenique, '')
                HAVING COUNT(DISTINCT specialite) > 1
                """,
                tuple(names),
            )
        except Error:
            return
        shared = {tuple(row) for row in rows}
        for item in results:
            if not item["label"] and (item["name"], item["dosage"], item["form"]) in shared:
                item["label"] = item["specialite"]

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


def dosage_variants(word: str) -> list[str]:
    """The catalog writes 1 g as "1G": "1000", "1000mg" and "1g" must find each other."""
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(mg|g)?", word.strip().lower())
    if not match:
        return [word]
    value = float(match.group(1).replace(",", "."))
    milligrams = value * 1000 if match.group(2) == "g" else value
    variants = {word}
    if milligrams >= 1000 and milligrams % 1000 == 0:
        variants.add(f"{int(milligrams // 1000)}G")
    if milligrams.is_integer():
        variants.add(f"{int(milligrams)}MG")
    return sorted(variants)
