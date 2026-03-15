# Implementation Plan: Order Management API

## Overview

Incremental build-out of a Flask + PostgreSQL order management service. Each task produces runnable, integrated code. The order follows: project scaffold → data layer → core services → order flow → API layer → containerization → tests.

## Tasks

- [x] 1. Scaffold project structure and configuration
  - Create directory layout: `app/`, `app/routes/`, `app/services/`, `app/models/`, `migrations/`, `tests/`
  - Create `app/config.py` — read `DATABASE_URL` (required) and `APP_PORT` (default 5000) from env; log error and `sys.exit(1)` on missing required vars
  - Create `app/__init__.py` application factory `create_app()` that registers blueprints and error handlers
  - Initialize Poetry project: `poetry init` with `pyproject.toml`; add dependencies: `flask`, `gunicorn`, `sqlalchemy`, `psycopg2-binary`, `alembic`, `geoalchemy2`; add dev dependencies: `pytest`, `pytest-flask`
  - _Requirements: 9.3, 9.4_

- [x] 2. Define database schema and Alembic migrations
  - [x] 2.1 Create SQLAlchemy models in `app/models.py`
    - Define `Warehouse`, `Product`, `WarehouseInventory`, `Order`, `OrderItem`, `Payment` mapped classes
    - `orders.customer_id TEXT NOT NULL` (not customer_name — fix schema discrepancy from design)
    - `products.manufacturer_country CHAR(2) NOT NULL`
    - `warehouse_inventory` composite PK `(warehouse_id, product_id)`, `available_qty >= 0`, `reserved_qty >= 0`
    - `orders.status` CHECK constraint: `pending_payment`, `paid`, `failed_payment`, `cancelled`
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 Create Alembic migration for initial schema
    - `alembic init migrations` and configure `env.py` to use `DATABASE_URL`
    - Generate initial migration: all six tables + `CREATE EXTENSION IF NOT EXISTS postgis`
    - Add all three indexes: `warehouses_location_gix` (GIST), `wi_product_warehouse_instock_idx`, `wi_warehouse_product_instock_idx`
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 3. Implement exception hierarchy and error handlers
  - Create `app/exceptions.py` with `OrderServiceError` base and subclasses: `ValidationError` (400), `GeocodingError` (422), `NoWarehouseAvailableError` (422), `NoPaymentMethodError` (422), `PaymentError` (402), `InventoryConflictError`
  - Register Flask error handlers in `create_app()`: each `OrderServiceError` subclass → JSON `{"error": "..."}` with correct status; catch-all handler logs full traceback at ERROR and returns 500 `{"error": "an internal error occurred"}`
  - group exceptions but avoid creating a huge file with all the exception declaration inside
  - _Requirements: 11.1, 11.2_

  - [ ]* 3.1 Write test: error responses are JSON with an error field
    - Any 4xx/5xx response body must be valid JSON with a non-empty `error` key
    - _Requirements: 11.1_

- [ ] 4. Implement mock external services
  - [x] 4.1 Create `app/services/geocoder.py`
    - Define `GeocoderInterface` ABC with `geocode(address: str) -> tuple[float, float]`
    - Implement `MockGeocoder`: deterministic lat/lng from `hash(address)` (stable, no randomness)
    - _Requirements: 3.3_

  - [x] 4.2 Create `app/services/payment.py`
    - Define `PaymentGatewayInterface` ABC with `charge(card_number, amount, description) -> PaymentResult`
    - Define `PaymentResult` dataclass: `success: bool`, `provider_ref: str | None`, `error_message: str | None`
    - Implement `MockPaymentGateway`: returns success unless `card_number == "4000000000000002"`
    - _Requirements: 8.4_

  - [x] 4.3 Create `app/services/customer_payment_store.py`
    - Define `CustomerPaymentStoreInterface` ABC with `get_card_number(customer_id: str) -> str`
    - Implement `MockCustomerPaymentStore`: load `customer_id → card_number` dict from `tests/fixtures/customers.json` at init; raise `NoPaymentMethodError` if not found
    - Create `tests/fixtures/customers.json` with at least 3 test customers (one mapped to the failure card)
    - _Requirements: 7.3, 7.4_

- [x] 5. Implement WarehouseSelector
  - [x] 5.1 Create `app/services/warehouse_selector.py` with `WarehouseSelector.select()`
    - `SEARCH_BANDS_MILES = [15, 60, 300, None]`; convert miles → meters via `× 1609.344`
    - Build the CTE fulfillment SQL as a parameterized `sqlalchemy.text()` query
    - Bind `requested` CTE values list, `countries_filter` (pass `None` to omit filter), `radius_meters` (pass `None` for nationwide), `lat`, `lng`
    - Iterate bands; return first `warehouse_id` found or `None`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 10.3_

- [x] 6. Implement OrderService — reservation and inventory flow
  - [x] 6.1 Create `app/services/order_service.py` with `OrderService.create_order()`
    - Validate `CreateOrderRequest`: non-empty `customer_id`, non-empty `shipping_address`, at least one item, all quantities > 0, `manufacturer_countries` values are valid ISO 3166-1 alpha-2 (2-letter uppercase); raise `ValidationError` on failure
    - Geocode address via injected `GeocoderInterface`
    - Call `WarehouseSelector.select()` outside any transaction; raise `NoWarehouseAvailableError` if `None`
    - Open DB transaction: `SELECT FOR UPDATE` on `warehouse_inventory` rows for the selected warehouse + ordered products; re-check `available_qty - reserved_qty >= qty` (raise `InventoryConflictError` if not); `UPDATE` to increment `reserved_qty`; `INSERT` into `orders` (status=`pending_payment`) and `order_items`; commit
    - Retry the warehouse-selection + reservation block up to 3 times on `InventoryConflictError`; raise `NoWarehouseAvailableError` after 3 failures
    - _Requirements: 1.2, 1.3, 2.1, 2.2, 2.3, 6.1, 6.2, 6.5, 6.6_

  - [ ]* 6.2 Write property test for reservation invariant (Property 6)
    - **Property 6: Reservation invariant on order placement**
    - **Validates: Requirements 6.1**

  - [x] 6.3 Implement payment lookup and gateway call in `OrderService`
    - After reservation commit: call `CustomerPaymentStoreInterface.get_card_number(customer_id)`; on `NoPaymentMethodError` → release reservation (decrement `reserved_qty`) + set status=`failed_payment` → re-raise
    - Call `PaymentGatewayInterface.charge(card_number, total_amount, description)` outside transaction
    - On payment success: open transaction → decrement `available_qty` and `reserved_qty` → set `status=paid` → commit
    - On payment failure: open transaction → decrement `reserved_qty` only → set `status=failed_payment` → commit → raise `PaymentError`
    - Insert a `payments` row in both success and failure paths
    - _Requirements: 7.1, 7.2, 7.4, 8.1, 8.2, 8.3_

- [x] 7. Implement Flask route and request/response layer
  - [x] 7.1 Create `app/routes/orders.py` — `POST /orders` endpoint
    - Parse JSON body into `CreateOrderRequest` dataclass; pass to `OrderService.create_order()`
    - On success: return 201 `{"order_id": ..., "warehouse_id": ..., "status": "paid", "total_amount": ...}`
    - Emit structured INFO log: `order_id`, `warehouse_id`, `processing_time_ms`
    - Ignore any `card_number` field present in the request payload
    - _Requirements: 1.1, 1.4, 11.3_

- [x] 8. Write tests
  - Create `tests/conftest.py` with a `client` fixture backed by a test PostgreSQL schema; inject mock services via `create_app()`
  - [x] 8.1 Test: valid order returns 201 with order_id and warehouse_id
    - Seed one warehouse with sufficient inventory; POST valid order; assert 201 and response fields
    - _Requirements: 1.1_
  - [x] 8.2 Test: invalid payload returns 400 with error field
    - POST with missing `customer_id` and with `quantity=0`; assert 400 and `error` key present
    - _Requirements: 1.2, 1.3, 2.3_
  - [x] 8.3 Test: no warehouse available returns 422
    - POST with empty inventory; assert 422 `"no warehouse available to fulfill this order"`
    - _Requirements: 4.5_
  - [x] 8.4 Test: payment failure releases reservation and returns 402
    - Seed customer with failure card `"4000000000000002"`; POST order; assert 402, `reserved_qty` back to 0, `available_qty` unchanged
    - _Requirements: 6.4, 8.3_
  - [x] 8.5 Test: no payment method on file returns 422
    - POST with unknown `customer_id`; assert 422 `"no payment method on file"`
    - _Requirements: 7.2_

- [x] 9. Containerize the service
  - Create `Dockerfile`: Python base image, install Poetry, copy `pyproject.toml` + `poetry.lock`, run `poetry install --no-dev`, copy app, add entrypoint script
  - Create `docker-compose.yml`: `order-api` service (build from `.`) + `postgres` service (`postgis/postgis:15-3.4`); `order-api` depends on `postgres` with healthcheck; expose `APP_PORT`; set `DATABASE_URL` pointing to the `postgres` service
  - Create `entrypoint.sh`: `alembic upgrade head && gunicorn -b 0.0.0.0:${APP_PORT:-5000} "app:create_app()"`
  - _Requirements: 9.1, 9.2, 9.3_

- [ ] 10. Final checkpoint — Ensure all tests pass
  - Run `poetry run pytest`; ensure all 5 tests pass; ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional
- Package management uses Poetry (`pyproject.toml`); run tests with `poetry run pytest`
- `conftest.py` provides a `client` fixture backed by a test PostgreSQL schema with transactions rolled back after each test
- Mock services are injected via `create_app()` in test mode
