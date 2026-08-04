"""Tests for service layer."""
from io import BytesIO
import pytest
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import FileStorage

from app.services.auth import AuthService, EstablishmentService
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


class TestAuthV32:
    """Tests for V3.2 account verification helpers."""

    def test_validate_identity_document_accepts_pdf(self, app):
        with app.app_context():
            file_storage = FileStorage(
                stream=BytesIO(b'%PDF-1.4'),
                filename='piece.pdf',
                content_type='application/pdf',
            )

            document, error = AuthService.validate_identity_document(file_storage)

        assert error is None
        assert document['filename'] == 'piece.pdf'
        assert document['mime_type'] == 'application/pdf'
        assert document['content'] != b'%PDF-1.4'

    def test_validate_identity_document_rejects_bad_mime(self, app):
        with app.app_context():
            file_storage = FileStorage(
                stream=BytesIO(b'hello'),
                filename='piece.txt',
                content_type='text/plain',
            )

            document, error = AuthService.validate_identity_document(file_storage)

        assert document is None
        assert 'Format' in error

    @patch('app.services.auth.DatabasePool.execute_query')
    def test_get_identity_document_decodes_base64_content(self, mock_query):
        import base64

        mock_query.return_value = [{
            'filename': 'piece.pdf',
            'mime_type': 'application/pdf',
            'size_bytes': 8,
            'content': base64.b64encode(b'%PDF-1.4').decode('ascii'),
            'status': 'pending',
        }]

        document = AuthService.get_identity_document(2)

        assert document['content'] == b'%PDF-1.4'

    def test_create_account_request_reports_missing_fields(self):
        success, message, extra = AuthService.create_account_request(
            email='doc@example.test',
            first_name='Jean',
            last_name='ADJOVI',
        )

        assert success is False
        assert "champs" in message
        assert extra['error_source'] == 'missing_required_fields'
        assert 'phone' in extra['fields']

    @patch('app.services.auth.EmailService.send')
    @patch('app.services.auth.AuthService.get_user')
    @patch('app.services.auth.DatabasePool.get_cursor')
    def test_review_account_approves_with_email_and_deletes_document(self, mock_cursor_cm, mock_get_user, mock_send):
        reviewer = {'id': 1, 'role': 'admin', 'status': 'approved'}
        mock_get_user.return_value = {
            'id': 2,
            'email': 'doc@example.test',
            'role': 'prescriber',
            'status': 'pending',
        }
        cursor = MagicMock()
        mock_cursor_cm.return_value.__enter__.return_value = cursor

        success, message, extra = AuthService.review_account(2, reviewer, True)

        assert success is True
        assert 'envoyé' in message
        assert extra is None
        mock_send.assert_called_once()
        assert any('DELETE FROM identity_documents' in call.args[0] for call in cursor.execute.call_args_list)

    @patch('app.services.auth.EmailService.send')
    @patch('app.services.auth.AuthService.get_user')
    @patch('app.services.auth.DatabasePool.get_cursor')
    def test_review_account_approves_with_manual_delivery_when_email_fails(self, mock_cursor_cm, mock_get_user, mock_send):
        from app.services.email import EmailDeliveryError

        reviewer = {'id': 1, 'role': 'admin', 'status': 'approved'}
        mock_get_user.return_value = {
            'id': 2,
            'email': 'doc@example.test',
            'role': 'prescriber',
            'status': 'pending',
            'first_name': 'Jean',
            'last_name': 'ADJOVI',
        }
        mock_send.side_effect = EmailDeliveryError('SMTP non configuré')
        cursor = MagicMock()
        mock_cursor_cm.return_value.__enter__.return_value = cursor

        success, message, extra = AuthService.review_account(2, reviewer, True)

        assert success is True
        assert 'SMTP indisponible' in message
        assert extra['manual_delivery']['email'] == 'doc@example.test'
        assert 'Mot de passe temporaire:' in extra['manual_delivery']['text']
        assert any('UPDATE iam_users' in call.args[0] for call in cursor.execute.call_args_list)
        assert any('DELETE FROM identity_documents' in call.args[0] for call in cursor.execute.call_args_list)

    @patch('app.services.auth.DatabasePool.execute_query')
    def test_list_account_requests_declares_iam_users_alias(self, mock_query):
        mock_query.return_value = []

        AuthService.list_account_requests({'id': 1, 'role': 'admin', 'status': 'approved'})

        sql = mock_query.call_args.args[0]
        assert 'FROM iam_users u' in sql
        assert 'LEFT JOIN identity_documents d ON d.user_id = u.id' in sql


class TestEstablishmentService:
    """Tests for prescriber establishment helpers."""

    @patch('app.services.auth.DatabasePool.execute_query')
    def test_list_for_prescriber_serializes_flags(self, mock_query):
        mock_query.return_value = [{
            'id': 1,
            'name': 'Clinique IAM',
            'type': 'Clinique',
            'address': 'Cotonou',
            'phone': None,
            'email': None,
            'identifier_label': None,
            'identifier_value': None,
            'secondary_identifier_label': None,
            'secondary_identifier_value': None,
            'free_text': None,
            'logo_filename': None,
            'logo_mime_type': None,
            'logo_size_bytes': None,
            'has_logo': 0,
            'is_active': 1,
        }]

        results = EstablishmentService.list_for_prescriber(3)

        assert results[0]['name'] == 'Clinique IAM'
        assert results[0]['is_active'] is True
        assert results[0]['has_logo'] is False
