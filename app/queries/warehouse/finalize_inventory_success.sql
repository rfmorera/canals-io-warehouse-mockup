-- Decrement both available_qty and reserved_qty after successful payment.
-- Parameters: :qty, :warehouse_id, :product_id
UPDATE warehouse_inventory
SET available_qty = available_qty - :qty,
    reserved_qty  = reserved_qty  - :qty,
    updated_at    = now()
WHERE warehouse_id = :warehouse_id
  AND product_id   = :product_id;
