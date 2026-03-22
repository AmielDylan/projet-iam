/**
 * Application configuration
 * Uses relative URLs for portability across environments
 */
const Config = {
    // API endpoints (relative URLs)
    api: {
        validate: '/api/v1/validate',
        interactions: '/api/v1/interactions',
        autocomplete: '/api/v1/autocomplete',
        classes: '/api/v1/classes'
    },

    // Legacy endpoints (for backward compatibility)
    legacy: {
        testClasse: '/testClasse',
        testSubstance: '/testSubstance',
        testSpecialite: '/testSpecialite',
        getListClasses: '/getListClasses',
        autocomplete: '/autocomplete_input'
    },

    // UI settings
    ui: {
        debounceDelay: 300,
        autocompleteMinChars: 1,
        maxAutocompleteResults: 6
    }
};

// Freeze config to prevent modifications
Object.freeze(Config);
Object.freeze(Config.api);
Object.freeze(Config.legacy);
Object.freeze(Config.ui);

export default Config;
