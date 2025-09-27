E-commerce Monorepo (Auth, Catalog, Cart, Order, Gateway)
=========================================================

Описание
--------
Монорепозиторий с микросервисами для e-commerce прототипа:
- services/auth_service — аутентификация/регистрация, JWT (PostgreSQL)
- services/catalog_service — каталог товаров (CRUD, PostgreSQL)
- services/cart_service — корзина (Redis)
- services/order_service — оформление заказов (PostgreSQL)
- services/gateway — веб‑интерфейс (FastAPI + Jinja2) и API‑прокси

Требования
----------
- Docker 24+ и Docker Compose v2
- Порт `8000` свободен на хосте (для gateway)

Быстрый старт (Docker Compose)
------------------------------
1) Собрать и запустить:

```bash
docker compose up -d --build
```

2) Проверить статус контейнеров и логи (опционально):

```bash
docker compose ps
docker compose logs -f gateway
```

3) Открыть интерфейс:
- Gateway/UI: http://localhost:8000/
- Страница логина: http://localhost:8000/login
- Админка: http://localhost:8000/admin

По умолчанию при старте сидируется админ‑пользователь:
- email: `admin@example.com`
- пароль: `admin123`

Миграции БД применяются автоматически при старте сервисов (Alembic в `auth_service`, `catalog_service`, `order_service`). Данные сохраняются в Docker volume’ах.

Остановка и сброс
-----------------
- Остановить сервисы: `docker compose down`
- Пересобрать/перезапустить: `docker compose up -d --build`
- Полный сброс данных (удалить volumes с БД/Redis):

```bash
docker compose down -v
```

Переменные окружения (используются в compose)
--------------------------------------------
- gateway:
  - `AUTH_URL` (по умолчанию `http://auth:8000`)
  - `CATALOG_URL` (`http://catalog:8000`)
  - `CART_URL` (`http://cart:8000`)
  - `ORDER_URL` (`http://order:8000`)
  - `SECRET_KEY`
- auth_service:
  - `DATABASE_URL` (PostgreSQL)
  - `SECRET_KEY`
  - `ADMIN_EMAIL`, `ADMIN_PASSWORD` — сид админа на старте
- catalog_service:
  - `DATABASE_URL` (PostgreSQL)
  - `SECRET_KEY`
- cart_service:
  - `REDIS_URL`
  - `SECRET_KEY`
- order_service:
  - `DATABASE_URL` (PostgreSQL)
  - `SECRET_KEY`
  - `CATALOG_URL`, `CART_URL`

Полезные эндпоинты
------------------
- Gateway UI: `GET /` (список товаров), `GET /login`, `GET /admin`
- Health‑чеки: `GET /health` у каждого сервиса
- Swagger для внутренних сервисов доступен внутри docker‑сети:
  - auth: `http://auth:8000/docs`
  - catalog: `http://catalog:8000/docs`
  - cart: `http://cart:8000/docs`
  - order: `http://order:8000/docs`

Структура
---------
- `services/*` — исходный код сервисов
- `docker-compose.yml` — локальный запуск всего проекта
- `docs/*` — архитектура, описание окружения и API

Дополнительно
--------------
- Секреты и нестандартные параметры удобно переопределять через `docker-compose.override.yml` (не коммитить в репозиторий).
- Для полного описания архитектуры см. `docs/ARCHITECTURE.md`, окружение — `docs/ENVIRONMENT.md`, API — `docs/API.md`.
