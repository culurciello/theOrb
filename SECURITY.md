# Security Implementation Guide

This document outlines the security measures implemented in theOrb-web application.

## Overview

The following security enhancements have been implemented to protect against common web vulnerabilities:

1. Cross-Site Scripting (XSS) Protection
2. Security Headers
3. Input Validation and Sanitization
4. Proper Error Handling
5. Environment Configuration
6. CORS Configuration
7. Rate Limiting (Coming Soon)
8. Secure Dependencies

---

## 1. Cross-Site Scripting (XSS) Protection

### Client-Side Protection

**File: `static/js/sanitize.js`**

A comprehensive sanitization library that provides:

- HTML escaping for user-generated content
- URL validation to prevent javascript: and data: URIs
- Input validation with configurable constraints
- Safe DOM manipulation methods

**Usage Example:**

```javascript
// Escape HTML special characters
const safe = Sanitizer.escapeHTML(userInput);

// Validate input
const validated = Sanitizer.validateInput(input, {
    maxLength: 100,
    minLength: 3,
    pattern: /^[a-zA-Z0-9]+$/,
    fieldName: 'Username'
});

// Safely set text content
Sanitizer.setTextContent(element, userText);
```

### Server-Side Protection

**File: `security_utils.py`**

Input validation utilities with strict type checking and pattern matching.

**Usage Example:**

```python
from security_utils import InputValidator

# Validate username
username = InputValidator.validate_username(raw_username)

# Validate email
email = InputValidator.validate_email(raw_email)

# Validate collection name
collection_name = InputValidator.validate_collection_name(raw_name)
```

---

## 2. Security Headers

**File: `security_middleware.py`**

Implements comprehensive security headers equivalent to helmet.js:

### Headers Implemented

- **Content-Security-Policy (CSP)**: Prevents unauthorized script execution
- **X-Frame-Options**: Prevents clickjacking attacks
- **X-Content-Type-Options**: Prevents MIME-type sniffing
- **X-XSS-Protection**: Enables browser XSS filtering
- **Referrer-Policy**: Controls referrer information
- **Permissions-Policy**: Restricts browser feature access

### Production Recommendations

For production environments, uncomment the Strict-Transport-Security header in `security_middleware.py`:

```python
response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
```

---

## 3. Input Validation and Sanitization

### Validation Rules

**Usernames:**
- 3-50 characters
- Letters, numbers, hyphens, underscores only

**Emails:**
- Valid email format
- Maximum 100 characters

**Passwords:**
- Minimum 8 characters
- Must contain letters and numbers
- Maximum 128 characters

**Collection Names:**
- 1-100 characters
- Alphanumeric with spaces, hyphens, underscores, periods

### Server-Side Validation Example

```python
from security_utils import InputValidator

try:
    # Validate user input
    username = InputValidator.validate_username(request.form.get('username'))
    email = InputValidator.validate_email(request.form.get('email'))
    password = InputValidator.validate_password(request.form.get('password'))

except ValueError as e:
    return jsonify({'error': str(e)}), 400
```

### Client-Side Validation Example

```javascript
try {
    // Validate before submission
    const username = Sanitizer.validateInput(input, {
        maxLength: 50,
        minLength: 3,
        fieldName: 'Username'
    });

    if (!Sanitizer.isValidEmail(email)) {
        throw new Error('Invalid email format');
    }

} catch (error) {
    displayError(error.message);
}
```

---

## 4. Error Handling and Logging

### Centralized Error Handlers

**File: `security_middleware.py` - `setup_error_handlers()`**

Implements global error handlers for:
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 413 Request Too Large
- 429 Too Many Requests
- 500 Internal Server Error

### Logging Configuration

**File: `app.py` - `setup_logging()`**

- Rotating file handler (10MB per file, 10 backups)
- Console output for development
- Structured log format with timestamps
- Separate logs directory

### Security Event Logging

```python
from security_utils import log_security_event

log_security_event('suspicious_login', {
    'username': username,
    'reason': 'Multiple failed attempts'
})
```

---

## 5. Environment Configuration

### Environment Variables

**File: `.env.example`**

All sensitive configuration is stored in environment variables:

```bash
# Security
SECRET_KEY=your-secret-key-here
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
MAX_CONTENT_LENGTH=52428800

# Database
DATABASE_URL=sqlite:///orb.db
MYSQL_PASSWORD=secure-password

# API Keys
ANTHROPIC_API_KEY=your-api-key
```

### Setup Instructions

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update all placeholder values with your actual configuration

3. **IMPORTANT**: Never commit `.env` file to version control

4. In production, use a strong SECRET_KEY:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

---

## 6. CORS Configuration

**File: `app.py`**

Properly configured CORS with:
- Allowed origins from environment variable
- Specific HTTP methods (GET, POST, PUT, DELETE, OPTIONS)
- Controlled headers (Content-Type, Authorization)
- Credentials support
- Pre-flight cache (1 hour)

### Configuration

```python
cors_origins = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS(app,
     origins=cors_origins,
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True,
     max_age=3600)
```

---

## 7. Request Validation

**File: `security_middleware.py` - `setup_request_validation()`**

### Features

- Content-Type validation for POST/PUT requests
- Content-Length validation (prevents large payload attacks)
- Automatic rejection of oversized requests

### Configuration

Set max content length in environment:
```bash
MAX_CONTENT_LENGTH=52428800  # 50MB
```

---

## 8. Dependency Security

### Updated Dependencies

```
Flask>=2.3.0
Flask-SQLAlchemy>=3.0.0
Flask-CORS>=4.0.0
Flask-Login>=0.6.3
Flask-Limiter>=3.5.0
Werkzeug>=3.0.0
email-validator>=2.1.0
```

### Security Maintenance

Run these commands regularly:

```bash
# Check for known vulnerabilities
pip install safety
safety check

# Update dependencies
pip install --upgrade -r requirements.txt

# Audit dependencies
pip-audit
```

---

## Security Best Practices

### For Development

1. Always use `.env` file for sensitive configuration
2. Never hardcode API keys or passwords
3. Test with `BYPASS_AUTH=false` to ensure proper authentication
4. Use strong, unique passwords for test accounts

### For Production

1. Set `FLASK_ENV=production`
2. Use HTTPS (enable HSTS header)
3. Generate strong SECRET_KEY
4. Configure proper ALLOWED_ORIGINS
5. Enable rate limiting (see below)
6. Regular security audits
7. Keep dependencies updated
8. Monitor logs for suspicious activity

### Rate Limiting (Recommended)

Add rate limiting to prevent brute force attacks:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Protect login endpoint
@bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # ...
```

---

## Vulnerability Reporting

If you discover a security vulnerability, please email: security@example.com

**Do not** open public issues for security vulnerabilities.

---

## Security Checklist

- [x] XSS Protection (client and server-side)
- [x] Security Headers
- [x] Input Validation
- [x] Error Handling and Logging
- [x] Environment Configuration
- [x] CORS Configuration
- [x] Request Validation
- [x] Dependency Updates
- [ ] Rate Limiting (recommended)
- [ ] HTTPS/TLS (production only)
- [ ] Security Audits
- [ ] Penetration Testing

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

---

## License

MIT License - See LICENSE file for details
