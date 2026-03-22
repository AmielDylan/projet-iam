"""Web page routes."""
from flask import Blueprint, render_template, request

from app.services.interaction import InteractionService
from app.api.validators import sanitize_medication_name, ValidationError

web_bp = Blueprint('web', __name__)


@web_bp.route('/', methods=['GET', 'POST'])
def home():
    """Render the main page with optional interaction results."""
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
