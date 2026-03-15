-- Insert a new order with status=pending_payment.
-- Parameters: :id, :customer_id, :shipping_address, :shipping_lat, :shipping_lng, :warehouse_id, :total_amount
INSERT INTO orders
    (id, customer_id, shipping_address, shipping_lat, shipping_lng,
     warehouse_id, status, total_amount)
VALUES
    (:id, :customer_id, :shipping_address, :shipping_lat, :shipping_lng,
     :warehouse_id, 'pending_payment', :total_amount);
