from __future__ import annotations

import json
from typing import Optional, Dict, Any

import httpx
from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import uuid

from .config import settings


app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Jinja filters
def format_price(value) -> str:
    try:
        n = float(value)
    except Exception:
        return str(value)
    s = f"{n:,.2f}"  # 1,234,567.89
    s = s.replace(",", "_")  # 1_234_567.89
    s = s.replace(".", ",")   # 1_234_567,89
    s = s.replace("_", ".")   # 1.234.567,89
    return s

templates.env.filters["price"] = format_price

# no in-memory cart; gateway proxies to cart-service


def get_token_from_cookie(request: Request) -> Optional[str]:
    return request.cookies.get("access_token")


def is_admin(token: Optional[str]) -> bool:
    if not token:
        return False
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload.get("role") == "admin"
    except JWTError:
        return False


def get_user_payload(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError:
        return None


def mint_admin_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {"sub": "gateway", "role": "admin", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    products = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # forward search/filter query params to catalog-service
            query_params = dict(request.query_params)
            user = get_user_payload(get_token_from_cookie(request))
            if "is_active" not in query_params and not (user and user.get("role") == "admin"):
                query_params["is_active"] = "true"
            url = f"{settings.catalog_url}/products/"
            if query_params:
                from urllib.parse import urlencode
                url = f"{url}?{urlencode(query_params)}"
            r = await client.get(url)
            if r.status_code == 200:
                products = r.json()
    except httpx.RequestError:
        # каталог ещё не готов или недоступен — показываем пустой список
        products = []
    user = get_user_payload(get_token_from_cookie(request))
    return templates.TemplateResponse("index.html", {"request": request, "products": products, "user": user})


@app.get("/product/{pid}", response_class=HTMLResponse)
async def product_page(pid: str, request: Request):
    user = get_user_payload(get_token_from_cookie(request))
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.catalog_url}/products/{pid}")
            if r.status_code != 200:
                return templates.TemplateResponse("product.html", {"request": request, "user": user, "product": None})
            product = r.json()
    except httpx.RequestError:
        product = None
    return templates.TemplateResponse("product.html", {"request": request, "user": user, "product": product})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_user_payload(get_token_from_cookie(request))
    return templates.TemplateResponse("login.html", {"request": request, "user": user})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = get_user_payload(get_token_from_cookie(request))
    return templates.TemplateResponse("register.html", {"request": request, "user": user})


@app.post("/auth/login")
async def login(request: Request, response: Response):
    form = await request.form()
    data = {"username": form.get("username"), "password": form.get("password")}  # OAuth2 form
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{settings.auth_url}/auth/login", data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code != 200:
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})
    token = r.json().get("access_token")
    resp = JSONResponse({"ok": True})
    resp.set_cookie("access_token", token, httponly=True, secure=False, samesite="lax")
    return resp


@app.post("/auth/logout")
async def logout(response: Response):
    response = JSONResponse({"ok": True})
    response.delete_cookie("access_token")
    return response


@app.post("/auth/register")
async def register(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{settings.auth_url}/auth/register", json=payload)
    if r.status_code != 200:
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return JSONResponse(status_code=r.status_code, content={"detail": r.text})
    # auto-login
    login_form = {"username": payload.get("email"), "password": payload.get("password")}
    async with httpx.AsyncClient() as client:
        lr = await client.post(
            f"{settings.auth_url}/auth/login",
            data=login_form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if lr.status_code == 200:
        token = lr.json().get("access_token")
        resp = JSONResponse({"ok": True})
        resp.set_cookie("access_token", token, httponly=True, secure=False, samesite="lax")
        return resp
    return JSONResponse({"registered": True})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return RedirectResponse("/login", status_code=302)
    user = get_user_payload(token)
    return templates.TemplateResponse("admin.html", {"request": request, "user": user})


@app.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders_page(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return RedirectResponse("/login", status_code=302)
    user = get_user_payload(token)
    return templates.TemplateResponse("admin_orders.html", {"request": request, "user": user})


@app.get("/admin/stats", response_class=HTMLResponse)
async def admin_stats_page(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return RedirectResponse("/login", status_code=302)
    user = get_user_payload(token)
    return templates.TemplateResponse("admin_stats.html", {"request": request, "user": user})


@app.get("/admin/templates", response_class=HTMLResponse)
async def admin_templates_page(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return RedirectResponse("/login", status_code=302)
    user = get_user_payload(token)
    return templates.TemplateResponse("admin_templates.html", {"request": request, "user": user})


# Proxy API endpoints
@app.get("/api/products")
async def api_list_products(request: Request):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            incoming = dict(request.query_params)
            token = get_token_from_cookie(request)
            if "is_active" not in incoming and not is_admin(token):
                incoming["is_active"] = "true"
            url = f"{settings.catalog_url}/products/"
            if incoming:
                from urllib.parse import urlencode
                url = f"{url}?{urlencode(incoming)}"
            r = await client.get(url)
            return JSONResponse(r.json(), status_code=r.status_code)
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": "catalog unavailable"})


@app.get("/api/products/{pid}")
async def api_get_product(pid: str):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.catalog_url}/products/{pid}")
            return JSONResponse(r.json(), status_code=r.status_code)
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": "catalog unavailable"})


@app.get("/api/products/sku/{sku}")
async def api_get_product_by_sku(sku: str):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.catalog_url}/products/sku/{sku}")
            return JSONResponse(r.json(), status_code=r.status_code)
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": "catalog unavailable"})


# Templates proxy (admin protected for write operations)
@app.get("/api/templates")
async def api_list_templates():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.catalog_url}/templates/")
            return JSONResponse(r.json(), status_code=r.status_code)
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": "catalog unavailable"})


@app.post("/api/templates")
async def api_create_template(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return JSONResponse(status_code=403, content={"detail": "Admin required"})
    payload = await request.json()
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.post(
            f"{settings.catalog_url}/templates/",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return JSONResponse(status_code=r.status_code, content={"detail": r.text})


@app.patch("/api/templates/{tid}")
async def api_update_template(tid: str, request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return JSONResponse(status_code=403, content={"detail": "Admin required"})
    payload = await request.json()
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.patch(
            f"{settings.catalog_url}/templates/{tid}",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return JSONResponse(status_code=r.status_code, content={"detail": r.text})


@app.delete("/api/templates/{tid}")
async def api_delete_template(tid: str, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return JSONResponse(status_code=403, content={"detail": "Admin required"})
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.delete(
            f"{settings.catalog_url}/templates/{tid}",
            headers={"Authorization": f"Bearer {token}"},
        )
        return Response(status_code=r.status_code)


@app.post("/api/products")
async def api_create_product(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return JSONResponse(status_code=403, content={"detail": "Admin required"})
    payload = await request.json()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(f"{settings.catalog_url}/products/", json=payload, headers=headers)
            return JSONResponse(r.json(), status_code=r.status_code)
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": "catalog unavailable"})


@app.patch("/api/products/{pid}")
async def api_update_product(pid: str, request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return JSONResponse(status_code=403, content={"detail": "Admin required"})
    payload = await request.json()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.patch(f"{settings.catalog_url}/products/{pid}", json=payload, headers=headers)
            return JSONResponse(r.json(), status_code=r.status_code)
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": "catalog unavailable"})


@app.delete("/api/products/{pid}")
async def api_delete_product(pid: str, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return JSONResponse(status_code=403, content={"detail": "Admin required"})
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.delete(f"{settings.catalog_url}/products/{pid}", headers=headers)
            return Response(status_code=r.status_code)
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": "catalog unavailable"})


# Cart helpers and endpoints (in-memory per user)
def _require_user_email(token: Optional[str]) -> Optional[str]:
    payload = get_user_payload(token)
    return payload.get("sub") if payload else None


@app.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not token:
        return RedirectResponse("/login", status_code=302)
    items = []
    user = get_user_payload(token)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            cr = await client.get(f"{settings.cart_url}/cart", headers={"Authorization": f"Bearer {token}"})
            if cr.status_code == 200:
                cart_map: Dict[str, int] = cr.json()
                for pid, qty in cart_map.items():
                    pr = await client.get(f"{settings.catalog_url}/products/{pid}")
                    if pr.status_code == 200:
                        p = pr.json()
                        items.append({"product": p, "qty": qty})
    except httpx.RequestError:
        pass
    return templates.TemplateResponse("cart.html", {"request": request, "items": items, "user": user})


@app.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    token = get_token_from_cookie(request)
    user = get_user_payload(token)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("account.html", {"request": request, "user": user})


@app.post("/auth/change_password")
async def change_password(request: Request):
    token = get_token_from_cookie(request)
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    payload = await request.json()
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.auth_url}/auth/change_password",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
    if r.status_code != 200:
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return JSONResponse(status_code=r.status_code, content={"detail": r.text})
    return JSONResponse({"ok": True})


@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request):
    token = get_token_from_cookie(request)
    user = get_user_payload(token)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("orders.html", {"request": request, "user": user})


@app.get("/orders/{oid}", response_class=HTMLResponse)
async def order_detail_page(oid: str, request: Request):
    token = get_token_from_cookie(request)
    user = get_user_payload(token)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("order_detail.html", {"request": request, "user": user})


@app.get("/api/cart")
async def api_get_cart(token: Optional[str] = Depends(get_token_from_cookie)):
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    items = []
    total = 0.0
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            cr = await client.get(f"{settings.cart_url}/cart", headers={"Authorization": f"Bearer {token}"})
            if cr.status_code != 200:
                return JSONResponse(status_code=cr.status_code, content=cr.json())
            cart_map: Dict[str, int] = cr.json()
            for pid, qty in cart_map.items():
                pr = await client.get(f"{settings.catalog_url}/products/{pid}")
                if pr.status_code == 200:
                    p = pr.json()
                    price = float(p.get("price", 0))
                    items.append({"product": p, "qty": qty, "subtotal": round(price * qty, 2)})
                    total += price * qty
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": "cart unavailable"})
    return {"items": items, "total": round(total, 2)}


@app.post("/api/cart/add")
async def api_cart_add(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    payload = await request.json()
    pid = str(payload.get("product_id"))
    # validate product exists and stock availability
    async with httpx.AsyncClient(timeout=5.0) as client:
        pr = await client.get(f"{settings.catalog_url}/products/{pid}")
        if pr.status_code != 200:
            return JSONResponse(status_code=404, content={"detail": "Product not found"})
        product = pr.json()
        if not product.get("is_active", True):
            return JSONResponse(status_code=409, content={"detail": "Product not available"})
        # compute resulting qty = current in cart + incoming qty
        try:
            qty_add = int(payload.get("qty", 1))
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "Invalid qty"})
        if qty_add <= 0:
            return JSONResponse(status_code=422, content={"detail": "Invalid qty"})
        cr0 = await client.get(f"{settings.cart_url}/cart", headers={"Authorization": f"Bearer {token}"})
        current_qty = 0
        if cr0.status_code == 200:
            cart_map = cr0.json()
            current_qty = int(cart_map.get(pid, 0))
        target_qty = current_qty + qty_add
        try:
            stock = int(product.get("stock", 0))
        except Exception:
            stock = 0
        if target_qty > stock:
            return JSONResponse(status_code=409, content={"detail": "Not enough stock"})
        cr = await client.post(
            f"{settings.cart_url}/cart/add",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        if cr.status_code != 200:
            try:
                return JSONResponse(status_code=cr.status_code, content=cr.json())
            except Exception:
                return JSONResponse(status_code=cr.status_code, content={"detail": cr.text})
    return JSONResponse({"ok": True})


@app.post("/api/order/checkout")
async def api_order_checkout(token: Optional[str] = Depends(get_token_from_cookie)):
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{settings.order_url}/orders/checkout",
                headers={"Authorization": f"Bearer {token}"},
            )
            try:
                content = r.json()
            except Exception:
                content = {"detail": r.text}
            return JSONResponse(status_code=r.status_code, content=content)
    except httpx.RequestError:
        return JSONResponse(status_code=503, content={"detail": "order-service unavailable"})


@app.post("/api/cart/remove")
async def api_cart_remove(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    payload = await request.json()
    if not payload.get("product_id"):
        return JSONResponse(status_code=422, content={"detail": "Invalid input"})
    async with httpx.AsyncClient(timeout=5.0) as client:
        cr = await client.post(
            f"{settings.cart_url}/cart/remove",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        if cr.status_code != 200:
            try:
                return JSONResponse(status_code=cr.status_code, content=cr.json())
            except Exception:
                return JSONResponse(status_code=cr.status_code, content={"detail": cr.text})
    return JSONResponse({"ok": True})


@app.post("/api/cart/set")
async def api_cart_set(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    payload = await request.json()
    if not payload.get("product_id"):
        return JSONResponse(status_code=422, content={"detail": "Invalid input"})
    # validate product exists and stock availability
    async with httpx.AsyncClient(timeout=5.0) as client:
        pr = await client.get(f"{settings.catalog_url}/products/{payload.get('product_id')}")
        if pr.status_code != 200:
            return JSONResponse(status_code=404, content={"detail": "Product not found"})
        product = pr.json()
        if not product.get("is_active", True):
            return JSONResponse(status_code=409, content={"detail": "Product not available"})
        try:
            qty = int(payload.get("qty", 0))
        except Exception:
            return JSONResponse(status_code=422, content={"detail": "Invalid qty"})
        if qty < 0:
            return JSONResponse(status_code=422, content={"detail": "Invalid qty"})
        if qty > 0:
            try:
                stock = int(product.get("stock", 0))
            except Exception:
                stock = 0
            if qty > stock:
                return JSONResponse(status_code=409, content={"detail": "Not enough stock"})
        cr = await client.post(
            f"{settings.cart_url}/cart/set",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        if cr.status_code != 200:
            try:
                return JSONResponse(status_code=cr.status_code, content=cr.json())
            except Exception:
                return JSONResponse(status_code=cr.status_code, content={"detail": cr.text})
    return JSONResponse({"ok": True})


@app.post("/api/cart/clear")
async def api_cart_clear(token: Optional[str] = Depends(get_token_from_cookie)):
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    async with httpx.AsyncClient(timeout=5.0) as client:
        cr = await client.post(
            f"{settings.cart_url}/cart/clear",
            headers={"Authorization": f"Bearer {token}"},
        )
        if cr.status_code != 200:
            try:
                return JSONResponse(status_code=cr.status_code, content=cr.json())
            except Exception:
                return JSONResponse(status_code=cr.status_code, content={"detail": cr.text})
    return JSONResponse({"ok": True})


@app.get("/api/orders")
async def api_orders(token: Optional[str] = Depends(get_token_from_cookie)):
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{settings.order_url}/orders", headers={"Authorization": f"Bearer {token}"})
    try:
        return JSONResponse(status_code=r.status_code, content=r.json())
    except Exception:
        return JSONResponse(status_code=r.status_code, content={"detail": r.text})


@app.get("/api/orders/{oid}")
async def api_order_detail(oid: str, token: Optional[str] = Depends(get_token_from_cookie)):
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{settings.order_url}/orders/{oid}", headers={"Authorization": f"Bearer {token}"})
    try:
        return JSONResponse(status_code=r.status_code, content=r.json())
    except Exception:
        return JSONResponse(status_code=r.status_code, content={"detail": r.text})


@app.patch("/api/orders/{oid}/cancel")
async def api_user_cancel_order(oid: str, token: Optional[str] = Depends(get_token_from_cookie)):
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Login required"})
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.patch(
            f"{settings.order_url}/orders/{oid}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return JSONResponse(status_code=r.status_code, content={"detail": r.text})


@app.get("/api/admin/orders")
async def api_admin_orders(request: Request, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return JSONResponse(status_code=403, content={"detail": "Admin required"})
    params = str(request.query_params) or ""
    url = f"{settings.order_url}/admin/orders"
    if params:
        url = f"{url}?{params}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return JSONResponse(status_code=r.status_code, content={"detail": r.text})


@app.patch("/api/admin/orders/{oid}/cancel")
async def api_admin_cancel_order(oid: str, token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return JSONResponse(status_code=403, content={"detail": "Admin required"})
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.patch(
            f"{settings.order_url}/orders/{oid}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            return JSONResponse(status_code=r.status_code, content=r.json())
        except Exception:
            return JSONResponse(status_code=r.status_code, content={"detail": r.text})


@app.get("/api/admin/stats")
async def api_admin_stats(token: Optional[str] = Depends(get_token_from_cookie)):
    if not is_admin(token):
        return JSONResponse(status_code=403, content={"detail": "Admin required"})
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # products
            pr = await client.get(f"{settings.catalog_url}/products/")
            products = pr.json() if pr.status_code == 200 else []
            # orders (admin)
            orr = await client.get(
                f"{settings.order_url}/admin/orders",
                headers={"Authorization": f"Bearer {token}"},
            )
            orders = orr.json() if orr.status_code == 200 else []
    except httpx.RequestError:
        products, orders = [], []

    # products stats
    total_products = len(products)
    active_products = sum(1 for p in products if p.get("is_active", True))
    low_stock_threshold = 3
    low_stock = [
        {"id": p.get("id"), "sku": p.get("sku"), "name": p.get("name"), "stock": int(p.get("stock", 0))}
        for p in products
        if int(p.get("stock", 0)) <= low_stock_threshold
    ]

    # orders stats
    total_orders = len(orders)
    total_revenue = 0.0
    buyers = set()
    by_product: Dict[str, Dict[str, object]] = {}
    by_day: Dict[str, Dict[str, float]] = {}
    from datetime import datetime
    for o in orders:
        buyers.add(o.get("user"))
        try:
            total_revenue += float(o.get("total", 0))
        except Exception:
            pass
        for it in o.get("items", []):
            pid = str(it.get("product_id"))
            qty = int(it.get("qty", 0))
            revenue = float(it.get("subtotal", 0))
            name = it.get("name")
            sku = it.get("sku")
            acc = by_product.setdefault(pid, {"product_id": pid, "name": name, "sku": sku, "qty": 0, "revenue": 0.0})
            acc["qty"] = int(acc["qty"]) + qty
            acc["revenue"] = float(acc["revenue"]) + revenue
        # timeseries
        created_at = o.get("created_at")
        if created_at:
            try:
                d = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date().isoformat()
                rec = by_day.setdefault(d, {"count": 0, "revenue": 0.0})
                rec["count"] += 1
                rec["revenue"] += float(o.get("total", 0))
            except Exception:
                pass

    # top products by revenue
    top_products = sorted(by_product.values(), key=lambda x: (float(x["revenue"]), int(x["qty"])), reverse=True)[:5]

    # last 7 days summary
    from datetime import timedelta, date
    today = date.today()
    last7 = []
    for i in range(6, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        rec = by_day.get(day, {"count": 0, "revenue": 0.0})
        last7.append({"date": day, "count": rec["count"], "revenue": rec["revenue"]})

    return {
        "products": {
            "total": total_products,
            "active": active_products,
            "low_stock": low_stock[:10],
        },
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "unique_buyers": len([b for b in buyers if b]),
        "top_products": [
            {
                "product_id": p["product_id"],
                "name": p.get("name"),
                "sku": p.get("sku"),
                "qty": int(p.get("qty", 0)),
                "revenue": round(float(p.get("revenue", 0.0)), 2),
            }
            for p in top_products
        ],
        "last7": last7,
    }
