/**
 * Client-side sanitization utilities for XSS protection.
 * This provides a lightweight alternative to DOMPurify for basic sanitization.
 */

const Sanitizer = {
    /**
     * Sanitize HTML string to prevent XSS attacks.
     * Removes all HTML tags and returns plain text.
     *
     * @param {string} input - The input string to sanitize
     * @returns {string} - Sanitized string
     */
    sanitizeHTML(input) {
        if (typeof input !== 'string') {
            return '';
        }

        // Create a temporary div element to leverage browser's HTML parsing
        const temp = document.createElement('div');
        temp.textContent = input;
        return temp.innerHTML;
    },

    /**
     * Escape HTML special characters to prevent XSS.
     *
     * @param {string} str - The string to escape
     * @returns {string} - Escaped string
     */
    escapeHTML(str) {
        if (typeof str !== 'string') {
            return '';
        }

        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;',
            '/': '&#x2F;'
        };

        return str.replace(/[&<>"'\/]/g, char => map[char]);
    },

    /**
     * Validate and sanitize user input.
     *
     * @param {string} input - The input to validate
     * @param {Object} options - Validation options
     * @returns {string} - Sanitized input
     * @throws {Error} - If validation fails
     */
    validateInput(input, options = {}) {
        const {
            maxLength = 1000,
            minLength = 0,
            pattern = null,
            fieldName = 'Input'
        } = options;

        if (!input || typeof input !== 'string') {
            throw new Error(`${fieldName} must be a non-empty string`);
        }

        const trimmed = input.trim();

        if (trimmed.length < minLength) {
            throw new Error(`${fieldName} must be at least ${minLength} characters`);
        }

        if (trimmed.length > maxLength) {
            throw new Error(`${fieldName} must not exceed ${maxLength} characters`);
        }

        if (pattern && !pattern.test(trimmed)) {
            throw new Error(`${fieldName} contains invalid characters`);
        }

        return trimmed;
    },

    /**
     * Sanitize URL to prevent javascript: and data: URIs.
     *
     * @param {string} url - The URL to sanitize
     * @returns {string|null} - Sanitized URL or null if invalid
     */
    sanitizeURL(url) {
        if (typeof url !== 'string') {
            return null;
        }

        const trimmed = url.trim().toLowerCase();

        // Block dangerous protocols
        if (trimmed.startsWith('javascript:') ||
            trimmed.startsWith('data:') ||
            trimmed.startsWith('vbscript:') ||
            trimmed.startsWith('file:')) {
            console.warn('Blocked potentially dangerous URL:', url);
            return null;
        }

        return url.trim();
    },

    /**
     * Safely set element text content (prevents XSS).
     *
     * @param {HTMLElement} element - The element to update
     * @param {string} text - The text to set
     */
    setTextContent(element, text) {
        if (!element || !element.textContent === undefined) {
            console.error('Invalid element provided to setTextContent');
            return;
        }

        element.textContent = String(text || '');
    },

    /**
     * Safely set innerHTML with sanitization.
     * Only use this when you specifically need to render HTML.
     * For plain text, use setTextContent instead.
     *
     * @param {HTMLElement} element - The element to update
     * @param {string} html - The HTML to set (will be sanitized)
     */
    setInnerHTML(element, html) {
        if (!element) {
            console.error('Invalid element provided to setInnerHTML');
            return;
        }

        // For maximum safety, use textContent unless specifically rendering HTML
        element.innerHTML = this.escapeHTML(String(html || ''));
    },

    /**
     * Validate email format.
     *
     * @param {string} email - The email to validate
     * @returns {boolean} - True if valid
     */
    isValidEmail(email) {
        if (typeof email !== 'string') {
            return false;
        }

        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        return emailRegex.test(email.trim());
    },

    /**
     * Validate username format.
     *
     * @param {string} username - The username to validate
     * @returns {boolean} - True if valid
     */
    isValidUsername(username) {
        if (typeof username !== 'string') {
            return false;
        }

        const usernameRegex = /^[a-zA-Z0-9_-]{3,50}$/;
        return usernameRegex.test(username.trim());
    },

    /**
     * Sanitize form data before submission.
     *
     * @param {FormData} formData - The form data to sanitize
     * @returns {Object} - Sanitized data object
     */
    sanitizeFormData(formData) {
        const sanitized = {};

        for (let [key, value] of formData.entries()) {
            if (typeof value === 'string') {
                sanitized[key] = this.escapeHTML(value.trim());
            } else {
                sanitized[key] = value;
            }
        }

        return sanitized;
    }
};

// Make it available globally
window.Sanitizer = Sanitizer;
