Monorepo Overview
=================

This repository contains a microservices-based e-commerce prototype with separate services for authentication, catalog, and a web/UI gateway. It is designed for local development with Docker Compose and intended to expand with cart, order, and payment services.

Architecture Overview
- Services
  - auth-service: User registration/login, JWT issuance, roles (user/admin).
  - catalog-service: Product catalog (CRUD, admin-restricted writes).
  - gateway: Web UI (FastAPI + Jinja2 + Bootstrap) and API proxy to backend services.
- Data per service
  - auth-service: PostgreSQL (users).
  - catalog-service: PostgreSQL (products, categories, product_images, product_categories).
  - gateway: stateless.
- Communication
  - REST/JSON over HTTP between services.
  - Auth: JWT HS256 shared via `SECRET_KEY`. Services verify JWT locally, no cross-service DB calls.
- Deployment (local)
  - Docker Compose: one container per service + one Postgres per DB. Shared Docker network: services addressed by DNS names `auth`, `catalog`.

See also: docs/STRUCTURE.md for a file-by-file explanation of what each component does and how it connects.

Diagrams
--------

Service Topology

```mermaid
flowchart LR
  subgraph Auth_Service[auth-service]
    AAPI[FastAPI]
    ADB[(PostgreSQL users)]
    AAPI --- ADB
  end

  subgraph Catalog_Service[catalog-service]
    CAPI[FastAPI]
    CDB[(PostgreSQL catalog)]
    CAPI --- CDB
  end

  subgraph Gateway[gateway]
    GUI[FastAPI + Jinja2]
  end

  GUI -->|REST/JSON| AAPI
  GUI -->|REST/JSON| CAPI

  %% Shared JWT secret for dev
  AAPI <-. HS256 SECRET_KEY .-> CAPI

  %% Future services (planned)
  subgraph Planned[Planned]
    direction LR
    Cart[cart-service (Redis)]
    Order[order-service (Postgres)]
    Payment[payment-service]
  end

  GUI -.-> Cart
  GUI -.-> Order
  Order -.-> Payment
  Cart -.-> Order
  CAPI -. price/sku .-> Order
```

Sequence: Admin Login and Create Product

```mermaid
sequenceDiagram
  participant B as Browser
  participant G as Gateway
  participant AU as Auth Service
  participant CA as Catalog Service

  Note over B,G: Login
  B->>G: POST /auth/login (form)
  G->>AU: POST /auth/login (OAuth2 form)
  AU-->>G: 200 {access_token}
  G-->>B: Set-Cookie: access_token=JWT

  Note over B,G,CA: Create Product (admin)
  B->>G: POST /api/products {sku,name,price,...}
  G->>G: Read JWT from cookie
  G->>CA: POST /products (Authorization: Bearer JWT)
  CA->>CA: Verify HS256, role == admin
  CA-->>G: 201 {product}
  G-->>B: 201 {product}
```

Planned: Checkout and Payment Flow

```mermaid
sequenceDiagram
  participant U as User (Browser)
  participant G as Gateway
  participant CT as Cart Service
  participant OR as Order Service
  participant CA as Catalog Service
  participant PM as Payment Service

  Note over U,G: Add items to cart
  U->>G: POST /cart/add {product_id, qty}
  G->>CT: POST /cart/add (JWT: user)
  CT-->>G: 200 {cart}
  G-->>U: 200 {cart}

  Note over U,G,OR: Create order
  U->>G: POST /order/create
  G->>CT: GET /cart (JWT: user)
  CT-->>G: 200 {items}
  G->>CA: GET /products/{id} (for each item)
  CA-->>G: 200 {sku,price}
  G->>OR: POST /order/create {items, total} (JWT: user)
  OR-->>G: 201 {order_id, status: created}
  G-->>U: 201 {order_id}

  Note over U,G,PM,OR: Payment
  U->>G: POST /payment/pay {order_id}
  G->>PM: POST /payment/pay {order_id, amount}
  PM-->>OR: POST /order/{id}/status {paid}
  OR-->>PM: 200
  PM-->>G: 200 {status: paid}
  G-->>U: 200 {status: paid}
```

Services

Auth Service
- Purpose: user management and JWT tokens.
- Tech: FastAPI, SQLAlchemy (async), Alembic, PostgreSQL, python-jose, passlib.
- DB: `users(id UUID, email UNIQUE, password_hash, role, is_active, created_at)`.
- Endpoints
  - POST `/auth/register` → create user (role=user).
  - POST `/auth/login` → OAuth2 password form; returns `{access_token, token_type}` and sets `access_token` cookie (HttpOnly).
  - POST `/auth/logout` → clears cookie.
  - GET `/health` → service + DB health.
- Env
  - `DATABASE_URL`, `SECRET_KEY`, optional `ADMIN_EMAIL`, `ADMIN_PASSWORD` (seed admin on startup).

Catalog Service
- Purpose: product CRUD with admin authorization.
- Tech: FastAPI, SQLAlchemy (async), Alembic, PostgreSQL.
- DB
  - `products(id UUID, sku UNIQUE, name, price NUMERIC(12,2), stock, is_active, created_at, updated_at)`
  - `categories(id UUID, name, slug UNIQUE)`, `product_images`, `product_categories` (M2M)
- Endpoints
  - GET `/products`, GET `/products/{id}`
  - POST `/products` (admin), PATCH `/products/{id}` (admin), DELETE `/products/{id}` (admin)
  - GET `/health`
- Authz
  - Admin-only writes. Admin verified via JWT role claim.
- Env
  - `DATABASE_URL`, `SECRET_KEY`

Gateway
- Purpose: end-user web UI and proxy to backend APIs.
- Tech: FastAPI, Jinja2, Bootstrap (CDN), httpx.
- Pages
  - `/` catalog listing (public)
  - `/login` login form (forwards to auth service)
  - `/admin` admin panel (requires JWT admin; create product, toggle availability)
- Proxy API
  - `/api/products` → `GET` list
  - `/api/products/{id}` → `GET` by id
  - `/api/products` → `POST` create (admin JWT)
  - `/api/products/{id}` → `PATCH` update (admin JWT), `DELETE` (admin JWT)
- Resilience
  - If catalog is unavailable, root page shows empty list; API returns `503 {detail: catalog unavailable}` instead of 500.
- Env
  - `AUTH_URL` (default `http://auth:8000`), `CATALOG_URL` (default `http://catalog:8000`), `SECRET_KEY` (for optional JWT decode).

Local Development & Deployment
- Docker Compose (`docker-compose.yml`)
  - Services: `auth`, `auth-db` (Postgres), `catalog`, `catalog-db` (Postgres), `gateway`.
  - Ports: gateway exposed on host `8000` → `http://localhost:8000`.
  - Migrations: both `auth` and `catalog` run Alembic upgrade on startup after waiting for DB.
  - Admin seed: set in compose `ADMIN_EMAIL=admin@example.com`, `ADMIN_PASSWORD=admin123` (for auth-service).
- Images
  - Python 3.12-slim base, dependencies installed via `uv`.
- Health endpoints
  - `/health` on each backend; gateway: `/health` (simple ok).

Security Model
- JWT: HS256 with shared `SECRET_KEY` across services (for dev only; rotate/use secrets manager in prod).
- Roles: `user` (default), `admin` (required for catalog writes).
- Cookies: login sets `access_token` HttpOnly cookie; gateway also uses cookie for proxying admin calls.
- Next steps: service-to-service auth (internal token), CSRF for non-API forms (gateway), password policies, account lockout.

Error Handling & Observability
- Auth/Catalog: structured exception handlers for integrity errors (409) and generic 500.
- Gateway: graceful handling of backend unavailability (503 instead of 500), avoids crashing UI.
- Logs: basic logging configured; next steps: structured JSON logs, request IDs, correlation.

Testing (Current and TODO)
- Unit/API tests: skeleton present earlier; to be reintroduced per service.
- TODO: pytest suites per service, httpx-based API tests, contract tests for proxy endpoints, smoke tests in CI.

Roadmap & Improvements
- Cart Service (Redis)
  - Endpoints: POST `/cart/add {product_id, qty}`, POST `/cart/remove {product_id}`, GET `/cart`.
  - Storage: Redis hash per user (`cart:{user_id}`), price snapshot optional.
  - Gateway: add `/cart` page; show total; server-side aggregation.
- Order Service (PostgreSQL)
  - Endpoints: POST `/order/create` (reads cart, validates SKUs/prices via catalog), GET `/order/{id}`.
  - States: created → paid → processing → completed/cancelled.
  - Webhooks: accept payment callback to mark paid.
  - DB: `orders`, `order_items`, `order_events`.
- Payment Service
  - Endpoint: POST `/payment/pay {order_id, amount}` → emulate success/failure; callback to order-service.
  - Security: internal service token + allowlist.
- Gateway Enhancements
  - Pages: `/orders` (user orders), `/cart` (add/remove), admin views for orders.
  - Better UX, toasts, pagination/filtering.
- Catalog Enhancements
  - Filtering/pagination: by name, sku, active, price range.
  - Categories/images endpoints and UI.
- Cross-Cutting Concerns
  - CI/CD: GitHub Actions (lint, test, build, push images), Dev containers.
  - Kubernetes: k8s manifests (Deployment/Service/Ingress) per service; NGINX Ingress as API gateway; secrets via Kubernetes Secrets/External Secrets.
  - Config: .env per service in dev; 12-factor configs; centralized config planning for prod.
  - Observability: OpenTelemetry traces/metrics, Prometheus scraping, Grafana dashboards.
  - Resilience: retries with exponential backoff, circuit breaker (e.g., httpx + tenacity or resilience libraries).
  - Data: idempotency keys for payments/orders; outbox pattern for cross-service events if MQ introduced.
  - Security: rate limiting, CORS policies, secure cookies, session timeout, password reset flows.

Quick Start (Recap)
- `docker compose build --no-cache && docker compose up`
- UI: http://localhost:8000/
- Admin login: `admin@example.com` / `admin123`
- Swagger (inside Docker network): `http://auth:8000/docs`, `http://catalog:8000/docs`
