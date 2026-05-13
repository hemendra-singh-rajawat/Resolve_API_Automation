from __future__ import annotations

import allure
import pytest

pytestmark = [allure.feature("Smoke"), pytest.mark.smoke]


@allure.story("Liveness probe returns 200")
@allure.severity(allure.severity_level.BLOCKER)
def test_health_endpoint_returns_200(api):
    resp = api.get("/health", authenticate=False)
    resp.assert_status(200).assert_latency_under(2000)
    body = resp.json()
    assert body.get("status") in {"ok", "UP", "healthy"}, body


@allure.story("Readiness probe returns 200")
@allure.severity(allure.severity_level.BLOCKER)
def test_ready_endpoint_returns_200(api):
    resp = api.get("/ready", authenticate=False)
    resp.assert_status(200).assert_latency_under(2000)


@allure.story("ALB-routable health is mounted under /api/v1/claims")
def test_alb_routable_health(api):
    api.get("/api/v1/claims/health", authenticate=False).assert_status(200)


@allure.story("OpenAPI document is published")
def test_openapi_document(api):
    resp = api.get("/openapi.json", authenticate=False).assert_status(200)
    body = resp.json()
    assert body["info"]["title"] == "billing-rcm-service"
    assert "/api/v1/payers" in body["paths"]


@allure.story("Static HS256 JWT can be minted")
@allure.severity(allure.severity_level.BLOCKER)
def test_token_acquisition(token_store):
    token = token_store.get()
    assert token.access_token, "Empty access_token from token store"
    assert not token.is_expired


@allure.story("Unauthenticated calls to protected endpoints return 401")
@pytest.mark.negative
def test_unauthenticated_access_rejected(api):
    api.get("/api/v1/payers", authenticate=False).assert_status(401)
