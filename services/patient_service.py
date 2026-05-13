from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class PatientService(BaseService):
    """billing-rcm-service does NOT own patient demographics — those live in
    patient-service. This shim is kept for compatibility with conftest fixtures
    but only exposes the read-only handles that touch payer data here (which
    is the closest analogue available in this service)."""

    base_path = "/api/v1/payers"  # repurposed: payers are this service's only standalone master entity

    def create(self, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.post(self.base_path, json_body=payload)

    def get(self, patient_id: str) -> APIResponseWrapper:
        # No GET-by-id endpoint exists — return the listing and let callers filter.
        return self.client.get(self.base_path)

    def search(self, **filters: Any) -> APIResponseWrapper:
        return self.client.get(self.base_path, params=filters)

    def update(self, patient_id: str, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.put(f"{self.base_path}/{patient_id}", json_body=payload)

    def patch(self, patient_id: str, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.put(f"{self.base_path}/{patient_id}", json_body=payload)

    def delete(self, patient_id: str) -> APIResponseWrapper:
        return self.client.delete(f"{self.base_path}/{patient_id}")
