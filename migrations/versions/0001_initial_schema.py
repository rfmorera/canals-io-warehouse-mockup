"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # warehouses
    op.execute("""
        CREATE TABLE warehouses (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        TEXT NOT NULL,
            address     TEXT NOT NULL,
            location    GEOGRAPHY(Point, 4326) NOT NULL,
            active      BOOLEAN NOT NULL DEFAULT true
        )
    """)

    # products
    op.execute("""
        CREATE TABLE products (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            sku                  TEXT NOT NULL UNIQUE,
            name                 TEXT NOT NULL,
            manufacturer_country CHAR(2) NOT NULL
        )
    """)

    # warehouse_inventory
    op.execute("""
        CREATE TABLE warehouse_inventory (
            warehouse_id  UUID NOT NULL REFERENCES warehouses(id),
            product_id    UUID NOT NULL REFERENCES products(id),
            available_qty INTEGER NOT NULL DEFAULT 0 CHECK (available_qty >= 0),
            reserved_qty  INTEGER NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (warehouse_id, product_id)
        )
    """)

    # orders
    op.execute("""
        CREATE TABLE orders (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id      TEXT NOT NULL,
            shipping_address TEXT NOT NULL,
            shipping_lat     DOUBLE PRECISION NOT NULL,
            shipping_lng     DOUBLE PRECISION NOT NULL,
            warehouse_id     UUID NOT NULL REFERENCES warehouses(id),
            status           TEXT NOT NULL CHECK (status IN (
                                 'pending_payment', 'paid',
                                 'failed_payment', 'cancelled')),
            total_amount     NUMERIC(12, 2) NOT NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # order_items
    op.execute("""
        CREATE TABLE order_items (
            order_id    UUID NOT NULL REFERENCES orders(id),
            product_id  UUID NOT NULL REFERENCES products(id),
            quantity    INTEGER NOT NULL CHECK (quantity > 0),
            unit_price  NUMERIC(12, 2) NOT NULL,
            PRIMARY KEY (order_id, product_id)
        )
    """)

    # payments
    op.execute("""
        CREATE TABLE payments (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id     UUID NOT NULL REFERENCES orders(id),
            status       TEXT NOT NULL,
            amount       NUMERIC(12, 2) NOT NULL,
            provider_ref TEXT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Indexes
    op.execute(
        "CREATE INDEX warehouses_location_gix ON warehouses USING GIST (location)"
    )
    op.execute(
        "CREATE INDEX wi_product_warehouse_instock_idx "
        "ON warehouse_inventory (product_id, warehouse_id) "
        "INCLUDE (available_qty, reserved_qty) "
        "WHERE available_qty > 0"
    )
    op.execute(
        "CREATE INDEX wi_warehouse_product_instock_idx "
        "ON warehouse_inventory (warehouse_id, product_id) "
        "INCLUDE (available_qty, reserved_qty) "
        "WHERE available_qty > 0"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payments")
    op.execute("DROP TABLE IF EXISTS order_items")
    op.execute("DROP TABLE IF EXISTS orders")
    op.execute("DROP TABLE IF EXISTS warehouse_inventory")
    op.execute("DROP TABLE IF EXISTS products")
    op.execute("DROP TABLE IF EXISTS warehouses")
    op.execute("DROP EXTENSION IF EXISTS postgis")
