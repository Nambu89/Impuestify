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

# start-period generoso: el arranque importa agent_framework y todos los
# routers (~10 s) y después el lifespan ejecuta init_schema contra Turso
# remoto (~79 statements, cada uno con su commit). Con un margen corto el
# contenedor se marca unhealthy mientras todavía está levantando.
# (No hay modelos de embeddings locales: los embeddings van por API de OpenAI
# + Upstash Vector. El requirements no trae torch ni sentence-transformers.)
HEALTHCHECK --interval=30s --timeout=5s --start-period=150s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT:-8000}/health" || exit 1

# Forma shell (sh -c) para que ${PORT} se expanda en runtime.
#
# OJO con dónde manda este CMD: en Railway SOLO se ejecuta si
# `backend/railway.toml` no define `startCommand` (hoy sí lo define, así que
# este CMD es el que usan Coolify y docker-compose). Se mantienen idénticos a
# propósito para que la app arranque igual en las dos plataformas.
#
# ${PORT:-8000}: Railway inyecta PORT y enruta el tráfico ahí; Coolify no la
# define y cae al 8000 con el que se escribió este fichero.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-keep-alive 120"]
