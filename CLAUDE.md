# Behavioral Authentication & Phishing Detection System

## Project context

This is a master's thesis project at Moldova State University (USM), Faculty of Mathematics and Informatics. The thesis topic is: **"Использование поведенческого анализа на основе AI для аутентификации транзакций и предотвращения phishing-атак"** (Behavioral analysis with AI for transaction authentication and phishing prevention).

Expected defense: summer 2027. Thesis language: Russian.

## What the system does

A demo web application that combines two ML-driven security modules:

1. **Behavioral authentication module** — continuous user authentication based on a combination of behavioral signals: keystroke dynamics (dwell time, flight time), mouse/touch dynamics (movement, clicks, scrolls), and transaction patterns (amounts, timing, recipients, geolocation). Builds a per-user behavioral profile during an enrollment phase, then flags deviations.

2. **Phishing detection module** — classifies URLs as legitimate or phishing based on lexical and host-based features, combined with behavioral anomalies on the login page (bot-like input speed, copy-paste of passwords, absence of human micro-movements).

The novel contribution is the **coupled use of both modules**: when a behavioral anomaly coincides with a suspicious URL, the risk score is amplified. This is the hypothesis to validate experimentally.

## Technology stack

**Backend**: Python 3.13.x in the current local environment, Django 5.x, Django REST Framework, PostgreSQL.
**ML**: scikit-learn (Isolation Forest, One-Class SVM), XGBoost (phishing URL classifier), joblib for model serialization. No deep learning in v1 — classical ML only. Author has no prior ML experience, so code should favor clarity over cleverness.
**Frontend**: React + Vite + Tailwind + shadcn/ui. Separate SPA, not Django templates. JS collectors in the browser stream behavioral events to the backend via REST.
**Dev tooling**: pytest, black, ruff, pre-commit.

## Architectural principles (critical — will be defended before the thesis committee)

The code must cleanly demonstrate **SOLID principles**. This is non-negotiable and must be visible from the folder structure, not just buried in comments:

- **Single Responsibility**: `FeatureExtractor`, `AnomalyDetector`, `DecisionEngine` are separate classes in separate modules. A class that extracts features does not also predict.
- **Open/Closed**: adding a new behavioral signal (e.g. scroll dynamics) must not require modifying existing extractor code. New `SignalExtractor` subclass, register in the factory, done.
- **Liskov Substitution**: all detectors implement a common `BaseAnomalyDetector` interface (`fit`, `predict`, `score`). Swapping IsolationForest for OneClassSVM must not break the pipeline.
- **Interface Segregation**: narrow interfaces — `IFeatureProvider`, `IPredictor`, `IRiskScorer` are separate, not one god-interface.
- **Dependency Inversion**: `DecisionEngine` depends on `BaseAnomalyDetector`, never on `IsolationForestDetector` directly. Models are injected through a registry.

When you suggest code, check against these principles. If a change would violate one, flag it.

## Repository structure

```
thesis-behavioral-auth/
├── backend/
│   ├── config/                    # Django settings, urls, wsgi
│   ├── apps/
│   │   ├── accounts/              # custom User, auth, enrollment
│   │   ├── transactions/          # transaction model, API
│   │   ├── behavior/              # behavior session tracking
│   │   │   ├── models.py          # BehaviorSession, KeystrokeEvent, MouseEvent
│   │   │   ├── collectors.py      # collection interfaces
│   │   │   ├── serializers.py
│   │   │   └── views.py
│   │   ├── ml_engine/             # ALL ML logic — isolated
│   │   │   ├── interfaces.py      # BaseAnomalyDetector, IFeatureExtractor
│   │   │   ├── extractors/        # KeystrokeFeatureExtractor, MouseFeatureExtractor, URLFeatureExtractor
│   │   │   ├── detectors/         # IsolationForestDetector, XGBoostPhishingDetector
│   │   │   ├── decision.py        # RiskDecisionEngine — combines scores
│   │   │   └── registry.py        # DI container for models
│   │   ├── phishing/              # phishing detection, URL checks
│   │   └── dashboard/             # admin dashboard
│   ├── ml_artifacts/              # serialized models (.pkl, .joblib) — gitignored
│   ├── tests/
│   └── manage.py
├── frontend/
│   ├── src/
│   │   ├── collectors/            # JS: keystroke.js, mouse.js — event listeners
│   │   ├── pages/                 # Login, Transaction, Dashboard
│   │   └── api/                   # axios client for DRF
│   └── public/
├── notebooks/                     # Jupyter — experiments, NOT production code
│   ├── 01_data_exploration.ipynb
│   ├── 02_keystroke_model.ipynb
│   ├── 03_phishing_url_model.ipynb
│   └── 04_evaluation.ipynb
├── data/
│   ├── raw/                       # downloaded datasets — gitignored
│   ├── synthetic/                 # generated transactions
│   └── processed/
└── docs/                          # thesis document lives elsewhere, figures/diagrams here
```

## Datasets

- **CMU Keystroke Dynamics Benchmark Dataset** (Killourhy & Maxion, 2009): 51 users typing `.tie5Roanl` 400 times each. Primary dataset for keystroke experiments. Download: https://www.cs.cmu.edu/~keystroke/
- **UCI Phishing Websites Dataset** / **PhishTank**: URL-based phishing dataset. Classic benchmark, ~30 features.
- **IEEE-CIS Fraud Detection (Kaggle)**: base for synthetic transaction generation.

Do not commit datasets to git. Put them in `data/raw/`, which is gitignored.

## Coding conventions

- PEP 8, type hints everywhere (`from __future__ import annotations` at top of every Python file).
- Docstrings in NumPy style for ML code (explicit input/output shape matters).
- Keep functions under 50 lines. Classes under 200.
- No `print()` for logs — use `logging` module.
- Tests for every public API endpoint and every ML interface contract.
- Commit messages in English, imperative mood: `add keystroke feature extractor`, not `added keystroke feature extractor`.

## Things to avoid

- No deep learning libraries (PyTorch, TensorFlow) unless explicitly asked. Not needed for v1.
- No premature optimization. Correctness first, performance later.
- No copying code from Stack Overflow or tutorials without understanding it — will need to defend every line in front of the committee.
- No hardcoded secrets, API keys, or dataset paths. Use environment variables via `python-decouple` or `django-environ`.
- Do not violate SOLID to save three lines of code. Readable structure matters more than LOC.

## Current status

The repository is no longer just a skeleton. The phishing module has a working
backend implementation through the API layer:

- `apps/phishing/extractors/` implements the URL feature extraction layer for the UCI-style phishing feature set.
- `URLFeatureExtractor` orchestrates lexical extraction first, then runs WHOIS, SSL, HTML, and external-service extractors with timeout handling.
- `FeatureCache` stores and retrieves serialized `URLFeatures` through Django cache.
- `XGBoostPhishingDetector` wraps the model artifact, cache, feature pipeline, and threshold decision semantics.
- `POST /api/phishing/check/` is implemented and returns URL risk probabilities, decision, cache status, and extracted features.
- Phishing checks are persisted as audit records through the existing `PhishingEvent` model.
- The phishing model path is configured via `PHISHING_MODEL_PATH`, with a local default of `data/models/phishing_xgboost_v1.joblib` at the repository root.

The behavior backend collection layer is implemented for sessions, keystroke
events, and mouse events. Anonymous behavior sessions are allowed by default in
development/demo through `BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS=True` so pre-auth
login and phishing collection can be tested. Production transaction
authentication should disable anonymous behavior sessions
(`BEHAVIOR_ALLOW_ANONYMOUS_SESSIONS=False`) unless a pre-auth collection flow is
enabled deliberately.

## What to work on next (context for new sessions)

Near-term priorities, in order:
1. Integrate the phishing check endpoint into the frontend flow without changing detector internals.
2. Decide where phishing checks belong in the login workflow and how the result affects UX/risk handling.
3. Add frontend behavior collectors for the existing behavior collection API.
4. Add deployment/runtime documentation for model artifacts and production cache/database settings.
5. Keep thesis-facing architecture explicit: validation, extraction, caching, prediction, persistence, and HTTP response should remain separate responsibilities.
