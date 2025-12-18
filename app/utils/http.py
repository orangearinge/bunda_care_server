from typing import Any, Dict, Optional
from flask import request, jsonify

def ok(payload: Dict[str, Any], status: int = 200):
    return jsonify(payload), status


def error(code: str, message: str, status: int = 400, **extra):
    body: Dict[str, Any] = {"error": {"code": code, "message": message}}
    if extra:
        body["error"].update(extra)
    return jsonify(body), status

def json_body() -> Dict[str, Any]:
    # Try parsing as JSON first (force=True allows missing Content-Type header)
    data = request.get_json(force=True, silent=True)
    if data is not None:
        return data
    # Fallback to form data (converted to dict) if JSON parsing fails
    return request.form.to_dict() if request.form else {}


def arg_str(name: str, default: Optional[str] = None) -> Optional[str]:
    val = request.args.get(name)
    if val is None:
        return default
    return val


def arg_int(name: str, default: int, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
    try:
        v = int(request.args.get(name, default))
    except Exception:
        v = default
    if min_value is not None:
        v = max(min_value, v)
    if max_value is not None:
        v = min(max_value, v)
    return v


def parse_iso_datetime(value: Any):
    try:
        from datetime import datetime
        if isinstance(value, str):
            return datetime.fromisoformat(value)
    except Exception:
        pass
    return None
