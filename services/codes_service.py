from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class CodesService(BaseService):
    """HCPCS + ICD-10 code master data — added on origin/main (PRs after #83).

    Paths (live as of 2026-05-22):
      GET  /api/v1/codes/hcpcs                  — list with pagination/filter
      GET  /api/v1/codes/hcpcs/{code}           — fetch one HCPCS by code
      POST /api/v1/codes/hcpcs/import           — bulk upsert from JSON
      POST /api/v1/codes/hcpcs/import/csv       — bulk upsert from CSV
      GET  /api/v1/codes/icd10                  — list
      GET  /api/v1/codes/icd10/{code}           — fetch one
      POST /api/v1/codes/icd10/import           — bulk upsert from JSON
      POST /api/v1/codes/icd10/import/csv       — bulk upsert from CSV
    """

    base_path = "/api/v1/codes"

    # --- HCPCS -------------------------------------------------------------
    def list_hcpcs(self, **filters: Any) -> APIResponseWrapper:
        return self.client.get(self._path("hcpcs"), params=filters or None)

    def get_hcpcs(self, code: str) -> APIResponseWrapper:
        return self.client.get(self._path("hcpcs", code))

    def import_hcpcs_json(self, payload: dict[str, Any] | list[Any]) -> APIResponseWrapper:
        return self.client.post(self._path("hcpcs", "import"), json_body=payload)

    # --- ICD-10 ------------------------------------------------------------
    def list_icd10(self, **filters: Any) -> APIResponseWrapper:
        return self.client.get(self._path("icd10"), params=filters or None)

    def get_icd10(self, code: str) -> APIResponseWrapper:
        return self.client.get(self._path("icd10", code))

    def import_icd10_json(self, payload: dict[str, Any] | list[Any]) -> APIResponseWrapper:
        return self.client.post(self._path("icd10", "import"), json_body=payload)
