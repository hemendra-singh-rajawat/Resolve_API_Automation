from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class EligibilityService(BaseService):
    """270/271 eligibility verification — billing-rcm-service routes.

    Paths:
      GET  /api/v1/eligibility/logs
      POST /api/v1/eligibility/verify
      POST /api/v1/eligibility/batch
    """

    base_path = "/api/v1/eligibility"

    def check(self, payload: dict[str, Any]) -> APIResponseWrapper:
        """Submit a single 270 inquiry → 271 response."""
        return self.client.post(self._path("verify"), json_body=payload)

    def batch(self, requests: list[dict[str, Any]]) -> APIResponseWrapper:
        return self.client.post(self._path("batch"), json_body={"requests": requests})

    def history(self, patient_id: str | None = None) -> APIResponseWrapper:
        params: dict[str, Any] = {}
        if patient_id:
            params["patient_id"] = patient_id
        return self.client.get(self._path("logs"), params=params or None)

    def coverage(self, patient_id: str, payer_id: str | None = None) -> APIResponseWrapper:
        """No dedicated /coverage endpoint exists on billing-rcm-service.
        Returns the history log filtered by patient as the closest analogue."""
        params: dict[str, Any] = {"patient_id": patient_id}
        if payer_id:
            params["payer_id"] = payer_id
        return self.client.get(self._path("logs"), params=params)
