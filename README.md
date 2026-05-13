# RCM API Automation Framework

API automation framework for an RCM / DME billing service, built on **Playwright (Python)** + **pytest** + **Allure**.

Covers: Patient · Eligibility (270/271) · Claim lifecycle · Payment posting · Remittance (ERA/835) · Prior Authorization.

---

## Highlights

| Capability | Where |
|---|---|
| Multi-environment config (dev/qa/stage/prod) | [config/](config/) + [framework/config.py](framework/config.py) |
| OAuth token caching + auto-refresh | [framework/auth.py](framework/auth.py) |
| Playwright APIRequestContext wrapper | [framework/api_client.py](framework/api_client.py) |
| JSON Schema response validation | [framework/schema_validator.py](framework/schema_validator.py) + [schemas/](schemas/) |
| DB side-effect verification (Postgres/MySQL/Mongo) | [framework/db.py](framework/db.py) |
| Data-driven tests (JSON + CSV) | [testdata/](testdata/) |
| Structured logging + file rotation | [framework/logger.py](framework/logger.py) |
| Allure reporting (steps, attachments, history) | `--alluredir` in [pytest.ini](pytest.ini) |
| Parallel execution | pytest-xdist (`-n auto`) |
| Smart retries on transient failures | pytest-rerunfailures |
| CI workflow + scheduled regression | [.github/workflows/api-tests.yml](.github/workflows/api-tests.yml) |

---

## Project layout

```
.
├── config/                 # one YAML per environment
├── framework/              # reusable framework modules
│   ├── api_client.py       # Playwright wrapper with logging + Allure attachments
│   ├── auth.py             # token store with auto-refresh
│   ├── config.py           # typed config loader (pydantic)
│   ├── data_loader.py      # JSON/CSV helpers
│   ├── db.py               # SQLAlchemy-based DB helpers
│   ├── logger.py           # loguru bootstrap
│   └── schema_validator.py # JSON Schema validation w/ Allure attachments
├── services/               # one class per RCM domain (Page-Object equivalent for APIs)
├── schemas/                # JSON Schemas for response contracts
├── testdata/               # JSON/CSV scenario data
├── tests/
│   ├── conftest.py         # all fixtures live here
│   ├── smoke/              # auto-tagged @pytest.mark.smoke
│   ├── billing/            # patient / claim / payment / eligibility
│   └── regression/         # auto-tagged @pytest.mark.regression
├── scripts/                # run_tests.ps1, run_tests.sh
├── .github/workflows/      # CI pipeline
├── pytest.ini
├── requirements.txt
└── .env.example            # copy to .env and fill secrets
```

---

## Quick start

### 1. Prereqs
- Python 3.11+
- (Optional) Allure CLI — https://allurereport.org/docs/install/

### 2. Set up
```powershell
# Windows / PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit secrets
```
```bash
# macOS / Linux
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # then edit secrets
```

### 3. Run

| Command | What it does |
|---|---|
| `pytest -m smoke --env qa` | Smoke suite against QA |
| `pytest -m "smoke or billing" --env dev` | Smoke + billing against dev |
| `pytest -n auto -m regression --env stage` | Full regression in parallel against stage |
| `pytest tests/billing/test_claim_lifecycle.py -k lifecycle` | Single test |
| `.\scripts\run_tests.ps1 -Env qa -Marker smoke -OpenReport` | One-shot Windows runner |
| `ENV=qa MARKER=smoke ./scripts/run_tests.sh` | One-shot bash runner |

### 4. View the report
```bash
allure serve reports/allure-results
# or, to generate a static site:
allure generate reports/allure-results -o reports/allure-report --clean
```

---

## Writing a new test

1. **Add an endpoint method** to the relevant service (or create a new service under [services/](services/)).
2. **Drop a schema** in [schemas/](schemas/) if you want contract validation.
3. **Add test data** in [testdata/](testdata/) if it's data-driven.
4. **Write the test** under `tests/<area>/`, using the fixtures from [tests/conftest.py](tests/conftest.py):

```python
import allure, pytest
from framework.schema_validator import validate

@allure.feature("Claim")
def test_create_claim(claims, created_patient):
    body = {"patientId": created_patient["id"], "payerId": "P1", "serviceLines": [...]}
    resp = claims.create(body).assert_status(201).assert_latency_under(2000)
    validate(resp.json(), "claim")
```

Useful markers (registered in `pytest.ini`): `smoke`, `regression`, `billing`, `eligibility`, `patient`, `payment`, `auth`, `negative`, `db`, `slow`.

---

## Configuration model

Each environment file in `config/env.<name>.yaml` declares base URLs, default headers, timeouts, retry policy, and feature flags. Switch envs with:

```bash
pytest --env stage         # CLI flag (preferred)
ENV=stage pytest           # env var
RCM_BASE_URL=http://localhost:8080 pytest   # ad-hoc override of base_url
```

Secrets live in `.env` (never committed) or CI secrets — see [.env.example](.env.example).

---

## CI

[.github/workflows/api-tests.yml](.github/workflows/api-tests.yml) runs on every push/PR + a nightly cron, supports a `workflow_dispatch` form (env + suite picker), uploads Allure raw results & logs as artifacts, and publishes a versioned Allure history site to `gh-pages` on `main`.

Required repository secrets: `RCM_USERNAME`, `RCM_PASSWORD`, `RCM_CLIENT_ID`, `RCM_CLIENT_SECRET`, and (optional, for `@pytest.mark.db` tests) `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_DIALECT`.

---

## Plugging in a real API

The endpoints in [services/](services/) and the schemas in [schemas/](schemas/) are an **RCM-flavoured skeleton** — you'll want to:

1. Update `base_path` and any path segments per service to match your real spec.
2. Refine each schema in `schemas/` against an actual response (use a recorded payload as a starting point).
3. Adjust the auth flow in [framework/auth.py](framework/auth.py) if you're using something other than OAuth2 password grant (e.g. client_credentials, JWT, session cookie).
4. Replace the example SQL in [tests/billing/test_patient.py](tests/billing/test_patient.py)'s DB-marked test with your real schema's table/columns.
