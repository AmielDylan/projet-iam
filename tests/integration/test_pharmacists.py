"""Pharmacists: waitlist for the pharmacy offer, never access to prescribing."""
import io
from unittest.mock import patch

from app.services.auth import AuthService
from app.services.database import DatabasePool


def register(client, profession, email):
    data = {'email': email, 'first_name': 'Ama', 'last_name': 'Dossou', 'birthdate': '1985-03-02',
            'profession': profession, 'order_number': 'PH-1', 'phone': '+229 90 00 00 00',
            'identity_document': (io.BytesIO(b'%PDF-1.4 test'), 'id.pdf', 'application/pdf')}
    return client.post('/api/v1/auth/register', data=data, content_type='multipart/form-data')


def test_a_pharmacist_request_joins_the_waitlist_without_keeping_the_id_document(client, db):
    response = register(client, 'Pharmacien', 'ama@officine.bj')

    body = response.get_json()
    assert response.status_code == 200 and body['code'] == 'waitlist'
    assert 'officine' in body['message']
    row = DatabasePool.execute_query(
        "SELECT id, role, status FROM iam_users WHERE email = 'ama@officine.bj'", dictionary=True)[0]
    assert (row['role'], row['status']) == ('pharmacist', 'waitlist')
    assert DatabasePool.execute_query('SELECT COUNT(*) FROM identity_documents WHERE user_id = %s', (row['id'],))[0][0] == 0
    reviewer = {'role': 'admin', 'status': 'approved'}
    assert all(r['email'] != 'ama@officine.bj' for r in AuthService.list_account_requests(reviewer))


def test_admin_lists_and_exports_the_waitlist(client, db):
    register(client, 'Pharmacien', 'ama@officine.bj')
    register(client, 'Médecin', 'kofi@clinique.bj')
    admin = {'id': 1, 'role': 'admin', 'status': 'approved', 'must_change_password': 0}
    with patch('app.api.routes.AuthService.current_user', return_value=admin):
        waitlist = client.get('/api/v1/admin/waitlist').get_json()['results']
        csv = client.get('/api/v1/admin/waitlist.csv')

    assert [r['email'] for r in waitlist] == ['ama@officine.bj']
    assert csv.mimetype == 'text/csv'
    text = csv.get_data(as_text=True)
    assert text.startswith('\ufeffemail;')  # BOM so that Excel reads the accents
    assert 'ama@officine.bj' in text and 'kofi@clinique.bj' not in text


def test_a_pharmacist_approved_as_prescriber_by_mistake_still_cannot_prescribe(client, db):
    pharmacist = {'id': 5, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0,
                  'profession': 'Pharmacien'}
    with patch('app.services.auth.AuthService.current_user', return_value=pharmacist):
        api = client.post('/api/v1/ordonnances', json={})
        page = client.get('/ordonnances')

    assert api.status_code == 403 and api.get_json()['code'] == 'profession_not_allowed'
    assert page.status_code == 302
