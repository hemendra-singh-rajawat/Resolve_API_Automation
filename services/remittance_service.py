from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class RemittanceService(BaseService):
    """ERA / 835 remittance endpoints in billing-rcm-service.

    Paths:
      GET  /api/v1/eras                              — paginated list
      GET  /api/v1/eras/{era_id}                     — detail
      POST /api/v1/eras/retrieve                     — pull from clearinghouse
      POST /api/v1/eras/{era_id}/auto-post           — auto-post all matched claims
      POST /api/v1/eras/{era_id}/matches/{match_id}/post  — post one match
      GET  /api/v1/era/                              — secondary list endpoint
      POST /api/v1/era/process                       — ingest raw 835 payload
    """

    base_path = "/api/v1/eras"

    def list(self, **filters: Any) -> APIResponseWrapper:
        return self.client.get(self.base_path, params=filters)

    def get(self, era_id: str) -> APIResponseWrapper:
        return self.client.get(self._path(era_id))

    def upload(self, era_payload: dict[str, Any]) -> APIResponseWrapper:
        """Submit an 835 for processing via the /era/process endpoint."""
        return self.client.post("/api/v1/era/process", json_body=era_payload)

    def retrieve(self, tenant_id: str, date_from: str, date_to: str) -> APIResponseWrapper:
        """Trigger a pull from the clearinghouse. tenant_id is (oddly) a query param."""
        return self.client.post(
            self._path("retrieve"),
            params={"tenant_id": tenant_id},
            json_body={"date_from": date_from, "date_to": date_to},
        )

    def auto_post(self, era_id: str) -> APIResponseWrapper:
        return self.client.post(self._path(era_id, "auto-post"))

    def post_to_claim(self, era_id: str, claim_id: str) -> APIResponseWrapper:
        """Closest analogue to per-match post; signature kept for back-compat."""
        return self.client.post(
            self._path(era_id, "matches", claim_id, "post"),
        )
