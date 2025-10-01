# Autograde

Autograde is an automated paper correction tool. Students upload a PDF of their answer sheet; the system extracts text per question using NLP/OCR and evaluates it against the teacher-provided question paper and rubric. Teachers can review, correct, and publish results.

Components
- Frontend: Flutter (Student and Teacher views)
- Backend: FastAPI (Python)
- DB: PostgreSQL
- Queue/Cache: Redis (for background processing)

High-level flows
- Student: select subject -> view question paper -> upload answer sheet (PDF) -> view result
- Teacher: upload question paper -> view student submissions -> adjust/correct predicted results -> publish results

Getting started (backend)
1) Create a virtualenv
   python3 -m venv backend/.venv
   source backend/.venv/bin/activate
2) Install deps
   pip install -r backend/requirements.txt
3) Run the API (development)
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend

Docker (optional)
- Copy .env.example to .env and adjust values
- docker compose -f infra/docker-compose.yml up --build

Flutter frontend
- If Flutter is installed, the frontend app will reside in frontend/. If it hasn’t been generated yet, see frontend/README.md for instructions.

Repo layout
- backend/    FastAPI app and worker code
- frontend/   Flutter app
- infra/      Docker Compose and infra configs
- docs/       Architecture and design docs

License
- MIT (add your preferred license)
