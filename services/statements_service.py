from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class StatementsService(BaseService):
    """Patient statement generation & management — added on origin/main.

    Paths (live as of 2026-05-22):
      GET  /api/v1/statements                          — list with filters
      POST /api/v1/statements/generate                 — build a new statement
      GET  /api/v1/statements/{statement_id}           — detail
      POST /api/v1/statements/{statement_id}/issue     — mark as issued/sent
      POST /api/v1/statements/{statement_id}/void      — void / cancel
    """

    base_path = "/api/v1/statements"

    def list(self, **filters: Any) -> APIResponseWrapper:
        return self.client.get(self.base_path, params=filters or None)

    def generate(self, payload: dict[str, Any]) -> APIResponseWrapper:
        return self.client.post(self._path("generate"), json_body=payload)

    def get(self, statement_id: str) -> APIResponseWrapper:
        return self.client.get(self._path(statement_id))

    def issue(self, statement_id: str, payload: dict[str, Any] | None = None) -> APIResponseWrapper:
        return self.client.post(self._path(statement_id, "issue"), json_body=payload)

    def void(self, statement_id: str, payload: dict[str, Any] | None = None) -> APIResponseWrapper:
        return self.client.post(self._path(statement_id, "void"), json_body=payload)
