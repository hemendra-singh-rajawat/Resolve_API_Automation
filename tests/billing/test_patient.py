"""billing-rcm-service does not own patient demographics — those live in
patient-service. The PatientService class is repurposed to call the payer
endpoints, which are this service's only standalone master entity. These
tests therefore exercise payer CRUD via the patient-shaped fixtures."""

from __future__ import annotations

import allure
import pytest

from framework.schema_validator import validate

pytestmark = [allure.feature("Payer (Patient shim)"), pytest.mark.patient]


@allure.story("Create payer returns 201 and the new record matches the schema")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_payer_returns_id_and_matches_schema(payers, payer_payload):
    resp = payers.create(payer_payload).assert_status_in([200, 201])
    body = resp.json()
    assert body["name"] == payer_payload["name"]
    assert body["id"]
    validate(body, "payer")
    payers.delete(body["id"]).assert_status_in([200, 204])


@allure.story("List payers is paginated and contains a created payer")
def test_list_payers_contains_created(payers, created_payer):
    resp = payers.list().assert_status(200)
    body = resp.json()
    assert "items" in body and "total" in body
    ids = {p["id"] for p in body["items"]}
    assert created_payer["id"] in ids


@allure.story("Filter payers by status=active")
def test_search_payer_by_status(payers, created_payer):
    resp = payers.list(status="active").assert_status(200)
    items = resp.json()["items"]
    assert any(p["id"] == created_payer["id"] for p in items)


@allure.story("PUT a payer (currently 500 — known service bug)")
@pytest.mark.xfail(
    reason="billing-rcm-service bug: PUT /api/v1/payers/{id} returns 500 — see API_TEST_REPORT.md",
    strict=False,
)
def test_put_payer_updates_record(payers, created_payer, payer_payload):
    updated = dict(payer_payload)
    updated["name"] = created_payer["name"] + "-renamed"
    updated["electronic_payer_id"] = created_payer["electronic_payer_id"]
    resp = payers.update(created_payer["id"], updated).assert_status(200)
    assert resp.json()["name"].endswith("-renamed")


@allure.story("Soft-delete a payer returns 204")
def test_delete_payer(payers, payer_payload):
    payer = payers.create(payer_payload).assert_status_in([200, 201]).json()
    payers.delete(payer["id"]).assert_status(204)


@allure.story("Negative — create without required name")
@pytest.mark.negative
def test_create_payer_missing_name(payers, payer_payload):
    payer_payload.pop("name")
    payers.create(payer_payload).assert_status_in([400, 422])


@allure.story("Negative — duplicate electronic_payer_id returns 409")
@pytest.mark.negative
def test_create_payer_duplicate_electronic_id(payers, created_payer, payer_payload):
    payer_payload["electronic_payer_id"] = created_payer["electronic_payer_id"]
    payers.create(payer_payload).assert_status(409)
