Cart Service
============

FastAPI + Redis: хранение корзины пользователя в Hash (`cart:{sub}`).

Переменные окружения
- `REDIS_URL` — напр. `redis://cart-redis:6379/0`
- `SECRET_KEY` — общий секрет валидации JWT (берём `sub` как идентификатор пользователя)

Доступ
- Запуск через корень: `docker compose up -d` (контейнер `cart`).
- Swagger: `http://cart:8000/docs` внутри сети.

Эндпоинты
- GET `/cart` → `{product_id: qty}`
- POST `/cart/add` → тело `{product_id, qty}`
- POST `/cart/remove` → тело `{product_id}`
- POST `/cart/set` → тело `{product_id, qty}` (0 или меньше — удаление позиции)
- POST `/cart/clear` → очистить корзину

Примеры (нужен Bearer JWT)

```bash
# Получаем пользовательский токен
USER_TOKEN=$(docker compose exec gateway sh -lc "curl -s \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin@example.com&password=admin123' \
  http://auth:8000/auth/login | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'")

# Добавить товар в корзину
docker compose exec gateway curl -s \
  -H "Authorization: Bearer $USER_TOKEN" -H 'Content-Type: application/json' \
  -d '{"product_id":"<uuid>","qty":2}' \
  http://cart:8000/cart/add

# Прочитать корзину
docker compose exec gateway curl -s -H "Authorization: Bearer $USER_TOKEN" http://cart:8000/cart
```
