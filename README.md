# Behavioral Authentication & Phishing Detection

Master's thesis project — Moldova State University, 2027.

## Quick start

### 1. Start PostgreSQL

```bash
docker compose up -d
```

### 2. Create and activate virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
# .venv\Scripts\activate       # Windows
```

### 3. Install dependencies

```bash
pip install -r backend/requirements-dev.txt
```

### 4. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set SECRET_KEY and DATABASE_URL
```

### 5. Apply migrations

```bash
cd backend
python manage.py migrate
```

### 6. Run development server

```bash
python manage.py runserver
```

Server available at http://127.0.0.1:8000/

## Project structure

```
backend/          Django project root (manage.py lives here)
  config/         Settings package (base / development / production)
  apps/           All Django applications
    accounts/     Custom User model, authentication
    transactions/ Transaction model and API
    behavior/     Behavioral event collection
    ml_engine/    All ML logic — isolated
    phishing/     Phishing URL detection
    dashboard/    Admin dashboard
frontend/         React + Vite SPA (separate dev server)
notebooks/        Jupyter experiments — NOT production code
data/             Datasets (gitignored)
```

## Running tests

```bash
cd backend
pytest
```

## Phishing Module

The phishing API is exposed at:

```text
POST /api/phishing/check/
```

Request body:

```json
{
  "url": "https://example.com/login"
}
```

The endpoint validates the URL, calls the phishing detector through the service
layer, and stores an audit record in `PhishingEvent`.

### Model Artifact

The XGBoost model artifact is configured with `PHISHING_MODEL_PATH`.

Default local value:

```text
../data/models/phishing_xgboost_v1.joblib
```

This path is resolved from the `backend/` directory when loaded from
`backend/.env`. Keep model artifacts out of source code and do not hardcode
absolute machine-specific paths.

If needed, override it in `backend/.env`:

```env
PHISHING_MODEL_PATH=../data/models/phishing_xgboost_v1.joblib
BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS=True
```

### Phishing Tests

Run the phishing test suite from the repository root:

```bash
XDG_CACHE_HOME=/tmp .venv/bin/python -m pytest backend/apps/phishing/tests -v
```

`XDG_CACHE_HOME=/tmp` keeps `tldextract` cache writes in a writable temporary
directory. Without it, local sandboxed runs may fail when `tldextract` tries to
write under the user's home cache directory.

## Behavior Collection

The behavior API collects session, keystroke, and mouse events. Development and
demo runs allow anonymous behavior sessions by default for pre-auth login and
phishing collection scenarios:

```env
BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS=True
```

For production transaction authentication, set
`BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS=False` so behavior sessions must be attached
to an authenticated user. If pre-auth collection is needed in production, enable
it deliberately for that flow rather than treating anonymous sessions as the
default transaction-authentication path.

## Transaction Authentication Flow

The current end-to-end demo flow is:

```text
login -> behavior collection -> transaction attempt -> phishing check
      -> behavior anomaly score -> final transaction decision
```

After login, the frontend behavior collector creates a behavior session and
streams keystroke/mouse metadata to the backend. When the user submits a demo
transaction, the backend creates a transaction attempt, checks the optional
target URL with the phishing detector, extracts behavioral features from the
provided behavior session, runs the baseline anomaly detector, and stores the
final risk assessment.

### Decision Matrix

The transaction risk service currently uses an explainable skeleton policy:

| Condition | Final decision |
| --- | --- |
| Phishing decision is `phishing` | `DENY` |
| Phishing decision is `suspicious` | `CHALLENGE` |
| Phishing check fails while `target_url` is present | `CHALLENGE` |
| Behavior decision is `anomalous` | `CHALLENGE` |
| Behavior decision is `suspicious` and amount is `>= 1000` | `CHALLENGE` |
| Otherwise | `ALLOW` |

This is intentionally not a final production risk engine. It is a thesis demo
workflow that makes phishing and behavioral signals visible and auditable.

### ML Models

- **XGBoost** is used for phishing URL detection.
- **IsolationForest** is used as the baseline behavioral anomaly detector.

The behavioral detector is currently a baseline layer. Persisted per-user model
training is a planned next step.

### Privacy Note

Raw typed key values are not stored. The behavior module stores timing metadata,
mouse metadata, optional hashes, and statistical feature vectors. This keeps the
demo useful for behavioral authentication while avoiding plaintext password or
typed-text collection.

### Manual Demo Steps

1. Log in through the frontend login page.
2. Open the dashboard and verify that behavior sessions/events are visible.
3. Open the transaction page and submit a demo transaction with an optional target URL.
4. Review the returned decision, phishing result, behavior result, and reasons.
5. Use Django admin/audit records to inspect persisted phishing events, behavior sessions, and transaction risk assessments.
