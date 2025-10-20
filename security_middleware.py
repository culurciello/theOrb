"""
Security middleware for Flask application.
Implements security headers and request validation.
"""
from flask import request, jsonify
from functools import wraps
import logging

logger = logging.getLogger('orb')


def setup_security_headers(app):
    """
    Configure security headers for the Flask application.
    Equivalent to helmet.js in Express.
    """

    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""

        # Content Security Policy
        # Note: Adjust these as needed for your specific requirements
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net",
            "img-src 'self' data: https: blob:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers['Content-Security-Policy'] = '; '.join(csp_directives)

        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Strict Transport Security (HTTPS only)
        # Uncomment when using HTTPS in production
        # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy (formerly Feature-Policy)
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        return response

    logger.info('Security headers middleware configured')


def setup_request_validation(app):
    """Setup request validation middleware."""

    @app.before_request
    def validate_request():
        """Validate incoming requests."""

        # Skip validation for static files
        if request.path.startswith('/static/'):
            return None

        # Check content type for POST/PUT requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.content_type or ''

            # Only validate for API endpoints
            if request.path.startswith('/api/'):
                # Allow JSON and multipart form data
                if not (content_type.startswith('application/json') or
                       content_type.startswith('multipart/form-data') or
                       content_type.startswith('application/x-www-form-urlencoded')):
                    logger.warning(f'Invalid content type: {content_type} for {request.path}')
                    return jsonify({'error': 'Invalid content type'}), 415

        # Validate Content-Length to prevent large payload attacks
        max_content_length = app.config.get('MAX_CONTENT_LENGTH', 50 * 1024 * 1024)  # 50MB default
        content_length = request.content_length or 0

        if content_length > max_content_length:
            logger.warning(f'Request too large: {content_length} bytes from {request.remote_addr}')
            return jsonify({'error': 'Request entity too large'}), 413

        return None

    logger.info('Request validation middleware configured')


def rate_limit_exceeded_handler():
    """Handle rate limit exceeded errors."""
    return jsonify({
        'error': 'Too many requests',
        'message': 'Please slow down and try again later'
    }), 429


def setup_error_handlers(app):
    """Setup global error handlers with proper logging."""

    @app.errorhandler(400)
    def bad_request(error):
        logger.error(f'Bad request: {error}', extra={
            'path': request.path,
            'method': request.method,
            'ip': request.remote_addr
        })
        return jsonify({'error': 'Bad request', 'message': str(error)}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        logger.warning(f'Unauthorized access attempt: {request.path}', extra={
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent')
        })
        return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401

    @app.errorhandler(403)
    def forbidden(error):
        logger.warning(f'Forbidden access attempt: {request.path}', extra={
            'ip': request.remote_addr
        })
        return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found', 'message': 'Resource not found'}), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        logger.warning(f'Request too large from {request.remote_addr}')
        return jsonify({'error': 'Request too large', 'message': 'File or request size exceeds limit'}), 413

    @app.errorhandler(415)
    def unsupported_media_type(error):
        logger.warning(f'Unsupported media type: {request.content_type}')
        return jsonify({'error': 'Unsupported media type'}), 415

    @app.errorhandler(429)
    def too_many_requests(error):
        logger.warning(f'Rate limit exceeded from {request.remote_addr}')
        return rate_limit_exceeded_handler()

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error(f'Internal server error: {error}', extra={
            'path': request.path,
            'method': request.method,
            'ip': request.remote_addr
        }, exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        logger.error(f'Unexpected error: {error}', extra={
            'path': request.path,
            'method': request.method,
            'ip': request.remote_addr
        }, exc_info=True)
        return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500

    logger.info('Error handlers configured')


def secure_route(f):
    """
    Decorator to add additional security checks to routes.
    Use this for sensitive endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log access to sensitive endpoints
        logger.info(f'Access to secured route: {request.path}', extra={
            'user': getattr(request, 'user', 'anonymous'),
            'ip': request.remote_addr,
            'method': request.method
        })

        return f(*args, **kwargs)

    return decorated_function
