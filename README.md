# Impuestify - Asistente Fiscal Inteligente

Impuestify es un asistente fiscal con IA especializado en normativa espanola que utiliza **RAG (Retrieval-Augmented Generation)** con **OpenAI GPT-5-mini** y **Google Gemini 3 Flash** para proporcionar respuestas precisas y contextualizadas. Cubre los 21 territorios fiscales de Espana: 15 CCAA de regimen comun, 4 territorios forales (Araba, Bizkaia, Gipuzkoa, Navarra), Ceuta y Melilla.

**Web**: [impuestify.com](https://impuestify.com)

## Caracteristicas Principales

### Sistema Multi-Agente

| Agente | Funcion |
|--------|---------|
| **CoordinatorAgent** | Router inteligente que decide que agente usar |
| **TaxAgent** | IRPF, IVA, cuotas autonomos, deducciones |
| **PayslipAgent** | Analisis de nominas (13 patrones regex) |
| **NotificationAgent** | Analisis de notificaciones PDF de la AEAT |
| **WorkspaceAgent** | Gestion de documentos fiscales del usuario |

### Herramientas Fiscales (12 tools)

| Tool | Proposito |
|------|-----------|
| `simulate_irpf` | Simulacion completa con auto-descubrimiento de deducciones |
| `calculate_irpf` | Calculo por tramos y CCAA |
| `calculate_autonomous_quota` | Cuotas autonomos 2025 (15 tramos RDL 13/2022) |
| `search_tax_regulations` | Busqueda FTS5 + BM25 en 456+ documentos oficiales |
| `discover_deductions` | ~1.008 deducciones (21 territorios al 100%) |
| `compare_joint_individual` | Comparativa tributacion conjunta vs individual |
| `iae_lookup` | Busqueda epigrafe IAE para creadores |
| `lookup_casilla` | Busqueda casillas Modelo 100 (2.064 casillas) |
| `calculate_modelo_303` | IVA trimestral |
| `calculate_modelo_130` | Pago fraccionado IRPF autonomos |
| `calculate_modelo_ipsi` | IPSI Ceuta/Melilla (6 tipos) |
| `calculate_isd` | Impuesto sobre Sucesiones y Donaciones (21 CCAA) |

### Simulador IRPF

- 8 sub-calculadoras: trabajo, ahorro, inmuebles, MPYF, actividades, renta imputada, perdidas, crypto FIFO
- Tributacion conjunta, foral (vasco 7 + navarra 11 tramos), Ceuta/Melilla 60%
- Endpoint REST: `POST /api/irpf/estimate` — sin LLM, ~50-100ms
- XSD Modelo 100: ~100% cobertura

### Motor de Deducciones (~1.008)

- 16 estatales + 195 territoriales + 339 XSD + 408 CCAA 2025 + 50 forales
- 21/21 territorios cubiertos al 100%
- `simulate_irpf` encadena automaticamente `discover_deductions`

### Clasificador de Facturas (Gemini 3 Flash)

- OCR con Gemini 3 Flash Vision ($0,0003/factura)
- Clasificacion automatica PGC (201 cuentas, 7 grupos)
- Asientos contables en partida doble
- Libros: Diario, Mayor, Balance, Perdidas y Ganancias
- Export CSV/Excel para Registro Mercantil
- 5 tipos de factura soportados: autonomo, creador, farmacia (multi-IVA + RE), simplificada, intracomunitaria

### Guia Fiscal Adaptativa

| Plan | Pasos | Contenido especifico |
|------|-------|---------------------|
| Particular | 7 | Personal, Trabajo, Ahorro, Inmuebles, Familia, Deducciones, Resultado |
| Creator | 8 | + Plataformas, IAE, IVA intracomunitario, M349, DAC7 |
| Autonomo | 8 | + Actividad economica, cuota SS, retenciones, M130 |

### Calculadoras Publicas

| Calculadora | URL | Descripcion |
|-------------|-----|-------------|
| Sueldo Neto | `/calculadora-neto` | 5 regimenes fiscales (Madrid, Canarias IGIC, Melilla IPSI, Pais Vasco, Navarra) |
| Retenciones IRPF | `/calculadora-retenciones` | Algoritmo oficial AEAT 2026 |
| Umbrales Contables | `/calculadora-umbrales` | PGC Normal vs PYMES, necesidad de auditoria (LSC) |
| Obligaciones Fiscales | `/modelos-obligatorios` | Modelos por perfil, CCAA y actividad |
| Obligado a Declarar | `/obligado-declarar` | Art. 96 LIRPF |
| Checklist Borrador | `/checklist-borrador` | Verificacion pre-declaracion |

### Suscripciones

| Plan | Precio | Audiencia |
|------|--------|-----------|
| Particular | 5 EUR/mes | Asalariados, pensionistas |
| Creator | 49 EUR/mes | Influencers, YouTubers, streamers |
| Autonomo | 39 EUR/mes IVA incl. | Trabajadores por cuenta propia |

Stripe Checkout + Customer Portal. Sin permanencia.

## Arquitectura

```
+------------------+
|    Frontend      |  React 18 + Vite + TypeScript
|  /chat           |  SSE streaming
|  /guia-fiscal    |  Tax Guide Wizard + LiveEstimatorBar
|  /clasificador   |  Invoice OCR + PGC classification
|  /contabilidad   |  Libro Diario/Mayor/Balance/PyG
+--------+---------+
         |
         v  JWT + Rate Limit + 13 Security Layers
+------------------------------------------------------------+
|                  FastAPI Backend                           |
|                                                            |
|  +--------------------------------------------------+     |
|  |           CoordinatorAgent (Router)              |     |
|  +----+------------+------------+----------+--------+     |
|       |            |            |          |              |
|  +----v----+  +----v----+  +---v----+  +---v------+       |
|  | TaxAgent|  |Payslip  |  |Notif.  |  |Workspace |       |
|  |         |  |Agent    |  |Agent   |  |Agent     |       |
|  +---------+  +---------+  +--------+  +----------+       |
|                                                            |
|  12 Tools + Gemini OCR + Contabilidad Service             |
+------------------------------------------------------------+
       |          |          |         |          |
       v          v          v         v          v
  +--------+ +--------+ +------+ +-------+ +--------+
  | Turso  | |Upstash | |OpenAI| |Stripe | | Gemini |
  | SQLite | | Redis  | | LLM  | |Payments| | OCR   |
  +--------+ +--------+ +------+ +-------+ +--------+
```

### Stack

**Backend:** FastAPI, Python 3.12+, Turso (SQLite), Upstash Redis/Vector, OpenAI GPT-5-mini, Google Gemini 3 Flash, Groq (LlamaGuard4), Stripe, Resend

**Frontend:** React 18, Vite 5, TypeScript, React Router, Lucide React, vanilla-cookieconsent v3

**Infra:** Railway (auto-deploy), Cloudflare (DNS + Turnstile CAPTCHA)

## Seguridad (13 capas)

1. Rate Limiting (SlowAPI + Upstash Redis)
2. Security Headers (CSP, X-Frame-Options, XSS, Referrer-Policy)
3. JWT Auth (access + refresh tokens)
4. Cloudflare Turnstile CAPTCHA (Login + Register)
5. MFA / 2FA (TOTP + backup codes)
6. Prompt Injection (Llama Prompt Guard 2 via Groq)
7. PII Detection (DNI/NIE, telefonos, emails, cuentas bancarias)
8. SQL Injection (consultas parametrizadas + deteccion OWASP)
9. Content Moderation (Llama Guard 4, 14 categorias)
10. Content Restriction (autonomo content bloqueado para plan Particular)
11. Semantic Cache (Upstash Vector, umbral 0,93, TTL 24h)
12. Guardrails (validacion input/output)
13. Audit Logger (registro inmutable)

## Quick Start

### Requisitos

- Python 3.12+
- Node.js 18+
- API Keys: OpenAI, Turso, Upstash, Groq, Stripe, Resend, Google Gemini

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Seed datos de referencia
python scripts/seed_estatal_scale.py
python scripts/seed_deductions.py
python scripts/seed_deductions_territorial.py
python scripts/seed_pgc_accounts.py
python scripts/seed_test_users.py

# Iniciar
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### Variables de entorno

Crea `.env` en la raiz (ver `.env.example` para la lista completa):

```bash
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-5-mini
GOOGLE_GEMINI_API_KEY=AIza...
TURSO_DATABASE_URL=libsql://...
TURSO_AUTH_TOKEN=...
JWT_SECRET_KEY=...  # openssl rand -hex 32
STRIPE_SECRET_KEY=sk_live_...
# ... ver .env.example
```

## Testing

```bash
# Backend (~1.758 tests)
cd backend
pytest tests/ -v

# Frontend (build check)
cd frontend
npm run build

# E2E Playwright (17 tests clasificador + contabilidad)
npx tsx tests/e2e/fixtures/invoices/generate-invoice-images.ts
npx playwright test tests/e2e/qa-invoices-contabilidad-full.spec.ts
```

### Test Users

| Email | Password | Plan |
|-------|----------|------|
| `test.particular@impuestify.es` | `Test2026!` | particular |
| `test.autonomo@impuestify.es` | `Test2026!` | autonomo |
| `test.creator@impuestify.es` | `Test2026!` | creator |

Seed: `cd backend && python scripts/seed_test_users.py`

## RAG

- 456+ documentos oficiales (AEAT, BOE, Diputaciones Forales)
- ~89.000 chunks, ~82.000 embeddings (text-embedding-3-large)
- FTS5 + semantic search
- Crawler automatizado (90 URLs, 23 territorios, Scrapling anti-bot)

## Deployment (Railway)

Railway auto-deploy en cada push a `main`. Dos servicios:

- **Backend**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4`
- **Frontend**: `npm run build && npx vite preview --host 0.0.0.0 --port $PORT`

## Troubleshooting

| Problema | Solucion |
|----------|----------|
| Backend no conecta a Turso | Verificar `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN` |
| Escala IRPF no encontrada | `python scripts/seed_estatal_scale.py` |
| Deducciones vacias | `python scripts/seed_deductions.py` + `seed_deductions_territorial.py` |
| PGC cuentas vacias | `python scripts/seed_pgc_accounts.py` |
| Clasificador facturas 503 | Verificar `GOOGLE_GEMINI_API_KEY` |
| Upload timeout | El OCR Gemini tarda 30-60s, timeout configurado a 120s |
| CORS errors | Verificar `ALLOWED_ORIGINS` incluye URL del frontend |
| UnicodeEncodeError Windows | Ejecutar con `PYTHONUTF8=1` |
| Usuarios de test | `python scripts/seed_test_users.py` |

## Licencia

MIT License

## Disclaimer Legal

Impuestify es una herramienta de asistencia informativa. **No constituye asesoramiento fiscal profesional.** Siempre consulta con un asesor fiscal cualificado para decisiones importantes.

---

**Fernando Prada** — [impuestify.com](https://impuestify.com)
