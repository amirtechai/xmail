.PHONY: dev prod deploy logs ps down migrate test lint

COMPOSE_DEV  = docker compose -f docker-compose.yml
COMPOSE_PROD = docker compose -f docker-compose.yml -f docker-compose.prod.yml

# ── Development ───────────────────────────────────────────────────────────────
dev:
	$(COMPOSE_DEV) up --build

dev-down:
	$(COMPOSE_DEV) down

# ── Production ────────────────────────────────────────────────────────────────
deploy:
	@set -a && . .env.prod && set +a && ./scripts/deploy.sh

prod-logs:
	$(COMPOSE_PROD) logs -f --tail=100

prod-ps:
	$(COMPOSE_PROD) ps

prod-down:
	$(COMPOSE_PROD) down

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	$(COMPOSE_DEV) run --rm --no-deps backend alembic upgrade head

migrate-prod:
	$(COMPOSE_PROD) run --rm --no-deps backend alembic upgrade head

# ── Tests ─────────────────────────────────────────────────────────────────────
test-backend:
	cd backend && python -m pytest tests/ -v --tb=short

test-frontend:
	cd frontend && npm test

test-e2e:
	cd frontend && npx playwright test

test: test-backend test-frontend

# ── Code quality ──────────────────────────────────────────────────────────────
lint:
	cd backend && python -m ruff check app/ && python -m ruff format --check app/
	cd frontend && npm run lint

# ── Secrets helper ───────────────────────────────────────────────────────────
gen-secrets:
	@echo "SECRET_KEY=$(shell openssl rand -hex 32)"
	@echo "DB_PASSWORD=$(shell openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)"
	@echo "REDIS_PASSWORD=$(shell openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)"
	@echo "ENCRYPTION_KEY=$(shell python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
