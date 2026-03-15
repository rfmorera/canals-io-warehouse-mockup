-- Fulfillment CTE: finds the nearest active warehouse that can fulfill all
-- requested line items, optionally filtered by manufacturer country.
--
-- Parameters (injected by warehouse_data_store.py):
--   values_clause   — VALUES rows, one per line item (Python str.format substitution)
--   countries_filter — text[] of ISO 3166-1 alpha-2 codes, or NULL for no restriction
--   radius_meters   — search radius in meters, or NULL for nationwide
--   lat, lng        — shipping coordinates

WITH requested(product_id, qty) AS (
    VALUES
        {values_clause}
),
candidate_warehouses AS (
    SELECT wi.warehouse_id
    FROM warehouse_inventory wi
    JOIN requested r
      ON r.product_id = wi.product_id
     AND (wi.available_qty - wi.reserved_qty) >= r.qty
    JOIN products p ON p.id = wi.product_id
    WHERE (
        CAST(:countries_filter AS char(2)[]) IS NULL
        OR p.manufacturer_country = ANY(CAST(:countries_filter AS char(2)[]))
    )
    GROUP BY wi.warehouse_id
    HAVING COUNT(*) = (SELECT COUNT(*) FROM requested)
)
SELECT w.id
FROM warehouses w
JOIN candidate_warehouses c ON c.warehouse_id = w.id
WHERE w.active = true
  AND (
      :radius_meters IS NULL
      OR ST_DWithin(
             w.location,
             ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
             :radius_meters
         )
  )
ORDER BY w.location <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
LIMIT 1
