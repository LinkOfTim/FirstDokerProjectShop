Auth Service
============

FastAPI service for registration/login and JWT issuing.

Env
- `DATABASE_URL` (postgresql+asyncpg)
- `SECRET_KEY` (shared across services)
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` (optional seed)

Run (Docker)
- Built and run via root docker-compose.

