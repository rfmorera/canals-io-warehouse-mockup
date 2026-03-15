import logging
import traceback

from flask import jsonify

from app.exceptions import (
    ValidationError,
    GeocodingError,
    NoWarehouseAvailableError,
    NoPaymentMethodError,
    PaymentError,
)


def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return jsonify({"error": str(e)}), 400

    @app.errorhandler(GeocodingError)
    def handle_geocoding_error(e):
        return jsonify({"error": str(e)}), 422

    @app.errorhandler(NoWarehouseAvailableError)
    def handle_no_warehouse(e):
        return jsonify({"error": str(e)}), 422

    @app.errorhandler(NoPaymentMethodError)
    def handle_no_payment_method(e):
        return jsonify({"error": str(e)}), 422

    @app.errorhandler(PaymentError)
    def handle_payment_error(e):
        return jsonify({"error": str(e)}), 402

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        logging.error("Unhandled exception:\n%s", traceback.format_exc())
        return jsonify({"error": "an internal error occurred"}), 500
