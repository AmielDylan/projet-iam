/**
 * API Client for backend communication
 */
import Config from './config.js';

class ApiClient {
    /**
     * Make a POST request with JSON body
     * @param {string} url - Endpoint URL
     * @param {Object} data - Request body data
     * @returns {Promise<Object>} Response data
     */
    static async postJson(url, data) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new ApiError(
                errorData.error || 'Request failed',
                response.status,
                errorData
            );
        }

        return response.json();
    }

    /**
     * Make a POST request with form data
     * @param {string} url - Endpoint URL
     * @param {Object} data - Form data as object
     * @returns {Promise<Object>} Response data
     */
    static async postForm(url, data) {
        const formData = new FormData();
        Object.entries(data).forEach(([key, value]) => {
            formData.append(key, value);
        });

        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new ApiError('Request failed', response.status);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return response.json();
        }
        return response.text();
    }

    /**
     * Make a GET request
     * @param {string} url - Endpoint URL
     * @param {Object} params - Query parameters
     * @returns {Promise<Object>} Response data
     */
    static async get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;

        const response = await fetch(fullUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new ApiError('Request failed', response.status);
        }

        return response.json();
    }

    /**
     * Validate a medication (single API call replacing 3 legacy calls)
     * @param {string} medication - Medication name
     * @returns {Promise<Object>} Validation result
     */
    static async validateMedication(medication) {
        return this.postJson(Config.api.validate, { medication });
    }

    /**
     * Get interactions between two medications
     * @param {string} med1 - First medication
     * @param {string} med2 - Second medication
     * @returns {Promise<Object>} Interaction results
     */
    static async getInteractions(med1, med2) {
        return this.postJson(Config.api.interactions, {
            med_1: med1,
            med_2: med2
        });
    }

    /**
     * Get autocomplete suggestions
     * @param {string} query - Search query
     * @returns {Promise<Array>} Autocomplete results
     */
    static async getAutocomplete(query) {
        return this.get(Config.api.autocomplete, { q: query });
    }

    /**
     * Get classes for a substance
     * @param {string} substance - Substance name
     * @returns {Promise<Object>} Classes result
     */
    static async getClasses(substance) {
        return this.postJson(Config.api.classes, { substance });
    }
}

/**
 * Custom error class for API errors
 */
class ApiError extends Error {
    constructor(message, status, data = {}) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
}

export { ApiClient, ApiError };
