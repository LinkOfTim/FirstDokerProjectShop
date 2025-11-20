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

RUN uv pip install --system --no-cache .

EXPOSE 8000

ENV REDIS_URL="redis://cart-redis:6379/0"
ENV SECRET_KEY="dev-secret-change-me"

CMD uvicorn app.main:app --host 0.0.0.0 --port 8000

