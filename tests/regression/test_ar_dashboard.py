from __future__ import annotations

import allure

from framework.schema_validator import validate

pytestmark = [allure.feature("AR / Dashboard")]


@allure.story("AR aging report returns the expected envelope")
def test_ar_aging_envelope(ar):
    body = ar.aging().assert_status(200).json()
    validate(body, "ar")


@allure.story("AR trend report respects the days parameter")
def test_ar_trend_default(ar):
    body = ar.trend().assert_status(200).json()
    assert "days" in body and "points" in body


@allure.story("AR trend with days=30")
def test_ar_trend_with_days(ar):
    body = ar.trend(days=30).assert_status(200).json()
    assert body["days"] == 30


@allure.story("Dashboard summary returns expected KPIs")
def test_dashboard_kpis(ar):
    body = ar.dashboard().assert_status(200).json()
    validate(body, "dashboard")
