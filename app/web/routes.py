"""Web page routes."""
from urllib.parse import urlparse

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from app.services.auth import (
    AuthService,
    EstablishmentService,
    ProfileService,
    require_account_reviewer,
    require_login,
    require_approved_prescriber,
)
from app.services.interaction import InteractionService
from app.services.ordonnance import OrdonnanceService, prescriber_identity
from app.services.patient import PatientService
from app.services.access_log import AccessLog
from app.services import two_factor
from app.services.two_factor import TwoFactor
from app.api.validators import sanitize_medication_name, ValidationError

web_bp = Blueprint('web', __name__)


def login_destination_for(user: dict, requested_next: str | None = None) -> str:
    """Return a safe post-login destination compatible with the user role."""
    role = user.get('role')
    default_destination = (
        url_for('web.prescriptions')
        if role == 'prescriber'
        else url_for('web.admin')
    )
    if not requested_next:
        return default_destination

    parsed = urlparse(requested_next)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith('/'):
        return default_destination

    path = parsed.path.rstrip('/') or '/'
    allowed_prefixes = {
        'prescriber': ('/ordonnances', '/patients', '/securite', '/prescripteur', '/etablissements', '/changer-mot-de-passe'),
        'admin': ('/admin',),
    }.get(role, ())
    public_paths = ('/', '/changelog')
    if path in public_paths or any(path == prefix or path.startswith(f'{prefix}/') for prefix in allowed_prefixes):
        return requested_next
    return default_destination


@web_bp.route('/', methods=['GET', 'POST'])
def home():
    """Render the public interaction page with optional interaction results."""
    result = []
    med_1_value = ''
    med_2_value = ''
    error_message = None

    if request.method == 'POST':
        med_1_raw = request.form.get('med-1', '')
        med_2_raw = request.form.get('med-2', '')

        try:
            med_1 = sanitize_medication_name(med_1_raw)
            med_2 = sanitize_medication_name(med_2_raw)

            med_1_value = med_1
            med_2_value = med_2

            interactions = InteractionService.get_interactions(med_1, med_2)

            # Format results for template compatibility
            for interaction in interactions:
                result.append([
                    interaction['class_1'],
                    interaction['class_2'],
                    [
                        interaction['details'],
                        interaction['risques'],
                        interaction['niveau'],
                        interaction['actions']
                    ]
                ])

            # Append med names at the end (legacy template format)
            if result:
                result.append(med_1)
                result.append(med_2)

        except ValidationError as e:
            error_message = e.message
            med_1_value = med_1_raw
            med_2_value = med_2_raw
        except Exception as e:
            error_message = "An error occurred while processing your request"
            med_1_value = med_1_raw
            med_2_value = med_2_raw

    return render_template(
        'index.html',
        resultats=result,
        med_1_value=med_1_value,
        med_2_value=med_2_value,
        error_message=error_message
    )


@web_bp.route('/ordonnances')
@require_approved_prescriber
def prescriptions():
    """List of drafts and issued ordonnances (Preact)."""
    user = AuthService.current_user()
    return render_template('prescriber_app.html', title='Ordonnances', entry='list.js', initial={
        'prescriber': prescriber_identity(int(user['id'])),
    })


@web_bp.route('/securite')
@require_login
def security_page():
    """Two-factor authentication settings (ticket 22)."""
    return render_template('prescriber_app.html', title='Sécurité', entry='security.js',
                           extra_scripts=['vendor/qrcode-generator.js'],
                           initial={'enrollment_required': bool(session.get('two_factor_enroll'))})


@web_bp.route('/patients/<int:patient_id>')
@require_approved_prescriber
def patient_sheet(patient_id):
    """Patient sheet: clinical data and ordonnance history (Preact)."""
    user = AuthService.current_user()
    patient = PatientService.get(int(user['id']), patient_id)
    if patient is None:
        abort(404)
    AccessLog.record(int(user['id']), 'patient', patient_id, 'read', request.remote_addr)
    return render_template('prescriber_app.html', title='Patient', entry='patient.js', initial={
        'prescriber': prescriber_identity(int(user['id'])),
        'patient': patient,
    })


@web_bp.route('/ordonnances/nouvelle')
@require_approved_prescriber
def new_ordonnance():
    """Start a draft and open it at the patient step."""
    user = AuthService.current_user()
    owner_id = int(user['id'])
    establishments = EstablishmentService.list_for_prescriber(owner_id)
    content = {'establishment_id': establishments[0]['id'] if establishments else None}
    patient_id = request.args.get('patient', type=int)
    if patient_id and PatientService.exists(owner_id, patient_id):
        content['patient_id'] = patient_id
    else:
        # Reuse an untouched empty draft rather than piling up empty ones.
        drafts = OrdonnanceService.list(owner_id, status='draft', per_page=20)['items']
        untouched = next((d for d in drafts if d['version'] == 1 and not d['patient_id'] and not d['medications']), None)
        if untouched:
            return redirect(url_for('web.write_ordonnance', ordonnance_id=untouched['id'], etape=1))
    draft = OrdonnanceService.create_draft(owner_id, content)
    AccessLog.record(int(user['id']), 'ordonnance', draft['id'], 'create', request.remote_addr)
    return redirect(url_for('web.write_ordonnance', ordonnance_id=draft['id'], etape=2 if draft['patient_id'] else 1))


@web_bp.route('/ordonnances/<int:ordonnance_id>/rediger')
@require_approved_prescriber
def write_ordonnance(ordonnance_id):
    """Prescribing screen: three steps, autosave, live analysis (Preact)."""
    user = AuthService.current_user()
    owner_id = int(user['id'])
    ordonnance = OrdonnanceService.get(owner_id, ordonnance_id)
    if ordonnance is None:
        abort(404)
    patient = PatientService.get(owner_id, ordonnance['patient_id']) if ordonnance['patient_id'] else None
    step = request.args.get('etape', type=int)
    if ordonnance['status'] != 'draft':
        step = 3
    elif step not in (1, 2, 3):
        step = 2 if patient else 1
    AccessLog.record(owner_id, 'ordonnance', ordonnance_id, 'read', request.remote_addr)
    initial = {
        'ordonnance': ordonnance,
        'patient': patient,
        'establishments': EstablishmentService.list_for_prescriber(owner_id),
        'prescriber': prescriber_identity(owner_id),
        'step': step,
    }
    return render_template('redaction.html', initial=initial)


@web_bp.route('/ordonnances/<int:ordonnance_id>/impression')
@require_approved_prescriber
def print_ordonnance(ordonnance_id):
    """Print view of an issued ordonnance, rendered only from its frozen snapshot."""
    user = AuthService.current_user()
    ordonnance = OrdonnanceService.get(int(user['id']), ordonnance_id)
    if ordonnance is None or not ordonnance.get('snapshot'):
        abort(404)
    AccessLog.record(int(user['id']), 'ordonnance', ordonnance_id, 'print', request.remote_addr)
    return render_template('print/ordonnance.html', ordonnance=ordonnance, s=ordonnance['snapshot'])


@web_bp.route('/connexion', methods=['GET', 'POST'])
def login():
    """Authenticate an approved user."""
    if request.method == 'POST':
        success, message = AuthService.authenticate(
            request.form.get('email', ''),
            request.form.get('password', ''),
        )
        flash(message, 'success' if success else 'danger')
        if success:
            session_user = AuthService.current_session_user()
            if session_user and two_factor.after_password(
                    session_user['id'], session_user['role']).get('two_factor_required'):
                return redirect(url_for('web.two_factor_page', next=request.args.get('next') or ''))
            user = AuthService.current_user() or {}
            if user.get('must_change_password'):
                return redirect(url_for('web.change_password', next=request.args.get('next') or ''))
            return redirect(login_destination_for(user, request.args.get('next')))
    return render_template('account_app.html', account_page='login')


@web_bp.route('/connexion/verification', methods=['GET', 'POST'])
def two_factor_page():
    """Second step of the login for accounts with 2FA."""
    if not session.get('user_id') or not session.get('two_factor_pending'):
        return redirect(url_for('web.login'))
    error = None
    if request.method == 'POST':
        if TwoFactor.verify(int(session['user_id']), request.form.get('code', ''), request.form.get('recovery_code', '')):
            two_factor.complete()
            user = AuthService.current_user() or {}
            if user.get('must_change_password'):
                return redirect(url_for('web.change_password'))
            return redirect(login_destination_for(user, request.args.get('next')))
        error = 'Code incorrect.'
    return render_template('two_factor.html', error=error)


@web_bp.route('/inscription', methods=['GET', 'POST'])
def register():
    """Create a pending prescriber account request."""
    if request.method == 'POST':
        result = AuthService.create_account_request(
            request.form.get('email', ''),
            '',
            request.form.get('first_name', ''),
            request.form.get('last_name', ''),
            'prescriber',
            request.form.get('birthdate', ''),
            request.form.get('profession', ''),
            request.form.get('order_number', ''),
            request.form.get('phone', ''),
            request.files.get('identity_document'),
        )
        if isinstance(result, tuple) and len(result) == 3:
            success, message, _extra = result
        else:
            success, message = result
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('web.login'))
    return render_template('account_app.html', account_page='register')


@web_bp.route('/changer-mot-de-passe', methods=['GET', 'POST'])
@require_login
def change_password():
    """Force or allow a password change."""
    user = AuthService.current_user()
    if request.method == 'POST':
        success, message = AuthService.change_password(
            int(user['id']),
            request.form.get('current_password', ''),
            request.form.get('new_password', ''),
        )
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(login_destination_for(user, request.args.get('next')))
    return render_template('account_app.html', account_page='change-password')


@web_bp.route('/deconnexion', methods=['POST', 'GET'])
def logout():
    """Clear the current session."""
    AuthService.logout()
    flash('Déconnexion effectuée.', 'success')
    return redirect(url_for('web.home'))


@web_bp.route('/prescripteur', methods=['GET', 'POST'])
@require_approved_prescriber
def prescriber_profile():
    """Manage the current prescriber's profile."""
    user = AuthService.current_user()
    if request.method == 'POST':
        ProfileService.save_profile(int(user['id']), request.form.to_dict())
        flash('Profil prescripteur enregistré.', 'success')
        return redirect(url_for('web.prescriber_profile'))
    return render_template('account_app.html', account_page='profile')


@web_bp.route('/etablissements')
@require_approved_prescriber
def establishments():
    """Manage the current prescriber's establishments."""
    return render_template('account_app.html', account_page='establishments')


@web_bp.route('/admin', methods=['GET', 'POST'])
@require_account_reviewer
def admin():
    """Review account requests visible to the current reviewer."""
    user = AuthService.current_user()
    if request.method == 'POST':
        action = request.form.get('action')
        target_id = int(request.form.get('user_id') or 0)
        success, message, _extra = AuthService.review_account(
            target_id,
            user,
            approve=action == 'approve',
            note=request.form.get('review_note', ''),
        )
        flash(message, 'success' if success else 'danger')
        return redirect(url_for('web.admin'))
    return render_template('account_app.html', account_page='admin')


@web_bp.route('/changelog')
def changelog():
    """Render the changelog page."""
    return render_template('changelog.html')


# Legacy route compatibility
@web_bp.route('/testClasse', methods=['POST'])
def test_classe():
    """Legacy endpoint: Check if medication is a class."""
    medication = request.form.get('medTest', '')
    try:
        medication = sanitize_medication_name(medication)
        med_type = InteractionService.validate_medication(medication)
        return 'True' if med_type.is_classe else 'False'
    except ValidationError:
        return 'False'


@web_bp.route('/testSubstance', methods=['POST'])
def test_substance():
    """Legacy endpoint: Check if medication is a substance."""
    medication = request.form.get('medTest', '')
    try:
        medication = sanitize_medication_name(medication)
        med_type = InteractionService.validate_medication(medication)
        return 'True' if med_type.is_substance else 'False'
    except ValidationError:
        return 'False'


@web_bp.route('/testSpecialite', methods=['POST'])
def test_specialite():
    """Legacy endpoint: Check if medication is a specialite."""
    medication = request.form.get('medTest', '')
    try:
        medication = sanitize_medication_name(medication)
        med_type = InteractionService.validate_medication(medication)
        return 'True' if med_type.is_specialite else 'False'
    except ValidationError:
        return 'False'


@web_bp.route('/getListClasses', methods=['POST'])
def get_list_classes():
    """Legacy endpoint: Get classes for a substance."""
    substance = request.form.get('substance', '')
    try:
        substance = sanitize_medication_name(substance)
        classes = InteractionService.get_classes_from_substance(substance)
        return classes
    except ValidationError:
        return []


@web_bp.route('/autocomplete_input', methods=['POST'])
def autocomplete_input():
    """Legacy endpoint: Autocomplete search."""
    from flask import jsonify
    from app.services.autocomplete import AutocompleteService
    from app.api.validators import validate_autocomplete_query

    query = request.form.get('query', '')
    try:
        query = validate_autocomplete_query(query)
    except ValidationError:
        return jsonify([])

    if not query:
        return jsonify([])

    results = AutocompleteService.search(query)
    return jsonify(results)
