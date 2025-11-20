Environment Variables Cheat Sheet
=================================

Global (shared across services in dev)
- `SECRET_KEY` — JWT HS256 secret shared between services (dev only; rotate per env in prod).

Auth Service (services/auth_service)
- `DATABASE_URL` — Postgres DSN, e.g. `postgresql+asyncpg://postgres:postgres@auth-db:5432/authdb`
- `SECRET_KEY` — JWT signing/verification key.
- `ADMIN_EMAIL` — optional; seed admin on startup.
- `ADMIN_PASSWORD` — optional; seed admin password.

Catalog Service (services/catalog_service)
- `DATABASE_URL` — Postgres DSN, e.g. `postgresql+asyncpg://postgres:postgres@catalog-db:5432/catalog`
- `SECRET_KEY` — used to verify JWTs issued by auth-service for admin operations.

Gateway (services/gateway)
- `AUTH_URL` — base URL to auth-service (inside Docker network), default `http://auth:8000`.
- `CATALOG_URL` — base URL to catalog-service (inside Docker network), default `http://catalog:8000`.
- `SECRET_KEY` — same value as backends to decode cookie JWT and check role (optional but recommended for role checks in UI layer).

Future Services (planned)
- cart-service
  - `REDIS_URL` — e.g. `redis://cart-redis:6379/0`
  - `SECRET_KEY` — for JWT verify.
- order-service
  - `DATABASE_URL` — Postgres DSN for orders DB.
  - `SECRET_KEY` — for JWT verify.
  - `CATALOG_URL`, `CART_URL`, `PAYMENT_URL` — internal service URLs.
- payment-service
  - `SECRET_KEY` — internal auth or service token.
  - `ORDER_URL` — callback to order-service.

Notes
- Do not reuse dev `SECRET_KEY` in staging/production.
- In Kubernetes, move secrets to `Secret` objects; mount via env or files.
- For Alembic, migrations use sync drivers; URLs are normalized by `alembic/env.py`.

