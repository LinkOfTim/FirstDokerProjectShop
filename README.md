Monorepo: Microservices (Auth, Catalog, Gateway)
===============================================

Services
- services/auth_service — регистрация/логин, JWT (PostgreSQL)
- services/catalog_service — каталог товаров (CRUD, PostgreSQL)
- services/gateway — веб‑интерфейс (FastAPI + Jinja2) и API‑прокси

Quickstart (Docker)
- docker compose build --no-cache
- docker compose up
- Gateway/UI: http://localhost:8000/
  - Login: http://localhost:8000/login (admin@example.com / admin123)
  - Admin: http://localhost:8000/admin
  - Swagger (per service): available inside docker network (auth: http://auth:8000/docs, catalog: http://catalog:8000/docs)

Env defaults (docker-compose)
- Shared SECRET_KEY: dev-secret-change-me
- Admin seed (auth): ADMIN_EMAIL=admin@example.com, ADMIN_PASSWORD=admin123

Next steps
- Добавить cart-service (Redis) и order/payment services
- Вынести API Gateway на NGINX/Ingress (для k8s)

More details: see docs/ARCHITECTURE.md
Diagrams: see docs/ARCHITECTURE.md (Mermaid)
Env cheat sheet: docs/ENVIRONMENT.md
API spec (draft): docs/API.md
