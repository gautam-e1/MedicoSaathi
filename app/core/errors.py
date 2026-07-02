import traceback

from flask import Flask, jsonify

from app.utils.exceptions import (
    DomainError,
    Forbidden,
    NotFound,
    TenantContextError,
)
from app.services.service_exceptions import ServiceError, ValidationError


def register_error_handlers(app: Flask) -> None:

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "success": False,
            "message": str(e.description) if hasattr(e, "description") else "Bad request",
            "error_code": "BAD_REQUEST",
        }), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({
            "success": False,
            "message": "Unauthorized",
            "error_code": "UNAUTHORIZED",
        }), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({
            "success": False,
            "message": "Forbidden",
            "error_code": "FORBIDDEN",
        }), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "success": False,
            "message": "Resource not found",
            "error_code": "NOT_FOUND",
        }), 404

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({
            "success": False,
            "message": str(e.description) if hasattr(e, "description") else "Unprocessable entity",
            "error_code": "UNPROCESSABLE_ENTITY",
        }), 422

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(
            "Internal server error: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return jsonify({
            "success": False,
            "message": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        }), 500

    # --- Domain exception handlers ---

    @app.errorhandler(NotFound)
    def handle_not_found(e):
        return jsonify({
            "success": False,
            "message": e.message,
            "error_code": "NOT_FOUND",
        }), 404

    @app.errorhandler(Forbidden)
    def handle_forbidden(e):
        return jsonify({
            "success": False,
            "message": e.message,
            "error_code": "FORBIDDEN",
        }), 403

    @app.errorhandler(TenantContextError)
    def handle_tenant_error(e):
        return jsonify({
            "success": False,
            "message": e.message,
            "error_code": "TENANT_ERROR",
        }), 403

    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return jsonify({
            "success": False,
            "message": e.message,
            "error_code": "VALIDATION_ERROR",
        }), 422

    @app.errorhandler(ServiceError)
    def handle_service_error(e):
        return jsonify({
            "success": False,
            "message": e.message,
            "error_code": "SERVICE_ERROR",
        }), 400

    @app.errorhandler(DomainError)
    def handle_domain_error(e):
        return jsonify({
            "success": False,
            "message": e.message,
            "error_code": "DOMAIN_ERROR",
        }), 400
