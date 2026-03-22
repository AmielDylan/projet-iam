/**
 * Autocomplete functionality with debouncing
 */
import Config from './config.js';
import { ApiClient } from './api.js';
import { debounce, escapeHtml, createElement } from './utils.js';

class Autocomplete {
    /**
     * Initialize autocomplete for an input field
     * @param {HTMLInputElement} input - Input element
     * @param {Object} options - Configuration options
     */
    constructor(input, options = {}) {
        this.input = input;
        this.options = {
            minChars: options.minChars || Config.ui.autocompleteMinChars,
            debounceDelay: options.debounceDelay || Config.ui.debounceDelay,
            onSelect: options.onSelect || (() => {}),
            containerClass: options.containerClass || 'autocomplete-container'
        };

        this.container = this.createContainer();
        this.isOpen = false;
        this.selectedIndex = -1;
        this.results = [];

        this.bindEvents();
    }

    /**
     * Create autocomplete dropdown container
     * @returns {HTMLElement}
     */
    createContainer() {
        // Find existing container or create new one
        const inputId = this.input.id;
        const containerId = `autocomplete-container-${inputId.replace('med-', '')}`;
        let container = document.getElementById(containerId);

        if (!container) {
            container = createElement('div', {
                id: containerId,
                className: this.options.containerClass,
                role: 'listbox',
                'aria-label': 'Suggestions'
            });
            this.input.parentNode.insertBefore(container, this.input.nextSibling);
        }

        return container;
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Debounced search
        const debouncedSearch = debounce(
            this.search.bind(this),
            this.options.debounceDelay
        );

        this.input.addEventListener('input', (e) => {
            const value = e.target.value.trim();
            if (value.length >= this.options.minChars) {
                debouncedSearch(value);
            } else {
                this.close();
            }
        });

        // Keyboard navigation
        this.input.addEventListener('keydown', this.handleKeydown.bind(this));

        // Close on blur (with delay for click handling)
        this.input.addEventListener('blur', () => {
            setTimeout(() => this.close(), 200);
        });

        // Reopen on focus if there's a value
        this.input.addEventListener('focus', () => {
            const value = this.input.value.trim();
            if (value.length >= this.options.minChars && this.results.length > 0) {
                this.render();
            }
        });
    }

    /**
     * Handle keyboard navigation
     * @param {KeyboardEvent} e
     */
    handleKeydown(e) {
        if (!this.isOpen) return;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.navigate(1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navigate(-1);
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0) {
                    this.select(this.results[this.selectedIndex]);
                }
                break;
            case 'Escape':
                e.preventDefault();
                this.close();
                break;
        }
    }

    /**
     * Navigate through results
     * @param {number} direction - 1 for down, -1 for up
     */
    navigate(direction) {
        const items = this.container.querySelectorAll('.autocomplete-item');
        if (items.length === 0) return;

        // Remove previous selection
        if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
            items[this.selectedIndex].classList.remove('selected');
        }

        // Update index
        this.selectedIndex += direction;
        if (this.selectedIndex < 0) {
            this.selectedIndex = items.length - 1;
        } else if (this.selectedIndex >= items.length) {
            this.selectedIndex = 0;
        }

        // Apply new selection
        items[this.selectedIndex].classList.add('selected');
        items[this.selectedIndex].scrollIntoView({ block: 'nearest' });
    }

    /**
     * Search for autocomplete suggestions
     * @param {string} query - Search query
     */
    async search(query) {
        try {
            this.results = await ApiClient.getAutocomplete(query);
            this.render();
        } catch (error) {
            console.error('Autocomplete error:', error);
            this.results = [];
            this.close();
        }
    }

    /**
     * Render autocomplete suggestions
     */
    render() {
        this.container.innerHTML = '';
        this.selectedIndex = -1;

        if (this.results.length === 0) {
            this.close();
            return;
        }

        this.results.forEach((result, index) => {
            const item = createElement('div', {
                className: 'autocomplete-item',
                role: 'option',
                'aria-selected': 'false',
                dataset: { index: index.toString() },
                onClick: () => this.select(result)
            }, escapeHtml(result.resultat));

            // Add type badge if available
            if (result.type) {
                const badge = createElement('span', {
                    className: `autocomplete-type autocomplete-type--${result.type}`
                }, result.type);
                item.appendChild(badge);
            }

            this.container.appendChild(item);
        });

        this.isOpen = true;
        this.input.setAttribute('aria-expanded', 'true');
    }

    /**
     * Select a result
     * @param {Object} result - Selected result
     */
    select(result) {
        this.input.value = result.resultat;
        this.close();
        this.options.onSelect(result);
    }

    /**
     * Close autocomplete dropdown
     */
    close() {
        this.container.innerHTML = '';
        this.isOpen = false;
        this.selectedIndex = -1;
        this.input.setAttribute('aria-expanded', 'false');
    }
}

export default Autocomplete;
