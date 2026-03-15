from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PaymentResult:
    success: bool
    provider_ref: str | None
    error_message: str | None
