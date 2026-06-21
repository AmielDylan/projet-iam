"""Tests for API endpoints."""
import json
import pytest
from unittest.mock import patch, MagicMock


class TestValidateEndpoint:
    """Tests for /api/v1/validate endpoint."""

    def test_validate_valid_medication(self, client, mock_db):
        """Test validation of a valid medication."""
        # Mock the validation result
        mock_db.execute_function.side_effect = [False, True, False]  # is_classe, is_substance, is_specialite
        mock_db.call_procedure.return_value = [(1,)]
        mock_db.call_procedure_with_out.return_value = [1, 'ANTIAGREGANTS']

        with patch('app.services.database.DatabasePool', mock_db):
            response = client.post(
                '/api/v1/validate',
                data=json.dumps({'medication': 'ASPIRINE'}),
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['medication'] == 'ASPIRINE'

    def test_validate_empty_medication(self, client):
        """Test validation with empty medication name."""
        response = client.post(
            '/api/v1/validate',
            data=json.dumps({'medication': ''}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'error' in data

    def test_validate_missing_medication(self, client):
        """Test validation without medication field."""
        response = client.post(
            '/api/v1/validate',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_validate_invalid_characters(self, client):
        """Test validation with invalid characters."""
        response = client.post(
            '/api/v1/validate',
            data=json.dumps({'medication': '<script>alert("xss")</script>'}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestInteractionsEndpoint:
    """Tests for /api/v1/interactions endpoint."""

    def test_get_interactions_success(self, client, mock_db, sample_interaction_data):
        """Test getting interactions between two medications."""
        # Mock the interaction service
        with patch('app.api.routes.InteractionService') as mock_service:
            mock_service.get_interactions.return_value = sample_interaction_data['interactions']

            response = client.post(
                '/api/v1/interactions',
                data=json.dumps({'med_1': 'ASPIRINE', 'med_2': 'WARFARINE'}),
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'interactions' in data
        assert data['count'] == 1

    def test_get_interactions_missing_med1(self, client):
        """Test interactions with missing med_1."""
        response = client.post(
            '/api/v1/interactions',
            data=json.dumps({'med_2': 'WARFARINE'}),
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_get_interactions_missing_med2(self, client):
        """Test interactions with missing med_2."""
        response = client.post(
            '/api/v1/interactions',
            data=json.dumps({'med_1': 'ASPIRINE'}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestAutocompleteEndpoint:
    """Tests for /api/v1/autocomplete endpoint."""

    def test_autocomplete_success(self, client, mock_db, sample_autocomplete_results):
        """Test autocomplete with valid query."""
        with patch('app.services.autocomplete.AutocompleteService.search') as mock_search:
            mock_search.return_value = sample_autocomplete_results

            response = client.get('/api/v1/autocomplete?q=ASP')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]['resultat'] == 'ASPIRINE'

    def test_autocomplete_empty_query(self, client):
        """Test autocomplete with empty query."""
        response = client.get('/api/v1/autocomplete?q=')

        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_autocomplete_no_query(self, client):
        """Test autocomplete without query parameter."""
        response = client.get('/api/v1/autocomplete')

        assert response.status_code == 200
        data = response.get_json()
        assert data == []

    def test_autocomplete_post_method(self, client, mock_db, sample_autocomplete_results):
        """Test autocomplete via POST method."""
        with patch('app.services.autocomplete.AutocompleteService.search') as mock_search:
            mock_search.return_value = sample_autocomplete_results

            response = client.post(
                '/api/v1/autocomplete',
                data=json.dumps({'query': 'ASP'}),
                content_type='application/json'
            )

        assert response.status_code == 200


class TestClassesEndpoint:
    """Tests for /api/v1/classes endpoint."""

    def test_get_classes_success(self, client, mock_db):
        """Test getting classes for a substance."""
        with patch('app.services.interaction.InteractionService.get_classes_from_substance') as mock_method:
            mock_method.return_value = ['ANTIAGREGANTS PLAQUETTAIRES', 'AINS']

            response = client.post(
                '/api/v1/classes',
                data=json.dumps({'substance': 'ASPIRINE'}),
                content_type='application/json'
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'classes' in data
        assert len(data['classes']) == 2

    def test_get_classes_missing_substance(self, client):
        """Test classes endpoint without substance."""
        response = client.post(
            '/api/v1/classes',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestAuthAccountEndpoints:
    """Tests for account request and moderation endpoints."""

    def test_register_pharmacy_request(self, client):
        with patch('app.api.routes.AuthService.create_account_request') as mock_create:
            mock_create.return_value = (True, 'Demande créée.')

            response = client.post('/api/v1/auth/register', json={
                'email': 'pharmacie@example.test',
                'password': 'password123',
                'first_name': 'Pharmacie',
                'last_name': 'IAM',
                'role': 'pharmacy',
            })

        assert response.status_code == 200
        assert response.get_json()['success'] is True
        mock_create.assert_called_once_with(
            'pharmacie@example.test',
            'password123',
            'Pharmacie',
            'IAM',
            'pharmacy',
        )

    def test_account_requests_for_pharmacy_reviewer(self, client):
        with patch('app.api.routes.AuthService.current_user') as mock_user, \
             patch('app.api.routes.AuthService.list_account_requests') as mock_list:
            reviewer = {'id': 2, 'role': 'pharmacy', 'status': 'approved'}
            mock_user.return_value = reviewer
            mock_list.return_value = [{'id': 3, 'role': 'prescriber', 'status': 'pending'}]

            response = client.get('/api/v1/accounts/requests')

        assert response.status_code == 200
        assert response.get_json()['results'][0]['role'] == 'prescriber'
        mock_list.assert_called_once_with(reviewer)

    def test_review_account_requires_login(self, client):
        response = client.post('/api/v1/accounts/3/review', json={'action': 'approve'})

        assert response.status_code == 401
