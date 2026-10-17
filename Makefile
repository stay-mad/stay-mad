VENV = .venv
PYTHON = $(VENV)/bin/python
PYTEST = $(VENV)/bin/pytest
RUFF = $(VENV)/bin/ruff
NODE_PATH = /Users/susi/.nvm/versions/node/v24.14.0/bin:/opt/homebrew/bin:$(PATH)

.PHONY: test lint eval eval-baseline demo seed-demo run-api run-frontend build-frontend up down docker-build smoke-test help venv

help:
	@echo "Available commands:"
	@echo "  make up             - Start services via docker-compose"
	@echo "  make down           - Stop services via docker-compose"
	@echo "  make docker-build   - Build Docker container images (backend & frontend)"
	@echo "  make smoke-test     - Run automated smoke test suite (API_URL=...)"
	@echo "  make test           - Run unit, contract, and e2e tests"
	@echo "  make lint           - Run code linter and formatting checks"
	@echo "  make eval           - Run model and pipeline evaluation against eval/gold"
	@echo "  make eval-baseline  - Run baseline evaluation checks against demo fixtures (23 articles)"
	@echo "  make demo           - Run end-to-end demo using eval/fixtures"
	@echo "  make seed-demo      - Seed local SQLite dev database (backend/staymad_dev.db)"
	@echo "  make run-api        - Launch FastAPI dev server on port 8080"
	@echo "  make run-frontend   - Launch Next.js dev server on port 3000"
	@echo "  make build-frontend - Build and validate Next.js frontend"

venv:
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV) && \
		$(VENV)/bin/pip install pytest ruff pyyaml pydantic sqlalchemy alembic pgvector fastapi uvicorn httpx; \
	fi

up:
	docker compose up -d

down:
	docker compose down

docker-build:
	@echo "==> Building Backend Docker image..."
	docker build -t staymad-backend:latest -f deploy/Dockerfile .
	@echo "==> Building Frontend Docker image..."
	docker build -t staymad-frontend:latest -f frontend/Dockerfile frontend/

smoke-test:
	bash deploy/smoke_test.sh

test:
	$(PYTEST) backend/tests

lint:
	$(RUFF) check backend
	$(RUFF) format --check backend

eval-baseline:
	$(PYTHON) -m backend.staymad.jobs.eval_runner --baseline --fixtures eval/fixtures/seed_demo_23.json

eval:
	$(PYTHON) -m backend.staymad.jobs.eval_runner --gold eval/gold --split test --ablation tier3 --output eval/reports

demo:
	$(PYTHON) -m backend.staymad.jobs.demo_pipeline --fixtures eval/fixtures/seed_demo_23.json

SOURCE ?= antara
LIMIT ?= 3

live-ingest:
	DATA_MODE=live DATABASE_URL="postgresql://staymad:staymad_secret@localhost:5432/staymad_db" $(PYTHON) -m backend.staymad.jobs.live_ingest --source $(SOURCE) --limit $(LIMIT)

live-ingest-all:
	DATA_MODE=live DATABASE_URL="postgresql://staymad:staymad_secret@localhost:5432/staymad_db" $(PYTHON) -m backend.staymad.jobs.live_ingest --source all --limit 4

seed-demo:
	$(PYTHON) -m backend.staymad.jobs.demo_pipeline --fixtures eval/fixtures/seed_demo_23.json --db-url sqlite:///backend/staymad_dev.db

run-api:
	DATABASE_URL="sqlite:///backend/staymad_dev.db" $(PYTHON) -m backend.staymad.api.main

run-frontend:
	export PATH="$(NODE_PATH)"; cd frontend && npm run dev -- -p 3000

build-frontend:
	export PATH="$(NODE_PATH)"; cd frontend && npm run build
