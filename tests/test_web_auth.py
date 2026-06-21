"""Tests for web authentication routes."""
from unittest.mock import patch


class TestWebLogin:
    """Regression tests for role-aware login redirects."""

    def test_admin_login_redirects_to_admin_page(self, client):
        with patch('app.web.routes.AuthService.authenticate') as mock_auth, \
             patch('app.web.routes.AuthService.current_user') as mock_user:
            mock_auth.return_value = (True, 'Connexion réussie.')
            mock_user.return_value = {'id': 3, 'role': 'admin', 'status': 'approved'}

            response = client.post('/connexion', data={
                'email': 'iarappbj@gmail.com',
                'password': 'temporary-password',
            })

        assert response.status_code == 302
        assert response.headers['Location'].endswith('/admin')

    def test_prescriber_login_redirects_to_prescriptions_page(self, client):
        with patch('app.web.routes.AuthService.authenticate') as mock_auth, \
             patch('app.web.routes.AuthService.current_user') as mock_user:
            mock_auth.return_value = (True, 'Connexion réussie.')
            mock_user.return_value = {'id': 4, 'role': 'prescriber', 'status': 'approved'}

            response = client.post('/connexion', data={
                'email': 'prescriber@example.test',
                'password': 'temporary-password',
            })

        assert response.status_code == 302
        assert response.headers['Location'].endswith('/ordonnances')

    def test_login_respects_next_parameter(self, client):
        with patch('app.web.routes.AuthService.authenticate') as mock_auth, \
             patch('app.web.routes.AuthService.current_user') as mock_user:
            mock_auth.return_value = (True, 'Connexion réussie.')
            mock_user.return_value = {'id': 3, 'role': 'admin', 'status': 'approved'}

            response = client.post('/connexion?next=/admin', data={
                'email': 'iarappbj@gmail.com',
                'password': 'temporary-password',
            })

        assert response.status_code == 302
        assert response.headers['Location'].endswith('/admin')
