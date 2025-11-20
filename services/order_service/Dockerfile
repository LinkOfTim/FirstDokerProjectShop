FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && echo 'export PATH="/root/.local/bin:$PATH"' >> /etc/profile
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml README.md /app/
COPY app /app/app
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY docker-entrypoint.sh /app/docker-entrypoint.sh

RUN uv pip install --system --no-cache . \
    && chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

ENV DATABASE_URL="postgresql+asyncpg://postgres:postgres@order-db:5432/orderdb"
ENV SECRET_KEY="dev-secret-change-me"
ENV CATALOG_URL="http://catalog:8000"
ENV CART_URL="http://cart:8000"

CMD ["/app/docker-entrypoint.sh"]

