from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.dto import OrderItem

_Q = Path(__file__).parent.parent / "queries" / "warehouse"

_SQL_FULFILLMENT = (_Q / "fulfillment.sql").read_text()
_SQL_LOCK_INVENTORY = (_Q / "lock_inventory.sql").read_text()
_SQL_INCREMENT_RESERVED = (_Q / "increment_reserved_qty.sql").read_text()
_SQL_DECREMENT_RESERVED = (_Q / "decrement_reserved_qty.sql").read_text()
_SQL_FINALIZE_SUCCESS = (_Q / "finalize_inventory_success.sql").read_text()

_ROW_TEMPLATE = "(CAST(:product_id_{i} AS uuid), CAST(:qty_{i} AS int))"


class WarehouseDataStore:
    """Handles all database interactions for warehouse and inventory data."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    def find_nearest_fulfillable_warehouse(
        self,
        items: list[OrderItem],
        lat: float,
        lng: float,
        radius_meters: float | None,
        manufacturer_countries: list[str] | None,
    ) -> UUID | None:
        """Return the nearest warehouse UUID that can fulfill all items, or None."""
        values_clause = ",\n        ".join(
            _ROW_TEMPLATE.format(i=i) for i in range(len(items))
        )
        params: dict = {
            "countries_filter": manufacturer_countries or None,
            "radius_meters": radius_meters,
            "lat": lat,
            "lng": lng,
        }
        for i, item in enumerate(items):
            params[f"product_id_{i}"] = str(item.product_id)
            params[f"qty_{i}"] = item.quantity

        sql = text(_SQL_FULFILLMENT.format(values_clause=values_clause))
        row = self._conn.execute(sql, params).fetchone()
        return row[0] if row else None

    def lock_inventory(
        self, warehouse_id: UUID, items: list[OrderItem]
    ) -> dict[str, tuple[int, int]]:
        """SELECT FOR UPDATE on inventory rows; returns {product_id: (available, reserved)}."""
        rows = self._conn.execute(
            text(_SQL_LOCK_INVENTORY),
            {"warehouse_id": str(warehouse_id), "product_ids": [str(li.product_id) for li in items]},
        ).fetchall()
        return {str(row[0]): (row[1], row[2]) for row in rows}

    def increment_reserved_qty(self, warehouse_id: UUID, items: list[OrderItem]) -> None:
        """Increment reserved_qty for each item at the given warehouse."""
        for li in items:
            self._conn.execute(
                text(_SQL_INCREMENT_RESERVED),
                {"qty": li.quantity, "warehouse_id": str(warehouse_id), "product_id": str(li.product_id)},
            )

    def decrement_reserved_qty(self, warehouse_id: UUID, items: list[OrderItem]) -> None:
        """Decrement reserved_qty for each item (reservation release)."""
        for li in items:
            self._conn.execute(
                text(_SQL_DECREMENT_RESERVED),
                {"qty": li.quantity, "warehouse_id": str(warehouse_id), "product_id": str(li.product_id)},
            )

    def finalize_inventory_success(self, warehouse_id: UUID, items: list[OrderItem]) -> None:
        """Decrement both available_qty and reserved_qty after successful payment."""
        for li in items:
            self._conn.execute(
                text(_SQL_FINALIZE_SUCCESS),
                {"qty": li.quantity, "warehouse_id": str(warehouse_id), "product_id": str(li.product_id)},
            )
