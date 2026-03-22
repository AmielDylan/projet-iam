"""Input validation for API endpoints."""
import re
from typing import Optional


class ValidationError(Exception):
    """Raised when validation fails."""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


def sanitize_medication_name(name: Optional[str]) -> str:
    """
    Sanitize and validate medication name input.

    Raises:
        ValidationError: If the input is invalid.
    """
    if name is None:
        raise ValidationError("Medication name is required", "medication")

    name = name.strip()

    if not name:
        raise ValidationError("Medication name cannot be empty", "medication")

    if len(name) > 255:
        raise ValidationError("Medication name is too long (max 255 characters)", "medication")

    # Allow letters, numbers, spaces, hyphens, and common pharmaceutical characters
    # Remove potentially dangerous characters
    cleaned = re.sub(r'[<>"\';\\]', '', name)

    if cleaned != name:
        raise ValidationError("Medication name contains invalid characters", "medication")

    return cleaned.upper()


def validate_autocomplete_query(query: Optional[str]) -> str:
    """
    Validate autocomplete search query.

    Raises:
        ValidationError: If the query is invalid.
    """
    if query is None:
        return ""

    query = query.strip()

    if len(query) > 100:
        raise ValidationError("Search query is too long", "query")

    # Remove SQL injection attempts and special characters
    cleaned = re.sub(r'[<>"\';\\%_]', '', query)

    return cleaned
