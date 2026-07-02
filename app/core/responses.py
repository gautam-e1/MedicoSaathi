from flask import jsonify


def success_response(data=None, status_code=200):
    body = {"success": True, "data": data}
    return jsonify(body), status_code


def error_response(message, error_code=None, status_code=400):
    body = {"success": False, "message": message}
    if error_code:
        body["error_code"] = error_code
    return jsonify(body), status_code
