from __future__ import annotations

import re
import time
from uuid import UUID

from flask import Blueprint, current_app, jsonify, request

from app.dto import CreateOrderRequest, OrderItem
from app.exceptions import ValidationError

orders_bp = Blueprint("orders", __name__)

_ISO_ALPHA2_RE = re.compile(r"^[A-Z]{2}$")


def _parse_and_validate(body: dict) -> CreateOrderRequest:
    customer_id = body.get("customer_id") or ""
    shipping_address = body.get("shipping_address") or ""

    if not customer_id or not customer_id.strip():
        raise ValidationError("field 'customer_id' is required")
    if not shipping_address or not shipping_address.strip():
        raise ValidationError("field 'shipping_address' is required")

    raw_items = body.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValidationError("field 'items' must contain at least one item")

    try:
        items = [
            OrderItem(
                product_id=UUID(str(item.get("product_id", ""))),
                quantity=int(item.get("quantity", 0)),
            )
            for item in raw_items
            if isinstance(item, dict)
        ]
    except (ValueError, AttributeError):
        raise ValidationError("field 'items' contains an invalid product_id or quantity")

    for item in items:
        if item.quantity <= 0:
            raise ValidationError(
                f"quantity must be > 0 (got {item.quantity} for product '{item.product_id}')"
            )

    manufacturer_countries = body.get("manufacturer_countries")
    if manufacturer_countries is not None:
        for code in manufacturer_countries:
            if not _ISO_ALPHA2_RE.match(code):
                raise ValidationError(
                    f"invalid country code: '{code}'; expected ISO 3166-1 alpha-2"
                )

    return CreateOrderRequest(
        customer_id=customer_id,
        shipping_address=shipping_address,
        items=items,
        manufacturer_countries=manufacturer_countries,
    )


@orders_bp.route("/orders", methods=["POST"])
def create_order():
    body = request.get_json(silent=True) or {}
    order_request = _parse_and_validate(body)
    result = current_app.order_service.create_order(order_request)
    return jsonify(result), 201
