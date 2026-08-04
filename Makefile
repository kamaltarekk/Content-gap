.PHONY: up down test-deps backend-test frontend-test frontend-build lint migrate demo help

help:
	@echo "up            - start full local stack (docker compose)"
	@echo "down          - stop the stack"
	@echo "test-deps     - start test Postgres/Redis only"
	@echo "backend-test  - run backend tests (uv + pytest)"
	@echo "frontend-test - run frontend tests (vitest)"
	@echo "frontend-build- production build (vite)"
	@echo "migrate       - run alembic upgrade head"

up:
	docker compose -f infra/docker-compose.yml up --build

down:
	docker compose -f infra/docker-compose.yml down

test-deps:
	docker compose -f infra/docker-compose.test.yml up -d

backend-test:
	cd backend && uv run pytest -q

frontend-test:
	cd frontend && pnpm test

frontend-build:
	cd frontend && pnpm build

lint:
	cd backend && uv run ruff check .

migrate:
	cd backend && uv run alembic upgrade head
