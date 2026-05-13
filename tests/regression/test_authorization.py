from __future__ import annotations

import allure
import pytest

pytestmark = [allure.feature("Prior Authorization"), pytest.mark.regression]


@allure.story("Negative — POST with empty body returns 422")
@pytest.mark.negative
def test_request_empty_body_returns_422(authorizations):
    resp = authorizations.request({}).assert_status(422)
    fields = {err["loc"][-1] for err in resp.json()["detail"]}
    # Spot-check the most fundamental fields are flagged.
    assert {"patient_id", "payer_id"} & fields


@allure.story("Negative — GET unknown auth id returns 404")
@pytest.mark.negative
def test_get_unknown_auth_returns_404(authorizations):
    authorizations.get("00000000-0000-0000-0000-000000000000").assert_status(404)


@allure.story("Negative — DELETE unknown auth id returns 404")
@pytest.mark.negative
def test_delete_unknown_auth_returns_404(authorizations):
    authorizations.cancel("00000000-0000-0000-0000-000000000000").assert_status(404)
