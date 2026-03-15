from abc import ABC, abstractmethod
from decimal import Decimal
import uuid

from app.dto import PaymentResult


class PaymentGatewayInterface(ABC):
    @abstractmethod
    def charge(self, card_number: str, amount: Decimal, description: str) -> PaymentResult:
        """Returns PaymentResult(success, provider_ref, error_message)."""


class MockPaymentGateway(PaymentGatewayInterface):
    """Mock payment gateway for testing and local development.

    Returns success for all card numbers except the configured failure card
    (default: "4000000000000002"), which simulates a declined card.
    """

    DECLINE_CARD = "4000000000000002"

    def charge(self, card_number: str, amount: Decimal, description: str) -> PaymentResult:
        if card_number == self.DECLINE_CARD:
            return PaymentResult(
                success=False,
                provider_ref=None,
                error_message="Your card was declined.",
            )
        return PaymentResult(
            success=True,
            provider_ref=str(uuid.uuid4()),
            error_message=None,
        )
