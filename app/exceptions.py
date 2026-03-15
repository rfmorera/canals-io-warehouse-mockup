class OrderServiceError(Exception):
    """Base exception for all Order Service errors."""


class ValidationError(OrderServiceError):
    """Raised when request payload validation fails. → 400"""


class GeocodingError(OrderServiceError):
    """Raised when the geocoder cannot resolve an address. → 422"""


class NoWarehouseAvailableError(OrderServiceError):
    """Raised when no warehouse can fulfill the order. → 422"""


class NoPaymentMethodError(OrderServiceError):
    """Raised when no payment method is on file for the customer. → 422"""


class PaymentError(OrderServiceError):
    """Raised when the payment gateway declines the charge. → 402"""


class InventoryConflictError(OrderServiceError):
    """Raised when a concurrent order causes an inventory conflict during reservation."""
