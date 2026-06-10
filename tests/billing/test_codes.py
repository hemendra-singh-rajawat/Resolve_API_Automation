"""Smoke tests for the new HCPCS + ICD-10 code master endpoints
(added on billing-rcm-service origin/main after PR #83)."""

from __future__ import annotations

import allure
import pytest

pytestmark = [allure.feature("Code Master Data")]


# --- HCPCS --------------------------------------------------------------------

@allure.story("List HCPCS codes returns a paginated envelope")
def test_list_hcpcs_envelope(codes):
    body = codes.list_hcpcs().assert_status(200).json()
    assert "items" in body and "total" in body, body
    # next_cursor may be None on the first page; just assert it exists
    assert "next_cursor" in body


@allure.story("GET unknown HCPCS code returns 404")
@pytest.mark.negative
def test_get_unknown_hcpcs_returns_404(codes):
    codes.get_hcpcs("ZZ999").assert_status(404)


@allure.story("Negative — HCPCS import with empty body is rejected")
@pytest.mark.negative
def test_import_hcpcs_empty_body_rejected(codes):
    codes.import_hcpcs_json({}).assert_status_in([400, 422])


# --- ICD-10 -------------------------------------------------------------------

@allure.story("List ICD-10 codes returns a paginated envelope")
def test_list_icd10_envelope(codes):
    body = codes.list_icd10().assert_status(200).json()
    assert "items" in body and "total" in body, body


@allure.story("GET unknown ICD-10 code returns 404")
@pytest.mark.negative
def test_get_unknown_icd10_returns_404(codes):
    codes.get_icd10("Z99.999").assert_status(404)


@allure.story("Negative — ICD-10 import with empty body is rejected")
@pytest.mark.negative
def test_import_icd10_empty_body_rejected(codes):
    codes.import_icd10_json({}).assert_status_in([400, 422])
