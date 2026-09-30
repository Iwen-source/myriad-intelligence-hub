"""
Shared utility module for the AI Empowerment Platform Flask server.

Provides standard JSON response helpers and request validation.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import Response, jsonify, Request


def json_response(
    data: Any,
    status: str = "success",
    message: Optional[str] = None,
    status_code: int = 200,
) -> Response:
    """
    Build a standard Flask JSON response.

    Parameters
    ----------
    data : Any
        Payload to include in the response body.
    status : str, default ``"success"``
        Overall status indicator (e.g. ``"success"``, ``"error"``).
    message : str, optional
        Optional human-readable message.
    status_code : int, default 200
        HTTP status code.

    Returns
    -------
    flask.Response
        A JSON-encoded Flask response.
    """
    body: Dict[str, Any] = {
        "status": status,
        "data": data,
    }
    if message is not None:
        body["message"] = message

    return jsonify(body), status_code


def error_response(
    message: str = "Bad request",
    code: int = 400,
    details: Optional[Any] = None,
) -> Response:
    """
    Build a standard error JSON response.

    Parameters
    ----------
    message : str, default ``"Bad request"``
        Error description.
    code : int, default 400
        HTTP status code.
    details : Any, optional
        Extra error details (validation errors, stack info, etc.).

    Returns
    -------
    flask.Response
        A JSON-encoded Flask error response.
    """
    body: Dict[str, Any] = {
        "status": "error",
        "message": message,
    }
    if details is not None:
        body["details"] = details

    return jsonify(body), code


def validate_json_input(
    request: Request,
    required_fields: List[str],
) -> Optional[Response]:
    """
    Validate that a JSON request contains all required fields.

    Usage::

        @app.route("/predict", methods=["POST"])
        def predict():
            err = validate_json_input(request, ["age", "bmi"])
            if err:
                return err
            data = request.get_json()
            ...

    Parameters
    ----------
    request : flask.Request
        The incoming request object.
    required_fields : list of str
        Names of the JSON keys that must be present.

    Returns
    -------
    flask.Response or None
        If validation fails, returns an error ``Response`` with status 400.
        If validation passes, returns ``None`` so the caller can proceed.
    """
    if not request.is_json:
        return error_response("Request must be JSON", code=415)

    data: Any = request.get_json(silent=True)
    if data is None:
        return error_response("Invalid JSON body")

    missing: List[str] = [field for field in required_fields if field not in data]
    if missing:
        return error_response(
            message=f"Missing required fields: {', '.join(missing)}",
            code=400,
            details={"missing_fields": missing},
        )

    return None
