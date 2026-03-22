"""Tests for web routes."""
import pytest
from unittest.mock import patch


class TestHomeRoute:
    """Tests for the home page route."""

    def test_home_get(self, client):
        """Test GET request to home page."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Projet IAM' in response.data

    def test_home_post_with_results(self, client, sample_interaction_data):
        """Test POST request with medication search."""
        with patch('app.web.routes.InteractionService') as mock_service:
            mock_service.get_interactions.return_value = sample_interaction_data['interactions']

            response = client.post('/', data={
                'med-1': 'ASPIRINE',
                'med-2': 'WARFARINE'
            })

        assert response.status_code == 200

    def test_home_post_empty_fields(self, client):
        """Test POST request with empty fields."""
        response = client.post('/', data={
            'med-1': '',
            'med-2': ''
        })

        assert response.status_code == 200
        # Should show error or redirect


class TestLegacyRoutes:
    """Tests for legacy compatibility routes."""

    def test_test_classe_route(self, client):
        """Test legacy testClasse route."""
        with patch('app.web.routes.InteractionService.validate_medication') as mock_validate:
            from app.services.interaction import MedicationType
            mock_validate.return_value = MedicationType(
                is_classe=True,
                is_substance=False,
                is_specialite=False
            )

            response = client.post('/testClasse', data={'medTest': 'ANTICOAGULANTS'})

        assert response.status_code == 200
        assert response.data == b'True'

    def test_test_substance_route(self, client):
        """Test legacy testSubstance route."""
        with patch('app.web.routes.InteractionService.validate_medication') as mock_validate:
            from app.services.interaction import MedicationType
            mock_validate.return_value = MedicationType(
                is_classe=False,
                is_substance=True,
                is_specialite=False
            )

            response = client.post('/testSubstance', data={'medTest': 'ASPIRINE'})

        assert response.status_code == 200
        assert response.data == b'True'

    def test_test_specialite_route(self, client):
        """Test legacy testSpecialite route."""
        with patch('app.web.routes.InteractionService.validate_medication') as mock_validate:
            from app.services.interaction import MedicationType
            mock_validate.return_value = MedicationType(
                is_classe=False,
                is_substance=False,
                is_specialite=True
            )

            response = client.post('/testSpecialite', data={'medTest': 'DOLIPRANE'})

        assert response.status_code == 200
        assert response.data == b'True'

    def test_get_list_classes_route(self, client):
        """Test legacy getListClasses route."""
        with patch('app.web.routes.InteractionService.get_classes_from_substance') as mock_get:
            mock_get.return_value = ['CLASSE1', 'CLASSE2']

            response = client.post('/getListClasses', data={'substance': 'ASPIRINE'})

        assert response.status_code == 200

    def test_autocomplete_input_route(self, client, sample_autocomplete_results):
        """Test legacy autocomplete_input route."""
        with patch('app.services.autocomplete.AutocompleteService.search') as mock_search:
            mock_search.return_value = sample_autocomplete_results

            response = client.post('/autocomplete_input', data={'query': 'ASP'})

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
