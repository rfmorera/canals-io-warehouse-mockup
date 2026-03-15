-- Lock warehouse_inventory rows for the given warehouse + products (SELECT FOR UPDATE).
-- Parameters: :warehouse_id, :product_ids (uuid[])
SELECT product_id, available_qty, reserved_qty
FROM warehouse_inventory
WHERE warehouse_id = :warehouse_id
  AND product_id = ANY(CAST(:product_ids AS uuid[]))
ORDER BY product_id
FOR UPDATE;
