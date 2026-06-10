from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import allure
import pytest
from faker import Faker
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from framework.api_client import APIClient  # noqa: E402
from framework.auth import TokenStore  # noqa: E402
from framework.config import EnvConfig, get_env, get_secrets  # noqa: E402
from framework.logger import configure_logging, get_logger  # noqa: E402
from services.ar_service import ARService  # noqa: E402
from services.claim_service import ClaimService  # noqa: E402
from services.codes_service import CodesService  # noqa: E402
from services.denial_service import DenialService  # noqa: E402
from services.eligibility_service import EligibilityService  # noqa: E402
from services.patient_service import PatientService  # noqa: E402
from services.payer_service import PayerService  # noqa: E402
from services.payment_service import PaymentService  # noqa: E402
from services.remittance_service import RemittanceService  # noqa: E402
from services.statements_service import StatementsService  # noqa: E402

# NOTE: AuthorizationService removed — the billing-rcm-service "prior_authorization"
# feature was dropped on origin/main (commit 40ac307). Endpoints under
# /api/v1/prior-authorizations no longer exist.

log = get_logger(__name__)


# --- CLI options ------------------------------------------------------------

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--env",
        action="store",
        default=None,
        help="Override env (dev|qa|stage|prod). Falls back to $ENV then 'qa'.",
    )


def pytest_configure(config: pytest.Config) -> None:
    configure_logging()
    env_opt = config.getoption("--env")
    if env_opt:
        os.environ["ENV"] = env_opt
    # Reset the cached env after we may have changed it.
    get_env.cache_clear()  # type: ignore[attr-defined]


# --- session-scoped fixtures -----------------------------------------------

@pytest.fixture(scope="session")
def env() -> EnvConfig:
    cfg = get_env()
    log.info("Running against env={} base_url={}", cfg.name, cfg.base_url)
    allure.dynamic.parameter("env", cfg.name)
    allure.dynamic.parameter("base_url", cfg.base_url)
    return cfg


@pytest.fixture(scope="session")
def token_store(env: EnvConfig) -> TokenStore:
    return TokenStore(env, get_secrets())


@pytest.fixture(scope="session")
def playwright_request(env: EnvConfig):
    """Single Playwright APIRequestContext for the whole session.
    Cheaper than spinning one per test and gives us connection reuse."""
    with sync_playwright() as pw:
        ctx = pw.request.new_context(
            base_url=env.base_url,
            timeout=env.timeout_ms,
            extra_http_headers=env.default_headers,
            ignore_https_errors=not env.verify_ssl,
        )
        try:
            yield ctx
        finally:
            ctx.dispose()


@pytest.fixture(scope="session")
def api(playwright_request, env: EnvConfig, token_store: TokenStore) -> APIClient:
    return APIClient(playwright_request, env, token_store)


# --- service fixtures (one per RCM domain) ---------------------------------

@pytest.fixture(scope="session")
def patients(api: APIClient) -> PatientService:
    return PatientService(api)


@pytest.fixture(scope="session")
def payers(api: APIClient) -> PayerService:
    return PayerService(api)


@pytest.fixture(scope="session")
def claims(api: APIClient) -> ClaimService:
    return ClaimService(api)


@pytest.fixture(scope="session")
def eligibility(api: APIClient) -> EligibilityService:
    return EligibilityService(api)


@pytest.fixture(scope="session")
def payments(api: APIClient) -> PaymentService:
    return PaymentService(api)


@pytest.fixture(scope="session")
def remittances(api: APIClient) -> RemittanceService:
    return RemittanceService(api)


@pytest.fixture(scope="session")
def codes(api: APIClient) -> CodesService:
    return CodesService(api)


@pytest.fixture(scope="session")
def statements(api: APIClient) -> StatementsService:
    return StatementsService(api)


@pytest.fixture(scope="session")
def denials(api: APIClient) -> DenialService:
    return DenialService(api)


@pytest.fixture(scope="session")
def ar(api: APIClient) -> ARService:
    return ARService(api)


# --- per-test utilities ----------------------------------------------------

@pytest.fixture(scope="session")
def faker() -> Faker:
    return Faker("en_US")


def _payer_payload(faker: Faker) -> dict:
    """Builds a unique payer payload — safe to call many times per test run."""
    return {
        "name": f"AutoPayer-{faker.unique.bothify('??##??##')}",
        "electronic_payer_id": str(random.randint(70000, 99999)),
        "address_line1": faker.street_address(),
        "address_city": faker.city(),
        "address_state": faker.state_abbr(),
        "address_zip": faker.zipcode(),
        "phone": faker.numerify("+1##########"),
        "timely_filing_days": 90,
    }


@pytest.fixture
def payer_payload(faker: Faker) -> dict:
    return _payer_payload(faker)


@pytest.fixture
def created_payer(payers: PayerService, faker: Faker):
    """Create a payer for a test, then soft-delete on teardown."""
    body = _payer_payload(faker)
    resp = payers.create(body).assert_status_in([200, 201])
    record = resp.json()
    yield record
    try:
        payers.delete(record["id"]).assert_status_in([200, 204, 404])
    except Exception as e:  # noqa: BLE001
        log.warning("Cleanup delete failed for payer {}: {}", record.get("id"), e)


# Backwards-compatible alias — the original conftest's `patient_payload` and
# `created_patient` fixtures are repurposed to payers since billing-rcm-service
# does not own patient data.
@pytest.fixture
def patient_payload(payer_payload: dict) -> dict:
    return payer_payload


@pytest.fixture
def created_patient(created_payer: dict):
    return created_payer


@pytest.fixture(scope="session")
def existing_claim_id(claims: ClaimService) -> str | None:
    """Pick the first claim_id from the existing dataset, if any.
    Used by lifecycle tests that need a real claim without creating one."""
    resp = claims.search(limit=1)
    if resp.status != 200:
        return None
    items = resp.json().get("items", [])
    return items[0]["id"] if items else None


# --- DB fixture (opt-in via @pytest.mark.db) -------------------------------

@pytest.fixture
def db():
    """Lazy import so suites that don't touch DB don't need DB drivers configured."""
    from framework import db as _db
    return _db


# --- Allure metadata on every test -----------------------------------------

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        log.error("FAIL {}: {}", item.nodeid, rep.longreprtext[:500])


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-tag tests under tests/smoke/ and tests/regression/ for convenience."""
    for item in items:
        nodeid = item.nodeid.replace("\\", "/")
        if "/smoke/" in nodeid:
            item.add_marker(pytest.mark.smoke)
        if "/regression/" in nodeid:
            item.add_marker(pytest.mark.regression)
