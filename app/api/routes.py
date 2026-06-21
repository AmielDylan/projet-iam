"""API routes for the application."""
from flask import Blueprint, request, jsonify

from app.services.interaction import InteractionService
from app.services.autocomplete import AutocompleteService
from app.services.auth import AuthService, ProfileService
from app.services.catalog import MedicationCatalogService
from app.api.validators import (
    sanitize_medication_name,
    validate_autocomplete_query,
    ValidationError
)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


def current_api_user(required_role=None):
    """Return the current session user or a JSON response tuple."""
    user = AuthService.current_user()
    if not user:
        return None, (jsonify({'success': False, 'error': 'Connexion requise'}), 401)
    if user['status'] != 'approved':
        return None, (jsonify({'success': False, 'error': 'Compte non validé'}), 403)
    if required_role:
        allowed_roles = {required_role} if isinstance(required_role, str) else set(required_role)
        if user['role'] not in allowed_roles:
            return None, (jsonify({'success': False, 'error': 'Droits insuffisants'}), 403)
    return user, None


@api_bp.route('/auth/session', methods=['GET'])
def auth_session():
    """Return the current authenticated user, if any."""
    user = AuthService.current_user()
    return jsonify({'success': True, 'user': user})


@api_bp.route('/auth/login', methods=['POST'])
def auth_login():
    """Authenticate using JSON credentials."""
    data = request.get_json(silent=True) or {}
    success, message = AuthService.authenticate(data.get('email', ''), data.get('password', ''))
    status = 200 if success else 401
    return jsonify({'success': success, 'message': message, 'user': AuthService.current_user() if success else None}), status


@api_bp.route('/auth/register', methods=['POST'])
def auth_register():
    """Create a pending account request for pharmacy or prescriber."""
    data = request.get_json(silent=True) or {}
    success, message = AuthService.create_account_request(
        data.get('email', ''),
        data.get('password', ''),
        data.get('first_name', ''),
        data.get('last_name', ''),
        data.get('role', 'prescriber'),
    )
    return jsonify({'success': success, 'message': message}), 200 if success else 400


@api_bp.route('/auth/logout', methods=['POST'])
def auth_logout():
    """Clear the current session."""
    AuthService.logout()
    return jsonify({'success': True, 'message': 'Déconnexion effectuée.'})


@api_bp.route('/accounts/requests', methods=['GET'])
def account_requests():
    """Return account requests visible to the current reviewer."""
    user, error = current_api_user(required_role={'admin', 'pharmacy'})
    if error:
        return error
    return jsonify({'success': True, 'results': AuthService.list_account_requests(user)})


@api_bp.route('/accounts/<int:user_id>/review', methods=['POST'])
def review_account(user_id):
    """Approve or reject one visible account request."""
    user, error = current_api_user(required_role={'admin', 'pharmacy'})
    if error:
        return error
    data = request.get_json(silent=True) or {}
    approve = data.get('action') == 'approve' or data.get('approve') is True
    success, message = AuthService.review_account(user_id, user, approve, data.get('review_note', ''))
    return jsonify({'success': success, 'message': message}), 200 if success else 403


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
    data = request.get_json(silent=True) or {}
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
    data = request.get_json(silent=True) or {}

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

    try:
        interactions = InteractionService.get_interactions(med_1, med_2)
    except Exception as e:
        import logging
        logging.exception("Error fetching interactions for %s / %s", med_1, med_2)
        return jsonify({'success': False, 'error': 'Erreur interne lors de la recherche.'}), 500

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
        (request.get_json(silent=True) or {}).get('query', '')
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
    data = request.get_json(silent=True) or {}
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


@api_bp.route('/summary', methods=['POST'])
def get_summary():
    """Generate an AI summary of interaction data via Groq."""
    data = request.get_json(silent=True) or {}
    med1 = (data.get('med1') or '').upper().strip()
    med2 = (data.get('med2') or '').upper().strip()
    interactions = data.get('interactions', [])

    if not med1 or not med2 or not interactions:
        return jsonify({'success': False, 'error': 'Données manquantes'}), 400

    from app.services.summary import generate_interaction_summary
    summary = generate_interaction_summary(med1, med2, interactions)

    if summary:
        return jsonify({'success': True, 'summary': summary})
    return jsonify({'success': False, 'error': 'Service de résumé non disponible'})


@api_bp.route('/medications/search', methods=['GET'])
def search_medications():
    """Search the enriched prescription medication catalog."""
    query = request.args.get('q') or request.args.get('query') or ''
    try:
        query = validate_autocomplete_query(query)
    except ValidationError as e:
        return jsonify({'success': False, 'error': e.message, 'results': []}), 400

    if not query:
        return jsonify({'success': True, 'results': []})

    try:
        limit = min(int(request.args.get('limit', 12)), 25)
    except ValueError:
        limit = 12

    results = MedicationCatalogService.search(query, limit=limit)
    return jsonify({'success': True, 'results': results})


@api_bp.route('/medications/<int:medication_id>', methods=['GET'])
def get_medication(medication_id):
    """Return one enriched catalog medication."""
    medication = MedicationCatalogService.get(medication_id)
    if not medication:
        return jsonify({'success': False, 'error': 'Médicament introuvable'}), 404
    return jsonify({'success': True, 'medication': medication})


@api_bp.route('/prescriptions/analyze', methods=['POST'])
def analyze_prescription():
    """Analyze a prescription draft with IAM interactions and duplicate checks."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error

    data = request.get_json(silent=True) or {}
    items = data.get('items') or data.get('medications') or []
    if not isinstance(items, list):
        return jsonify({'success': False, 'error': 'La liste des médicaments est invalide'}), 400
    if not items:
        return jsonify({'success': True, 'items': [], 'alerts': [], 'interactions': [], 'summary': {
            'items_count': 0,
            'alerts_count': 0,
            'interactions_count': 0,
            'can_print': True,
        }})

    result = MedicationCatalogService.analyze_prescription(items)
    return jsonify(result)


@api_bp.route('/prescriber/profile', methods=['GET', 'POST'])
def prescriber_profile_api():
    """Read or update the current prescriber profile."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error

    if request.method == 'GET':
        return jsonify({'success': True, 'profile': ProfileService.get_profile(int(user['id']))})

    data = request.get_json(silent=True) or {}
    profile = ProfileService.save_profile(int(user['id']), data)
    return jsonify({'success': True, 'profile': profile})


@api_bp.route('/patients/search', methods=['GET'])
def search_patients():
    """Search patient history for the current prescriber."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error

    query = request.args.get('q') or request.args.get('query') or ''
    if len(query.strip()) < 2:
        return jsonify({'success': True, 'results': []})
    results = ProfileService.search_patients(int(user['id']), query)
    for item in results:
        birthdate = item.get('patient_birthdate')
        if birthdate is not None:
            item['patient_birthdate'] = birthdate.isoformat()
        last_seen = item.get('last_seen_at')
        if last_seen is not None:
            item['last_seen_at'] = last_seen.isoformat()
        if item.get('patient_weight') is not None:
            item['patient_weight'] = float(item['patient_weight'])
    return jsonify({'success': True, 'results': results})


@api_bp.route('/patients', methods=['POST'])
def save_patient():
    """Upsert a patient into the current prescriber's history."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error

    data = request.get_json(silent=True) or {}
    patient = ProfileService.upsert_patient(int(user['id']), data)
    return jsonify({'success': True, 'patient': patient})
