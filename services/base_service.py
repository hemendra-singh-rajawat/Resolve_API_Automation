from __future__ import annotations

from framework.api_client import APIClient


class BaseService:
    """Base for all RCM service objects. Holds a shared APIClient and exposes
    common helpers. Sub-classes declare their base path and endpoint methods."""

    base_path: str = ""

    def __init__(self, client: APIClient) -> None:
        self.client = client

    def _path(self, *parts: str | int) -> str:
        joined = "/".join(str(p).strip("/") for p in parts if p is not None and p != "")
        return f"{self.base_path}/{joined}" if joined else self.base_path
