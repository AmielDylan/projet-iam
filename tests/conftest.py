"""Pytest fixtures for the test suite."""
import pytest
from unittest.mock import MagicMock, patch

from app import create_app
from app.config import TestingConfig


@pytest.fixture
def app():
    """Create application for testing."""
    # Mock database initialization
    with patch('app.services.database.DatabasePool.initialize'):
        application = create_app(TestingConfig())
        application.config['TESTING'] = True
        yield application


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture
def mock_db():
    """Mock database operations."""
    with patch('app.services.database.DatabasePool') as mock:
        # Setup common return values
        mock.execute_query.return_value = []
        mock.execute_function.return_value = False
        mock.call_procedure.return_value = []
        mock.call_procedure_with_out.return_value = [None, None]
        yield mock


@pytest.fixture
def sample_medication_data():
    """Sample medication data for tests."""
    return {
        'aspirin': {
            'name': 'ASPIRINE',
            'type': 'substance',
            'is_classe': False,
            'is_substance': True,
            'is_specialite': False,
            'classes': ['ANTIAGREGANTS PLAQUETTAIRES', 'AINS']
        },
        'doliprane': {
            'name': 'DOLIPRANE',
            'type': 'specialite',
            'is_classe': False,
            'is_substance': False,
            'is_specialite': True,
            'classes': ['ANTALGIQUES']
        },
        'anticoagulants': {
            'name': 'ANTICOAGULANTS ORAUX',
            'type': 'classe',
            'is_classe': True,
            'is_substance': False,
            'is_specialite': False,
            'classes': []
        }
    }


@pytest.fixture
def sample_interaction_data():
    """Sample interaction data for tests."""
    return {
        'interactions': [
            {
                'class_1': 'ANTIAGREGANTS PLAQUETTAIRES',
                'class_2': 'ANTICOAGULANTS ORAUX',
                'details': 'Majoration du risque hemorragique',
                'risques': 'Hemorragie',
                'niveau': 'Association deconseillee',
                'niveau_id': 2,
                'actions': 'Surveillance clinique'
            }
        ],
        'med_1': 'ASPIRINE',
        'med_2': 'WARFARINE',
        'count': 1
    }


@pytest.fixture
def sample_autocomplete_results():
    """Sample autocomplete results."""
    return [
        {'resultat': 'ASPIRINE', 'type': 'substance'},
        {'resultat': 'ASPIRIN UPSA', 'type': 'specialite'},
        {'resultat': 'ASPEGIC', 'type': 'specialite'}
    ]
