"""Session lock after 10 minutes of inactivity."""
import time

from werkzeug.security import generate_password_hash

from app.services.database import DatabasePool
from app.services.ordonnance import OrdonnanceService


def login_as(client, user_id, idle_seconds=0):
    with client.session_transaction() as sess:
        sess.update({'user_id': user_id, 'email': 'x', 'role': 'prescriber', 'status': 'approved',
                     'must_change_password': False, 'last_activity': int(time.time()) - idle_seconds})


def set_password(user_id, password):
    with DatabasePool.get_cursor() as cursor:
        cursor.execute('UPDATE iam_users SET password_hash = %s WHERE id = %s',
                       (generate_password_hash(password), user_id))


def test_active_session_works_and_idle_session_is_locked(client, prescriber):
    draft = OrdonnanceService.create_draft(prescriber)
    login_as(client, prescriber, idle_seconds=60)
    assert client.get(f"/api/v1/ordonnances/{draft['id']}").status_code == 200

    login_as(client, prescriber, idle_seconds=11 * 60)
    locked = client.get(f"/api/v1/ordonnances/{draft['id']}")
    assert locked.status_code == 423 and locked.get_json()['code'] == 'session_locked'
    assert client.get('/api/v1/auth/session').get_json() == {'success': True, 'locked': True, 'user': None}
    page = client.get(f"/ordonnances/{draft['id']}/impression")
    assert page.status_code == 302 and 'locked=1' in page.headers['Location']


def test_unlock_with_password_resumes_the_same_draft(client, prescriber):
    set_password(prescriber, 'bon-mot-de-passe')
    draft = OrdonnanceService.create_draft(prescriber)
    login_as(client, prescriber, idle_seconds=11 * 60)
    client.get('/api/v1/ordonnances')  # triggers the lock

    assert client.post('/api/v1/auth/unlock', json={'password': 'faux'}).status_code == 401
    assert client.get('/api/v1/ordonnances').status_code == 423
    assert client.post('/api/v1/auth/unlock', json={'password': 'bon-mot-de-passe'}).status_code == 200
    resumed = client.get(f"/api/v1/ordonnances/{draft['id']}")
    assert resumed.status_code == 200 and resumed.get_json()['ordonnance']['version'] == 1


def test_another_user_can_log_in_and_replaces_the_locked_session(client, prescriber, other_prescriber):
    set_password(other_prescriber, 'autre-mot-de-passe')
    login_as(client, prescriber, idle_seconds=11 * 60)
    client.get('/api/v1/ordonnances')

    response = client.post('/api/v1/auth/login', json={'email': 'kossi.prescripteur@example.org',
                                                       'password': 'autre-mot-de-passe'})
    assert response.status_code == 200
    session = client.get('/api/v1/auth/session').get_json()
    assert session['locked'] is False and session['user']['id'] == other_prescriber
