"""Two-factor authentication: optional in the pilot, required by a global setting."""
from unittest.mock import patch

import pyotp
import pytest
from werkzeug.security import generate_password_hash

from app.services.database import DatabasePool

EMAIL = 'awa.prescriptrice@example.org'
PASSWORD = 'mot-de-passe-solide'


@pytest.fixture
def account(prescriber):
    with DatabasePool.get_cursor() as cursor:
        cursor.execute('UPDATE iam_users SET password_hash = %s WHERE id = %s',
                       (generate_password_hash(PASSWORD), prescriber))
    return prescriber


def login(client):
    return client.post('/api/v1/auth/login', json={'email': EMAIL, 'password': PASSWORD})


def enroll(client):
    """Log in, set up and confirm 2FA; return (totp, recovery codes)."""
    login(client)
    setup = client.post('/api/v1/auth/2fa/setup').get_json()
    totp = pyotp.TOTP(setup['secret'])
    assert setup['otpauth_uri'].startswith('otpauth://totp/')
    confirm = client.post('/api/v1/auth/2fa/confirm', json={'code': totp.now()}).get_json()
    client.post('/api/v1/auth/logout')
    return totp, confirm['recovery_codes']


def test_enrolment_shows_ten_recovery_codes_once_and_stores_no_clear_secret(client, account):
    totp, codes = enroll(client)
    assert len(codes) == 10 and len(set(codes)) == 10
    stored = DatabasePool.execute_query('SELECT secret FROM user_two_factor WHERE user_id = %s', (account,))[0][0]
    assert totp.secret not in stored
    hashes = [row[0] for row in DatabasePool.execute_query('SELECT code_hash FROM user_recovery_codes')]
    assert not set(codes) & set(hashes)


def test_wrong_confirmation_code_does_not_enable(client, account):
    login(client)
    client.post('/api/v1/auth/2fa/setup')
    assert client.post('/api/v1/auth/2fa/confirm', json={'code': '000000'}).status_code == 400
    assert client.get('/api/v1/auth/2fa').get_json()['enabled'] is False


def test_login_waits_for_the_code_before_any_access(client, account):
    totp, _ = enroll(client)
    response = login(client)
    assert response.get_json()['two_factor_required'] is True

    blocked = client.get('/api/v1/ordonnances')
    assert blocked.status_code == 401 and blocked.get_json()['code'] == 'two_factor_required'
    assert client.post('/api/v1/auth/2fa/verify', json={'code': '123456'}).status_code == 401
    with patch('app.services.two_factor.TwoFactor._last_timestep', return_value=None):
        assert client.post('/api/v1/auth/2fa/verify', json={'code': totp.now()}).status_code == 200
    assert client.get('/api/v1/ordonnances').status_code == 200


def test_a_code_cannot_be_replayed(client, account):
    totp, _ = enroll(client)
    login(client)
    code = totp.now()
    first = client.post('/api/v1/auth/2fa/verify', json={'code': code})
    client.post('/api/v1/auth/logout')
    login(client)
    second = client.post('/api/v1/auth/2fa/verify', json={'code': code})
    assert first.status_code == 200 or second.status_code == 401
    assert not (first.status_code == 200 and second.status_code == 200)


def test_recovery_code_works_once(client, account):
    _, codes = enroll(client)
    login(client)
    assert client.post('/api/v1/auth/2fa/verify', json={'recovery_code': codes[0]}).status_code == 200
    client.post('/api/v1/auth/logout')
    login(client)
    assert client.post('/api/v1/auth/2fa/verify', json={'recovery_code': codes[0]}).status_code == 401


def test_global_setting_requires_enrolment_first(client, account, monkeypatch):
    monkeypatch.setenv('TWO_FACTOR_REQUIRED', 'true')
    assert login(client).get_json()['two_factor_enrollment_required'] is True
    refused = client.get('/api/v1/ordonnances')
    assert refused.status_code == 403 and refused.get_json()['code'] == 'two_factor_enrollment_required'

    secret = client.post('/api/v1/auth/2fa/setup').get_json()['secret']
    client.post('/api/v1/auth/2fa/confirm', json={'code': pyotp.TOTP(secret).now()})
    assert client.get('/api/v1/ordonnances').status_code == 200


def test_admin_reset_clears_2fa_and_is_logged(client, account):
    enroll(client)
    admin = {'id': 99, 'role': 'admin', 'status': 'approved', 'must_change_password': 0}
    with patch('app.api.routes.AuthService.current_user', return_value=admin):
        assert client.post(f'/api/v1/admin/accounts/{account}/2fa/reset').status_code == 200

    assert login(client).get_json().get('two_factor_required') is not True
    log = DatabasePool.execute_query(
        "SELECT user_id, object_type, object_id, action FROM access_log", dictionary=True)
    assert log == [{'user_id': 99, 'object_type': 'account', 'object_id': account, 'action': 'reset_2fa'}]


def test_web_login_sends_a_2fa_user_to_the_code_page(client, account):
    enroll(client)
    response = client.post('/connexion', data={'email': EMAIL, 'password': PASSWORD})
    assert response.status_code == 302 and '/connexion/verification' in response.headers['Location']
    page = client.get('/connexion/verification')
    assert page.status_code == 200 and 'name="code"' in page.get_data(as_text=True)
