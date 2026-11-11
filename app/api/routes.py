"""API routes for the application."""
from io import BytesIO

from flask import Blueprint, current_app, request, jsonify, send_file, session

from app.services.interaction import InteractionService
from app.services.autocomplete import AutocompleteService
from app.services.auth import AuthService, ProfileService, EstablishmentService, PROFESSIONS, can_prescribe
from app.services.catalog import MedicationCatalogService
from app.services.patient import PatientError, PatientService
from app.services.ordonnance import (
    CANCEL_REASONS, OrdonnanceError, OrdonnanceService, VersionConflict, normalize_content,
)
from app.services.analysis import analyze, normalize_dci
from app.services.access_log import AccessLog
from app.services import session_lock, two_factor
from app.services.two_factor import TwoFactor
from app.services.catalog_gaps import CatalogEntryError, CatalogGaps
from app.services.prescriber_assets import AssetError, PrescriberAssets
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
    if user.get('must_change_password') and request.endpoint != 'api.auth_change_password':
        return None, (jsonify({'success': False, 'error': 'Changement de mot de passe requis', 'code': 'must_change_password'}), 403)
    if required_role:
        allowed_roles = {required_role} if isinstance(required_role, str) else set(required_role)
        if user['role'] not in allowed_roles:
            return None, (jsonify({'success': False, 'error': 'Droits insuffisants'}), 403)
        if user['role'] == 'prescriber' and not can_prescribe(user):
            return None, (jsonify({'success': False, 'code': 'profession_not_allowed',
                                   'error': "La rédaction d'ordonnances n'est pas ouverte à votre profession."}), 403)
    return user, None


@api_bp.route('/auth/session', methods=['GET'])
def auth_session():
    """Return the current user, or only the lock state when the session is locked."""
    if session_lock.is_locked():
        return jsonify({'success': True, 'locked': True, 'user': None})
    user = AuthService.current_user()
    return jsonify({'success': True, 'locked': False, 'user': user})


@api_bp.route('/auth/unlock', methods=['POST'])
def auth_unlock():
    """Unlock an idle-locked session with the same user's password."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Connexion requise'}), 401
    password = (request.get_json(silent=True) or {}).get('password') or ''
    if not AuthService.verify_password(int(user_id), password):
        return jsonify({'success': False, 'error': 'Mot de passe incorrect', 'code': 'wrong_password'}), 401
    session_lock.unlock()
    return jsonify({'success': True})


@api_bp.route('/auth/login', methods=['POST'])
def auth_login():
    """Authenticate using JSON credentials."""
    data = request.get_json(silent=True) or {}
    success, message = AuthService.authenticate(data.get('email', ''), data.get('password', ''))
    if not success:
        return jsonify({'success': False, 'message': message, 'user': None}), 401
    user = AuthService.current_session_user()
    next_step = two_factor.after_password(user['id'], user['role'])
    return jsonify({'success': True, 'message': message, 'user': None if next_step.get('two_factor_required') else user,
                    **next_step})


@api_bp.route('/auth/2fa', methods=['GET'])
def two_factor_status():
    """Whether 2FA is enabled for the current account, and whether it is required."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Connexion requise'}), 401
    return jsonify({'success': True, 'enabled': TwoFactor.is_enabled(int(user_id)),
                    'required': two_factor.required()})


@api_bp.route('/auth/2fa/setup', methods=['POST'])
def two_factor_setup():
    """Draw a secret; the client shows it as a QR code from otpauth_uri."""
    user_id = session.get('user_id')
    if not user_id or session.get('two_factor_pending'):
        return jsonify({'success': False, 'error': 'Connexion requise'}), 401
    return jsonify({'success': True, **TwoFactor.setup(int(user_id), session.get('email') or '')})


@api_bp.route('/auth/2fa/confirm', methods=['POST'])
def two_factor_confirm():
    """Enable 2FA with a first code; the recovery codes are returned once."""
    user_id = session.get('user_id')
    if not user_id or session.get('two_factor_pending'):
        return jsonify({'success': False, 'error': 'Connexion requise'}), 401
    codes = TwoFactor.confirm(int(user_id), (request.get_json(silent=True) or {}).get('code') or '')
    if codes is None:
        return jsonify({'success': False, 'error': 'Code incorrect', 'code': 'wrong_code'}), 400
    two_factor.complete()
    return jsonify({'success': True, 'recovery_codes': codes})


@api_bp.route('/auth/2fa/verify', methods=['POST'])
def two_factor_verify():
    """Finish a login with an authenticator code or a recovery code."""
    user_id = session.get('user_id')
    if not user_id or not session.get('two_factor_pending'):
        return jsonify({'success': False, 'error': 'Aucune connexion en attente'}), 400
    data = request.get_json(silent=True) or {}
    if not TwoFactor.verify(int(user_id), data.get('code') or '', data.get('recovery_code') or ''):
        return jsonify({'success': False, 'error': 'Code incorrect', 'code': 'wrong_code'}), 401
    two_factor.complete()
    return jsonify({'success': True, 'user': AuthService.current_session_user()})


@api_bp.route('/auth/register', methods=['POST'])
def auth_register():
    """Create a pending prescriber account request."""
    data = request.form if request.form else (request.get_json(silent=True) or {})
    result = AuthService.create_account_request(
        data.get('email', ''),
        '',
        data.get('first_name', ''),
        data.get('last_name', ''),
        'prescriber',
        data.get('birthdate', ''),
        data.get('profession', ''),
        data.get('order_number', ''),
        data.get('phone', ''),
        request.files.get('identity_document'),
    )
    # support both (success, message) and (success, message, extra)
    if isinstance(result, tuple) and len(result) == 3:
        success, message, extra = result
    else:
        success, message = result
        extra = None
    payload = {'success': success, 'message': message}
    if extra:
        payload.update(extra)
    return jsonify(payload), 200 if success else 400


@api_bp.route('/auth/change-password', methods=['POST'])
def auth_change_password():
    """Change the current user's password."""
    user = AuthService.current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Connexion requise'}), 401
    data = request.get_json(silent=True) or {}
    success, message = AuthService.change_password(
        int(user['id']),
        data.get('current_password', ''),
        data.get('new_password', ''),
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
    user, error = current_api_user(required_role='admin')
    if error:
        return error
    return jsonify({'success': True, 'results': AuthService.list_account_requests(user)})


@api_bp.route('/accounts/<int:user_id>/review', methods=['POST'])
def review_account(user_id):
    """Approve or reject one visible account request."""
    user, error = current_api_user(required_role='admin')
    if error:
        return error
    data = request.get_json(silent=True) or {}
    approve = data.get('action') == 'approve' or data.get('approve') is True
    success, message, extra = AuthService.review_account(user_id, user, approve, data.get('review_note', ''))
    payload = {'success': success, 'message': message}
    if extra:
        payload.update(extra)
    return jsonify(payload), 200 if success else 403


@api_bp.route('/accounts/<int:user_id>/identity-document', methods=['GET'])
def identity_document(user_id):
    """Return one pending identity document to the global admin."""
    user, error = current_api_user(required_role='admin')
    if error:
        return error
    document = AuthService.get_identity_document(user_id)
    if not document:
        return jsonify({'success': False, 'error': 'Pièce indisponible'}), 404
    response = send_file(
        BytesIO(document['content']),
        mimetype=document['mime_type'],
        as_attachment=False,
        download_name=document['filename'],
    )
    response.headers['Content-Disposition'] = f'inline; filename="{document["filename"]}"'
    response.headers['Cache-Control'] = 'no-store, private'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Permissions-Policy'] = 'clipboard-write=(), fullscreen=()'
    return response


@api_bp.route('/professions', methods=['GET'])
def professions():
    """Return requestable prescriber professions."""
    return jsonify({'success': True, 'results': list(PROFESSIONS)})


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

    # Flag a declared allergy as soon as the suggestion appears (prescribers only).
    patient_id = request.args.get('patient_id', type=int)
    user = AuthService.current_user() if patient_id else None
    patient = PatientService.get(int(user['id']), patient_id) if user and user.get('role') == 'prescriber' else None
    allergies = [normalize_dci(a) for a in (patient or {}).get('allergies', [])]
    for result in results:
        substances = [normalize_dci(s) for s in result.get('substances', [])]
        result['allergy_warning'] = [a for a in allergies if any(a == s or s.startswith(a + ' ') for s in substances)]
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
    """Analyze draft lines live: interactions, same substance, allergies, derogations."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error

    data = request.get_json(silent=True) or {}
    lines = data.get('lines', data.get('items', []))
    if not isinstance(lines, list):
        return jsonify({'success': False, 'error': 'La liste des médicaments est invalide'}), 400
    try:
        content = normalize_content({'lines': lines, 'derogations': data.get('derogations') or {}})
    except OrdonnanceError as exc:
        return ordonnance_error(exc)

    patient = None
    if data.get('patient_id'):
        patient = PatientService.get(int(user['id']), int(data['patient_id']))
        if patient is None:
            return jsonify({'success': False, 'error': 'Patient introuvable', 'code': 'not_found'}), 404
    try:
        result = analyze(content['lines'], patient=patient, derogations=content['derogations'])
    except Exception:
        current_app.logger.exception('IAM analysis failed')
        return jsonify({'success': False, 'error': "L'analyse IAM est indisponible. Réessayez dans un instant.",
                        'code': 'analysis_unavailable'}), 503
    return jsonify({'success': True, **result})


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


@api_bp.route('/prescriber/establishments', methods=['GET', 'POST'])
def prescriber_establishments():
    """List or create establishments for the current prescriber."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'results': EstablishmentService.list_for_prescriber(int(user['id']), active_only=False),
        })
    payload = request.form if request.form else (request.get_json(silent=True) or {})
    success, message, establishment = EstablishmentService.upsert(
        int(user['id']),
        payload,
        request.files.get('logo'),
    )
    return jsonify({'success': success, 'message': message, 'establishment': establishment}), 200 if success else 400


@api_bp.route('/prescriber/establishments/<int:establishment_id>', methods=['PUT', 'POST', 'DELETE'])
def prescriber_establishment(establishment_id):
    """Update or deactivate one establishment for the current prescriber."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    if request.method == 'DELETE':
        deleted = EstablishmentService.delete(int(user['id']), establishment_id)
        return jsonify({'success': deleted}), 200 if deleted else 404
    payload = request.form if request.form else (request.get_json(silent=True) or {})
    success, message, establishment = EstablishmentService.upsert(
        int(user['id']),
        payload,
        request.files.get('logo'),
        establishment_id,
    )
    return jsonify({'success': success, 'message': message, 'establishment': establishment}), 200 if success else 400


@api_bp.route('/admin/establishments', methods=['GET'])
def admin_establishments():
    """Return all prescriber establishments to the global admin."""
    user, error = current_api_user(required_role='admin')
    if error:
        return error
    return jsonify({'success': True, 'results': EstablishmentService.list_all_for_admin()})


@api_bp.route('/patients', methods=['GET'])
def search_patients():
    """Find the current prescriber's patients by name prefix or birthdate."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error

    if request.args.get('recent'):
        results = PatientService.recent(int(user['id']))
        trace(user, 'patient', None, 'list')
        return jsonify({'success': True, 'results': results})
    query = request.args.get('q') or ''
    if len(query.strip()) < 2:
        return jsonify({'success': True, 'results': []})
    results = PatientService.search(int(user['id']), query)
    trace(user, 'patient', None, 'search')
    return jsonify({'success': True, 'results': results})


@api_bp.route('/patients', methods=['POST'])
def create_patient():
    """Create a patient for the current prescriber."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    try:
        patient = PatientService.create(int(user['id']), request.get_json(silent=True) or {})
    except PatientError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    trace(user, 'patient', patient['id'], 'create')
    return jsonify({'success': True, 'patient': patient}), 201


@api_bp.route('/patients/<int:patient_id>', methods=['GET'])
def get_patient(patient_id):
    """Read one of the current prescriber's patients."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    patient = PatientService.get(int(user['id']), patient_id)
    if patient is None:
        return jsonify({'success': False, 'error': 'Patient introuvable'}), 404
    trace(user, 'patient', patient_id, 'read')
    return jsonify({'success': True, 'patient': patient})


@api_bp.route('/patients/<int:patient_id>', methods=['PUT'])
def update_patient(patient_id):
    """Correct a patient in place; the id and the ordonnances stay attached."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    try:
        patient = PatientService.update(int(user['id']), patient_id, request.get_json(silent=True) or {})
    except PatientError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    if patient is None:
        return jsonify({'success': False, 'error': 'Patient introuvable'}), 404
    trace(user, 'patient', patient_id, 'update')
    return jsonify({'success': True, 'patient': patient})


def trace(user, object_type, object_id, action):
    """Record a successful access in the access log (identifiers only)."""
    AccessLog.record(int(user['id']), object_type, object_id, action, request.remote_addr)


def ordonnance_error(exc: OrdonnanceError):
    """Translate a rule refusal from the Ordonnance module into JSON."""
    body = {'success': False, 'error': str(exc), 'code': exc.code}
    if isinstance(exc, VersionConflict):
        body['current'] = exc.current
    if getattr(exc, 'reasons', None):
        body['reasons'] = exc.reasons
    return jsonify(body), exc.status


@api_bp.route('/ordonnances', methods=['POST'])
def create_ordonnance():
    """Start a draft."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    try:
        draft = OrdonnanceService.create_draft(int(user['id']))
    except OrdonnanceError as exc:
        return ordonnance_error(exc)
    trace(user, 'ordonnance', draft['id'], 'create')
    return jsonify({'success': True, 'ordonnance': draft}), 201


@api_bp.route('/ordonnances/<int:ordonnance_id>', methods=['GET'])
def get_ordonnance(ordonnance_id):
    """Read one of the current prescriber's ordonnances."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    ordonnance = OrdonnanceService.get(int(user['id']), ordonnance_id)
    if ordonnance is None:
        return jsonify({'success': False, 'error': 'Ordonnance introuvable', 'code': 'not_found'}), 404
    trace(user, 'ordonnance', ordonnance_id, 'read')
    return jsonify({'success': True, 'ordonnance': ordonnance})


@api_bp.route('/ordonnances/<int:ordonnance_id>', methods=['PUT'])
def save_ordonnance(ordonnance_id):
    """Autosave a draft: full content plus the version it was based on."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        version = int(data.get('version'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Version manquante', 'code': 'invalid'}), 400
    try:
        draft = OrdonnanceService.save_draft(int(user['id']), ordonnance_id, data.get('content') or {}, version)
    except OrdonnanceError as exc:
        return ordonnance_error(exc)
    trace(user, 'ordonnance', ordonnance_id, 'update')
    return jsonify({'success': True, 'ordonnance': draft})


@api_bp.route('/ordonnances/<int:ordonnance_id>/check', methods=['GET'])
def check_ordonnance(ordonnance_id):
    """Verification step: refusal reasons, warnings, IAM analysis and referentials."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    try:
        check = OrdonnanceService.check(int(user['id']), ordonnance_id)
    except OrdonnanceError as exc:
        return ordonnance_error(exc)
    except Exception:
        current_app.logger.exception('Ordonnance check failed')
        return jsonify({'success': False, 'error': "L'analyse IAM est indisponible. Réessayez dans un instant.",
                        'code': 'analysis_unavailable'}), 503
    trace(user, 'ordonnance', ordonnance_id, 'check')
    return jsonify({'success': True, 'check': check})


@api_bp.route('/ordonnances/<int:ordonnance_id>/issue', methods=['POST'])
def issue_ordonnance(ordonnance_id):
    """Issue at first print or PDF: freeze and number, or explain why not."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        version = int(data.get('version'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Version manquante', 'code': 'invalid'}), 400
    try:
        ordonnance = OrdonnanceService.issue(int(user['id']), ordonnance_id, version)
    except OrdonnanceError as exc:
        return ordonnance_error(exc)
    except Exception:
        current_app.logger.exception('Ordonnance issue failed')
        return jsonify({'success': False, 'error': "L'analyse IAM est indisponible. Réessayez dans un instant.",
                        'code': 'analysis_unavailable'}), 503
    trace(user, 'ordonnance', ordonnance_id, 'issue')
    return jsonify({'success': True, 'ordonnance': ordonnance,
                    'print_url': f'/ordonnances/{ordonnance_id}/impression'})


@api_bp.route('/ordonnances', methods=['GET'])
def list_ordonnances():
    """List drafts and issued ordonnances, most recent first, 50 per page."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    try:
        result = OrdonnanceService.list(
            int(user['id']),
            status=request.args.get('status') or None,
            patient_id=request.args.get('patient_id', type=int),
            page=request.args.get('page', 1, type=int),
        )
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc), 'code': 'invalid'}), 400
    trace(user, 'ordonnance', None, 'list')
    return jsonify({'success': True, **result})


@api_bp.route('/ordonnances/<int:ordonnance_id>', methods=['DELETE'])
def discard_ordonnance(ordonnance_id):
    """Delete a draft; issued ordonnances are kept forever."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    try:
        OrdonnanceService.discard_draft(int(user['id']), ordonnance_id)
    except OrdonnanceError as exc:
        return ordonnance_error(exc)
    trace(user, 'ordonnance', ordonnance_id, 'discard')
    return jsonify({'success': True})


@api_bp.route('/patients/<int:patient_id>/ordonnances', methods=['GET'])
def patient_ordonnances(patient_id):
    """Patient sheet: clinical data and ordonnance history."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    patient = PatientService.get(int(user['id']), patient_id)
    if patient is None:
        return jsonify({'success': False, 'error': 'Patient introuvable', 'code': 'not_found'}), 404
    result = OrdonnanceService.list(int(user['id']), patient_id=patient_id,
                                    page=request.args.get('page', 1, type=int))
    trace(user, 'patient', patient_id, 'read')
    return jsonify({'success': True, 'patient': patient, **result})


@api_bp.route('/ordonnances/cancel-reasons', methods=['GET'])
def cancel_reasons():
    """Common cancellation reasons offered by "Annuler et corriger"."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    return jsonify({'success': True, 'reasons': CANCEL_REASONS})


@api_bp.route('/ordonnances/<int:ordonnance_id>/renew', methods=['POST'])
def renew_ordonnance(ordonnance_id):
    """Prefilled draft from an issued ordonnance; a cancelled one needs confirm_cancelled."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        result = OrdonnanceService.renew(int(user['id']), ordonnance_id,
                                         confirm_cancelled=data.get('confirm_cancelled') is True)
    except OrdonnanceError as exc:
        return ordonnance_error(exc)
    trace(user, 'ordonnance', ordonnance_id, 'renew')
    trace(user, 'ordonnance', result['ordonnance']['id'], 'create')
    return jsonify({'success': True, **result}), 201


@api_bp.route('/ordonnances/<int:ordonnance_id>/cancel', methods=['POST'])
def cancel_ordonnance(ordonnance_id):
    """Cancel an issued ordonnance with a written reason."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        ordonnance = OrdonnanceService.cancel(int(user['id']), ordonnance_id, data.get('reason') or '')
    except OrdonnanceError as exc:
        return ordonnance_error(exc)
    trace(user, 'ordonnance', ordonnance_id, 'cancel')
    return jsonify({'success': True, 'ordonnance': ordonnance})


@api_bp.route('/ordonnances/<int:ordonnance_id>/cancel-and-correct', methods=['POST'])
def cancel_and_correct_ordonnance(ordonnance_id):
    """Cancel, then return the prefilled correction draft."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        result = OrdonnanceService.cancel_and_correct(int(user['id']), ordonnance_id, data.get('reason') or '')
    except OrdonnanceError as exc:
        return ordonnance_error(exc)
    trace(user, 'ordonnance', ordonnance_id, 'cancel')
    trace(user, 'ordonnance', result['ordonnance']['id'], 'create')
    return jsonify({'success': True, **result}), 201


@api_bp.route('/ordonnances/<int:ordonnance_id>/access-log', methods=['GET'])
def ordonnance_access_log(ordonnance_id):
    """Who consulted or changed this ordonnance, for its prescriber only."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    if OrdonnanceService.get(int(user['id']), ordonnance_id) is None:
        return jsonify({'success': False, 'error': 'Ordonnance introuvable', 'code': 'not_found'}), 404
    return jsonify({'success': True, 'entries': AccessLog.for_object('ordonnance', ordonnance_id)})


@api_bp.route('/admin/catalog/gaps', methods=['GET'])
def admin_catalog_gaps():
    """Medications typed freely or searched in vain, most frequent first. No patient data."""
    user, error = current_api_user(required_role='admin')
    if error:
        return error
    return jsonify({'success': True, 'gaps': CatalogGaps.list()})


@api_bp.route('/admin/catalog/substances', methods=['GET'])
def admin_catalog_substances():
    """Thesaurus substances to attach to a new catalog entry."""
    user, error = current_api_user(required_role='admin')
    if error:
        return error
    return jsonify({'success': True, 'results': CatalogGaps.substances(request.args.get('q') or '')})


@api_bp.route('/admin/catalog/entries', methods=['POST'])
def admin_create_catalog_entry():
    """Create a catalog entry from thesaurus substances; prescribers find it at once."""
    user, error = current_api_user(required_role='admin')
    if error:
        return error
    try:
        entry = CatalogGaps.create_entry(int(user['id']), request.get_json(silent=True) or {})
    except CatalogEntryError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    return jsonify({'success': True, 'entry': entry}), 201


@api_bp.route('/admin/waitlist', methods=['GET'])
def admin_waitlist():
    """Pharmacists waiting for the pharmacy offer."""
    user, error = current_api_user(required_role='admin')
    if error:
        return error
    return jsonify({'success': True, 'results': AuthService.list_waitlist()})


@api_bp.route('/admin/waitlist.csv', methods=['GET'])
def admin_waitlist_csv():
    """Waitlist export, semicolon-separated for spreadsheet software in French locales."""
    user, error = current_api_user(required_role='admin')
    if error:
        return error
    import csv
    import io

    columns = ['email', 'first_name', 'last_name', 'profession', 'order_number', 'phone', 'requested_at']
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, delimiter=';', extrasaction='ignore')
    writer.writeheader()
    writer.writerows(AuthService.list_waitlist())
    return current_app.response_class(
        '\ufeff' + buffer.getvalue(), mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename="liste-attente-officine.csv"'})


@api_bp.route('/admin/accounts/<int:user_id>/2fa/reset', methods=['POST'])
def admin_reset_two_factor(user_id):
    """Reset a user's 2FA (lost phone); recorded in the access log."""
    user, error = current_api_user(required_role='admin')
    if error:
        return error
    if AuthService.get_user(user_id) is None:
        return jsonify({'success': False, 'error': 'Compte introuvable'}), 404
    TwoFactor.reset(user_id)
    AccessLog.record(int(user['id']), 'account', user_id, 'reset_2fa', request.remote_addr)
    return jsonify({'success': True})


@api_bp.route('/prescriber/establishments/<int:establishment_id>/logo', methods=['GET'])
def establishment_logo(establishment_id):
    """Logo of one of the current prescriber's establishments, for the live preview."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    logo = EstablishmentService.logo(int(user['id']), establishment_id)
    if logo is None:
        return jsonify({'success': False, 'error': 'Logo introuvable'}), 404
    mime_type, content = logo
    return send_file(BytesIO(content), mimetype=mime_type, max_age=300)


@api_bp.route('/prescriber/assets', methods=['GET'])
def prescriber_assets_status():
    """Which of the signature and the stamp the prescriber has uploaded."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    return jsonify({'success': True, 'assets': PrescriberAssets.status(int(user['id']))})


@api_bp.route('/prescriber/assets/<kind>', methods=['GET', 'POST', 'DELETE'])
def prescriber_asset(kind):
    """Read, replace (raw PNG body or `image` file) or delete the signature or the stamp."""
    user, error = current_api_user(required_role='prescriber')
    if error:
        return error
    try:
        if request.method == 'GET':
            content = PrescriberAssets.get(int(user['id']), kind)
            if content is None:
                return jsonify({'success': False, 'error': 'Image introuvable'}), 404
            return send_file(BytesIO(content), mimetype='image/png', max_age=0)
        if request.method == 'DELETE':
            PrescriberAssets.delete(int(user['id']), kind)
            return jsonify({'success': True})
        upload = request.files.get('image')
        PrescriberAssets.save(int(user['id']), kind, upload.read() if upload else request.get_data())
    except AssetError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    return jsonify({'success': True})
