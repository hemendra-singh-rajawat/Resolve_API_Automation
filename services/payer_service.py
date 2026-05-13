from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class PayerService(BaseService):
    """Payer master data endpoints — list, create, update (soft-delete) payers."""

    base_path = "/api/v1/payers"

    def list(self, **filters: Any) -> APIResponseWrapper:
        return self.client.get(self.base_path, params=filters)

    def create(self, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.post(self.base_path, json_body=payload)

    def update(self, payer_id: str, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.put(f"{self.base_path}/{payer_id}", json_body=payload)

    def delete(self, payer_id: str) -> APIResponseWrapper:
        return self.client.delete(f"{self.base_path}/{payer_id}")
