from __future__ import annotations

import allure
import pytest

from framework.schema_validator import validate

pytestmark = [allure.feature("Payment Posting"), pytest.mark.payment]


@allure.story("List payments returns a paginated envelope")
def test_list_payments_envelope(payments):
    resp = payments.list().assert_status(200)
    validate(resp.json(), "payment")


@allure.story("Negative — POST /payments with empty body returns 422 with required fields")
@pytest.mark.negative
def test_post_payment_empty_body_returns_422(payments):
    resp = payments.post_payment({}).assert_status(422)
    fields = {err["loc"][-1] for err in resp.json()["detail"]}
    assert {"payment_type", "source", "amount"} & fields


@allure.story("Negative — refund endpoint is not implemented and 404s")
@pytest.mark.negative
def test_refund_endpoint_not_implemented(payments):
    payments.refund("00000000-0000-0000-0000-000000000000", 10.0, "n/a").assert_status_in(
        [404, 405]
    )
