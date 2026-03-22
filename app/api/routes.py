"""API routes for the application."""
from flask import Blueprint, request, jsonify

from app.services.interaction import InteractionService
from app.services.autocomplete import AutocompleteService
from app.api.validators import (
    sanitize_medication_name,
    validate_autocomplete_query,
    ValidationError
)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle validation errors."""
    return jsonify({
        'success': False,
        'error': error.message,
        'field': error.field
    }), 400


@api_bp.route('/validate', methods=['POST'])
def validate_medication():
    """
    Validate a medication name and return its type.

    Request JSON:
        {"medication": "ASPIRIN"}

    Response JSON:
        {
            "success": true,
            "medication": "ASPIRIN",
            "is_valid": true,
            "type": "substance",
            "is_classe": false,
            "is_substance": true,
            "is_specialite": false,
            "classes": ["ANTIAGRÉGANTS PLAQUETTAIRES", ...]
        }
    """
    data = request.get_json() or {}
    medication_name = data.get('medication') or request.form.get('medTest')

    try:
        medication = sanitize_medication_name(medication_name)
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': e.message,
            'field': e.field
        }), 400

    med_type = InteractionService.validate_medication(medication)

    response = {
        'success': True,
        'medication': medication,
        'is_valid': med_type.is_valid,
        'type': med_type.type_name,
        'is_classe': med_type.is_classe,
        'is_substance': med_type.is_substance,
        'is_specialite': med_type.is_specialite
    }

    # If it's a substance, include associated classes
    if med_type.is_substance:
        response['classes'] = InteractionService.get_classes_from_substance(medication)

    return jsonify(response)


@api_bp.route('/interactions', methods=['POST'])
def get_interactions():
    """
    Get interactions between two medications.

    Request JSON:
        {"med_1": "ASPIRIN", "med_2": "WARFARIN"}

    Response JSON:
        {
            "success": true,
            "med_1": "ASPIRIN",
            "med_2": "WARFARIN",
            "count": 1,
            "interactions": [
                {
                    "class_1": "ANTIAGRÉGANTS PLAQUETTAIRES",
                    "class_2": "ANTICOAGULANTS ORAUX",
                    "details": "...",
                    "risques": "...",
                    "niveau": "Association déconseillée",
                    "actions": "..."
                }
            ]
        }
    """
    data = request.get_json() or {}

    # Support both JSON body and form data
    med_1_raw = data.get('med_1') or request.form.get('med-1')
    med_2_raw = data.get('med_2') or request.form.get('med-2')

    try:
        med_1 = sanitize_medication_name(med_1_raw)
        med_2 = sanitize_medication_name(med_2_raw)
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': e.message,
            'field': e.field
        }), 400

    interactions = InteractionService.get_interactions(med_1, med_2)

    return jsonify({
        'success': True,
        'med_1': med_1,
        'med_2': med_2,
        'count': len(interactions),
        'interactions': interactions
    })


@api_bp.route('/autocomplete', methods=['GET', 'POST'])
def autocomplete():
    """
    Get autocomplete suggestions for medication search.

    Query params or form data:
        q or query: Search query string

    Response JSON:
        [
            {"resultat": "ASPIRIN", "type": "substance"},
            {"resultat": "ASPIRINE UPSA", "type": "specialite"}
        ]
    """
    # Support multiple input methods
    query = (
        request.args.get('q') or
        request.args.get('query') or
        request.form.get('query') or
        (request.get_json() or {}).get('query', '')
    )

    try:
        query = validate_autocomplete_query(query)
    except ValidationError:
        return jsonify([])

    if not query:
        return jsonify([])

    results = AutocompleteService.search(query)
    return jsonify(results)


@api_bp.route('/classes', methods=['POST'])
def get_classes():
    """
    Get classes associated with a substance.

    Request JSON or form data:
        {"substance": "ASPIRINE"}

    Response JSON:
        {
            "success": true,
            "substance": "ASPIRINE",
            "classes": ["ANTIAGRÉGANTS PLAQUETTAIRES", ...]
        }
    """
    data = request.get_json() or {}
    substance_name = data.get('substance') or request.form.get('substance')

    try:
        substance = sanitize_medication_name(substance_name)
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': e.message,
            'field': e.field
        }), 400

    classes = InteractionService.get_classes_from_substance(substance)

    return jsonify({
        'success': True,
        'substance': substance,
        'classes': classes
    })
