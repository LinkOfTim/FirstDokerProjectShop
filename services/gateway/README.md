Gateway/UI Service
==================

FastAPI + Jinja2: веб‑интерфейс и лёгкий API‑прокси к backend‑сервисам. Включает карточку товара, миниатюры в корзине, форматирование цен и админ‑разделы (товары, заказы, статистика, шаблоны).

Переменные окружения
- `AUTH_URL`, `CATALOG_URL`, `CART_URL`, `ORDER_URL`
- `SECRET_KEY`

Запуск
- Через корневой `docker compose up -d` (порт 8000 проброшен на хост).
- UI: `http://localhost:8000/`
- Login: `http://localhost:8000/login` (по умолчанию `admin@example.com / admin123`)
- Admin: `http://localhost:8000/admin`

Дополнительные страницы UI
- `GET /product/{id}` — карточка товара (галерея, описание, характеристики)
- `GET /admin/stats` — админ‑статистика (выручка, топ‑товары, низкий остаток, динамика)
- `GET /admin/templates` — управление шаблонами характеристик

API‑прокси (через gateway)
- GET `/api/products` — список (проксирует в catalog `/products/`); поддерживает параметры как в каталоге.
- GET `/api/products/{id}` — карточка товара.
- GET `/api/products/sku/{sku}` — найти товар по точному SKU.
- POST `/api/products` — создать товар (нужна админ‑cookie JWT).
- Шаблоны: `GET /api/templates`, `POST /api/templates`, `PATCH /api/templates/{id}`, `DELETE /api/templates/{id}` (админ)
- Статистика: `GET /api/admin/stats` (админ)

Примеры
- Логин и сохранение cookie:

```bash
curl -i -X POST 'http://localhost:8000/auth/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=admin@example.com&password=admin123'
# Из ответа возьмите Set-Cookie: access_token=...
```

- Создать товар через gateway (передайте cookie):

```bash
curl -s -X POST 'http://localhost:8000/api/products' \
  -H 'Content-Type: application/json' \
  -H 'Cookie: access_token=<JWT>' \
  -d '{
        "sku":"SKU-2",
        "name":"Gateway Product",
        "price":999.0,
        "stock":3,
        "is_active":true,
        "images":["https://example.com/p.jpg"],
        "description":"Описание через gateway",
        "attributes": {"brand":"Acme"}
      }'
```

Отображение
- Цены форматируются в UI как `1.234.567,89 ₸`.
- Изображения карточек вписываются без обрезания, в корзине показываются миниатюры.
