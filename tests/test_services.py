"""Tests for service layer."""
import pytest
from unittest.mock import patch, MagicMock

from app.services.interaction import InteractionService, MedicationType
from app.services.autocomplete import AutocompleteService
from app.api.validators import (
    sanitize_medication_name,
    validate_autocomplete_query,
    ValidationError
)


class TestMedicationType:
    """Tests for MedicationType dataclass."""

    def test_is_valid_classe(self):
        """Test is_valid for classe type."""
        med_type = MedicationType(is_classe=True, is_substance=False, is_specialite=False)
        assert med_type.is_valid is True
        assert med_type.type_name == 'classe'

    def test_is_valid_substance(self):
        """Test is_valid for substance type."""
        med_type = MedicationType(is_classe=False, is_substance=True, is_specialite=False)
        assert med_type.is_valid is True
        assert med_type.type_name == 'substance'

    def test_is_valid_specialite(self):
        """Test is_valid for specialite type."""
        med_type = MedicationType(is_classe=False, is_substance=False, is_specialite=True)
        assert med_type.is_valid is True
        assert med_type.type_name == 'specialite'

    def test_is_invalid(self):
        """Test is_valid for invalid type."""
        med_type = MedicationType(is_classe=False, is_substance=False, is_specialite=False)
        assert med_type.is_valid is False
        assert med_type.type_name == 'unknown'

    def test_multiple_types(self):
        """Test medication that matches multiple types."""
        med_type = MedicationType(is_classe=True, is_substance=True, is_specialite=False)
        assert med_type.is_valid is True
        # Classe takes priority
        assert med_type.type_name == 'classe'


class TestInteractionService:
    """Tests for InteractionService."""

    @patch('app.services.database.DatabasePool.execute_function')
    def test_validate_medication_classe(self, mock_execute):
        """Test validation of a classe."""
        mock_execute.side_effect = [1, 0, 0]  # is_classe=True, others=False

        result = InteractionService.validate_medication('ANTICOAGULANTS')

        assert result.is_classe is True
        assert result.is_substance is False
        assert result.is_specialite is False
        assert result.type_name == 'classe'

    @patch('app.services.database.DatabasePool.execute_function')
    def test_validate_medication_legacy_string_return(self, mock_execute):
        """Test validation with legacy string return values."""
        mock_execute.side_effect = ['False', 'True', 'False']

        result = InteractionService.validate_medication('ASPIRINE')

        assert result.is_classe is False
        assert result.is_substance is True
        assert result.is_specialite is False

    @patch('app.services.database.DatabasePool.call_procedure')
    @patch('app.services.database.DatabasePool.call_procedure_with_out')
    def test_get_classes_from_substance(self, mock_proc_out, mock_proc):
        """Test getting classes from a substance."""
        mock_proc.return_value = [(1,), (2,)]
        mock_proc_out.side_effect = [
            [1, 'ANTIAGREGANTS'],
            [2, 'AINS']
        ]

        result = InteractionService.get_classes_from_substance('ASPIRINE')

        assert len(result) == 2
        assert 'ANTIAGREGANTS' in result
        assert 'AINS' in result


class TestAutocompleteService:
    """Tests for AutocompleteService."""

    @patch('app.services.database.DatabasePool.execute_query')
    def test_search_returns_results(self, mock_query):
        """Test search with results."""
        mock_query.return_value = [
            ('ASPIRINE', 'substance'),
            ('ASPEGIC', 'specialite')
        ]

        results = AutocompleteService.search('ASP')

        assert len(results) == 2
        assert results[0]['resultat'] == 'ASPIRINE'
        assert results[0]['type'] == 'substance'

    def test_search_empty_query(self):
        """Test search with empty query."""
        results = AutocompleteService.search('')
        assert results == []

    def test_search_whitespace_query(self):
        """Test search with whitespace query."""
        results = AutocompleteService.search('   ')
        assert results == []


class TestValidators:
    """Tests for input validators."""

    def test_sanitize_valid_name(self):
        """Test sanitization of valid medication name."""
        result = sanitize_medication_name('aspirine')
        assert result == 'ASPIRINE'

    def test_sanitize_with_spaces(self):
        """Test sanitization preserves spaces."""
        result = sanitize_medication_name('aspirine upsa')
        assert result == 'ASPIRINE UPSA'

    def test_sanitize_strips_whitespace(self):
        """Test sanitization strips leading/trailing whitespace."""
        result = sanitize_medication_name('  aspirine  ')
        assert result == 'ASPIRINE'

    def test_sanitize_empty_raises(self):
        """Test sanitization raises for empty input."""
        with pytest.raises(ValidationError):
            sanitize_medication_name('')

    def test_sanitize_none_raises(self):
        """Test sanitization raises for None input."""
        with pytest.raises(ValidationError):
            sanitize_medication_name(None)

    def test_sanitize_invalid_chars_raises(self):
        """Test sanitization raises for invalid characters."""
        with pytest.raises(ValidationError):
            sanitize_medication_name('<script>')

    def test_sanitize_too_long_raises(self):
        """Test sanitization raises for too long input."""
        with pytest.raises(ValidationError):
            sanitize_medication_name('A' * 300)

    def test_validate_autocomplete_query(self):
        """Test autocomplete query validation."""
        result = validate_autocomplete_query('asp')
        assert result == 'asp'

    def test_validate_autocomplete_empty(self):
        """Test autocomplete validation with empty string."""
        result = validate_autocomplete_query('')
        assert result == ''

    def test_validate_autocomplete_none(self):
        """Test autocomplete validation with None."""
        result = validate_autocomplete_query(None)
        assert result == ''

    def test_validate_autocomplete_strips_sql_chars(self):
        """Test autocomplete strips SQL injection characters."""
        result = validate_autocomplete_query("asp'; DROP TABLE--")
        # Should remove dangerous characters
        assert "'" not in result
        assert ";" not in result

    def test_validate_autocomplete_too_long_raises(self):
        """Test autocomplete validation raises for too long query."""
        with pytest.raises(ValidationError):
            validate_autocomplete_query('A' * 200)
