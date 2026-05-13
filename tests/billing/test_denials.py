from __future__ import annotations

import allure
import pytest

pytestmark = [allure.feature("Denials"), pytest.mark.billing]


@allure.story("Denial worklist returns a paginated envelope")
def test_list_denials_envelope(denials):
    body = denials.list().assert_status(200).json()
    assert "items" in body and "total" in body


@allure.story("Negative — appeal a denial with unknown id returns 404 or 422")
@pytest.mark.negative
def test_appeal_unknown_denial(denials):
    denials.appeal(
        "00000000-0000-0000-0000-000000000000", reason="test"
    ).assert_status_in([404, 422])


@allure.story("Negative — assign a denial with unknown id returns 404 or 422")
@pytest.mark.negative
def test_assign_unknown_denial(denials):
    denials.assign(
        "00000000-0000-0000-0000-000000000000",
        assigned_to="316c469571cb4a9d8a8d82ae1272340c",
    ).assert_status_in([404, 422])


@allure.story("Negative — resolve a denial with unknown id returns 404 or 422")
@pytest.mark.negative
def test_resolve_unknown_denial(denials):
    denials.resolve(
        "00000000-0000-0000-0000-000000000000", resolution="test"
    ).assert_status_in([404, 422])
