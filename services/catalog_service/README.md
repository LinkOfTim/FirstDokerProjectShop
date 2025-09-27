Catalog Service
===============

Сервис FastAPI: каталог товаров (CRUD), поиск/фильтры. Изменения доступны только админу (JWT).

Переменные окружения
- `DATABASE_URL` — `postgresql+asyncpg://...`
- `SECRET_KEY` — общий секрет для валидации JWT

Запуск и доступ
- Запускается через корневой `docker compose up -d` (контейнер `catalog`).
- Swagger доступен внутри сети: `http://catalog:8000/docs`.
- Пример вызовов с хоста: `docker compose exec gateway curl http://catalog:8000/health`.

Эндпоинты
- GET `/products/` — список товаров
  - Параметры: `q`, `min_price`, `max_price`, `is_active`
- GET `/products/{id}` — карточка товара
- POST `/products/` — создать товар (только admin, Bearer JWT)
- PATCH `/products/{id}` — изменить (admin)
- DELETE `/products/{id}` — удалить (admin)

Примеры
- Поиск и фильтр:

```bash
docker compose exec gateway curl -s \
  'http://catalog:8000/products/?q=phone&min_price=1000&is_active=true'
```

- Создание товара (admin JWT):

```bash
# Получить admin токен напрямую у auth-сервиса
TOKEN=$(docker compose exec gateway sh -lc "curl -s \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin@example.com&password=admin123' \
  http://auth:8000/auth/login | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'")

docker compose exec gateway curl -s \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"sku":"SKU-1","name":"Product","price":1999.0,"stock":10,"is_active":true}' \
  http://catalog:8000/products/
```

- Обновление остатка:

```bash
docker compose exec gateway curl -s -X PATCH \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"stock":5}' \
  http://catalog:8000/products/{product_uuid}
```
