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
        // Remove error state class only
        input.classList.remove('danger');

        if (helper) {
            helper.classList.remove('text-danger');

            switch (state) {
                case 'danger':
                    input.classList.add('danger');
                    helper.classList.add('text-danger');
                    helper.textContent = message || 'Entrez une valeur correcte svp.';
                    break;
                default:
                    helper.textContent = 'Entrez le nom d\'un médicament, substance ou classe.';
            }
        }
    }

    /**
     * Show class information notice (informational only, not interactive)
     * @param {number} inputNumber - 1 or 2
     * @param {Array<string>} classes - List of class names
     */
    showClassChoices(inputNumber, classes) {
        const container = document.getElementById(`choix-classe-${inputNumber}`);
        if (!container) return;

        const listItems = classes.map(c => `<li>${escapeHtml(c)}</li>`).join('');

        container.innerHTML = `
            <div class="class-notice" role="note">
                <div class="class-notice__header">
                    <span class="class-notice__icon">ℹ</span>
                    <span>Cette substance appartient à plusieurs classes</span>
                    <button class="class-notice__close" aria-label="Fermer" type="button">✕</button>
                </div>
                <ul class="class-notice__list">${listItems}</ul>
            </div>
        `;

        container.querySelector('.class-notice__close').addEventListener('click', () => {
            this.hideClassChoices(inputNumber);
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
            container.innerHTML = '';
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
     * Map niveau string to CSS severity class
     * @param {string} niveau
     * @returns {string} CSS class
     */
    getSeverityClass(niveau) {
        const n = (niveau || '').toLowerCase();
        if (n.includes('contre') || n.includes('ci')) return 'niveau--ci';
        if (n.includes('d\u00e9conseil') || n.includes('deconseil')) return 'niveau--ad';
        if (n.includes('pr\u00e9caution') || n.includes('precaution')) return 'niveau--pe';
        return 'niveau--aptc';
    }

    /**
     * Render interaction results
     * @param {Object} data - API response data
     */
    renderResults(data) {
        const container = this.options.resultsContainer;
        if (!container) return;

        const topSeverityClass = data.interactions && data.interactions.length > 0
            ? this.getSeverityClass(data.interactions[0].niveau)
            : 'niveau--aptc';
        const cardModifier = topSeverityClass.replace('niveau--', 'rx-card--');

        if (!data.interactions || data.interactions.length === 0) {
            container.innerHTML = `
                <div class="rx-card ${cardModifier}" role="alert">
                    <div class="rx-card__header">
                        <div class="rx-card__title">
                            <span class="rx-card__label">Résultat</span>
                            <span class="rx-card__meds">${escapeHtml(data.med_1)} × ${escapeHtml(data.med_2)}</span>
                        </div>
                    </div>
                    <div style="padding: var(--space-6); color: var(--color-text-secondary); font-size: var(--text-sm);">
                        Aucune interaction trouvée entre ces deux médicaments.
                    </div>
                </div>
            `;
            return;
        }

        const interactionsHtml = data.interactions.map(interaction => {
            const severityClass = this.getSeverityClass(interaction.niveau);
            return `
                <div class="rx-interaction">
                    <p class="rx-classes">${escapeHtml(interaction.class_1)} — ${escapeHtml(interaction.class_2)}</p>
                    <div class="rx-interaction__body">
                        <div class="rx-niveau-row">
                            <span class="rx-section__label">Niveau d'interaction</span>
                            <span class="rx-niveau ${severityClass}">${escapeHtml(interaction.niveau)}</span>
                        </div>
                        <div class="rx-section">
                            <p class="rx-section__label">Détails des classes</p>
                            <p class="rx-section__value">${escapeHtml(interaction.details)}</p>
                        </div>
                        <div class="rx-section">
                            <p class="rx-section__label">Risques</p>
                            <p class="rx-section__value">${escapeHtml(interaction.risques)}</p>
                        </div>
                        <div class="rx-section">
                            <p class="rx-section__label">Conduite à tenir</p>
                            <p class="rx-section__value">${escapeHtml(interaction.actions)}</p>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = `
            <div class="rx-card ${cardModifier}" id="third" aria-live="polite">
                <div class="rx-card__header">
                    <div class="rx-card__title">
                        <span class="rx-card__label">Interactions médicamenteuses</span>
                        <span class="rx-card__meds">${escapeHtml(data.med_1)} × ${escapeHtml(data.med_2)}</span>
                    </div>
                    <button class="rx-card__close" type="button" aria-label="Fermer"
                        onclick="this.closest('.rx-card').remove()">✕</button>
                </div>
                ${interactionsHtml}
            </div>
        `;
    }
}

export default InteractionForm;
