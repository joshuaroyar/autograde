# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project overview
- Purpose: Autograde ingests student answer sheet PDFs, extracts per-question text via OCR/NLP, and evaluates against a teacher-provided question paper and rubric. Teachers can review, correct, and publish results.
- Major components:
  - backend/: FastAPI (Python) HTTP API
  - frontend/: Flutter app (scaffold to be generated)
  - infra/: Docker Compose for local stack (backend + PostgreSQL + Redis)

Common commands
Backend (local development)
- Create and activate a virtualenv, then install deps:
  - python3 -m venv backend/.venv
  - source backend/.venv/bin/activate
  - pip install -r backend/requirements.txt
- Run the API with autoreload from repo root:
  - uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend

Backend (Docker image)
- Build and run just the backend image locally from repo root:
  - docker build -f backend/Dockerfile -t autograde-backend .
  - docker run --rm -p 8000:8000 autograde-backend

Local stack with Docker Compose
- Ensure an .env file exists at repo root with the variables referenced in infra/docker-compose.yml (see “Environment” below).
- Bring up the stack (backend, Postgres, Redis) from infra/:
  - docker compose -f infra/docker-compose.yml up --build
- Hot-reload dev (backend code mounted into the container) is enabled via volumes.

Dependencies
- Python dependencies are pinned in backend/requirements.txt. The backend Dockerfile installs system packages for Tesseract OCR and compilers needed by some wheels.

Environment
- docker-compose reads env vars from ../.env relative to infra/. Provide at least:
  - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
  - DATABASE_URL (e.g., postgresql+psycopg2://USER:PASSWORD@db:5432/DB)
  - REDIS_URL (e.g., redis://redis:6379/0)

Frontend (Flutter)
- Generate scaffold in frontend/ (if not present) and run:
  - flutter create frontend
  - flutter run -d chrome (or -d linux if configured)
  See frontend/README.md for the current guidance.

Tests and linting
- A test framework and linter are not configured in this repository yet. No canonical commands exist here for running tests, running a single test, or linting.

High-level architecture and flows
- API surface (backend/app/main.py):
  - Health: GET /health
  - Student flows: upload answer sheet; fetch results (optionally filtered by subject)
  - Teacher flows: upload question paper; list answer sheets; correct a result; publish a result
  - Most business logic is currently stubbed with TODOs; endpoints return placeholder payloads.
- OCR/NLP pipeline intent (from requirements and Dockerfile):
  - pdfplumber and pytesseract are included; the backend image installs tesseract-ocr, indicating on-box OCR for extracting text per question.
  - celery and redis are listed in requirements, and Redis is provisioned via docker-compose; this suggests background jobs for document processing are planned, though worker code is not yet present.
- Persistence:
  - PostgreSQL is provisioned via docker-compose. DATABASE_URL is passed to the backend container. SQLAlchemy and Alembic are included in requirements, though no Alembic config is committed yet.
- Runtime topology (local):
  - docker-compose.yml orchestrates three services: backend (FastAPI via uvicorn), db (Postgres 16), and redis (Redis 7). The backend service depends_on db and redis and mounts ../backend -> /app for live reload.

References summarized from repo docs
- Root README highlights the student and teacher flows and provides quickstart for the backend and Compose stack.
- docs/README.md lists placeholders for architecture and API docs to be added.
- frontend/README.md describes how to generate and run a Flutter app for both student and teacher views.

Notes for future updates
- When tests (e.g., pytest) and lint/format tools are added, update this file with the exact commands, including how to run a single test or a filtered subset (e.g., -k expressions) and the chosen linter/formatter invocations.
