from __future__ import annotations

import uuid
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.dto import CreateOrderRequest, OrderItem

_Q = Path(__file__).parent.parent / "queries" / "order"

_SQL_INSERT_ORDER = (_Q / "insert_order.sql").read_text()
_SQL_INSERT_ORDER_ITEM = (_Q / "insert_order_item.sql").read_text()
_SQL_UPDATE_ORDER_STATUS = (_Q / "update_order_status.sql").read_text()
_SQL_INSERT_PAYMENT = (_Q / "insert_payment.sql").read_text()


class OrderDataStore:
    """Handles all database interactions for orders, order items, and payments."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn

    @contextmanager
    def transaction(self):
        """Context manager that wraps operations in a database transaction."""
        _owner = not self._conn.in_transaction()
        if _owner:
            self._conn.begin()
        try:
            yield
            if _owner:
                self._conn.commit()
        except Exception as exc:
            if _owner:
                self._conn.rollback()
            raise exc

    def insert_order(
        self,
        request: CreateOrderRequest,
        warehouse_id: UUID,
        lat: float,
        lng: float,
        total_amount: Decimal,
    ) -> UUID:
        """Insert a new order with status=pending_payment; returns the new order UUID."""
        order_id = uuid.uuid4()
        self._conn.execute(
            text(_SQL_INSERT_ORDER),
            {
                "id": str(order_id),
                "customer_id": request.customer_id,
                "shipping_address": request.shipping_address,
                "shipping_lat": lat,
                "shipping_lng": lng,
                "warehouse_id": str(warehouse_id),
                "total_amount": str(total_amount),
            },
        )
        return order_id

    def insert_order_items(
        self, order_id: UUID, items: list[OrderItem], unit_price: Decimal
    ) -> None:
        """Insert all line items for an order."""
        for li in items:
            self._conn.execute(
                text(_SQL_INSERT_ORDER_ITEM),
                {
                    "order_id": str(order_id),
                    "product_id": str(li.product_id),
                    "quantity": li.quantity,
                    "unit_price": str(unit_price),
                },
            )

    def update_order_status(self, order_id: UUID, status: str) -> None:
        """Update the status field of an order."""
        self._conn.execute(
            text(_SQL_UPDATE_ORDER_STATUS),
            {"status": status, "id": str(order_id)},
        )

    def insert_payment(
        self,
        order_id: UUID,
        status: str,
        amount: Decimal,
        provider_ref: str | None,
    ) -> None:
        """Insert a payment record for an order."""
        self._conn.execute(
            text(_SQL_INSERT_PAYMENT),
            {
                "id": str(uuid.uuid4()),
                "order_id": str(order_id),
                "status": status,
                "amount": str(amount),
                "provider_ref": provider_ref,
            },
        )
