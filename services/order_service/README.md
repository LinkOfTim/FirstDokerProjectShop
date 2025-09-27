Order Service
=============

Сервис FastAPI: оформление заказов, хранение заказов в Postgres, интеграция с Cart и Catalog.

Переменные окружения
- `DATABASE_URL` — `postgresql+asyncpg://...`
- `SECRET_KEY` — общий секрет (JWT)
- `CATALOG_URL`, `CART_URL` — адреса зависимостей

Доступ
- Запускается через корневой compose (контейнер `order`). Swagger: `http://order:8000/docs` внутри сети.

Эндпоинты
- GET `/orders` — заказы текущего пользователя (Bearer JWT)
- GET `/orders/{id}` — один заказ пользователя
- POST `/orders/checkout` — оформить заказ: читает корзину, валидирует товары, уменьшает stock в каталоге, сохраняет заказ, очищает корзину
- GET `/admin/orders` — список заказов (admin), фильтры: `status`, `email`
- PATCH `/orders/{id}/cancel` — отменить заказ (admin)

Пример сценария (curl из контейнера gateway)

```bash
# 1) Получить user токен
USER_TOKEN=$(docker compose exec gateway sh -lc "curl -s \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=user@example.com&password=secret' \
  http://auth:8000/auth/login | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'")

# 2) Добавить в корзину позицию
docker compose exec gateway curl -s \
  -H "Authorization: Bearer $USER_TOKEN" -H 'Content-Type: application/json' \
  -d '{"product_id":"<uuid>","qty":1}' \
  http://cart:8000/cart/add

# 3) Оформить заказ
docker compose exec gateway curl -s \
  -H "Authorization: Bearer $USER_TOKEN" \
  http://order:8000/orders/checkout

# 4) Посмотреть список заказов пользователя
docker compose exec gateway curl -s \
  -H "Authorization: Bearer $USER_TOKEN" \
  http://order:8000/orders
```
