"""Smoke tests for the new patient statement endpoints
(added on billing-rcm-service origin/main after PR #83)."""

from __future__ import annotations

import allure
import pytest

pytestmark = [allure.feature("Patient Statements")]


@allure.story("List statements returns a paginated envelope")
def test_list_statements_envelope(statements):
    body = statements.list().assert_status(200).json()
    assert "items" in body and "total" in body, body
    assert "next_cursor" in body


@allure.story("GET unknown statement returns 404")
@pytest.mark.negative
def test_get_unknown_statement_returns_404(statements):
    statements.get("00000000-0000-0000-0000-000000000000").assert_status(404)


@allure.story("Negative — generate with empty body is rejected")
@pytest.mark.negative
def test_generate_empty_body_returns_422(statements):
    statements.generate({}).assert_status_in([400, 422])


@allure.story("Negative — issue an unknown statement returns 404")
@pytest.mark.negative
def test_issue_unknown_statement_returns_404(statements):
    statements.issue("00000000-0000-0000-0000-000000000000").assert_status_in(
        [404, 400, 422]
    )


@allure.story("Negative — void an unknown statement returns 404")
@pytest.mark.negative
def test_void_unknown_statement_returns_404(statements):
    statements.void("00000000-0000-0000-0000-000000000000").assert_status_in(
        [404, 400, 422]
    )
