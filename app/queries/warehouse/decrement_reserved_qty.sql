-- Decrement reserved_qty for a single product at a warehouse (reservation release).
-- Parameters: :qty, :warehouse_id, :product_id
UPDATE warehouse_inventory
SET reserved_qty = reserved_qty - :qty,
    updated_at   = now()
WHERE warehouse_id = :warehouse_id
  AND product_id   = :product_id;
