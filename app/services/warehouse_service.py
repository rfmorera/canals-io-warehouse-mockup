from __future__ import annotations

from uuid import UUID

from app.data_store.warehouse_data_store import WarehouseDataStore
from app.dto import OrderItem
from app.exceptions import InventoryConflictError

MILES_TO_METERS = 1_609.344


class WarehouseService:
    SEARCH_BANDS_MILES = [15, 60, 300, None]  # None = nationwide

    def __init__(self, store: WarehouseDataStore) -> None:
        self._store = store

    def select_warehouse(
        self,
        items: list[OrderItem],
        lat: float,
        lng: float,
        manufacturer_countries: list[str] | None = None,
    ) -> UUID | None:
        for band_miles in self.SEARCH_BANDS_MILES:
            radius_meters = band_miles * MILES_TO_METERS if band_miles is not None else None
            result = self._store.find_nearest_fulfillable_warehouse(
                items, lat, lng, radius_meters, manufacturer_countries
            )
            if result:
                return result
        return None

    def lock_and_reserve(
        self, warehouse_id: UUID, items: list[OrderItem]
    ) -> None:
        """Lock inventory rows and reserve quantities. Raises InventoryConflictError on shortage."""
        inventory = self._store.lock_inventory(warehouse_id, items)

        for li in items:
            pid = str(li.product_id)
            if pid not in inventory:
                raise InventoryConflictError(
                    f"product {pid} not found in warehouse {warehouse_id}"
                )
            avail, reserved = inventory[pid]
            if avail - reserved < li.quantity:
                raise InventoryConflictError(
                    f"insufficient inventory for product {pid} at warehouse {warehouse_id}"
                )

        self._store.increment_reserved_qty(warehouse_id, items)

    def release_reservation(self, warehouse_id: UUID, items: list[OrderItem]) -> None:
        self._store.decrement_reserved_qty(warehouse_id, items)

    def finalize_inventory(self, warehouse_id: UUID, items: list[OrderItem]) -> None:
        self._store.finalize_inventory_success(warehouse_id, items)
