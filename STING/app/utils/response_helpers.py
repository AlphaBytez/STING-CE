"""
Response helper utilities for consistent API responses
"""

from flask import jsonify
from typing import Any, Dict, Optional


def success_response(data: Any = None, message: str = "Success", status_code: int = 200) -> tuple:
    """
    Create a standardized success response
    
    Args:
        data: Response data (optional)
        message: Success message
        status_code: HTTP status code
        
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        "success": True,
        "message": message
    }
    
    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response["data"] = data
    
    return jsonify(response), status_code


def error_response(message: str, status_code: int = 400, error_code: str = None, details: Dict = None) -> tuple:
    """
    Create a standardized error response
    
    Args:
        message: Error message
        status_code: HTTP status code
        error_code: Optional error code for client handling
        details: Optional additional error details
        
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        "success": False,
        "error": message
    }
    
    if error_code:
        response["code"] = error_code
        
    if details:
        response["details"] = details
    
    return jsonify(response), status_code


def validation_error_response(errors: Dict, message: str = "Validation failed") -> tuple:
    """
    Create a validation error response
    
    Args:
        errors: Dictionary of field validation errors
        message: Error message
        
    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        message=message,
        status_code=422,
        error_code="VALIDATION_ERROR",
        details={"field_errors": errors}
    )


def not_found_response(resource: str = "Resource") -> tuple:
    """
    Create a not found error response
    
    Args:
        resource: Name of the resource that wasn't found
        
    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        message=f"{resource} not found",
        status_code=404,
        error_code="NOT_FOUND"
    )


def unauthorized_response(message: str = "Authentication required") -> tuple:
    """
    Create an unauthorized error response
    
    Args:
        message: Error message
        
    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        message=message,
        status_code=401,
        error_code="UNAUTHORIZED"
    )


def forbidden_response(message: str = "Access denied") -> tuple:
    """
    Create a forbidden error response
    
    Args:
        message: Error message
        
    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        message=message,
        status_code=403,
        error_code="FORBIDDEN"
    )


def server_error_response(message: str = "Internal server error") -> tuple:
    """
    Create a server error response
    
    Args:
        message: Error message
        
    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        message=message,
        status_code=500,
        error_code="INTERNAL_ERROR"
    )