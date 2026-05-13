from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class ClaimService(BaseService):
    """Claim lifecycle endpoints in billing-rcm-service.

    Paths confirmed against the live OpenAPI on 2026-05-13:
      GET    /api/v1/claims
      POST   /api/v1/claims
      GET    /api/v1/claims/{id}
      PUT    /api/v1/claims/{id}
      POST   /api/v1/claims/{id}/validate
      POST   /api/v1/claims/{id}/submit
      GET    /api/v1/claims/{id}/status
      POST   /api/v1/claims/bulk-submit
    """

    base_path = "/api/v1/claims"

    def create(self, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.post(self.base_path, json_body=payload)

    def get(self, claim_id: str) -> APIResponseWrapper:
        return self.client.get(self._path(claim_id))

    def search(self, **filters: Any) -> APIResponseWrapper:
        return self.client.get(self.base_path, params=filters)

    def update(self, claim_id: str, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.put(self._path(claim_id), json_body=payload)

    def validate(self, claim_id: str) -> APIResponseWrapper:
        return self.client.post(self._path(claim_id, "validate"))

    def submit(self, claim_id: str, submitted_by: str | None = None) -> APIResponseWrapper:
        body: dict[str, Any] = {}
        if submitted_by:
            body["submitted_by"] = submitted_by
        return self.client.post(self._path(claim_id, "submit"), json_body=body or None)

    def status(self, claim_id: str) -> APIResponseWrapper:
        return self.client.get(self._path(claim_id, "status"))

    def bulk_submit(self, claim_ids: list[str], submitted_by: str) -> APIResponseWrapper:
        return self.client.post(
            self._path("bulk-submit"),
            json_body={"claim_ids": claim_ids, "submitted_by": submitted_by},
        )
