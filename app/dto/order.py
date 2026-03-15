from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class OrderItem:
    """A single line item in an order: product UUID + requested quantity."""
    product_id: UUID
    quantity: int


@dataclass
class CreateOrderRequest:
    customer_id: str
    shipping_address: str
    items: list[OrderItem]
    manufacturer_countries: list[str] | None = None
