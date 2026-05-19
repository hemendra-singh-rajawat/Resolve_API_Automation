from __future__ import annotations

import os
import time

import allure
import pytest

pytestmark = [allure.feature("Eligibility"), pytest.mark.eligibility]


# --- 10-patient dummy batch --------------------------------------------------
# Fabricated patients sent to /api/v1/eligibility/batch. The endpoint queues
# them onto Celery and returns 202 immediately; the worker then processes each
# 270 inquiry asynchronously and writes one eligibility_log row per request.
#
# provider_npi and provider_tax_id are NOT varied per patient — in a real
# batch eligibility submission those identify the *provider* sending the
# request, not the patient, so they're constant across all 10 entries.
#
# This pair is approved in the Claim.MD sandbox. Changing either value causes
# Claim.MD to reject every 270 with CH_ERROR_VAL1 ("Provider record must be
# approved...") and the resulting log rows come back with every coverage
# field null. If you ever rotate providers, verify with a single
# /eligibility/verify call first.
BATCH_PROVIDER_NPI: str = "1111111112"
BATCH_PROVIDER_TAX_ID: str = "999999999"

BATCH_DUMMY_PATIENTS: list[dict] = [
    {"first_name": "Alice", "last_name": "Anderson", "date_of_birth": "1980-01-15", "policy_number": "P-001"},
    {"first_name": "Bob",   "last_name": "Barker",   "date_of_birth": "1972-03-22", "policy_number": "P-002"},
    {"first_name": "Carol", "last_name": "Carter",   "date_of_birth": "1990-07-08", "policy_number": "P-003"},
    {"first_name": "David", "last_name": "Davis",    "date_of_birth": "1965-11-30", "policy_number": "P-004"},
    {"first_name": "Eve",   "last_name": "Evans",    "date_of_birth": "1988-05-19", "policy_number": "P-005"},
    {"first_name": "Frank", "last_name": "Foster",   "date_of_birth": "1975-09-04", "policy_number": "P-006"},
    {"first_name": "Grace", "last_name": "Garcia",   "date_of_birth": "1992-12-12", "policy_number": "P-007"},
    {"first_name": "Henry", "last_name": "Hill",     "date_of_birth": "1968-06-27", "policy_number": "P-008"},
    {"first_name": "Iris",  "last_name": "Ingram",   "date_of_birth": "1983-02-14", "policy_number": "P-009"},
    {"first_name": "Jack",  "last_name": "Jones",    "date_of_birth": "1978-08-21", "policy_number": "P-010"},
]


# --- Dummy-patient verification scenarios ------------------------------------
# Sends a well-formed 270 inquiry for a fabricated patient and exercises the
# request → ClearinghouseAdapter → 271-parsing pipeline. We do NOT rely on the
# test running against any pre-seeded patient row in the DB.
#
# NOTE: there used to be a second "jane-doe-ineligible" case here that used a
# bad NPI (1234567890) to provoke an ineligible result. PR #83 added a CMS
# Luhn validator to provider_npi, so that NPI is now rejected with 422 at the
# API boundary before it ever reaches Claim.MD. That scenario is now covered
# precisely by test_pr83_npi_luhn_rejected below, so the redundant happy-path
# variant was removed rather than papered over.

DUMMY_PATIENT_CASES: list[dict] = [
    {
        "id": "tom-holland-eligible",
        "label": "Tom Holland — fabricated patient matching a sandbox policy, expect eligible",
        "electronic_payer_id": "52192",  # BlueCross NY — sandbox returns active coverage for this demo combo
        "payload_overrides": {
            "patient_id": "0193c1f4-5a8e-7b3c-9d2f-1a4b8c6d7e9f",
            # NOTE: policy_number was previously "" (the clearinghouse accepts demographic-only
            # lookups), but PR #83 added `min_length=1` to EligibilityVerifyRequest.policy_number.
            # An empty string now fails Pydantic validation with 422 before the call leaves the
            # service. Any non-empty value is accepted; the sandbox still resolves coverage from
            # demographics + payer.
            "policy_number": "POLICY-TOM-001",
            "first_name": "Tom",
            "last_name": "Holland",
            "date_of_birth": "1975-08-21",
            "provider_npi": "1111111112",
            "provider_tax_id": "999999999",
            "service_date": "2026-05-11",
            "checked_by": "0193c1f4-5a8e-7b3c-9d2f-3c6d0e8f9a1b",
        },
        "expected_eligible": True,
        "expected_coverage_active": True,
        "expected_issue_codes_any": set(),
    },
]


def _build_payload(case: dict, payer_id: str, electronic_payer_id: str) -> dict:
    base = {
        "patient_id": "00000000-1111-7000-8000-000000000001",
        "payer_id": payer_id,
        "electronic_payer_id": electronic_payer_id,
        "policy_number": "DUMMY-POLICY-000",
        "first_name": "Test",
        "last_name": "Patient",
        "date_of_birth": "1990-01-01",
        "provider_npi": "1234567890",
        "provider_tax_id": "123456789",
        "service_date": "2026-05-13",
        "service_type_code": "30",
        "patient_relationship": "18",
        "checked_by": os.getenv("JWT_USER_ID", "316c469571cb4a9d8a8d82ae1272340c"),
    }
    base.update(case["payload_overrides"])
    # Server-derived fields are filled in after the payer lookup.
    base["payer_id"] = payer_id
    base["electronic_payer_id"] = electronic_payer_id
    return base


@allure.story("Eligibility verify — dummy patient against a real payer")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("case", DUMMY_PATIENT_CASES, ids=lambda c: c["id"])
def test_verify_dummy_patient_returns_structured_result(eligibility, payers, case):
    """For each dummy-patient case:
      1. Pick a real payer from the system (so payer FK validation passes).
      2. Send the 270 inquiry.
      3. Assert that the response is the expected shape AND that eligible /
         coverage_active match the case expectation.
    The Claim.MD sandbox returns active coverage for some fabricated DOB +
    name combos and inactive for others — we capture both behaviours."""
    listing = payers.list().assert_status(200).json()["items"]
    target_eid = case["electronic_payer_id"]
    payer = next((p for p in listing if p.get("electronic_payer_id") == target_eid), None)
    if payer is None:
        pytest.skip(f"Payer with electronic_payer_id={target_eid} not seeded in this tenant")

    payload = _build_payload(case, payer["id"], payer["electronic_payer_id"])
    allure.attach(
        str(payload), name="request payload", attachment_type=allure.attachment_type.TEXT
    )

    with allure.step(case["label"]):
        resp = eligibility.check(payload).assert_status(200).assert_latency_under(10000)
        body = resp.json()

    allure.attach(
        str(body), name="response body", attachment_type=allure.attachment_type.TEXT
    )

    # --- shape checks --------------------------------------------------------
    assert body["patient_id"] == payload["patient_id"]
    assert body["payer_id"] == payer["id"]
    assert "log_id" in body and isinstance(body["log_id"], str)
    assert "checked_at" in body
    assert isinstance(body["coverage_active"], bool)
    assert isinstance(body["eligible"], bool)
    assert isinstance(body["eligibility_issues"], list)

    # --- per-case expectations -----------------------------------------------
    assert body["eligible"] is case["expected_eligible"], (
        f"case={case['id']} expected eligible={case['expected_eligible']} got {body['eligible']}"
    )
    assert body["coverage_active"] is case["expected_coverage_active"], (
        f"case={case['id']} expected coverage_active={case['expected_coverage_active']} "
        f"got {body['coverage_active']}"
    )

    issue_codes = {issue["code"] for issue in body["eligibility_issues"]}
    if case["expected_eligible"]:
        # Eligible case should return zero blocking issues.
        blocking = [i for i in body["eligibility_issues"] if i.get("severity") == "error"]
        assert not blocking, f"Eligible case had blocking issues: {blocking}"
    elif case["expected_issue_codes_any"]:
        assert issue_codes & case["expected_issue_codes_any"], (
            f"case={case['id']} expected one of {case['expected_issue_codes_any']} in issues, "
            f"got {issue_codes}"
        )


@allure.story("Batch eligibility — 10 fabricated patients accepted and processed")
@allure.severity(allure.severity_level.CRITICAL)
def test_batch_eligibility_10_dummy_patients(eligibility, payers):
    """End-to-end batch flow:
      1. Build a 10-patient batch payload (one approved provider, 10 patients).
      2. POST /api/v1/eligibility/batch → expect 202 with batch_id + request_count=10.
      3. Poll /api/v1/eligibility/logs and confirm 10 NEW rows with
         request_type='batch' land within the worker SLA.
      4. Assert the new batch rows carry real coverage data — at least one row
         must have a non-null transaction_id (i.e. a 270 transaction actually
         reached Claim.MD). All-null rows would mean the provider was rejected
         at the clearinghouse before the request was issued.
    """
    listing = payers.list().assert_status(200).json()["items"]
    payer = next((p for p in listing if p.get("electronic_payer_id") == "52192"), None)
    if payer is None:
        pytest.skip("BlueCross NY payer (52192) not seeded in this tenant")

    user_id = os.getenv("JWT_USER_ID", "316c469571cb4a9d8a8d82ae1272340c")
    requests_payload = []
    for i, p in enumerate(BATCH_DUMMY_PATIENTS, 1):
        requests_payload.append({
            "patient_id": f"00000000-1111-7000-8000-{i:012d}",
            "payer_id": payer["id"],
            "electronic_payer_id": payer["electronic_payer_id"],
            "provider_npi": BATCH_PROVIDER_NPI,
            "provider_tax_id": BATCH_PROVIDER_TAX_ID,
            "service_date": "2026-05-14",
            "service_type_code": "30",
            "patient_relationship": "18",
            "checked_by": user_id,
            **p,
        })
    allure.attach(
        str(requests_payload), name="batch payload (10 patients)",
        attachment_type=allure.attachment_type.TEXT,
    )

    # --- Submit the batch ---------------------------------------------------
    baseline = eligibility.history().assert_status(200).json()["total"]
    with allure.step(f"POST /api/v1/eligibility/batch with {len(requests_payload)} requests"):
        resp = eligibility.batch(requests_payload).assert_status(202).assert_latency_under(5000)
        body = resp.json()

    allure.attach(str(body), name="batch acceptance", attachment_type=allure.attachment_type.TEXT)
    assert body["request_count"] == 10
    assert body["batch_id"]

    # --- Wait for the worker to process every entry --------------------------
    deadline = time.time() + 60  # 60s SLA
    new_rows = 0
    with allure.step("Poll eligibility log until 10 new batch rows arrive (SLA 60 s)"):
        while time.time() < deadline:
            time.sleep(2)
            current = eligibility.history().assert_status(200).json()
            new_rows = current["total"] - baseline
            if new_rows >= 10:
                break

    assert new_rows >= 10, (
        f"Worker only landed {new_rows}/10 rows within 60 s SLA. "
        "Is the Celery worker running? (celery -A billing_rcm_service.worker worker)"
    )

    # --- Verify the new rows have real clearinghouse data --------------------
    # Pull the latest 10 rows and check they are our batch with populated fields.
    with allure.step("Inspect the 10 newest log rows and confirm 270 transactions were issued"):
        latest = eligibility.history().assert_status(200).json()["items"][:10]
        batch_rows = [r for r in latest if r.get("request_type") == "batch"]
        allure.attach(
            str(batch_rows), name="newest 10 batch rows",
            attachment_type=allure.attachment_type.TEXT,
        )

    assert len(batch_rows) >= 10, (
        f"Expected ≥10 newest rows to be batch type, got {len(batch_rows)}"
    )

    with_txn = [r for r in batch_rows if r.get("transaction_id")]
    assert with_txn, (
        "All batch rows have transaction_id=null. This means the 270 was rejected at the "
        "clearinghouse (likely provider not approved). Check BATCH_PROVIDER_NPI and "
        "BATCH_PROVIDER_TAX_ID in this file."
    )

    with_coverage = [r for r in batch_rows if r.get("coverage_active") is True]
    allure.attach(
        f"batch rows: {len(batch_rows)}\n"
        f"  with transaction_id: {len(with_txn)}\n"
        f"  with coverage_active=True: {len(with_coverage)}",
        name="row-level summary",
        attachment_type=allure.attachment_type.TEXT,
    )


# --- PR #83: input-validation guardrails -------------------------------------
# These tests exist to prove the new field-level validators in
# EligibilityVerifyRequest reject bad input at the API boundary.
# Reference: billing-rcm-service PR #83 (feat/eligibility-api-validation).
# If they fail with "expected 422, got 200", the running uvicorn has not yet
# picked up the new code — restart it and re-run.

def _valid_verify_payload(payer_id: str, electronic_payer_id: str) -> dict:
    """A baseline payload that passes every new validator. Each negative test
    mutates one field to assert the validator catches it."""
    return {
        "patient_id": "00000000-1111-7000-8000-000000000099",
        "payer_id": payer_id,
        "electronic_payer_id": electronic_payer_id,
        "policy_number": "BASELINE-001",
        "first_name": "Base",
        "last_name": "Line",
        "date_of_birth": "1980-01-01",
        "provider_npi": "1111111112",   # Luhn-valid
        "provider_tax_id": "999999999", # 9 digits
        "service_date": "2026-05-15",   # within window
        "service_type_code": "30",
        "patient_relationship": "18",
        "checked_by": "316c469571cb4a9d8a8d82ae1272340c",
    }


@allure.story("PR #83 — empty policy_number is rejected with 422")
@pytest.mark.negative
def test_pr83_empty_policy_number_rejected(eligibility, payers):
    payer = next(p for p in payers.list().json()["items"] if p.get("electronic_payer_id") == "52192")
    body = _valid_verify_payload(payer["id"], "52192")
    body["policy_number"] = ""
    eligibility.check(body).assert_status(422)


@allure.story("PR #83 — provider_npi failing Luhn checksum is rejected with 422")
@pytest.mark.negative
def test_pr83_npi_luhn_rejected(eligibility, payers):
    payer = next(p for p in payers.list().json()["items"] if p.get("electronic_payer_id") == "52192")
    body = _valid_verify_payload(payer["id"], "52192")
    body["provider_npi"] = "1234567890"  # 10 digits but fails Luhn (with 80840 prefix)
    eligibility.check(body).assert_status(422)


@allure.story("PR #83 — provider_tax_id not 9 digits is rejected with 422")
@pytest.mark.negative
def test_pr83_tax_id_format_rejected(eligibility, payers):
    payer = next(p for p in payers.list().json()["items"] if p.get("electronic_payer_id") == "52192")
    body = _valid_verify_payload(payer["id"], "52192")
    body["provider_tax_id"] = "12345"  # too short
    eligibility.check(body).assert_status(422)


@allure.story("PR #83 — patient_relationship outside {18, G8} is rejected with 422")
@pytest.mark.negative
def test_pr83_patient_relationship_rejected(eligibility, payers):
    payer = next(p for p in payers.list().json()["items"] if p.get("electronic_payer_id") == "52192")
    body = _valid_verify_payload(payer["id"], "52192")
    body["patient_relationship"] = "01"  # not in the allowed set
    eligibility.check(body).assert_status(422)


@allure.story("PR #83 — service_date too far in the future is rejected with 422")
@pytest.mark.negative
def test_pr83_service_date_too_future_rejected(eligibility, payers):
    payer = next(p for p in payers.list().json()["items"] if p.get("electronic_payer_id") == "52192")
    body = _valid_verify_payload(payer["id"], "52192")
    body["service_date"] = "2030-01-01"  # > today + 90 days
    eligibility.check(body).assert_status(422)


@allure.story("PR #83 — service_date too far in the past is rejected with 422")
@pytest.mark.negative
def test_pr83_service_date_too_past_rejected(eligibility, payers):
    payer = next(p for p in payers.list().json()["items"] if p.get("electronic_payer_id") == "52192")
    body = _valid_verify_payload(payer["id"], "52192")
    body["service_date"] = "2020-01-01"  # > today - 365 days
    eligibility.check(body).assert_status(422)


@allure.story("PR #83 — batch with duplicate (patient_id, payer_id, service_date) rejected 422")
@pytest.mark.negative
def test_pr83_batch_duplicate_rejected(eligibility, payers):
    payer = next(p for p in payers.list().json()["items"] if p.get("electronic_payer_id") == "52192")
    one = _valid_verify_payload(payer["id"], "52192")
    eligibility.batch([one, dict(one)]).assert_status(422)
