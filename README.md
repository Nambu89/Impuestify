<div align="center">

# Impuestify

### Tu copiloto fiscal con IA para España

[![Tests](https://img.shields.io/badge/tests-1800%2B%20passing-brightgreen)](https://impuestify.com)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/react-18-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/typescript-5-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Deploy](https://img.shields.io/badge/railway-deployed-blueviolet?logo=railway)](https://railway.app)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Asistente fiscal inteligente** con RAG, multi-agente y motor anti-alucinación.
Cubre los **21 territorios fiscales** de España: 15 CCAA + 4 forales + Ceuta + Melilla.

[Probar ahora](https://impuestify.com) &nbsp;&bull;&nbsp; [Documentación](#quick-start) &nbsp;&bull;&nbsp; [Arquitectura](#arquitectura)

</div>

---

## Qué hace Impuestify

- **Asistente fiscal conversacional** con GPT-5-mini + RAG sobre 463 documentos oficiales (AEAT, BOE, Diputaciones Forales)
- **Simulador IRPF** completo: 8 sub-calculadoras, tributación conjunta, regímenes forales, ~1.008 deducciones
- **DefensIA** — defensor fiscal automatizado con motor híbrido anti-alucinación
- **Clasificador de facturas** con Gemini 3 Flash Vision OCR ($0,0003/factura)
- **Contabilidad PGC** automática: asientos, Libro Diario, Mayor, Balance, PyG
- **Modelo 200 IS** — simulador Impuesto sobre Sociedades para SL/SA
- **6 calculadoras públicas** sin registro: sueldo neto, retenciones, umbrales, obligaciones, borrador
- **13 capas de seguridad**: desde rate limiting hasta LlamaGuard4

---

## Funcionalidades

### Sistema Multi-Agente

- **CoordinatorAgent** — Router inteligente que decide qué agente usar
- **TaxAgent** — IRPF, IVA, IS, cuotas autónomos, deducciones, Modelo 200
- **PayslipAgent** — Análisis de nóminas (13 patrones regex)
- **NotificationAgent** — Análisis de notificaciones PDF de la AEAT
- **WorkspaceAgent** — Gestión de documentos fiscales del usuario

### 13 Herramientas Fiscales (Tools)

- `simulate_irpf` — Simulación completa con auto-descubrimiento de deducciones
- `simulate_is` — Simulación Impuesto sobre Sociedades (7 territorios)
- `calculate_irpf` — Cálculo por tramos y CCAA
- `calculate_autonomous_quota` — Cuotas autónomos 2025 (15 tramos RDL 13/2022)
- `search_tax_regulations` — Búsqueda FTS5 + BM25 en 463+ documentos oficiales
- `discover_deductions` — ~1.008 deducciones (21 territorios al 100%)
- `compare_joint_individual` — Comparativa tributación conjunta vs individual
- `iae_lookup` — Búsqueda epígrafe IAE para creadores
- `lookup_casilla` — Búsqueda casillas Modelo 100 (2.064 casillas)
- `calculate_modelo_303` — IVA trimestral
- `calculate_modelo_130` — Pago fraccionado IRPF autónomos
- `calculate_modelo_ipsi` — IPSI Ceuta/Melilla (6 tipos)
- `calculate_isd` — Impuesto sobre Sucesiones y Donaciones (21 CCAA)

### DefensIA — Defensor Fiscal Automatizado

Motor híbrido anti-alucinación para reclamaciones tributarias:

- **Extracción** con Gemini (9 extractores especializados) + detector de fase procesal (12 estados)
- **30 reglas deterministas** (R001-R030) validadas contra jurisprudencia
- **RAG verificador** con legislación y doctrina fiscal
- **Redactor LLM controlado** con 9 plantillas Jinja2 (reposicion, TEAR abreviado/general, alegaciones...)
- **Export** a DOCX y PDF con disclaimer legal obligatorio
- **Tributos**: IRPF, IVA, ISD, ITP, Plusvalía Municipal
- **Procedimientos**: verificación, comprobación limitada, sancionador
- **Vías**: reposición, TEAR abreviado, TEAR general
- **379 tests** en la suite DefensIA

### Modelo 200 — Impuesto sobre Sociedades

- Simulador IS para SL, SA y empresas de nueva creación
- **7 territorios**: régimen común + 4 forales + ZEC + Ceuta/Melilla
- Pagos fraccionados Modelo 202 (Art. 40 LIS)
- Integración con workspace: auto-fill desde PyG contable
- PDF borrador con 16 casillas principales
- **47 tests** en la suite IS

### Simulador IRPF

- 8 sub-calculadoras: trabajo, ahorro, inmuebles, MPYF, actividades, renta imputada, pérdidas, crypto FIFO
- Tributación conjunta, foral (vasco 7 + navarra 11 tramos), Ceuta/Melilla 60%
- Endpoint REST: `POST /api/irpf/estimate` — sin LLM, ~50-100ms
- XSD Modelo 100: ~100% cobertura

### Motor de Deducciones (~1.008)

- 16 estatales + 195 territoriales + 339 XSD + 408 CCAA 2025 + 50 forales
- 21/21 territorios cubiertos al 100%
- `simulate_irpf` encadena automáticamente `discover_deductions`

### Clasificador de Facturas

- OCR con Gemini 3 Flash Vision ($0,0003/factura)
- Clasificación automática PGC (201 cuentas, 7 grupos)
- Asientos contables en partida doble
- Libros: Diario, Mayor, Balance, Pérdidas y Ganancias
- Export CSV/Excel para Registro Mercantil
- 5 tipos: autónomo, creador, farmacia (multi-IVA + RE), simplificada, intracomunitaria

### Calculadoras Públicas

- **Sueldo Neto** (`/calculadora-neto`) — 5 regímenes fiscales
- **Retenciones IRPF** (`/calculadora-retenciones`) — Algoritmo oficial AEAT 2026
- **Umbrales Contables** (`/calculadora-umbrales`) — PGC Normal vs PYMES
- **Obligaciones Fiscales** (`/modelos-obligatorios`) — Modelos por perfil y CCAA
- **Obligado a Declarar** (`/obligado-declarar`) — Art. 96 LIRPF
- **Checklist Borrador** (`/checklist-borrador`) — Verificación pre-declaración

### Guía Fiscal Adaptativa

- **Particular** (7 pasos) — Personal, Trabajo, Ahorro, Inmuebles, Familia, Deducciones, Resultado
- **Creator** (8 pasos) — + Plataformas, IAE, IVA intracomunitario, M349, DAC7
- **Autónomo** (8 pasos) — + Actividad económica, cuota SS, retenciones, M130

---

## Planes y Precios

| Plan | Precio | Audiencia | Destacado |
|:-----|:-------|:----------|:----------|
| **Particular** | 5 EUR/mes | Asalariados, pensionistas | IRPF, nóminas, deducciones básicas |
| **Autónomo** | 39 EUR/mes IVA incl. | Trabajadores por cuenta propia | + Todos los modelos (303/130/131), crypto, workspace, calendario |
| **Creator** | 49 EUR/mes | Influencers, YouTubers, streamers | + IVA por plataforma, M349, DAC7, CNAE 60.39, perfiles multi-rol |

Stripe Checkout + Customer Portal. Sin permanencia.

---

## Arquitectura

<details>
<summary>Ver diagrama completo</summary>

```
+------------------------------------------------------------+
|                       Frontend                             |
|  React 18 + Vite + TypeScript                              |
|                                                            |
|  /chat             SSE streaming conversacional            |
|  /guia-fiscal      Tax Guide Wizard + LiveEstimatorBar     |
|  /clasificador     Invoice OCR + PGC classification        |
|  /contabilidad     Libro Diario/Mayor/Balance/PyG          |
|  /defensia         Wizard reclamaciones + export DOCX/PDF  |
|  /modelo-200       Simulador IS + PDF borrador             |
+---------------------------+--------------------------------+
                            |
                            v  JWT + Rate Limit + 13 Security Layers
+------------------------------------------------------------+
|                    FastAPI Backend                          |
|                                                            |
|  +--------------------------------------------------+     |
|  |           CoordinatorAgent (Router)               |     |
|  +----+--------+----------+----------+---------+----+     |
|       |        |          |          |         |          |
|  +----v---+ +--v-----+ +-v------+ +-v------+            |
|  |  Tax   | |Payslip | | Notif. | |Workspace|            |
|  | Agent  | | Agent  | | Agent  | | Agent   |            |
|  +--------+ +--------+ +--------+ +---------+            |
|                                                            |
|  +--------------------------------------------------+     |
|  |              DefensIA Engine                      |     |
|  |  Extraccion Gemini -> Reglas R001-R030 ->         |     |
|  |  RAG Verificador -> Redactor LLM (Jinja2)        |     |
|  +--------------------------------------------------+     |
|                                                            |
|  +--------------------------------------------------+     |
|  |              Modelo 200 IS Engine                 |     |
|  |  Simulador 7 territorios + Modelo 202 + PDF      |     |
|  +--------------------------------------------------+     |
|                                                            |
|  13 Tools + Gemini OCR + Contabilidad Service             |
+------------------------------------------------------------+
       |          |          |         |          |
       v          v          v         v          v
  +--------+ +--------+ +------+ +-------+ +--------+
  | Turso  | |Upstash | |OpenAI| |Stripe | | Gemini |
  | SQLite | | Redis  | | LLM  | |Payments| | OCR   |
  +--------+ +--------+ +------+ +-------+ +--------+
```

</details>

### Stack Tecnológico

**Backend:** FastAPI, Python 3.12+, Turso (SQLite), Upstash Redis/Vector, OpenAI GPT-5-mini, Google Gemini 3 Flash, Groq (LlamaGuard4), Stripe, Resend

**Frontend:** React 18, Vite 5, TypeScript, React Router, Lucide React, Recharts, vanilla-cookieconsent v3

**Infra:** Railway (auto-deploy), Cloudflare (DNS + Turnstile CAPTCHA), GitHub (Copilot code review instructions)

### RAG Pipeline

- **463 documentos** oficiales (AEAT, BOE, Diputaciones Forales)
- **92.393 chunks**, **85.587 embeddings** (text-embedding-3-large)
- FTS5 + búsqueda semántica híbrida
- Crawler automatizado: 90 URLs, 23 territorios, Scrapling anti-bot

---

## Seguridad (13 capas)

<details>
<summary>Ver las 13 capas de seguridad</summary>

1. **Rate Limiting** — SlowAPI + Upstash Redis
2. **Security Headers** — CSP, X-Frame-Options, XSS, Referrer-Policy
3. **JWT Auth** — Access + refresh tokens
4. **Cloudflare Turnstile** — CAPTCHA en Login + Register
5. **MFA / 2FA** — TOTP + backup codes
6. **Prompt Injection** — Llama Prompt Guard 2 via Groq
7. **PII Detection** — DNI/NIE, telefonos, emails, cuentas bancarias
8. **SQL Injection** — Consultas parametrizadas + deteccion OWASP
9. **Content Moderation** — Llama Guard 4, 14 categorias
10. **Content Restriction** — Contenido autónomo bloqueado para plan Particular
11. **Semantic Cache** — Upstash Vector, umbral 0,93, TTL 24h
12. **Guardrails** — Validación input/output
13. **Audit Logger** — Registro inmutable

</details>

---

## Quick Start

### Requisitos previos

- Python 3.12+
- Node.js 18+
- API Keys: OpenAI, Turso, Upstash, Groq, Stripe, Resend, Google Gemini

### 1. Clonar y configurar variables de entorno

```bash
git clone https://github.com/Nambu89/Impuestify.git
cd Impuestify
cp .env.example .env
# Editar .env con tus API keys (ver .env.example para la lista completa)
```

### 2. Backend

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

### 3. Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Testing

```bash
# Backend (~1.800+ tests, incluye 379 DefensIA + 47 IS)
cd backend && pytest tests/ -v

# Frontend (build check)
cd frontend && npm run build

# E2E Playwright
npx playwright test tests/e2e/
```

<details>
<summary>Usuarios de test</summary>

| Email | Password | Plan |
|:------|:---------|:-----|
| `test.particular@impuestify.es` | `Test2026!` | particular |
| `test.autonomo@impuestify.es` | `Test2026!` | autonomo |
| `test.creator@impuestify.es` | `Test2026!` | creator |

Seed: `cd backend && python scripts/seed_test_users.py`

</details>

---

## Screenshots

> *Próximamente: capturas de la interfaz principal, DefensIA wizard, clasificador de facturas y dashboard contable.*

---

## Deployment

Railway auto-deploy en cada push a `main`. Dos servicios:

- **Backend**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
- **Frontend**: `npm run build && npx vite preview --host 0.0.0.0 --port $PORT`

<details>
<summary>Troubleshooting</summary>

| Problema | Solución |
|:---------|:---------|
| Backend no conecta a Turso | Verificar `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN` |
| Escala IRPF no encontrada | `python scripts/seed_estatal_scale.py` |
| Deducciones vacías | `python scripts/seed_deductions.py` + `seed_deductions_territorial.py` |
| PGC cuentas vacías | `python scripts/seed_pgc_accounts.py` |
| Clasificador facturas 503 | Verificar `GOOGLE_GEMINI_API_KEY` |
| Upload timeout | El OCR Gemini tarda 30-60s, timeout configurado a 120s |
| CORS errors | Verificar `ALLOWED_ORIGINS` incluye URL del frontend |
| UnicodeEncodeError Windows | Ejecutar con `PYTHONUTF8=1` |

</details>

---

## Contribuir

1. Fork del repositorio
2. Crear rama: `git checkout -b feat/mi-feature`
3. Seguir las convenciones de naming (ver `CLAUDE.md`)
4. Asegurar que pasan los tests: `pytest tests/ -v` + `npm run build`
5. Pull request contra `main`

El proyecto incluye instrucciones de code review para GitHub Copilot en `.github/copilot-instructions.md`.

---

## Disclaimer Legal

Impuestify es una herramienta de asistencia informativa. **No constituye asesoramiento fiscal profesional.** Siempre consulta con un asesor fiscal cualificado para decisiones importantes.

---

<div align="center">

**[impuestify.com](https://impuestify.com)**

Desarrollado por **Fernando Prada**

MIT License

</div>
