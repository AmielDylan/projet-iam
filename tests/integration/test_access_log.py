"""Access log: who read or changed which ordonnance or patient, and when. No medical data."""
from unittest.mock import patch

import mysql.connector
import pytest

from app.services.database import DatabasePool
from app.services.ordonnance import OrdonnanceService
from tests.integration.test_issue import ready_draft


def as_user(user_id):
    return patch('app.services.auth.AuthService.current_user',
                 return_value={'id': user_id, 'role': 'prescriber', 'status': 'approved', 'must_change_password': 0})


def log_rows():
    return DatabasePool.execute_query(
        'SELECT user_id, object_type, object_id, action FROM access_log ORDER BY id', dictionary=True)


def test_reads_and_changes_are_traced_on_api_and_print_view(client, prescriber):
    draft = ready_draft(prescriber)
    with as_user(prescriber):
        client.get(f"/api/v1/ordonnances/{draft['id']}")
        client.put(f"/api/v1/ordonnances/{draft['id']}", json={'version': draft['version'], 'content': draft['content']})
        issued = client.post(f"/api/v1/ordonnances/{draft['id']}/issue", json={'version': draft['version'] + 1})
        client.get(f"/ordonnances/{draft['id']}/impression")
        client.get(f"/api/v1/patients/{draft['patient_id']}")
        client.get('/api/v1/patients?q=koffi')

    assert issued.status_code == 200
    actions = [(row['object_type'], row['action']) for row in log_rows()]
    assert actions == [
        ('ordonnance', 'read'), ('ordonnance', 'update'), ('ordonnance', 'issue'), ('ordonnance', 'print'),
        ('patient', 'read'), ('patient', 'search'),
    ]
    assert all(row['user_id'] == prescriber for row in log_rows())


def test_the_log_holds_no_medical_data_and_cannot_be_altered(client, prescriber):
    draft = ready_draft(prescriber)
    with as_user(prescriber):
        client.get(f"/api/v1/ordonnances/{draft['id']}")
    columns = {row[0] for row in DatabasePool.execute_query(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'access_log' AND table_schema = DATABASE()")}
    assert columns == {'id', 'user_id', 'object_type', 'object_id', 'action', 'ip', 'created_at'}

    for statement in ('UPDATE access_log SET action = "x"', 'DELETE FROM access_log'):
        with pytest.raises(mysql.connector.Error):
            with DatabasePool.get_cursor() as cursor:
                cursor.execute(statement)


def test_prescriber_reads_the_log_of_their_own_ordonnance_only(client, prescriber, other_prescriber):
    draft = OrdonnanceService.create_draft(prescriber)
    with as_user(prescriber):
        client.get(f"/api/v1/ordonnances/{draft['id']}")
        own = client.get(f"/api/v1/ordonnances/{draft['id']}/access-log")
    with as_user(other_prescriber):
        foreign = client.get(f"/api/v1/ordonnances/{draft['id']}/access-log")

    entries = own.get_json()['entries']
    assert [entry['action'] for entry in entries] == ['read']
    assert entries[0]['user']['email'] == 'awa.prescriptrice@example.org'
    assert foreign.status_code == 404


def test_refused_access_is_not_logged_as_a_read(client, prescriber, other_prescriber):
    draft = OrdonnanceService.create_draft(prescriber)
    with as_user(other_prescriber):
        assert client.get(f"/api/v1/ordonnances/{draft['id']}").status_code == 404
    assert log_rows() == []
