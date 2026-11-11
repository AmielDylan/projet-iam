"""An administrator never reaches ordonnance or patient content (ticket 21)."""
import re
from unittest.mock import patch

import pytest

ADMIN = {'id': 1, 'role': 'admin', 'status': 'approved', 'must_change_password': 0}


def health_rules(app):
    for rule in app.url_map.iter_rules():
        if re.search(r'/(ordonnances|patients|prescriptions)(/|$)', rule.rule) and rule.endpoint != 'static':
            for method in rule.methods - {'HEAD', 'OPTIONS'}:
                yield rule, method


def test_there_are_health_routes_to_check(app):
    assert len(list(health_rules(app))) > 15


@pytest.mark.parametrize('kind', ['api', 'web'])
def test_admin_is_refused_on_every_health_route(app, client, kind):
    with patch('app.services.auth.AuthService.current_user', return_value=ADMIN), \
         patch('app.services.ordonnance.OrdonnanceService.get') as get_ordonnance, \
         patch('app.services.patient.PatientService.get') as get_patient:
        for rule, method in health_rules(app):
            if (kind == 'api') != rule.rule.startswith('/api/'):
                continue
            url = re.sub(r'<int:\w+>', '1', rule.rule)
            response = client.open(url, method=method, json={})
            assert response.status_code in (302, 403), f'{method} {url} answered {response.status_code}'
        get_ordonnance.assert_not_called()
        get_patient.assert_not_called()
