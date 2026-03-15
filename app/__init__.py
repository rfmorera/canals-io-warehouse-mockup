from flask import Flask

from app.error_handlers import register_error_handlers


def _build_order_service(app):
    """Instantiate OrderService with all dependencies from app.config."""
    from sqlalchemy import create_engine

    from app.data_store import OrderDataStore, WarehouseDataStore
    from app.services.customer_payment_store import MockCustomerPaymentStore
    from app.services.geocoder import MockGeocoder
    from app.services.order_service import OrderService
    from app.services.payment import MockPaymentGateway
    from app.services.warehouse_service import WarehouseService

    geocoder = MockGeocoder()
    payment_gateway = MockPaymentGateway()
    customer_payment_store = MockCustomerPaymentStore()

    conn = app.config.get("DB_CONN")
    if conn is None:
        engine = create_engine(app.config["DATABASE_URL"])
        conn = engine.connect()
        app.config["DB_ENGINE"] = engine

    warehouse_store = WarehouseDataStore(conn)
    order_store = OrderDataStore(conn)
    warehouse_service = WarehouseService(warehouse_store)

    return OrderService(
        geocoder=geocoder,
        warehouse_service=warehouse_service,
        payment_gateway=payment_gateway,
        customer_payment_store=customer_payment_store,
        order_store=order_store,
    )


def create_app(config=None):
    """Application factory."""
    from app.config import load_config

    app = Flask(__name__)

    # Load from environment first, then let explicit config override (useful in tests)
    app.config.update(load_config())
    if config:
        app.config.update(config)

    # Build and cache the service only when DATABASE_URL is available (skipped in minimal test setups)
    if app.config.get("DATABASE_URL") or app.config.get("DB_CONN"):
        app.order_service = _build_order_service(app)
    else:
        app.order_service = None

    from app.routes.orders import orders_bp
    app.register_blueprint(orders_bp)

    register_error_handlers(app)

    return app
