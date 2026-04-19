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
