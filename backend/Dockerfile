# syntax=docker/dockerfile:1.6

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --user -r requirements.txt

# ---- Runtime image ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PATH="/root/.local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

WORKDIR /app
COPY . .

# Puerto por defecto para plataformas que no inyectan PORT (Coolify, compose).
EXPOSE 8000

# start-period generoso: el arranque carga agent_framework y modelos de
# embeddings, y tarda ~1-2 min. Con un margen corto el contenedor se marca
# unhealthy mientras todavía está importando.
HEALTHCHECK --interval=30s --timeout=5s --start-period=150s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/health" || exit 1

# Forma shell (sh -c) para que ${PORT} se expanda en runtime.
#
# Railway inyecta PORT y enruta el tráfico a ese puerto: si el proceso escucha
# en otro, el healthcheck responde "service unavailable" y el deploy falla.
# Este Dockerfile se escribió para Coolify, donde PORT no existe, así que tenía
# el 8000 fijo; al llegar a main, Railway lo detectó ("Railway will always build
# with a Dockerfile if it finds one", por encima de builder=RAILPACK) y rompió
# el despliegue. Con ${PORT:-8000} sirve para las dos plataformas.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 120"]
