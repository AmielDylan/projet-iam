"""Tests for API endpoints."""
from io import BytesIO
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

    def test_login_returns_session_user(self, client):
        with patch('app.api.routes.AuthService.authenticate') as mock_auth, \
             patch('app.api.routes.AuthService.current_session_user') as mock_session_user:
            mock_auth.return_value = (True, 'Connexion réussie.')
            mock_session_user.return_value = {
                'id': 3,
                'email': 'iarappbj@gmail.com',
                'role': 'admin',
                'status': 'approved',
            }

            response = client.post('/api/v1/auth/login', json={
                'email': 'iarappbj@gmail.com',
                'password': 'temporary-password',
            })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['user']['role'] == 'admin'
        mock_session_user.assert_called_once_with()

    def test_register_prescriber_request(self, client):
        with patch('app.api.routes.AuthService.create_account_request') as mock_create:
            mock_create.return_value = (True, 'Demande créée.')

            response = client.post('/api/v1/auth/register', data={
                'email': 'prescripteur@example.test',
                'first_name': 'Jean',
                'last_name': 'ADJOVI',
                'birthdate': '1980-01-02',
                'profession': 'Médecin',
                'order_number': 'BJ-123',
                'phone': '+22901020304',
                'identity_document': (BytesIO(b'%PDF-1.4'), 'piece.pdf'),
            }, content_type='multipart/form-data')

        assert response.status_code == 200
        assert response.get_json()['success'] is True
        mock_create.assert_called_once_with(
            'prescripteur@example.test',
            '',
            'Jean',
            'ADJOVI',
            'prescriber',
            '1980-01-02',
            'Médecin',
            'BJ-123',
            '+22901020304',
            mock_create.call_args.args[-1],
        )

    def test_register_prescriber_request_returns_error_source(self, client):
        with patch('app.api.routes.AuthService.create_account_request') as mock_create:
            mock_create.return_value = (
                False,
                "Tous les champs d'identité prescripteur sont requis.",
                {'error_source': 'missing_required_fields', 'fields': ['phone']},
            )

            response = client.post('/api/v1/auth/register', data={
                'email': 'prescripteur@example.test',
                'first_name': 'Jean',
                'last_name': 'ADJOVI',
            }, content_type='multipart/form-data')

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error_source'] == 'missing_required_fields'
        assert data['fields'] == ['phone']

    def test_account_requests_for_admin_reviewer(self, client):
        with patch('app.api.routes.AuthService.current_user') as mock_user, \
             patch('app.api.routes.AuthService.list_account_requests') as mock_list:
            reviewer = {'id': 2, 'role': 'admin', 'status': 'approved'}
            mock_user.return_value = reviewer
            mock_list.return_value = [{'id': 3, 'role': 'prescriber', 'status': 'pending'}]

            response = client.get('/api/v1/accounts/requests')

        assert response.status_code == 200
        assert response.get_json()['results'][0]['role'] == 'prescriber'
        mock_list.assert_called_once_with(reviewer)

    def test_review_account_requires_login(self, client):
        response = client.post('/api/v1/accounts/3/review', json={'action': 'approve'})

        assert response.status_code == 401

    def test_review_account_returns_manual_delivery(self, client):
        with patch('app.api.routes.AuthService.current_user') as mock_user, \
             patch('app.api.routes.AuthService.review_account') as mock_review:
            mock_user.return_value = {'id': 1, 'role': 'admin', 'status': 'approved'}
            mock_review.return_value = (
                True,
                'Demande acceptée. SMTP indisponible: copiez le message de transmission.',
                {'manual_delivery': {'email': 'doc@example.test', 'text': 'Message à envoyer'}},
            )

            response = client.post('/api/v1/accounts/3/review', json={'action': 'approve'})

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['manual_delivery']['email'] == 'doc@example.test'

    def test_change_password_requires_login(self, client):
        response = client.post('/api/v1/auth/change-password', json={
            'current_password': 'temporary',
            'new_password': 'new-password',
        })

        assert response.status_code == 401

    def test_prescriber_establishments_list(self, client):
        with patch('app.api.routes.AuthService.current_user') as mock_user, \
             patch('app.api.routes.EstablishmentService.list_for_prescriber') as mock_list:
            mock_user.return_value = {'id': 4, 'role': 'prescriber', 'status': 'approved'}
            mock_list.return_value = [{'id': 1, 'name': 'Clinique IAM'}]

            response = client.get('/api/v1/prescriber/establishments')

        assert response.status_code == 200
        assert response.get_json()['results'][0]['name'] == 'Clinique IAM'
        mock_list.assert_called_once_with(4, active_only=False)

    def test_admin_establishments_requires_admin(self, client):
        with patch('app.api.routes.AuthService.current_user') as mock_user:
            mock_user.return_value = {'id': 4, 'role': 'prescriber', 'status': 'approved'}

            response = client.get('/api/v1/admin/establishments')

        assert response.status_code == 403
