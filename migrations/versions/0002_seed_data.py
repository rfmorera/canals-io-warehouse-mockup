"""Seed initial data for manual testing

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-15 00:00:00.000000
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Fixed UUIDs so the seed is idempotent and easy to reference in curl requests
WH_NYC  = "aaaaaaaa-0001-0001-0001-000000000001"
WH_LA   = "aaaaaaaa-0002-0001-0001-000000000002"

PROD_WIDGET  = "bbbbbbbb-0001-0001-0001-000000000001"
PROD_GADGET  = "bbbbbbbb-0002-0001-0001-000000000002"
PROD_GIZMO   = "bbbbbbbb-0003-0001-0001-000000000003"


def upgrade() -> None:
    # ── Warehouses ────────────────────────────────────────────────────────────
    op.execute(f"""
        INSERT INTO warehouses (id, name, address, location, active) VALUES
        (
            '{WH_NYC}',
            'NYC Warehouse',
            '1 Fulton St, New York, NY 10038',
            ST_SetSRID(ST_MakePoint(-74.0060, 40.7128), 4326),
            true
        ),
        (
            '{WH_LA}',
            'LA Warehouse',
            '700 W 7th St, Los Angeles, CA 90017',
            ST_SetSRID(ST_MakePoint(-118.2437, 34.0522), 4326),
            true
        )
    """)

    # ── Products ──────────────────────────────────────────────────────────────
    op.execute(f"""
        INSERT INTO products (id, sku, name, manufacturer_country) VALUES
        ('{PROD_WIDGET}', 'SKU-WIDGET-US', 'Widget Pro',   'US'),
        ('{PROD_GADGET}', 'SKU-GADGET-DE', 'Gadget Plus',  'DE'),
        ('{PROD_GIZMO}',  'SKU-GIZMO-US',  'Gizmo Ultra', 'US')
    """)

    # ── Inventory ─────────────────────────────────────────────────────────────
    # NYC: well stocked on all three products
    op.execute(f"""
        INSERT INTO warehouse_inventory (warehouse_id, product_id, available_qty, reserved_qty) VALUES
        ('{WH_NYC}', '{PROD_WIDGET}', 100, 0),
        ('{WH_NYC}', '{PROD_GADGET}',  50, 0),
        ('{WH_NYC}', '{PROD_GIZMO}',   75, 0)
    """)

    # LA: stocked on Widget and Gizmo only (no Gadget — useful for country-filter tests)
    op.execute(f"""
        INSERT INTO warehouse_inventory (warehouse_id, product_id, available_qty, reserved_qty) VALUES
        ('{WH_LA}', '{PROD_WIDGET}', 200, 0),
        ('{WH_LA}', '{PROD_GIZMO}',  30, 0)
    """)


def downgrade() -> None:
    op.execute(f"""
        DELETE FROM warehouse_inventory
        WHERE warehouse_id IN ('{WH_NYC}', '{WH_LA}')
    """)
    op.execute(f"""
        DELETE FROM products
        WHERE id IN ('{PROD_WIDGET}', '{PROD_GADGET}', '{PROD_GIZMO}')
    """)
    op.execute(f"""
        DELETE FROM warehouses
        WHERE id IN ('{WH_NYC}', '{WH_LA}')
    """)
