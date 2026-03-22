/**
 * Form handling with AJAX submission
 */
import { ApiClient, ApiError } from './api.js';
import { escapeHtml, showLoading, announceToScreenReader } from './utils.js';

class InteractionForm {
    /**
     * Initialize the interaction form
     * @param {HTMLFormElement} form - Form element
     * @param {Object} options - Configuration options
     */
    constructor(form, options = {}) {
        this.form = form;
        this.options = {
            resultsContainer: options.resultsContainer || document.getElementById('results-container'),
            onValidationChange: options.onValidationChange || (() => {})
        };

        this.med1Input = form.querySelector('#med-1');
        this.med2Input = form.querySelector('#med-2');
        this.submitButton = form.querySelector('button[type="submit"]');

        this.validationState = {
            med1: null,
            med2: null
        };

        this.bindEvents();
    }

    /**
     * Bind form events
     */
    bindEvents() {
        this.form.addEventListener('submit', this.handleSubmit.bind(this));
    }

    /**
     * Validate a medication input
     * @param {HTMLInputElement} input - Input element
     * @param {string} key - 'med1' or 'med2'
     */
    async validateMedication(input, key) {
        const value = input.value.trim();
        const helperId = `${input.id}-helper`;
        const helper = document.getElementById(helperId);
        const inputNumber = key === 'med1' ? 1 : 2;

        if (!value) {
            this.setInputState(input, helper, 'default');
            this.validationState[key] = null;
            this.hideClassChoices(inputNumber);
            return null;
        }

        try {
            const result = await ApiClient.validateMedication(value);
            this.validationState[key] = result;

            if (!result.is_valid) {
                this.setInputState(input, helper, 'danger', 'Entrez une valeur correcte svp.');
                this.hideClassChoices(inputNumber);
            } else if (result.is_substance && result.classes && result.classes.length > 0) {
                this.setInputState(input, helper, 'warning', 'Informations disponibles');
                this.showClassChoices(inputNumber, result.classes);
            } else {
                this.setInputState(input, helper, 'valid', 'Valeur valide');
                this.hideClassChoices(inputNumber);
            }

            this.options.onValidationChange(key, result);
            return result;
        } catch (error) {
            console.error('Validation error:', error);
            this.setInputState(input, helper, 'danger', 'Erreur de validation');
            this.validationState[key] = null;
            return null;
        }
    }

    /**
     * Set input visual state
     * @param {HTMLInputElement} input - Input element
     * @param {HTMLElement} helper - Helper text element
     * @param {string} state - 'default', 'danger', 'warning', 'valid'
     * @param {string} message - Helper message
     */
    setInputState(input, helper, state, message = '') {
        // Remove all state classes
        input.classList.remove('danger', 'warning', 'valide');

        // Update helper text
        if (helper) {
            helper.classList.remove('text-danger', 'text-success', 'text-warning');

            switch (state) {
                case 'danger':
                    input.classList.add('danger');
                    helper.classList.add('text-danger');
                    helper.textContent = message || 'Entrez une valeur correcte svp.';
                    break;
                case 'warning':
                    input.classList.add('warning');
                    helper.classList.add('text-warning');
                    helper.textContent = message || 'Informations disponibles';
                    break;
                case 'valid':
                    input.classList.add('valide');
                    helper.classList.add('text-success');
                    helper.textContent = message || 'Valeur valide';
                    break;
                default:
                    helper.textContent = 'Evitez les caracteres speciaux svp.';
            }
        }
    }

    /**
     * Show class choices for a substance
     * @param {number} inputNumber - 1 or 2
     * @param {Array<string>} classes - List of class names
     */
    showClassChoices(inputNumber, classes) {
        const container = document.getElementById(`choix-classe-${inputNumber}`);
        const propositions = document.getElementById(`propositions-${inputNumber}`);

        if (!container || !propositions) return;

        // Clear existing buttons
        propositions.innerHTML = '';

        // Create class buttons
        classes.forEach(className => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'btn btn-lg btn-warning rounded-pill';
            button.textContent = className;
            button.addEventListener('click', () => {
                this.selectClass(inputNumber, className);
            });
            propositions.appendChild(button);
        });

        container.classList.remove('invisible');
        container.classList.add('visible');
    }

    /**
     * Hide class choices
     * @param {number} inputNumber - 1 or 2
     */
    hideClassChoices(inputNumber) {
        const container = document.getElementById(`choix-classe-${inputNumber}`);
        if (container) {
            container.classList.add('invisible');
            container.classList.remove('visible');
        }
    }

    /**
     * Select a class from the choices
     * @param {number} inputNumber - 1 or 2
     * @param {string} className - Selected class name
     */
    selectClass(inputNumber, className) {
        const input = document.getElementById(`med-${inputNumber}`);
        if (input) {
            input.value = className;
            this.hideClassChoices(inputNumber);
            this.validateMedication(input, inputNumber === 1 ? 'med1' : 'med2');
        }
    }

    /**
     * Handle form submission
     * @param {Event} e - Submit event
     */
    async handleSubmit(e) {
        e.preventDefault();

        const med1 = this.med1Input.value.trim();
        const med2 = this.med2Input.value.trim();

        if (!med1 || !med2) {
            this.showError('Veuillez renseigner les deux medicaments.');
            return;
        }

        this.setLoading(true);
        announceToScreenReader('Recherche des interactions en cours...');

        try {
            const result = await ApiClient.getInteractions(med1, med2);
            this.renderResults(result);
            announceToScreenReader(`${result.count} interaction(s) trouvee(s).`);
        } catch (error) {
            console.error('Submission error:', error);
            if (error instanceof ApiError) {
                this.showError(error.message);
            } else {
                this.showError('Une erreur est survenue. Veuillez reessayer.');
            }
            announceToScreenReader('Erreur lors de la recherche.');
        } finally {
            this.setLoading(false);
        }
    }

    /**
     * Set loading state
     * @param {boolean} loading - Loading state
     */
    setLoading(loading) {
        if (loading) {
            this.submitButton.disabled = true;
            this.submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Recherche...';
        } else {
            this.submitButton.disabled = false;
            this.submitButton.textContent = 'Decouvrir interaction';
        }
    }

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError(message) {
        const container = this.options.resultsContainer;
        if (!container) return;

        container.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <strong>Erreur:</strong> ${escapeHtml(message)}
            </div>
        `;
    }

    /**
     * Render interaction results
     * @param {Object} data - API response data
     */
    renderResults(data) {
        const container = this.options.resultsContainer;
        if (!container) return;

        if (!data.interactions || data.interactions.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info" role="alert">
                    Aucune interaction trouvee entre <strong>${escapeHtml(data.med_1)}</strong>
                    et <strong>${escapeHtml(data.med_2)}</strong>.
                </div>
            `;
            return;
        }

        let html = `
            <div class="third" id="third" aria-live="polite">
                <div class="d-flex bg-white bg-opacity-20 justify-content-between">
                    <h3>Resultat interactions entre ${escapeHtml(data.med_1)} et ${escapeHtml(data.med_2)}</h3>
                    <button type="button" class="btn-close" aria-label="Fermer" onclick="this.closest('.third').remove()"></button>
                </div>
        `;

        data.interactions.forEach(interaction => {
            html += `
                <div class="container details">
                    <p class="title-3">
                        Composants: <span class="medName_yellow">${escapeHtml(interaction.class_1)}</span>
                        et <span class="medName_yellow">${escapeHtml(interaction.class_2)}</span>
                    </p>

                    <div class="row">
                        <div class="col">
                            <div>
                                <p class="title-4">Niveau d'interaction:</p>
                                <p class="resultat">${escapeHtml(interaction.niveau)}</p>
                            </div>
                        </div>
                    </div>

                    <div class="row mt-4">
                        <div class="col-12 col-md-4 mb-2">
                            <div>
                                <p class="title-4">Details des classes:</p>
                                <p class="resultat">${escapeHtml(interaction.details)}</p>
                            </div>
                        </div>

                        <div class="col-12 col-md-4">
                            <div>
                                <p class="title-4">Risques d'interaction:</p>
                                <p class="resultat">${escapeHtml(interaction.risques)}</p>
                            </div>
                        </div>

                        <div class="col-12 col-md-4">
                            <div>
                                <p class="title-4">Actions associees:</p>
                                <p class="resultat">${escapeHtml(interaction.actions)}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }
}

export default InteractionForm;
