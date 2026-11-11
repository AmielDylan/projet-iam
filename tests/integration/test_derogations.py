"""Derogations: a written reason lifts an alert to justify, never a CI."""
from unittest.mock import patch

import pytest

from app.services.ordonnance import IssueRefused, OrdonnanceService
from tests.integration.test_issue import ready_draft

CATALOG = {7: {'id': 7, 'name': 'ADVIL', 'substances': ['IBUPROFENE']},
           5: {'id': 5, 'name': 'COUMADINE', 'substances': ['WARFARINE']}}
ASDEC = [{'class_1': 'AINS', 'class_2': 'AVK', 'niveau': 'Association déconseillée',
          'risques': 'Risque hémorragique', 'details': '', 'actions': ''}]
LINES = [{'line_id': 'a', 'medication_id': 7, 'name': 'Advil', 'posology': '1/j'},
         {'line_id': 'b', 'medication_id': 5, 'name': 'Coumadine', 'posology': '1/j'}]


@pytest.fixture(autouse=True)
def references():
    with patch('app.services.analysis.MedicationCatalogService.get', side_effect=CATALOG.get), \
         patch('app.services.ordonnance.MedicationCatalogService.get', side_effect=CATALOG.get), \
         patch('app.services.analysis.InteractionService.get_interactions', return_value=ASDEC):
        yield


def test_asdec_needs_a_reason_then_the_reason_is_frozen(prescriber):
    draft = ready_draft(prescriber, lines=LINES)
    with pytest.raises(IssueRefused) as refused:
        OrdonnanceService.issue(prescriber, draft['id'], version=draft['version'])
    [reason] = refused.value.reasons
    assert reason['code'] == 'alert_unjustified'

    content = {**draft['content'], 'derogations': {reason['alert_id']: 'INR contrôlé chaque semaine'}}
    justified = OrdonnanceService.save_draft(prescriber, draft['id'], content, version=draft['version'])
    issued = OrdonnanceService.issue(prescriber, draft['id'], version=justified['version'])

    [derogation] = issued['snapshot']['derogations']
    assert derogation['reason'] == 'INR contrôlé chaque semaine'
    assert derogation['level'] == 'ASDEC'
    assert derogation['line_ids'] == ['a', 'b']


def test_editing_a_concerned_line_drops_the_derogation(prescriber):
    draft = ready_draft(prescriber, lines=LINES)
    alert_id = OrdonnanceService.check(prescriber, draft['id'])['reasons'][0]['alert_id']
    content = {**draft['content'], 'derogations': {alert_id: 'INR contrôlé'}}
    justified = OrdonnanceService.save_draft(prescriber, draft['id'], content, version=draft['version'])
    assert OrdonnanceService.check(prescriber, draft['id'])['can_issue'] is True

    edited_lines = [{**LINES[0], 'posology': '2/j'}, LINES[1]]
    OrdonnanceService.save_draft(prescriber, draft['id'], {**content, 'lines': edited_lines}, version=justified['version'])
    check = OrdonnanceService.check(prescriber, draft['id'])
    assert check['can_issue'] is False
    assert check['reasons'][0]['code'] == 'alert_unjustified'
