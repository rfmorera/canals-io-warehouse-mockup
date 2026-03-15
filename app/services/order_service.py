from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from retrying import retry

from app.data_store.order_data_store import OrderDataStore
from app.dto import CreateOrderRequest, OrderItem
from app.exceptions import (
    InventoryConflictError,
    NoPaymentMethodError,
    NoWarehouseAvailableError,
    PaymentError,
)
from app.services.customer_payment_store import CustomerPaymentStoreInterface
from app.services.geocoder import GeocoderInterface
from app.services.payment import PaymentGatewayInterface
from app.services.warehouse_service import WarehouseService


class OrderService:
    def __init__(
        self,
        geocoder: GeocoderInterface,
        warehouse_service: WarehouseService,
        payment_gateway: PaymentGatewayInterface,
        customer_payment_store: CustomerPaymentStoreInterface,
        order_store: OrderDataStore,
    ) -> None:
        self._geocoder = geocoder
        self._warehouse_service = warehouse_service
        self._payment_gateway = payment_gateway
        self._customer_payment_store = customer_payment_store
        self._order_store = order_store

    def create_order(
        self,
        request: CreateOrderRequest,
    ) -> dict:
        lat, lng = self._geocoder.geocode(request.shipping_address)

        line_items = [
            OrderItem(product_id=item.product_id, quantity=item.quantity)
            for item in request.items
        ]

        try:
            order_id, warehouse_id, total_amount = self._select_and_reserve(
                request, line_items, lat, lng
            )
        except InventoryConflictError:
            raise NoWarehouseAvailableError("no warehouse available to fulfill this order")

        # Payment info lookup (outside transaction)
        try:
            card_number = self._customer_payment_store.get_card_number(request.customer_id)
        except NoPaymentMethodError:
            with self._order_store.transaction():
                self._warehouse_service.release_reservation(warehouse_id, line_items)
                self._order_store.update_order_status(order_id, "failed_payment")
            raise

        # Charge (outside transaction)
        payment_result = self._payment_gateway.charge(
            card_number, total_amount, f"Order {order_id}"
        )

        if payment_result.success:
            with self._order_store.transaction():
                self._warehouse_service.finalize_inventory(warehouse_id, line_items)
                self._order_store.update_order_status(order_id, "paid")
                self._order_store.insert_payment(order_id, "success", total_amount, payment_result.provider_ref)
            return {
                "order_id": str(order_id),
                "warehouse_id": str(warehouse_id),
                "status": "paid",
                "total_amount": float(total_amount),
            }
        else:
            with self._order_store.transaction():
                self._warehouse_service.release_reservation(warehouse_id, line_items)
                self._order_store.update_order_status(order_id, "failed_payment")
                self._order_store.insert_payment(order_id, "failed", total_amount, None)
            raise PaymentError(payment_result.error_message or "payment failed")

    # ------------------------------------------------------------------
    # Reservation
    # ------------------------------------------------------------------

    @retry(
        retry_on_exception=lambda e: isinstance(e, InventoryConflictError),
        wait_exponential_multiplier=200,
        wait_exponential_max=1000,
        stop_max_attempt_number=3,
        wrap_exception=False,
    )
    def _select_and_reserve(
        self,
        request: CreateOrderRequest,
        line_items: list[OrderItem],
        lat: float,
        lng: float,
    ) -> tuple[UUID, UUID, Decimal]:
        warehouse_id = self._warehouse_service.select_warehouse(
            items=line_items,
            lat=lat,
            lng=lng,
            manufacturer_countries=request.manufacturer_countries,
        )
        if warehouse_id is None:
            raise NoWarehouseAvailableError("no warehouse available to fulfill this order")

        try:
            order_id, total_amount = self._reserve_and_insert(
                request, line_items, warehouse_id, lat, lng
            )
            return order_id, warehouse_id, total_amount
        except InventoryConflictError:
            raise

    def _reserve_and_insert(
        self,
        request: CreateOrderRequest,
        line_items: list[OrderItem],
        warehouse_id: UUID,
        lat: float,
        lng: float,
    ) -> tuple[UUID, Decimal]:
        with self._order_store.transaction():
            self._warehouse_service.lock_and_reserve(warehouse_id, line_items)

            unit_price = Decimal("0.00")
            total_amount = unit_price * sum(li.quantity for li in line_items)

            order_id = self._order_store.insert_order(request, warehouse_id, lat, lng, total_amount)
            self._order_store.insert_order_items(order_id, line_items, unit_price)

        return order_id, total_amount
