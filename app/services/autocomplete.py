"""Autocomplete service for medication search."""
from typing import Optional

from app.services.database import DatabasePool


class AutocompleteService:
    """Service for medication autocomplete functionality."""

    @staticmethod
    def search(query: str, limit: int = 6) -> list[dict]:
        """
        Search for medications matching the query.

        Searches across classes, substances, and specialites.
        """
        if not query or not query.strip():
            return []

        search_query = query.strip()

        sql = """
            SELECT denomination AS resultat, 'classe' AS type
            FROM projet_ipa.classes
            WHERE denomination LIKE %s
            UNION
            SELECT specialites AS resultat, 'specialite' AS type
            FROM projet_ipa.specialites
            WHERE specialites LIKE %s
            UNION
            SELECT substances AS resultat, 'substance' AS type
            FROM projet_ipa.substances
            WHERE substances LIKE %s
            ORDER BY resultat ASC
            LIMIT %s
        """

        pattern = f"{search_query}%"
        results = DatabasePool.execute_query(
            sql,
            (pattern, pattern, pattern, limit),
            dictionary=False
        )

        return [
            {'resultat': row[0], 'type': row[1]}
            for row in results
        ]
