"""Medication catalog and prescription analysis services."""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any

from mysql.connector import Error

from app.services.database import DatabasePool
from app.services.interaction import InteractionService


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
    def analyze_prescription(items: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze all medication pairs in a prescription draft."""
        normalized_items = [MedicationCatalogService._normalize_prescription_item(item, idx) for idx, item in enumerate(items)]
        alerts: list[dict[str, Any]] = []
        interactions: list[dict[str, Any]] = []

        for item in normalized_items:
            if not item["substances"]:
                alerts.append({
                    "type": "unknown_medication",
                    "severity": "info",
                    "message": f"{item['name']} n'est pas identifié dans la base d'analyse IAM.",
                    "item_ids": [item["client_id"]],
                    "can_override": True,
                })

        for first, second in combinations(normalized_items, 2):
            pair_interactions = MedicationCatalogService._interactions_for_items(first, second)
            for interaction in pair_interactions:
                interactions.append(interaction)
                alerts.append({
                    "type": "interaction",
                    "severity": MedicationCatalogService._severity_from_niveau(interaction.get("niveau")),
                    "message": f"Interaction entre {first['name']} et {second['name']}: {interaction.get('niveau') or 'niveau non précisé'}",
                    "item_ids": [first["client_id"], second["client_id"]],
                    "interaction": interaction,
                    "can_override": True,
                })

        alerts.extend(MedicationCatalogService._duplicate_class_alerts(normalized_items))

        return {
            "success": True,
            "items": normalized_items,
            "alerts": alerts,
            "interactions": interactions,
            "summary": {
                "items_count": len(normalized_items),
                "alerts_count": len(alerts),
                "interactions_count": len(interactions),
                "can_print": True,
            },
        }

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

    @staticmethod
    def _normalize_prescription_item(item: dict[str, Any], index: int) -> dict[str, Any]:
        catalog_item = None
        medication_id = item.get("medication_id") or item.get("id")
        if medication_id:
            try:
                catalog_item = MedicationCatalogService.get(int(medication_id))
            except (TypeError, ValueError):
                catalog_item = None

        substances = item.get("substances") or []
        if isinstance(substances, str):
            substances = MedicationCatalogService.split_substances(substances)
        if catalog_item and not substances:
            substances = catalog_item["substances"]

        name = (
            item.get("name")
            or item.get("nom_medicament")
            or (catalog_item or {}).get("name")
            or f"Médicament {index + 1}"
        )

        return {
            "client_id": item.get("client_id") or item.get("uid") or f"item-{index + 1}",
            "medication_id": medication_id,
            "name": str(name).strip(),
            "dosage": item.get("dosage") or (catalog_item or {}).get("dosage") or "",
            "form": item.get("form") or item.get("forme_galenique") or (catalog_item or {}).get("form") or "",
            "posology": item.get("posology") or item.get("posologie") or "",
            "box_count": item.get("box_count") or item.get("quantite_boites") or (catalog_item or {}).get("box_count"),
            "qsp": item.get("qsp") or "",
            "renewal": item.get("renewal") or item.get("ar") or "",
            "note": item.get("note") or "",
            "substances": [str(substance).strip() for substance in substances if str(substance).strip()],
            "is_free_text": bool(item.get("is_free_text")) or catalog_item is None,
            "is_known_catalog": catalog_item is not None,
            "is_known_iam": bool((catalog_item or {}).get("is_known")),
        }

    @staticmethod
    def _interactions_for_items(first: dict[str, Any], second: dict[str, Any]) -> list[dict[str, Any]]:
        seen = set()
        interactions = []
        for substance_1 in first["substances"]:
            for substance_2 in second["substances"]:
                try:
                    pair_results = InteractionService.get_interactions(substance_1, substance_2)
                except Exception:
                    pair_results = []
                for result in pair_results:
                    key = (
                        frozenset([result.get("class_1"), result.get("class_2")]),
                        result.get("niveau"),
                        result.get("details"),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    enriched = dict(result)
                    enriched["source_substances"] = [substance_1, substance_2]
                    enriched["item_names"] = [first["name"], second["name"]]
                    interactions.append(enriched)
        return interactions

    @staticmethod
    def _duplicate_class_alerts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        class_to_items: dict[str, set[str]] = defaultdict(set)
        for item in items:
            for substance in item["substances"]:
                try:
                    classes = InteractionService.get_classes_from_substance(substance.upper())
                except Exception:
                    classes = []
                for class_name in classes:
                    class_to_items[class_name].add(item["client_id"])

        alerts = []
        for class_name, item_ids in class_to_items.items():
            if len(item_ids) > 1:
                alerts.append({
                    "type": "therapeutic_duplicate",
                    "severity": "warning",
                    "message": f"Doublon thérapeutique possible: {class_name}.",
                    "item_ids": sorted(item_ids),
                    "can_override": True,
                })
        return alerts

    @staticmethod
    def _severity_from_niveau(niveau: str | None) -> str:
        value = strip_accents(niveau or "").upper()
        if "CONTRE" in value or re_search_word(value, "CI"):
            return "critical"
        if "DECONSEIL" in value or "ASDEC" in value:
            return "major"
        if "PRECAUTION" in value or re_search_word(value, "PE"):
            return "moderate"
        return "info"


def re_search_word(value: str, token: str) -> bool:
    """Return true when a short ANSM token appears as a standalone code."""
    import re

    return re.search(rf"(^|[^A-Z0-9]){re.escape(token)}([^A-Z0-9]|$)", value) is not None


def strip_accents(value: str) -> str:
    """Strip accents for severity matching."""
    import unicodedata

    return "".join(char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn")
