from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class PaymentService(BaseService):
    """Payment register endpoints.

    Paths:
      GET  /api/v1/payments
      POST /api/v1/payments  (requires payment_type, source, amount, posted_by, ...)
    """

    base_path = "/api/v1/payments"

    def list(self, **filters: Any) -> APIResponseWrapper:
        return self.client.get(self.base_path, params=filters)

    def post_payment(self, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.post(self.base_path, json_body=payload)

    def by_claim(self, claim_id: str) -> APIResponseWrapper:
        return self.client.get(self.base_path, params={"claim_id": claim_id})

    def get(self, payment_id: str) -> APIResponseWrapper:
        """No GET-by-id route exists — fall back to listing."""
        return self.list()

    def refund(self, payment_id: str, amount: float, reason: str) -> APIResponseWrapper:
        # No /payments/{id}/refund route exists; this is a placeholder that will 404 / 405.
        return self.client.post(
            self._path(payment_id, "refund"),
            json_body={"amount": amount, "reason": reason},
        )
