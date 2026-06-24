"""Web page routes."""
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services.auth import (
    AuthService,
    ProfileService,
    require_account_reviewer,
    require_approved_prescriber,
)
from app.services.interaction import InteractionService
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
        'prescriber': ('/ordonnances', '/prescripteur'),
        'admin': ('/admin',),
        'pharmacy': ('/admin',),
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
    """Render the protected prescription workspace."""
    user = AuthService.current_user()
    return render_template(
        'prescription.html',
        prescriber_profile=ProfileService.get_profile(int(user['id']))
    )


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
            user = AuthService.current_user() or {}
            return redirect(login_destination_for(user, request.args.get('next')))
    return render_template('account_app.html', account_page='login')


@web_bp.route('/inscription', methods=['GET', 'POST'])
def register():
    """Create a pending pharmacy or prescriber account request."""
    if request.method == 'POST':
        success, message = AuthService.create_account_request(
            request.form.get('email', ''),
            request.form.get('password', ''),
            request.form.get('first_name', ''),
            request.form.get('last_name', ''),
            request.form.get('role', 'prescriber'),
        )
        flash(message, 'success' if success else 'danger')
        if success:
            return redirect(url_for('web.login'))
    return render_template('account_app.html', account_page='register')


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


@web_bp.route('/admin', methods=['GET', 'POST'])
@require_account_reviewer
def admin():
    """Review account requests visible to the current reviewer."""
    user = AuthService.current_user()
    if request.method == 'POST':
        action = request.form.get('action')
        target_id = int(request.form.get('user_id') or 0)
        success, message = AuthService.review_account(
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
