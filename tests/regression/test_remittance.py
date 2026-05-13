from __future__ import annotations

import allure
import pytest

pytestmark = [allure.feature("Remittance (ERA/835)"), pytest.mark.regression]


@allure.story("List ERAs returns a paginated envelope on both endpoints")
def test_list_remittances_both_endpoints(remittances, api):
    primary = remittances.list(limit=10).assert_status(200).json()
    assert isinstance(primary.get("items", []), list)
    assert len(primary["items"]) <= 10

    secondary = api.get("/api/v1/era/").assert_status(200).json()
    assert "items" in secondary


@allure.story("GET an unknown ERA id returns 404")
@pytest.mark.negative
def test_get_unknown_era_returns_404(remittances):
    remittances.get("00000000-0000-0000-0000-000000000000").assert_status(404)


@allure.story("POST /era/process with empty body returns 422")
@pytest.mark.negative
def test_process_empty_body_returns_422(remittances):
    remittances.upload({}).assert_status(422)


@allure.story("POST /eras/retrieve still requires tenant_id as a query parameter (design concern)")
@pytest.mark.negative
def test_retrieve_requires_query_tenant_id(api):
    resp = api.post(
        "/api/v1/eras/retrieve",
        json_body={"date_from": "2026-05-01", "date_to": "2026-05-13"},
    )
    # Documents the bug: tenant_id is taken from the query string rather than the JWT.
    resp.assert_status(422)
    fields = {err["loc"][-1] for err in resp.json()["detail"]}
    assert "tenant_id" in fields
