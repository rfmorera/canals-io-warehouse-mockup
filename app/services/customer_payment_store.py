from abc import ABC, abstractmethod

from app.exceptions import NoPaymentMethodError


class CustomerPaymentStoreInterface(ABC):
    @abstractmethod
    def get_card_number(self, customer_id: str) -> str:
        """Returns the stored credit card number for the customer,
        or raises NoPaymentMethodError if none is on file."""


class MockCustomerPaymentStore(CustomerPaymentStoreInterface):
    """Mock payment store for testing and local development.

    Sentinel customer IDs:
      - "no_payment_customer"  → raises NoPaymentMethodError
      - "declined_customer"    → returns the failure card "4000000000000002"
      - any other customer_id  → returns a generic valid card "4111111111111111"
    """

    _DECLINED_CARD = "4000000000000002"
    _VALID_CARD = "4111111111111111"
    _NO_PAYMENT_CUSTOMER = "no_payment_customer"
    _DECLINED_CUSTOMER = "declined_customer"

    def get_card_number(self, customer_id: str) -> str:
        if customer_id == self._NO_PAYMENT_CUSTOMER:
            raise NoPaymentMethodError(
                f"no payment method for customer: {customer_id}"
            )
        if customer_id == self._DECLINED_CUSTOMER:
            return self._DECLINED_CARD
        return self._VALID_CARD
