"""
Safe Error Handling Utilities

This module provides utilities to prevent stack trace exposure in API responses.
Stack traces can reveal internal implementation details that aid attackers.

Usage:
    from app.utils.safe_errors import safe_error_response, log_and_sanitize_error

    # In route handlers:
    except Exception as e:
        return safe_error_response(e, "Failed to process request", logger)
"""

import logging
import traceback
import os
from flask import jsonify
from typing import Tuple, Optional

# Only show detailed errors in development
DEBUG_MODE = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'


def log_and_sanitize_error(
    error: Exception,
    user_message: str,
    logger: logging.Logger,
    log_level: int = logging.ERROR
) -> str:
    """
    Log the full error details server-side and return a sanitized message for users.

    Args:
        error: The exception that occurred
        user_message: A safe message to show users (no internal details)
        logger: The logger instance to use
        log_level: The logging level (default: ERROR)

    Returns:
        The sanitized user message (or full error in debug mode)
    """
    # Always log full details server-side
    logger.log(log_level, f"{user_message}: {str(error)}")
    logger.log(logging.DEBUG, f"Full traceback: {traceback.format_exc()}")

    # In debug mode, include error details for developers
    if DEBUG_MODE:
        return f"{user_message}: {str(error)}"

    # In production, return only the safe user message
    return user_message


def safe_error_response(
    error: Exception,
    user_message: str,
    logger: logging.Logger,
    status_code: int = 500,
    log_level: int = logging.ERROR
) -> Tuple:
    """
    Create a safe JSON error response that doesn't expose stack traces.

    Args:
        error: The exception that occurred
        user_message: A safe message to show users (no internal details)
        logger: The logger instance to use
        status_code: HTTP status code (default: 500)
        log_level: The logging level (default: ERROR)

    Returns:
        Tuple of (jsonify response, status_code)
    """
    sanitized_message = log_and_sanitize_error(error, user_message, logger, log_level)

    return jsonify({'error': sanitized_message}), status_code


def safe_error_dict(
    error: Exception,
    user_message: str,
    logger: logging.Logger,
    log_level: int = logging.ERROR
) -> dict:
    """
    Create a safe error dictionary that doesn't expose stack traces.
    Useful for non-Flask contexts or when you need more control over the response.

    Args:
        error: The exception that occurred
        user_message: A safe message to show users (no internal details)
        logger: The logger instance to use
        log_level: The logging level (default: ERROR)

    Returns:
        Dictionary with 'error' and 'success' keys
    """
    sanitized_message = log_and_sanitize_error(error, user_message, logger, log_level)

    return {
        'success': False,
        'error': sanitized_message
    }
