"""Key rotation: reseal every sealed column, rebuild the search index."""
import mysql.connector
import pytest

from app.services import vault as vault_module
from app.services.database import DatabasePool
from app.services.key_rotation import SEALED_COLUMNS, reindex_patients, reseal_all
from app.services.ordonnance import OrdonnanceService
from app.services.patient import PatientService
from app.services.vault import Vault, generate_key
from tests.integration.test_issue import ready_draft


@pytest.fixture
def keys():
    """Install a fresh vault for the test, restore the test vault afterwards."""
    original = vault_module.vault()
    old, index = generate_key(), generate_key()
    vault_module.install(Vault(f'old:{old}', index))
    yield {'old': old, 'index': index}
    vault_module.install(original)


def sealed_values():
    values = []
    for table, column in SEALED_COLUMNS:
        values += [row[0] for row in DatabasePool.execute_query(
            f'SELECT `{column}` FROM `{table}` WHERE `{column}` IS NOT NULL')]
    return values


def test_reseal_moves_every_sealed_value_to_the_new_key(prescriber, keys):
    draft = ready_draft(prescriber)
    issued = OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
    OrdonnanceService.cancel(prescriber, issued['id'], 'Erreur')
    assert all(value.startswith('v1:old:') for value in sealed_values())

    new = generate_key()
    vault_module.install(Vault(f"new:{new},old:{keys['old']}", keys['index']))
    counts = reseal_all()

    assert counts[('ordonnance_versions', 'content')] >= 2
    assert all(value.startswith('v1:new:') for value in sealed_values())

    vault_module.install(Vault(f'new:{new}', keys['index']))  # old key retired
    reread = OrdonnanceService.get(prescriber, issued['id'])
    assert reread['snapshot']['patient']['last_name'] == 'Koffi'
    assert reread['cancel_reason'] == 'Erreur'
    assert reseal_all() == {column: 0 for column in SEALED_COLUMNS}


def test_versions_stay_append_only_outside_a_rotation(prescriber, keys):
    OrdonnanceService.create_draft(prescriber)
    with pytest.raises(mysql.connector.Error):
        with DatabasePool.get_cursor() as cursor:
            cursor.execute("UPDATE ordonnance_versions SET content = 'x'")
    with pytest.raises(mysql.connector.Error):
        with DatabasePool.get_cursor() as cursor:
            cursor.execute('SET @digiremed_key_rotation = 1')
            cursor.execute('UPDATE ordonnance_versions SET version = version + 1')


def test_reindex_after_changing_the_index_key(prescriber, keys):
    PatientService.create(prescriber, {'first_name': 'Awa', 'last_name': 'Koffi', 'birthdate': '1980-05-01'})
    vault_module.install(Vault(f"old:{keys['old']}", generate_key()))
    assert PatientService.search(prescriber, 'koffi') == []

    assert reindex_patients() == 1
    assert len(PatientService.search(prescriber, 'koffi')) == 1
    assert len(PatientService.search(prescriber, '01/05/1980')) == 1
