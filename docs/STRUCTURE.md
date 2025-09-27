Repository Structure and File Roles
==================================

This document explains what each file/folder in the project does, how services relate to each other, and how requests/data flow through the system.

Top-level
- `docker-compose.yml`
  - Orchestrates local environment: runs `auth`, `catalog`, `gateway`, and their Postgres DBs.
  - Defines service DNS names used for inter-service HTTP calls: `auth`, `catalog`.
  - Sets env vars (e.g., `SECRET_KEY`, admin seed for auth).
- `services/`
  - Contains each microservice as an installable Python package with its own Dockerfile.
- `docs/`
  - Architecture and structure documentation.
- `DB_architecture.docx`, `TZ_microservices.docx`
  - Source documents with initial requirements and DB ideas.
- `.gitignore`, `.python-version`
  - VCS and local Python version hints.

Common Service Layout
- `pyproject.toml`
  - Python package metadata; declares dependencies used by the service.
- `Dockerfile`
  - Container build for the service. Uses Python 3.12-slim and installs deps via `uv`.
- `app/`
  - `main.py` — FastAPI application entry: mounts routers, configures handlers, (auth: seeds admin).
  - `config.py` — Pydantic Settings for env-configured variables (e.g., `DATABASE_URL`, `SECRET_KEY`).
  - `db.py` — async SQLAlchemy engine/session; health check.
  - `models.py` — SQLAlchemy models for this service (e.g., `User` in auth, `Product` in catalog).
  - `schemas.py` — Pydantic models (request/response DTOs).
  - `errors.py` — central exception handlers and basic logging setup.
  - `routers/` — FastAPI routers grouped by domain (e.g., `auth.py`, `products.py`).
  - (catalog) `authz.py` — JWT-based admin authorization (decoding/role check).
- `alembic/`
  - `env.py` — Alembic environment; reads `DATABASE_URL`, switches to sync driver for migrations.
  - `versions/` — migration scripts for DB schema (e.g., `0001_*`).
- `scripts/wait_for_db.py`
  - Small helper to wait for Postgres to be reachable before running migrations.
- `docker-entrypoint.sh`
  - Entry script: waits for DB, runs `alembic upgrade head`, then starts `uvicorn`.

Service: auth_service
- Path: `services/auth_service/`
- Purpose: user registration/login, JWT issuance, admin seeding.
- Key files
  - `app/models.py` — `User` table (email unique, password_hash, role, is_active, created_at).
  - `app/routers/auth.py` — endpoints: `/auth/register`, `/auth/login`, `/auth/logout`.
  - `app/auth.py` — password hashing (passlib), JWT creation/verification helpers, DB access for users.
  - `alembic/versions/0001_users.py` — creates `users` table and index.
  - `pyproject.toml` — includes `email-validator`, `python-multipart` for form logins.
  - `Dockerfile`, `docker-entrypoint.sh`, `scripts/wait_for_db.py` — container runtime setup.
- Env Vars
  - `DATABASE_URL` — Postgres DSN for users DB.
  - `SECRET_KEY` — shared JWT secret (HS256) across services.
  - `ADMIN_EMAIL`, `ADMIN_PASSWORD` — optional admin seed on startup.

Service: catalog_service
- Path: `services/catalog_service/`
- Purpose: product catalog with admin-restricted writes.
- Key files
  - `app/models.py` — `Product`, `Category`, `ProductImage`, `product_categories` (M2M) tables.
  - `app/routers/products.py` — endpoints: `GET /products`, `GET /products/{id}`, `POST/PATCH/DELETE` (admin only).
  - `app/authz.py` — decodes JWT and enforces `role == 'admin'` for write operations.
  - `alembic/versions/0001_initial.py` — schema for products and related tables; indexes (`sku`, `is_active`).
  - `Dockerfile`, `docker-entrypoint.sh`, `scripts/wait_for_db.py` — container runtime setup.
- Env Vars
  - `DATABASE_URL` — Postgres DSN for catalog DB.
  - `SECRET_KEY` — used to verify JWTs from auth-service.

Service: gateway
- Path: `services/gateway/`
- Purpose: web UI and proxy to auth/catalog APIs.
- Key files
  - `app/main.py`
    - Mounts static and templates.
    - Pages: `/` (catalog list), `/login` (form), `/admin` (admin panel w/ token check).
    - Proxy REST: `/api/products[...]` → forwards to catalog with `Authorization` header from cookie JWT.
    - Resilience: catches backend connection errors and returns 503 (or shows empty list).
  - `templates/` — Jinja2 templates: `base.html` (Bootstrap layout), `index.html`, `login.html`, `admin.html`.
  - `static/` — optional CSS.
  - `pyproject.toml` — includes `httpx`, `python-multipart`, `Jinja2`.
- Env Vars
  - `AUTH_URL`, `CATALOG_URL` — internal service URLs on Docker network (default `http://auth:8000`, `http://catalog:8000`).
  - `SECRET_KEY` — needed to decode cookie JWT and check admin role.

docker-compose Services
- `auth-db` — Postgres for auth_service (`authdb`).
- `catalog-db` — Postgres for catalog_service (`catalog`).
- `auth` — builds `services/auth_service`, waits for DB, runs migrations, seeds admin, serves FastAPI on `:8000`.
- `catalog` — builds `services/catalog_service`, waits for DB, runs migrations, serves FastAPI on `:8000`.
- `gateway` — builds `services/gateway`, serves UI on host `:8000`.

Relationships & Request Flows
1) Login
   - Browser → gateway `/login` (form) → gateway forwards to `auth /auth/login`.
   - Auth issues JWT (HS256) and gateway sets `access_token` cookie.
2) Admin-only product creation
   - Browser (admin) → gateway `/api/products` (POST) with cookie.
   - Gateway reads cookie, forwards to `catalog /products` with `Authorization: Bearer <JWT>`.
   - Catalog verifies JWT via `SECRET_KEY` and role claim; creates product.
3) Home page
   - Browser → gateway `/`.
   - Gateway GETs `catalog /products`; renders `index.html` with the list. If catalog is down, shows empty list.

Startup Sequence
- Each backend container runs `docker-entrypoint.sh`:
  1) `scripts/wait_for_db.py` waits for Postgres TCP.
  2) `alembic upgrade head` applies DB migrations.
  3) `uvicorn app.main:app` starts the service.
- Auth additionally seeds the admin user when `ADMIN_EMAIL` and `ADMIN_PASSWORD` are provided.

Error Handling
- Auth/Catalog
  - Integrity errors (e.g., duplicate email/SKU) → HTTP 409.
  - Unexpected errors → HTTP 500 with logged traceback.
- Gateway
  - Backend connect failures → HTTP 503 on proxy endpoints, no crash on UI pages.

Extending the System
- Add a new service (pattern):
  1) Create `services/<name>/{app,pyproject.toml,Dockerfile,alembic,...}` mirroring existing services.
  2) Define models, routers, and migrations.
  3) Add service to `docker-compose.yml` (plus DB/Redis if needed).
  4) Wire gateway routes/pages as needed.
- Planned services:
  - cart-service (Redis): `/cart/add`, `/cart/remove`, `/cart`.
  - order-service (Postgres): `/order/create`, `/order/{id}`; integrates with cart and catalog.
  - payment-service: `/payment/pay` emulated; callback to order-service.

Conventions
- Python: FastAPI, async SQLAlchemy, Alembic; code style PEP8.
- Env config via Pydantic Settings; secrets via env vars (for dev; use secrets manager in prod).
- JWT: HS256 shared secret in dev; rotate/change per environment.
- DB: all PK UUID; monetary fields NUMERIC(12,2); timestamps stored as UTC.

