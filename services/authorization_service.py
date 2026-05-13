from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class AuthorizationService(BaseService):
    """Prior authorization endpoints — billing-rcm-service uses /prior-authorizations."""

    base_path = "/api/v1/prior-authorizations"

    def request(self, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.post(self.base_path, json_body=payload)

    def get(self, auth_id: str) -> APIResponseWrapper:
        return self.client.get(self._path(auth_id))

    def update(self, auth_id: str, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.put(self._path(auth_id), json_body=payload)

    def cancel(self, auth_id: str, reason: str | None = None) -> APIResponseWrapper:
        # No /cancel route exists; soft-delete is exposed via DELETE.
        return self.client.delete(self._path(auth_id))
