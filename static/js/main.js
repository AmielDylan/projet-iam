/**
 * Main application entry point
 */
import Autocomplete from './autocomplete.js';
import InteractionForm from './form.js';

class App {
    constructor() {
        this.form = null;
        this.autocomplete1 = null;
        this.autocomplete2 = null;
    }

    /**
     * Initialize the application
     */
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    /**
     * Setup all components
     */
    setup() {
        this.setupForm();
        this.setupAutocomplete();
        this.setupClassChoices();
        this.setupAccessibility();
    }

    /**
     * Setup the interaction form
     */
    setupForm() {
        const formElement = document.getElementById('medForm');
        if (!formElement) return;

        // Create results container if it doesn't exist
        let resultsContainer = document.getElementById('results-container');
        if (!resultsContainer) {
            resultsContainer = document.createElement('div');
            resultsContainer.id = 'results-container';
            resultsContainer.className = 'container last';
            resultsContainer.setAttribute('aria-live', 'polite');

            // Find existing results div or append after form
            const existingResults = document.querySelector('.container.last');
            if (existingResults) {
                resultsContainer = existingResults;
                resultsContainer.id = 'results-container';
            } else {
                formElement.parentNode.insertBefore(resultsContainer, formElement.nextSibling);
            }
        }

        this.form = new InteractionForm(formElement, {
            resultsContainer: resultsContainer
        });
    }

    /**
     * Setup autocomplete for medication inputs
     */
    setupAutocomplete() {
        const input1 = document.getElementById('med-1');
        const input2 = document.getElementById('med-2');

        if (input1) {
            this.autocomplete1 = new Autocomplete(input1, {
                onSelect: (result) => {
                    if (this.form) {
                        this.form.validateMedication(input1, 'med1');
                    }
                }
            });
        }

        if (input2) {
            this.autocomplete2 = new Autocomplete(input2, {
                onSelect: (result) => {
                    if (this.form) {
                        this.form.validateMedication(input2, 'med2');
                    }
                }
            });
        }
    }

    /**
     * Setup class choice visibility
     */
    setupClassChoices() {
        const choices1 = document.getElementById('choix-classe-1');
        const choices2 = document.getElementById('choix-classe-2');

        if (choices1) {
            choices1.classList.add('invisible');
        }
        if (choices2) {
            choices2.classList.add('invisible');
        }
    }

    /**
     * Setup accessibility features
     */
    setupAccessibility() {
        // Create screen reader announcer
        if (!document.getElementById('sr-announcer')) {
            const announcer = document.createElement('div');
            announcer.id = 'sr-announcer';
            announcer.className = 'sr-only';
            announcer.setAttribute('aria-live', 'polite');
            announcer.setAttribute('aria-atomic', 'true');
            document.body.appendChild(announcer);
        }

        // Add focus handlers for inputs
        const inputs = document.querySelectorAll('input[type="text"]');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                this.clearInputBorder(input);
            });
        });
    }

    /**
     * Clear input validation styles
     * @param {HTMLInputElement} input
     */
    clearInputBorder(input) {
        input.classList.remove('danger', 'warning', 'valide');

        const inputNumber = input.id === 'med-1' ? 1 : 2;
        const helper = document.getElementById(`med-${inputNumber}-helper`);

        if (helper) {
            helper.classList.remove('text-danger', 'text-success', 'text-warning');
            helper.textContent = 'Evitez les caracteres speciaux svp.';
        }

        // Hide class choices
        const choices = document.getElementById(`choix-classe-${inputNumber}`);
        if (choices) {
            choices.classList.add('invisible');
            choices.classList.remove('visible');
        }
    }
}

// Initialize the application
const app = new App();
app.init();

// Export for potential use
export default App;
