"""
Security utilities for input validation and sanitization.
"""
import re
from typing import Any, Optional
from flask import request
import logging

logger = logging.getLogger('orb')


class InputValidator:
    """Input validation utilities."""

    # Common validation patterns
    PATTERNS = {
        'alphanumeric': re.compile(r'^[a-zA-Z0-9\s\-_]+$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'username': re.compile(r'^[a-zA-Z0-9_-]{3,50}$'),
        'filename': re.compile(r'^[a-zA-Z0-9\s\-_\.]+$'),
        'collection_name': re.compile(r'^[a-zA-Z0-9\s\-_\.]{1,100}$'),
    }

    # Maximum lengths
    MAX_LENGTHS = {
        'username': 50,
        'email': 100,
        'password': 128,
        'collection_name': 100,
        'message': 10000,
        'filename': 255,
        'api_key': 500,
    }

    @staticmethod
    def validate_string(value: Any, field_name: str = 'input',
                       min_length: int = 1, max_length: Optional[int] = None,
                       pattern: Optional[str] = None) -> str:
        """
        Validate and sanitize string input.

        Args:
            value: Input value to validate
            field_name: Name of the field for error messages
            min_length: Minimum allowed length
            max_length: Maximum allowed length
            pattern: Regex pattern name from PATTERNS dict

        Returns:
            Validated and stripped string

        Raises:
            ValueError: If validation fails
        """
        if not value or not isinstance(value, str):
            raise ValueError(f'{field_name} must be a non-empty string')

        value = value.strip()

        if len(value) < min_length:
            raise ValueError(f'{field_name} must be at least {min_length} characters')

        if max_length and len(value) > max_length:
            raise ValueError(f'{field_name} must not exceed {max_length} characters')

        if pattern and pattern in InputValidator.PATTERNS:
            if not InputValidator.PATTERNS[pattern].match(value):
                raise ValueError(f'{field_name} contains invalid characters')

        return value

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email address."""
        email = InputValidator.validate_string(
            email,
            'Email',
            max_length=InputValidator.MAX_LENGTHS['email']
        )

        if not InputValidator.PATTERNS['email'].match(email):
            raise ValueError('Invalid email format')

        return email.lower()

    @staticmethod
    def validate_username(username: str) -> str:
        """Validate username."""
        username = InputValidator.validate_string(
            username,
            'Username',
            min_length=3,
            max_length=InputValidator.MAX_LENGTHS['username']
        )

        if not InputValidator.PATTERNS['username'].match(username):
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')

        return username

    @staticmethod
    def validate_password(password: str) -> str:
        """Validate password strength."""
        if not password or not isinstance(password, str):
            raise ValueError('Password is required')

        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters long')

        if len(password) > InputValidator.MAX_LENGTHS['password']:
            raise ValueError(f'Password must not exceed {InputValidator.MAX_LENGTHS["password"]} characters')

        # Check for at least one letter and one number
        if not re.search(r'[a-zA-Z]', password) or not re.search(r'[0-9]', password):
            raise ValueError('Password must contain at least one letter and one number')

        return password

    @staticmethod
    def validate_collection_name(name: str) -> str:
        """Validate collection name."""
        return InputValidator.validate_string(
            name,
            'Collection name',
            min_length=1,
            max_length=InputValidator.MAX_LENGTHS['collection_name'],
            pattern='collection_name'
        )

    @staticmethod
    def validate_integer(value: Any, field_name: str = 'value',
                        min_value: Optional[int] = None,
                        max_value: Optional[int] = None) -> int:
        """Validate integer input."""
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValueError(f'{field_name} must be a valid integer')

        if min_value is not None and int_value < min_value:
            raise ValueError(f'{field_name} must be at least {min_value}')

        if max_value is not None and int_value > max_value:
            raise ValueError(f'{field_name} must not exceed {max_value}')

        return int_value

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage."""
        from werkzeug.utils import secure_filename

        if not filename:
            raise ValueError('Filename is required')

        # Use werkzeug's secure_filename as base
        safe_name = secure_filename(filename)

        if not safe_name:
            raise ValueError('Invalid filename')

        # Additional validation
        if len(safe_name) > InputValidator.MAX_LENGTHS['filename']:
            raise ValueError(f'Filename too long (max {InputValidator.MAX_LENGTHS["filename"]} characters)')

        return safe_name


def log_security_event(event_type: str, details: dict):
    """Log security-related events."""
    logger.warning(f'SECURITY EVENT: {event_type}', extra={
        'event_type': event_type,
        'ip_address': request.remote_addr if request else 'unknown',
        'user_agent': request.headers.get('User-Agent') if request else 'unknown',
        **details
    })
