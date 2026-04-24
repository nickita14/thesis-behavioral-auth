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
