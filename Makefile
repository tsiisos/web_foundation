# Recipe lines start with "> " instead of a tab (avoids copy/paste tab problems)
.RECIPEPREFIX := >

COMPOSE_DEV = HOST_UID=$$(id -u) HOST_GID=$$(id -g) docker compose --env-file backend/.env -f docker/compose.dev.yml

.PHONY: up dev down logs ps migrate makemigrations superuser shell test psql

up:
> $(COMPOSE_DEV) up -d --build

dev:
> $(COMPOSE_DEV) up --build

down:
> $(COMPOSE_DEV) down

logs:
> $(COMPOSE_DEV) logs -f

ps:
> $(COMPOSE_DEV) ps

migrate:
> $(COMPOSE_DEV) exec backend python manage.py migrate

makemigrations:
> $(COMPOSE_DEV) exec backend python manage.py makemigrations

superuser:
> $(COMPOSE_DEV) exec backend python manage.py createsuperuser

shell:
> $(COMPOSE_DEV) exec backend python manage.py shell

test:
> $(COMPOSE_DEV) exec backend python manage.py test

psql:
> $(COMPOSE_DEV) exec db sh -c 'psql -U $$POSTGRES_USER -d $$POSTGRES_DB'

.PHONY: fe-add fe-lint

# Usage: make fe-add PKG=zod
fe-add:
> docker run --rm -u $$(id -u):$$(id -g) -e HOME=/tmp -v $(CURDIR)/frontend:/work -w /work node:22-slim sh -c "npm install -g pnpm@10 --prefix /tmp/npm >/dev/null && /tmp/npm/bin/pnpm add $(PKG)"
> rm -rf frontend/node_modules
> $(COMPOSE_DEV) up -d --build frontend

fe-lint:
> $(COMPOSE_DEV) exec frontend pnpm lint

COMPOSE_PROD = docker compose --env-file .env.prod -f docker/compose.prod.yml

.PHONY: prod-up prod-down prod-logs prod-ps prod-superuser prod-psql

prod-up:
> $(COMPOSE_PROD) up -d --build

prod-down:
> $(COMPOSE_PROD) down

prod-logs:
> $(COMPOSE_PROD) logs -f

prod-ps:
> $(COMPOSE_PROD) ps

prod-superuser:
> $(COMPOSE_PROD) exec backend python manage.py createsuperuser

prod-psql:
> $(COMPOSE_PROD) exec db sh -c 'psql -U $$POSTGRES_USER -d $$POSTGRES_DB'
