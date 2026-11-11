"""Ordonnance module: the whole life cycle of a prescription.

Draft, then issued (frozen and numbered), then possibly cancelled.
Every rule lives behind this interface; HTTP routes stay thin.
See CONTEXT.md for the vocabulary and .scratch/ordonnance-v4/spec.md for the rules.

Every method takes the prescriber's id first. An ordonnance that does not
belong to that prescriber behaves as if it did not exist.
"""
from __future__ import annotations

from typing import Any


class OrdonnanceService:
    """Create, save, issue, cancel, renew and list a prescriber's ordonnances."""

    @staticmethod
    def create_draft(owner_id: int, origin_id: int | None = None) -> dict[str, Any]:
        """Start a draft, empty or prefilled from an issued ordonnance (renewal)."""
        raise NotImplementedError("Ticket 02")

    @staticmethod
    def save_draft(owner_id: int, ordonnance_id: int, content: dict[str, Any], version: int) -> dict[str, Any]:
        """Save the full draft content; refuse it if another tab saved a newer version."""
        raise NotImplementedError("Ticket 02")

    @staticmethod
    def get(owner_id: int, ordonnance_id: int) -> dict[str, Any] | None:
        """Read one ordonnance: the live draft, or the frozen snapshot once issued."""
        raise NotImplementedError("Ticket 02")

    @staticmethod
    def issue(owner_id: int, ordonnance_id: int) -> dict[str, Any]:
        """Re-run the IAM analysis, then freeze and number the draft, or return the reasons for refusal."""
        raise NotImplementedError("Ticket 04")

    @staticmethod
    def cancel(owner_id: int, ordonnance_id: int, reason: str) -> dict[str, Any]:
        """Cancel an issued ordonnance, keeping the document, the reason and the date."""
        raise NotImplementedError("Ticket 07")

    @staticmethod
    def renew(owner_id: int, ordonnance_id: int) -> dict[str, Any]:
        """Create a new draft linked to, and prefilled from, an issued ordonnance."""
        raise NotImplementedError("Ticket 08")

    @staticmethod
    def list(owner_id: int, status: str | None = None, patient_id: int | None = None) -> list[dict[str, Any]]:
        """List the prescriber's ordonnances, optionally filtered by status or patient."""
        raise NotImplementedError("Ticket 06")
