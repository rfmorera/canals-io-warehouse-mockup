-- Insert a payment record for an order.
-- Parameters: :id, :order_id, :status, :amount, :provider_ref
INSERT INTO payments (id, order_id, status, amount, provider_ref)
VALUES (:id, :order_id, :status, :amount, :provider_ref);
