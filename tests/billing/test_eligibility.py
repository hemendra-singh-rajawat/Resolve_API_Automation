from __future__ import annotations

import os

import allure
import pytest

from framework.schema_validator import validate

pytestmark = [allure.feature("Eligibility"), pytest.mark.eligibility]


def _dummy_verify_payload(payer_id: str, electronic_payer_id: str) -> dict:
    """Well-formed 270 inquiry for a fabricated patient. Coverage will come
    back inactive — the goal is to exercise the request → clearinghouse →
    structured response pipeline, not to find a live policy."""
    return {
        "patient_id": "00000000-1111-7000-8000-000000000001",
        "payer_id": payer_id,
        "electronic_payer_id": electronic_payer_id,
        "policy_number": "DUMMY-POLICY-001",
        "first_name": "Jane",
        "last_name": "Doe",
        "date_of_birth": "1985-04-12",
        "provider_npi": "1234567890",
        "provider_tax_id": "123456789",
        "service_date": "2026-05-13",
        "service_type_code": "30",
        "patient_relationship": "18",
        "checked_by": os.getenv("JWT_USER_ID", "316c469571cb4a9d8a8d82ae1272340c"),
    }


@allure.story("Eligibility log endpoint is paginated")
def test_eligibility_log_envelope(eligibility):
    body = eligibility.history().assert_status(200).json()
    assert "items" in body and "total" in body
    if body["items"]:
        validate(body["items"][0], "eligibility")


@allure.story("Negative — verify with empty body returns 422")
@pytest.mark.negative
def test_verify_empty_body_returns_422(eligibility):
    resp = eligibility.check({}).assert_status(422)
    fields = {err["loc"][-1] for err in resp.json()["detail"]}
    # Spot-check that the most fundamental fields are flagged.
    assert {"patient_id", "payer_id"} & fields


@allure.story("Negative — batch with empty requests list is rejected")
@pytest.mark.negative
def test_batch_empty_list_returns_422(eligibility):
    eligibility.batch([]).assert_status(422)


@allure.story("Negative — batch payload requires populated requests")
@pytest.mark.negative
def test_batch_missing_required_fields(eligibility):
    eligibility.batch([{}]).assert_status_in([400, 422])


@allure.story("Eligibility verify — dummy patient against a real payer")
@allure.severity(allure.severity_level.CRITICAL)
def test_verify_dummy_patient_returns_structured_result(eligibility, payers):
    """Sends a well-formed 270 inquiry for a made-up patient. The clearinghouse
    will respond with coverage_active=False — what we assert is that the
    pipeline (request validation → adapter call → response parsing) works."""
    listing = payers.list().assert_status(200).json()["items"]
    payer = next((p for p in listing if p.get("electronic_payer_id")), None)
    assert payer is not None, "No payer with an electronic_payer_id seeded"

    payload = _dummy_verify_payload(payer["id"], payer["electronic_payer_id"])
    with allure.step(f"Verify against payer {payer['name']} ({payer['electronic_payer_id']})"):
        body = eligibility.check(payload).assert_status(200).assert_latency_under(10000).json()

    assert body["patient_id"] == payload["patient_id"]
    assert body["payer_id"] == payer["id"]
    assert "log_id" in body
    assert "checked_at" in body
    assert isinstance(body["coverage_active"], bool)
    assert isinstance(body["eligibility_issues"], list)
    # A dummy patient with a fake NPI must come back ineligible.
    assert body["eligible"] is False
    assert body["coverage_active"] is False
    issue_codes = {issue["code"] for issue in body["eligibility_issues"]}
    # We expect at least one clearinghouse-level error (bad NPI or inactive cov).
    assert issue_codes, "Expected at least one eligibility issue for a dummy patient"
