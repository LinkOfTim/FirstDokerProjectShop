API Specification (Draft)
=========================

This document outlines the REST API contracts for current services (auth, catalog, gateway proxy) and planned services (cart, order, payment). JSON is the default content type unless stated otherwise.

Auth Service
------------

POST /auth/register
- Request
  {
    "email": "user@example.com",
    "password": "Secret123!"
  }
- Responses
  - 201 Created
    {
      "id": "<uuid>",
      "email": "user@example.com",
      "role": "user"
    }
  - 409 Conflict — email already registered

POST /auth/login (OAuth2 Password form)
- Request (x-www-form-urlencoded)
  username=user@example.com&password=Secret123!
- Responses
  - 200 OK
    {
      "access_token": "<jwt>",
      "token_type": "bearer"
    }
    Sets HttpOnly cookie `access_token`.
  - 401 Unauthorized — invalid credentials

POST /auth/logout
- Response: 200 OK, clears cookie

GET /health
- Response: {"status":"ok","db":true}

Catalog Service
---------------

GET /products
- Query: (future) filters/pagination
- Response 200
  [
    {"id":"<uuid>","sku":"SKU-1","name":"Item","price":1999.99,"stock":10,"is_active":true}
  ]

GET /products/{id}
- Response 200: ProductOut
- 404 Not Found

POST /products (admin)
- Auth: `Authorization: Bearer <jwt>` with role=admin
- Request
  {"sku":"SKU-1","name":"Item","price":1999.99,"stock":10,"is_active":true}
- Responses
  - 201 Created: ProductOut
  - 409 Conflict — duplicate SKU
  - 403 Forbidden — missing admin role

PATCH /products/{id} (admin)
- Request: partial fields, e.g. {"is_active":false}
- Responses: 200 OK (ProductOut), 404 Not Found

DELETE /products/{id} (admin)
- Response: 204 No Content

GET /health
- Response: {"status":"ok","db":true}

Gateway (UI/Proxy)
------------------
HTML Pages
- GET `/` — renders product list
- GET `/login` — login form
- GET `/admin` — requires admin JWT cookie, shows simple admin panel

Proxy API (for UI)
- GET `/api/products` → forwards to catalog GET /products
- GET `/api/products/{id}` → forwards to catalog
- POST `/api/products` → forwards with Authorization header built from cookie
- PATCH `/api/products/{id}` → forwards with Authorization
- DELETE `/api/products/{id}` → forwards with Authorization
Responses and codes mirror catalog; if catalog is unreachable, returns 503.

Planned: Cart Service
---------------------
Storage: Redis (`cart:{user_id}` → hash/set of items)

POST /cart/add
- Auth: user JWT
- Request
  {"product_id":"<uuid>", "qty": 2}
- Responses
  - 200 OK {"items":[{"product_id":"<uuid>","qty":2}], "total_items": 2}
  - 400 Bad Request — invalid qty

POST /cart/remove
- Auth: user JWT
- Request
  {"product_id":"<uuid>"}
- Response 200 OK {"items":[...], "total_items": n}

GET /cart
- Auth: user JWT
- Response 200 OK {"items":[{"product_id":"<uuid>","qty":2}], "total_items": 2}

Planned: Order Service
----------------------
DB: PostgreSQL (`orders`, `order_items`, `order_events`)

POST /order/create
- Auth: user JWT
- Behavior
  - Reads cart from cart-service.
  - Validates each product (exists/active) and current price via catalog.
  - Persists order with snapshot of items/prices.
  - Returns order with status `created`.
- Response 201 Created
  {
    "id":"<uuid>",
    "status":"created",
    "total": 3999.98,
    "items":[{"product_id":"<uuid>","name":"Item","price":1999.99,"qty":2}]
  }
- Errors: 400 (empty cart), 409 (price changed/out of stock), 422 (invalid input)

GET /order/{id}
- Auth: user JWT (owner) or admin
- Response 200: order with items and status
- 404 Not Found

POST /order/{id}/status (internal)
- Auth: service token
- Request {"status":"paid"}
- Response 200

Planned: Payment Service
------------------------

POST /payment/pay
- Request
  {"order_id":"<uuid>", "amount": 3999.98}
- Behavior
  - Emulates success/failure (e.g., random or based on amount parity).
  - On success: callback to `order-service POST /order/{id}/status {paid}` using service token.
- Responses
  - 200 OK {"status":"paid"}
  - 402 Payment Required or 400 on failure scenarios

Auth & JWT Contracts
--------------------
- JWT claims (baseline)
  {
    "sub": "user@example.com",  // subject (email)
    "role": "user" | "admin",
    "exp": 1735689600            // expiry (Unix)
  }
- Algorithm: HS256, secret via `SECRET_KEY`.

Error Codes (Conventions)
-------------------------
- 400 — validation/business rule (e.g., bad qty)
- 401 — not authenticated
- 403 — not authorized (needs admin)
- 404 — not found
- 409 — conflict (duplicate SKU/email, price mismatch)
- 422 — semantic validation errors
- 500 — unexpected server error
- 503 — dependent service unavailable (gateway proxy)

Notes
-----
- All write endpoints require JSON `Content-Type: application/json` unless form is specified.
- Idempotency for payments should be added (idempotency keys) in Payment/Order.
- Add rate limiting and CSRF protections for web forms in Gateway for production.

