-- Update the status of an order.
-- Parameters: :status, :id
UPDATE orders SET status = :status WHERE id = :id;
