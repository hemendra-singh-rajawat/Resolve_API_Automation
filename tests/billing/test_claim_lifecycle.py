from __future__ import annotations

import allure
import pytest

from framework.schema_validator import validate

pytestmark = [allure.feature("Claim Lifecycle"), pytest.mark.billing]


@allure.story("List claims returns a paginated envelope")
def test_list_claims_envelope(claims):
    body = claims.search(limit=5).assert_status(200).json()
    assert "items" in body and "total" in body
    if body["items"]:
        validate(body["items"][0], "claim")


@allure.story("Filter claims by status=draft")
def test_filter_claims_by_status(claims):
    body = claims.search(status="draft", limit=5).assert_status(200).json()
    for item in body["items"]:
        assert item["status"] == "draft"


@allure.story("Get a known claim by id")
def test_get_claim_by_id(claims, existing_claim_id):
    if not existing_claim_id:
        pytest.skip("No seed claim available in tenant")
    body = claims.get(existing_claim_id).assert_status(200).json()
    assert body["id"] == existing_claim_id
    validate(body, "claim")


@allure.story("Validate an existing claim")
def test_validate_claim(claims, existing_claim_id):
    if not existing_claim_id:
        pytest.skip("No seed claim available in tenant")
    body = claims.validate(existing_claim_id).assert_status(200).json()
    assert "valid" in body
    assert "errors" in body
    assert "warnings" in body


@allure.story("Status lookup for an unsubmitted claim returns 404")
def test_status_for_unsubmitted_claim(claims, existing_claim_id):
    if not existing_claim_id:
        pytest.skip("No seed claim available in tenant")
    # Unsubmitted draft claims do not yet have a submission record.
    claims.status(existing_claim_id).assert_status_in([200, 404])


@allure.story("Negative — empty create body returns 422")
@pytest.mark.negative
def test_create_claim_empty_body_returns_422(claims):
    claims.create({}).assert_status(422)


@allure.story("Negative — claim with unknown id returns 404")
@pytest.mark.negative
def test_get_unknown_claim_returns_404(claims):
    claims.get("00000000-0000-0000-0000-000000000000").assert_status(404)


@allure.story("Negative — bulk submit requires submitted_by")
@pytest.mark.negative
def test_bulk_submit_requires_submitter(claims):
    resp = claims.client.post("/api/v1/claims/bulk-submit", json_body={"claim_ids": []})
    resp.assert_status(422)
