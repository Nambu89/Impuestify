# Deploy Fiscal IA Melilla en Contabo + Coolify

Guía paso a paso para desplegar el backend de la demo en un VPS Contabo con
Coolify ya instalado.

## Arquitectura

- **Backend**: este repo (`Nambu89/Impuestify`), rama `demo/fiscal-ia-melilla`. FastAPI + Python 3.12.
- **Frontend**: repo separado **`Nambu89/ia-melilla`** (React/Vite). Se despliega en Coolify como servicio independiente.
- Ambos servicios viven en el mismo VPS Contabo, gateados por Coolify reverse proxy (Caddy/Traefik). Cada uno con su subdominio o paths distintos.

## Pre-requisitos

- VPS Contabo con Coolify (>= v4) instalado y operativo
- Dos dominios (o subdominios) apuntando a la IP del VPS:
  - Backend API (p.ej. `api.fiscal-melilla.demo`)
  - Frontend (p.ej. `fiscal-melilla.demo`)
- Cuentas externas con credenciales válidas:
  - OpenAI (gpt-5-mini)
  - Groq (LlamaGuard4)
  - Google Gemini (OCR facturas)
  - Turso (libsql) — DB **nueva dedicada** al demo, no la de Impuestify prod
  - Upstash Redis + Upstash Vector (RAG + opcional semantic cache)
  - Resend (email)

## Pasos

### 1. Crear DB Turso dedicada (si no se ha hecho ya — Task 0b del plan)

```bash
turso db create demo-fiscal-melilla
turso db tokens create demo-fiscal-melilla
```

Apuntar URL + token — irán en `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN`.

### 2. Seed inicial de la DB nueva

Desde tu máquina (con el repo clonado):

```bash
cd backend
export TURSO_DATABASE_URL=libsql://demo-fiscal-melilla-...
export TURSO_AUTH_TOKEN=...
python scripts/seed_estatal_scale.py
python scripts/seed_casillas.py
python scripts/populate_tax_parameters.py
python scripts/seed_deductions_territorial.py
python scripts/seed_deductions_forales_2025.py
```

Verificar:

```bash
turso db shell demo-fiscal-melilla "SELECT COUNT(*) FROM irpf_scales WHERE jurisdiction='Estatal'"
# Expected: 8 tramos
turso db shell demo-fiscal-melilla "SELECT COUNT(*) FROM irpf_casillas"
# Expected: ~2064
turso db shell demo-fiscal-melilla "SELECT COUNT(*) FROM deductions WHERE ccaa IS NULL OR ccaa IN ('Melilla','Ceuta')"
# Expected: >16
```

### 3. Crear proyecto BACKEND en Coolify

1. Coolify dashboard → **+ New Resource** → **Public Repository** (o **Private**
   si has migrado a un fork).
2. Repo URL: `https://github.com/Nambu89/Impuestify`
3. **Branch**: `demo/fiscal-ia-melilla`
4. **Build Pack**: `Docker Compose`
5. **Compose file path**: `docker-compose.yml`
6. **Domain**: el subdominio API (p.ej. `api.fiscal-melilla.demo`)

### 3b. Crear proyecto FRONTEND en Coolify (servicio aparte)

1. Coolify dashboard → **+ New Resource** → **Public Repository**
2. Repo URL: `https://github.com/Nambu89/ia-melilla`
3. **Branch**: según el repo (probablemente `main`)
4. **Build Pack**: el que indique el README del frontend (Dockerfile / Nixpacks / Static)
5. **Domain**: el subdominio público (p.ej. `fiscal-melilla.demo`)
6. **Env vars del frontend**: configurar `VITE_API_BASE_URL` (o equivalente) apuntando al backend de paso 3 (`https://api.fiscal-melilla.demo`)

### 4. Configurar variables de entorno

Coolify → tu proyecto → **Environment Variables** → **Bulk Edit**.

Pega el contenido de `.env.demo.example` y reemplaza placeholders. Críticos:

- `JWT_SECRET_KEY` — generar fresco: `openssl rand -hex 32`. **NO** reusar el
  de Impuestify producción.
- `DEMO_USER_PASSWORD` — mínimo 16 chars, gestor de contraseñas.
- `OPENAI_API_KEY` — key dedicada con tope de gasto mensual.
- `DEFENSIA_STORAGE_KEY` — `openssl rand -hex 32` (si no se setea, uploads
  DefensIA devuelven 503).
- `ADMIN_API_KEY` — `openssl rand -hex 32` (NUNCA dejar el placeholder de
  `config.py` por defecto).
- `ALLOWED_ORIGINS` — incluir el dominio del frontend (paso 3b). Ej: `https://fiscal-melilla.demo,http://localhost:5173`. Sin esto, el navegador bloquea peticiones del frontend al backend por CORS.
- `FRONTEND_URL` — base URL del frontend (paso 3b). Se usa en emails (reset password, etc.).

### 5. Configurar healthcheck + TLS

- **Health URL**: `/health`
- **Port**: `8000` (interno; Coolify proxy lo expone vía 80/443)
- Coolify auto-genera certificado Let's Encrypt si el dominio resuelve a la IP.

### 6. Deploy

1. Click **Deploy**.
2. Logs en la tab **Logs**. Verificar:
   - `INFO: Application startup complete.`
   - `Seeded demo user: demo@...` (primera vez)
   - `Subscriptions disabled (SUBSCRIPTIONS_ENABLED=false) — skipping subscription routes`
   - Sin errores de conexión Turso/Upstash/OpenAI.

### 7. Verificación post-deploy

```bash
# Healthcheck
curl https://api.fiscal-melilla.demo/health
# Esperado:
# {
#   "status": "healthy",
#   "timestamp": 1737..., "rag_initialized": true, "statistics": {...},
#   "demo_mode": true,
#   "brand": "Fiscal IA Melilla",
#   "territory_lock": "Melilla",
#   "subscriptions_enabled": false
# }

# Login del usuario demo precreado
curl -X POST https://api.fiscal-melilla.demo/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@fiscal-melilla.demo","password":"<DEMO_USER_PASSWORD>"}'
# Esperado: 200 con access_token

# Chat (bearer token):
curl -X POST https://api.fiscal-melilla.demo/api/ask \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question":"Qué deducciones IRPF tengo en Melilla?"}'
# Esperado: respuesta con contexto Melilla (no Madrid/Cataluña)

# /subscription/* NO debe existir:
curl -i https://api.fiscal-melilla.demo/subscription/status
# Esperado: 404
```

### 8. Monitorización

- Coolify dashboard muestra CPU/RAM/disk del container.
- Logs: `docker logs demo-melilla-backend -f` (vía Coolify terminal).
- Si OOM: el Dockerfile ya usa `--workers 1`. Si persiste, subir RAM del VPS.

## Cambiar la marca

Para renombrar la demo (cuando el cliente decida un nombre comercial):

1. Coolify → Environment Variables.
2. Cambiar `BRAND_NAME=<nuevo nombre>` y `BRAND_DOMAIN=<nuevo.dominio>`.
3. Redeploy.

No requiere tocar código. Emails, PDFs, system prompts del LLM y `/health`
reflejan el nuevo valor automáticamente.

## Gotchas

- **CVEs Coolify** (ADR-007 Impuestify): la demo NO debe manejar datos
  personales reales. Banner cookies + disclaimer obligatorio. Si la demo se
  vuelve producto comercial → migrar a Docker compose directo + Caddy.
- **Tope de gasto APIs**: configurar límites en OpenAI/Gemini billing
  dashboards ANTES de exponer públicamente.
- **GDPR**: el responsable de tratamiento es el titular del dominio. Política
  de privacidad mínima obligatoria aunque sea demo.
- **`--workers 1`**: hardcodeado en Dockerfile CMD por OOM histórico. NO
  subir.
- **Healthcheck `start_period: 40s`**: si en el primer deploy el container
  queda `unhealthy` antes de tiempo, subir a 60s en `docker-compose.yml`.

## Rollback

Coolify → Deployments → seleccionar deployment anterior → **Redeploy**.
