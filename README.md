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
- Git (для клонирования репозитория)
- Порт `8000` свободен на хосте (для gateway)

Предварительная установка
-------------------------
- Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER   # чтобы запускать docker без sudo
newgrp docker                    # применить группу в текущей сессии
docker --version && docker compose version && git --version
```

- macOS (Homebrew):

```bash
brew install --cask docker   # установит Docker Desktop
brew install git
# Запустите Docker.app один раз, чтобы поднять демон
docker --version && docker compose version && git --version
```

- Windows 10/11:
- Установите Docker Desktop (включите WSL2 backend), перезагрузите машину.
- Установите Git for Windows (доступен как Git Bash).
- Проверьте версии в PowerShell или Git Bash: `docker --version`, `docker compose version`, `git --version`.

- Проверка доступа к Docker (Linux):
  - Если команда `docker ps` без sudo выдаёт ошибку прав — перелогиньтесь или выполните `newgrp docker`.

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

Docker шпаргалка
-----------------
- Собрать все образы: `docker compose build` (параллельно: `--parallel`, чистая сборка: `--no-cache`).
- Собрать один сервис: `docker compose build gateway`.
- Локально собрать образ без compose: `docker build -t catalog-service:dev services/catalog_service`.
- Запустить/пересобрать один сервис: `docker compose up -d --build gateway`.
- Перезапустить: `docker compose restart gateway`.
- Логи сервиса: `docker compose logs -f --tail=100 gateway`.
- Список контейнеров: `docker compose ps` (или `docker ps`).
- Войти в контейнер: `docker compose exec gateway sh` (или `bash`, если есть).
- Остановить все: `docker compose down` (с удалением данных: `docker compose down -v`).
- Очистить dangling-образы: `docker image prune` (всё неисп.: `docker system prune -f`). Внимание: может удалить кэш и сети.
- Удалить локальные образы проекта: `docker compose down --rmi local`.

Пример override для hot‑reload (локальная разработка)
----------------------------------------------------
Создайте файл `docker-compose.override.yml` рядом с `docker-compose.yml`:

```yaml
services:
  gateway:
    volumes:
      - ./services/gateway/app:/app/app:rw
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

После этого запустите `docker compose up -d --build gateway`. Код из хоста будет монтироваться в контейнер, `--reload` перезапускает сервер при изменениях.

Архитектура и структура
------------------------
- Монолит? Нет — здесь монорепозиторий с несколькими сервисами. Коммуникация — HTTP/JSON. Авторизация между сервисами через общий `SECRET_KEY` (HS256 JWT).
- Инфраструктура локально — `docker-compose.yml`: БД Postgres для `auth`, `catalog`, `order`, Redis для `cart`, один UI‑gateway, общая сеть, именованные volume’ы для данных.

Корень репозитория
- `docker-compose.yml` — состав окружения: сервисы, env, порты, зависимости, volume’ы.
- `docs/` — архитектура, окружение, API, структура.
- `services/` — весь продуктовый код микросервисов.
- `.python-version` — версия Python для локальной разработки (pyenv/asdf).
- `.gitignore` — игнор для артефактов сборки, окружений, IDE и т.д.

Сервисы (общие паттерны внутри `services/*/app`)
- `app/main.py` — точка входа FastAPI; создание `app`, маршруты, хелсчек, регистрация роутеров и обработчиков ошибок.
- `app/config.py` — настройки через `pydantic-settings`: чтение переменных окружения (URL БД/Redis, секрет, базовые URLs).
- `app/db.py` — инициализация подключения (Async SQLAlchemy/Redis), сессии, `health_check`.
- `app/models.py` — ORM‑модели (SQLAlchemy) и связи.
- `app/schemas.py` — Pydantic‑схемы запросов/ответов.
- `app/errors.py` — централизованные обработчики исключений, логирование.
- `app/auth.py`/`app/authz.py` — JWT‑утилиты, роли, проверка прав.
- `app/routers/*` — декларативные роуты FastAPI для групп эндпоинтов.

Миграции БД
- `alembic.ini`, `alembic/` — конфигурация Alembic; `alembic/versions/` содержит миграции (история схемы).
- Скрипты ожидания БД: `scripts/wait_for_db.py` (у `auth`, `catalog`, `order`).

Контейнеризация (каждый сервис)
- `Dockerfile` — базовый образ `python:3.12-slim`, установка зависимостей через `uv`, копирование кода, `EXPOSE 8000`.
- `pyproject.toml` — метаданные проекта и список зависимостей для установки в образ.
- `docker-entrypoint.sh` — порядок запуска: ожидание БД → `alembic upgrade head` → `uvicorn`.

Специфика отдельных сервисов
- gateway
  - `templates/` — Jinja2‑шаблоны (`index.html`, `login.html`, `admin*.html` и др.).
  - `static/` — статические файлы (CSS/JS/изображения).
  - Читает `AUTH_URL`, `CATALOG_URL`, `CART_URL`, `ORDER_URL`; проксирует запросы и рендерит UI.
- auth_service
  - Таблица пользователей, сид админа через `ADMIN_EMAIL`/`ADMIN_PASSWORD` на старте.
  - Эндпоинты `/auth/register`, `/auth/login` (OAuth2 form), `/health`.
- catalog_service
  - CRUD товаров, админ‑права на изменение, `is_active`, склад `stock`.
- cart_service
  - Redis‑хранилище корзины по пользователю (`cart:{sub}`), операции add/remove/list.
- order_service
  - Оркестрация оформления заказа: чтение корзины, проверка каталога, резерв/списание stock (через админ‑токен), запись заказа.

Где менять что
- Добавить поле к пользователю/товару/заказу: модель в `app/models.py` → миграция в `alembic/versions/` → схемы в `app/schemas.py` → обработка в роутерах/сервисах.
- Новые эндпоинты: создайте/расширьте роутер в `app/routers/*` и подключите его в `app/main.py`.
- Новые переменные окружения: объявите в `app/config.py` и прокиньте через `docker-compose.yml`.
- UI правки: правьте Jinja2 в `services/gateway/templates` и стили в `services/gateway/static`.
- Политики доступа: правьте `app/auth.py`/`authz.py` и проверки ролей в обработчиках.

Диагностика и здоровье
- Health‑эндпоинты `GET /health` у всех сервисов проверяют доступность зависимостей (БД/Redis).
- Общие логи и обработка ошибок — через `app/errors.py`; логи смотрите `docker compose logs -f <service>`.

Структура по сервисам (мини‑деревья)
------------------------------------

Auth Service (`services/auth_service`)
```text
auth_service/
├─ Dockerfile                  # Образ сервиса (uv, uvicorn, deps)
├─ pyproject.toml              # Зависимости и метаданные пакета
├─ README.md                   # Локальные заметки сервиса
├─ alembic.ini                 # Конфиг Alembic
├─ alembic/                    # Миграции БД (versions/*)
├─ scripts/
│  └─ wait_for_db.py          # Ожидание готовности Postgres
├─ docker-entrypoint.sh        # Старт: wait → alembic upgrade → uvicorn
└─ app/
   ├─ main.py                 # FastAPI app, роутеры, /health
   ├─ config.py               # Pydantic Settings (DATABASE_URL, SECRET_KEY, ...)
   ├─ db.py                   # AsyncSession, engine, health_check
   ├─ models.py               # SQLAlchemy модели (User и др.)
   ├─ schemas.py              # Pydantic схемы запросов/ответов
   ├─ auth.py                 # Хеширование паролей, JWT утилиты
   ├─ errors.py               # Логирование и обработчики исключений
   └─ routers/
      └─ auth.py             # /auth/register, /auth/login, пр.
```

Catalog Service (`services/catalog_service`)
```text
catalog_service/
├─ Dockerfile
├─ pyproject.toml
├─ README.md
├─ alembic.ini
├─ alembic/
├─ scripts/
│  └─ wait_for_db.py
├─ docker-entrypoint.sh
└─ app/
   ├─ main.py                 # Подключение роутеров каталога
   ├─ config.py
   ├─ db.py
   ├─ models.py               # Product, Category и связи
   ├─ schemas.py
   ├─ errors.py
   ├─ authz.py                # Проверки ролей/прав для изменения каталога
   └─ routers/
      └─ products.py         # CRUD эндпоинты каталога
```

Cart Service (`services/cart_service`)
```text
cart_service/
├─ Dockerfile
├─ pyproject.toml
└─ app/
   ├─ main.py                 # Эндпоинты корзины (Redis), OAuth2 токен
   └─ config.py               # REDIS_URL, SECRET_KEY
```

Order Service (`services/order_service`)
```text
order_service/
├─ Dockerfile
├─ pyproject.toml
├─ alembic.ini
├─ alembic/
├─ docker-entrypoint.sh
└─ app/
   ├─ main.py                 # Checkout: читает Cart, валидирует Catalog, пишет Order
   ├─ config.py               # DATABASE_URL, CATALOG_URL, CART_URL, SECRET_KEY
   ├─ db.py                   # AsyncSession/engine, health_check
   ├─ models.py               # Order, OrderItem
   ├─ schemas.py              # Pydantic DTO
   └─ scripts/
      └─ wait_for_db.py
```

Gateway (`services/gateway`)
```text
gateway/
├─ Dockerfile
├─ pyproject.toml
├─ README.md
├─ app/
│  ├─ main.py                 # FastAPI, прокси к сервисам, cookie JWT
│  └─ config.py               # AUTH_URL, CATALOG_URL, CART_URL, ORDER_URL, SECRET_KEY
├─ templates/                 # Jinja2 шаблоны (index, login, admin, orders, ...)
└─ static/                    # CSS/JS/изображения
```

Подсказки по модификации
- Новая таблица/поле: `models.py` → миграция в `alembic/versions` → обновить `schemas.py` → поправить обработчики в `routers/*`/`main.py`.
- Новой сервисный клиент/интеграция: добавить конфиг в `config.py`, использовать `httpx` в `main.py`/роутерах, прокинуть env через `docker-compose.yml`.
- Политики доступа: обновить `auth.py`/`authz.py` и места проверки ролей в обработчиках.
