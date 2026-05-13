from __future__ import annotations

import json
import time
from typing import Any, Optional

import allure
from playwright.sync_api import APIRequestContext, APIResponse

from framework.auth import TokenStore
from framework.config import EnvConfig
from framework.logger import get_logger

log = get_logger(__name__)

JSON = dict[str, Any] | list[Any]


class APIResponseWrapper:
    """Thin wrapper around Playwright's APIResponse that adds latency, json safety,
    and shorthand assertions used across tests."""

    def __init__(self, resp: APIResponse, elapsed_ms: float, request_meta: dict[str, Any]) -> None:
        self._resp = resp
        self.elapsed_ms = elapsed_ms
        self.request_meta = request_meta

    @property
    def status(self) -> int:
        return self._resp.status

    @property
    def ok(self) -> bool:
        return self._resp.ok

    @property
    def headers(self) -> dict[str, str]:
        return self._resp.headers

    @property
    def text(self) -> str:
        try:
            return self._resp.text()
        except Exception:  # noqa: BLE001
            return "<binary>"

    def json(self) -> JSON:
        try:
            return self._resp.json()
        except Exception as e:  # noqa: BLE001
            raise AssertionError(
                f"Response was not valid JSON. Status={self.status}. Body={self.text[:500]}"
            ) from e

    # --- shorthand assertions -------------------------------------------------
    def assert_status(self, expected: int) -> "APIResponseWrapper":
        assert self.status == expected, (
            f"Expected HTTP {expected} but got {self.status}. "
            f"URL={self.request_meta.get('url')} Body={self.text[:500]}"
        )
        return self

    def assert_status_in(self, allowed: list[int]) -> "APIResponseWrapper":
        assert self.status in allowed, (
            f"Expected status in {allowed} but got {self.status}. Body={self.text[:500]}"
        )
        return self

    def assert_latency_under(self, ms: float) -> "APIResponseWrapper":
        assert self.elapsed_ms < ms, (
            f"Latency budget breached: {self.elapsed_ms:.1f}ms >= {ms}ms"
        )
        return self


class APIClient:
    """High-level wrapper around playwright.request.APIRequestContext.

    Adds: auth header injection, logging, latency capture, Allure attachments,
    and uniform error semantics.
    """

    def __init__(
        self,
        request_context: APIRequestContext,
        env: EnvConfig,
        token_store: Optional[TokenStore] = None,
    ) -> None:
        self._ctx = request_context
        self._env = env
        self._tokens = token_store

    # --- public verbs ---------------------------------------------------------
    def get(self, path: str, **kw: Any) -> APIResponseWrapper:
        return self._request("GET", path, **kw)

    def post(self, path: str, **kw: Any) -> APIResponseWrapper:
        return self._request("POST", path, **kw)

    def put(self, path: str, **kw: Any) -> APIResponseWrapper:
        return self._request("PUT", path, **kw)

    def patch(self, path: str, **kw: Any) -> APIResponseWrapper:
        return self._request("PATCH", path, **kw)

    def delete(self, path: str, **kw: Any) -> APIResponseWrapper:
        return self._request("DELETE", path, **kw)

    # --- internals ------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[JSON] = None,
        headers: Optional[dict[str, str]] = None,
        data: Optional[Any] = None,
        authenticate: bool = True,
        timeout_ms: Optional[int] = None,
    ) -> APIResponseWrapper:
        url = path if path.startswith("http") else f"{self._env.base_url.rstrip('/')}/{path.lstrip('/')}"
        merged_headers = dict(self._env.default_headers)
        if authenticate and self._tokens is not None:
            merged_headers["Authorization"] = self._tokens.get().header_value
        if headers:
            merged_headers.update(headers)

        log.info("→ {} {}", method, url)
        if json_body is not None:
            log.debug("  request body: {}", _truncate(json.dumps(json_body)))

        start = time.perf_counter()
        with allure.step(f"{method} {path}"):
            fetch_kwargs: dict[str, Any] = {
                "method": method,
                "headers": merged_headers,
                "timeout": timeout_ms or self._env.timeout_ms,
            }
            if params is not None:
                fetch_kwargs["params"] = params
            if json_body is not None:
                # Playwright auto-serialises JSON when Content-Type is application/json.
                fetch_kwargs["data"] = json_body
            elif data is not None:
                fetch_kwargs["data"] = data
            resp = self._ctx.fetch(url, **fetch_kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            meta = {"url": url, "method": method, "params": params}
            wrapper = APIResponseWrapper(resp, elapsed_ms, meta)

            log.info("← {} {} [{}ms]", resp.status, url, f"{elapsed_ms:.0f}")
            _attach_to_allure(method, url, json_body, headers, wrapper)

            # If a request is unauthorized, invalidate token so the next call refetches.
            if resp.status == 401 and self._tokens is not None:
                log.warning("401 received — invalidating cached token")
                self._tokens.invalidate()

            return wrapper


def _truncate(s: str, limit: int = 2000) -> str:
    return s if len(s) <= limit else s[:limit] + f"... <{len(s) - limit} more chars>"


def _attach_to_allure(
    method: str,
    url: str,
    json_body: Any,
    headers: Optional[dict[str, str]],
    resp: APIResponseWrapper,
) -> None:
    try:
        req_dump = json.dumps(
            {"method": method, "url": url, "headers": _safe_headers(headers), "body": json_body},
            indent=2,
            default=str,
        )
        allure.attach(req_dump, name="request", attachment_type=allure.attachment_type.JSON)
        allure.attach(
            resp.text,
            name=f"response ({resp.status}, {resp.elapsed_ms:.0f}ms)",
            attachment_type=allure.attachment_type.JSON if _looks_like_json(resp.text) else allure.attachment_type.TEXT,
        )
    except Exception as e:  # noqa: BLE001
        log.debug("Allure attach failed: {}", e)


def _safe_headers(headers: Optional[dict[str, str]]) -> dict[str, str]:
    if not headers:
        return {}
    masked = {}
    for k, v in headers.items():
        masked[k] = "***" if k.lower() in {"authorization", "cookie", "x-api-key"} else v
    return masked


def _looks_like_json(s: str) -> bool:
    s = s.strip()
    return s.startswith("{") or s.startswith("[")
