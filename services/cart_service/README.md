Cart Service
============

FastAPI + Redis service for user carts.

Env
- `REDIS_URL` — e.g. `redis://cart-redis:6379/0`
- `SECRET_KEY` — shared JWT secret (decode `sub` as user id/email)

Endpoints
- GET `/cart` — return cart items as `{product_id: qty}`
- POST `/cart/add` — body `{product_id, qty}`
- POST `/cart/remove` — body `{product_id}`

Auth: Bearer JWT required; `sub` used as cart key.

