from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class DenialService(BaseService):
    """Denial worklist + appeal endpoints.

    Paths:
      GET  /api/v1/denials
      PUT  /api/v1/denials/{id}/assign
      POST /api/v1/denials/{id}/appeal
      PUT  /api/v1/denials/{id}/resolve
    """

    base_path = "/api/v1/denials"

    def list(self, **filters: Any) -> APIResponseWrapper:
        return self.client.get(self.base_path, params=filters)

    def assign(self, denial_id: str, assigned_to: str) -> APIResponseWrapper:
        return self.client.put(
            self._path(denial_id, "assign"),
            json_body={"assigned_to": assigned_to},
        )

    def appeal(self, denial_id: str, reason: str) -> APIResponseWrapper:
        return self.client.post(
            self._path(denial_id, "appeal"),
            json_body={"reason": reason},
        )

    def resolve(self, denial_id: str, resolution: str) -> APIResponseWrapper:
        return self.client.put(
            self._path(denial_id, "resolve"),
            json_body={"resolution": resolution},
        )
