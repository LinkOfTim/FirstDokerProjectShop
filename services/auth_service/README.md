Auth Service
============

Сервис FastAPI: регистрация, логин, выдача JWT (HS256), роли user/admin.

Переменные окружения
- `DATABASE_URL` — `postgresql+asyncpg://...`
- `SECRET_KEY` — общий секрет для подписи JWT
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` — опциональный сид админа при старте

Запуск
- Через корневой `docker compose up -d` (контейнер `auth`).
- Swagger доступен внутри docker-сети: `http://auth:8000/docs`.
  - С хоста удобно обращаться так: `docker compose exec gateway curl http://auth:8000/health`.

Эндпоинты и примеры
- POST `/auth/register` → создаёт пользователя (роль=user)

```bash
docker compose exec gateway curl -s \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com","password":"secret"}' \
  http://auth:8000/auth/register
```

- POST `/auth/login` → OAuth2 form; возвращает `{access_token}` и ставит cookie `access_token`

```bash
docker compose exec gateway sh -lc "curl -s -i \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin@example.com&password=admin123' \
  http://auth:8000/auth/login"
```

- POST `/auth/logout` → удаляет cookie
- POST `/auth/change_password` → смена пароля для текущего пользователя

Формат JWT
- `sub` — email пользователя
- `role` — `user` или `admin`
- Алгоритм: HS256, секрет берётся из `SECRET_KEY`
