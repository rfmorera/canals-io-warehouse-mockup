-- Insert a single order line item.
-- Parameters: :order_id, :product_id, :quantity, :unit_price
INSERT INTO order_items (order_id, product_id, quantity, unit_price)
VALUES (:order_id, :product_id, :quantity, :unit_price);
