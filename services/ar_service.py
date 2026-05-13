from __future__ import annotations

from typing import Any

from framework.api_client import APIResponseWrapper
from services.base_service import BaseService


class ARService(BaseService):
    """A/R aging + dashboard endpoints.

    Paths:
      GET /api/v1/ar/aging
      GET /api/v1/ar/trend
      GET /api/v1/dashboard
    """

    base_path = "/api/v1"

    def aging(self, **filters: Any) -> APIResponseWrapper:
        return self.client.get(self._path("ar", "aging"), params=filters)

    def trend(self, days: int | None = None) -> APIResponseWrapper:
        params = {"days": days} if days is not None else None
        return self.client.get(self._path("ar", "trend"), params=params)

    def dashboard(self) -> APIResponseWrapper:
        return self.client.get(self._path("dashboard"))
