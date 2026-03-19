# Impuestify - Asistente Fiscal Inteligente

Impuestify es un asistente fiscal especializado en normativa española que utiliza **RAG (Retrieval-Augmented Generation)** con **OpenAI GPT-5-mini** para proporcionar respuestas precisas, conversacionales y contextualizadas sobre temas fiscales. Cubre las 17 CCAA, los 4 territorios forales (Araba, Bizkaia, Gipuzkoa, Navarra) y Ceuta/Melilla. Especializado en 3 segmentos: asalariados, creadores de contenido e independientes.

## Caracteristicas Principales

### Sistema Multi-Agente (Microsoft Agent Framework)

- **CoordinatorAgent**: Router inteligente que decide que agente especializado usar
- **TaxAgent**: Experto en fiscalidad general (IRPF, cuotas autonomos, deducciones). Clarificacion obligatoria antes de asumir situacion laboral
- **PayslipAgent**: Especializado en analisis de nominas espanolas
- **NotificationAgent**: Analiza notificaciones PDF de la AEAT
- **WorkspaceAgent**: Gestion de espacios de trabajo con archivos fiscales del usuario

### Herramientas Fiscales (9 tools)

| Tool | Proposito |
|------|-----------|
| `simulate_irpf` | Simulacion completa Phase 1+2 con auto-descubrimiento de deducciones |
| `calculate_irpf` | Calculo exacto de IRPF por tramos y CCAA (compatibilidad retroactiva) |
| `calculate_autonomous_quota` | Cuotas de autonomos segun rendimientos 2025 |
| `search_tax_regulations` | Busqueda FTS5 + BM25 en documentacion oficial AEAT |
| `analyze_payslip` | Analisis completo de nominas con 13 patrones regex |
| `discover_deductions` | 64 deducciones: 16 estatales + 48 territoriales |
| `calculate_modelo_303` | Calculo de casillas IVA trimestral |
| `calculate_modelo_130` | Calculo de pago fraccionado IRPF autonomos |
| `calculate_isd` | Impuesto sobre Sucesiones y Donaciones |

### Simulador IRPF Completo

- Motor de clase `IRPFSimulator` con subcalculadoras especializadas (`WorkIncomeCalculator`, `SavingsIncomeCalculator`, `RentalIncomeCalculator`, `MPYFCalculator`, `TaxParameterRepository`)
- Cobertura completa: 17 CCAA + 4 forales + Ceuta/Melilla
- **Phase 1**: planes de pensiones (Art. 51-52, max 8.500 EUR), hipoteca pre-2013 (DT 18a, 15% max 9.040 EUR), maternidad (Art. 81, 1.200 EUR/hijo menor de 3 + 1.000 guarderia), familia numerosa (Art. 81bis, 1.200/2.400 EUR), donativos (Art. 68.3 + Ley 49/2002)
- **Phase 2**: tributacion conjunta (Art. 84, 3.400/2.150 EUR), alquiler habitual pre-2015 (DT 15a, 10,05%), rentas imputadas inmuebles (Art. 85, 1,1%/2% catastral)
- Deducciones reembolsables vs no reembolsables correctamente diferenciadas
- Endpoint REST: `POST /api/irpf/estimate` — sin LLM, ~50-100ms de latencia
- Los forales (Pais Vasco + Navarra) usan su propio sistema IRPF; no incluyen deducciones estatales

### Guia Fiscal Adaptativa por Rol

- Wizard inteligente en `/guia-fiscal` que adapta pasos y campos segun el plan del usuario:
  - **Particular (7 pasos)**: Personal → Trabajo → Ahorro → Inmuebles → Familia → Deducciones → Resultado
  - **Creator (8 pasos)**: + Step dedicado "Actividad como creador" con grid de 10 plataformas (YouTube, Twitch, TikTok, Instagram, OnlyFans, Patreon...), selector de epigrafe IAE, gastos de creador, info IVA intracomunitario, withholding tax W-8BEN, Modelo 349
  - **Autonomo (8 pasos)**: + Step dedicado "Actividad economica" con ingresos, gastos, cuota SS, retenciones, pagos fraccionados M130
- **Resultado adaptativo**: muestra obligaciones por rol (M349/DAC7 para creators, M130/M303/RETA para autonomos)
- **LiveEstimatorBar**: barra sticky con estimacion en tiempo real (debounce 600ms)
- Persistencia en localStorage via hook `useTaxGuideProgress`

### Calculadora Sueldo Neto Autonomo (NUEVO)

- Pagina dedicada `/calculadora-neto`: **"¿Cuanto te queda limpio?"**
- Input: facturacion bruta mensual → resultado inmediato con desglose visual
- **5 regimenes fiscales** con deteccion automatica por CCAA:
  - Madrid/Andalucia: IVA 21%, escala comun
  - Canarias: IGIC 7% (auto-detectado)
  - Ceuta/Melilla: IPSI 4% + deduccion 60% cuota IRPF (Art. 68.4 LIRPF)
  - Pais Vasco: escala foral propia (7 tramos)
  - Navarra: escala foral propia (11 tramos)
- **Cuota SS auto-calculada** por ingresos reales (15 tramos, RDL 13/2022)
- Desglose: facturacion bruta, IVA/IGIC/IPSI, retencion IRPF, cuota autonomo, gastos, neto mensual y anual
- Barras visuales proporcionales con colores semanticos
- Disclaimer legal en cada respuesta
- 21 tests backend PASS (territoriales + edge cases)

### Motor de Deducciones

- 600+ deducciones totales: 16 estatales + 195 territoriales v1/v2 + 339 XSD oficiales AEAT + 50 forales
- Territorios cubiertos: 17 CCAA + 4 forales (Araba, Bizkaia, Gipuzkoa, Navarra) + Ceuta/Melilla
- XSD Modelo 100: ~100% cobertura (gastos granulares, módulos, royalties, IAE lookup)
- `simulate_irpf` encadena automaticamente `discover_deductions`
- Scripts de seed: `seed_deductions.py`, `seed_deductions_territorial.py`, `seed_deductions_xsd.py`, `seed_forales_v2.py`, `seed_estatal_scale.py`

### Analisis de Nominas

- Upload de PDFs: extrae datos automaticamente con PyMuPDF4LLM
- 13 patrones regex: periodo, salarios, IRPF, SS, extras
- Proyecciones anuales de ingresos y retenciones
- Recomendaciones personalizadas segun rango salarial

### Analisis de Notificaciones AEAT

- Upload de PDFs: analiza notificaciones de la AEAT automaticamente
- Extraccion de importes, plazos y conceptos clave
- Contexto persistente durante toda la conversacion

### Workspaces - Espacios de Trabajo

- Gestion de archivos fiscales: sube facturas, nominas y declaraciones
- Extraccion automatica de facturas: 30+ patrones regex para datos fiscales espanoles
- Embeddings semanticos: OpenAI text-embedding-3-large (3072 dimensiones)
- Busqueda semantica: encuentra informacion relevante en documentos propios
- El asistente conoce tus archivos y responde sobre ellos en el chat

### Suscripciones Stripe

| Plan | Precio | Audiencia | Features |
|------|--------|-----------|----------|
| Particular | 5 EUR/mes | Asalariados, pensionistas | Guía fiscal, análisis nóminas, deducciones básicas |
| Creator | 49 EUR/mes | Influencers, YouTubers, streamers, bloggers | + IVA por plataforma, Modelo 349, DAC7, CNAE 60.39, perfiles multi-rol |
| Autonomo | 39 EUR/mes (IVA incluido) | Trabajadores por cuenta propia | + Todos los modelos (303/130/131), cripto, workspace, calendario |

- Stripe Checkout + Customer Portal integrados
- `ProtectedRoute` con subscription guard automatico
- Owner bypass para el propietario de la cuenta
- Grace period hasta 31/12/2026 para usuarios existentes

### Perfil Fiscal Extendido

- 13 campos autonomo almacenados en JSON `datos_fiscales` (sin migracion de BD)
- Campos Phase 1+2 IRPF: planes pensiones, hipoteca pre-2013, maternidad, familia numerosa, donativos, tributacion conjunta, alquiler pre-2015, rentas imputadas
- Panel de administracion de usuarios: `GET/PUT /api/admin/users` (owner-only)
- `AdminUsersPage`: cards en movil, tabla en escritorio (breakpoint 1024px)

### Export PDF y Email

- Generacion de informes IRPF en PDF via ReportLab
- Envio al asesor via Resend ("Enviar a mi asesor")
- Componente `DeductionCards` en el chat para visualizar deducciones aplicables

### Soporte Ceuta y Melilla

- Deduccion del 60% de la cuota integra IRPF (Art. 68.4 LIRPF)
- Deteccion automatica por `ccaa="Ceuta"/"Melilla"` en el perfil fiscal
- Bonificacion del 50% en cuota SS para autonomos

### Alto Rendimiento

- **Redis Cache**: Upstash para contexto de conversaciones, TTL 1 hora
- **Semantic Cache**: Upstash Vector, umbral 0,93, TTL 24h — reduce costes OpenAI ~30%
- **Complexity Router**: clasifica queries (simple/moderate/complex) para optimizar `reasoning_effort`

### Seguridad Avanzada

| Capa | Descripcion |
|------|-------------|
| Rate Limiting | SlowAPI + Upstash Redis distribuido. 5 violaciones → bloqueo 60 min |
| Security Headers | CSP, X-Frame-Options, XSS Protection, Referrer-Policy |
| JWT Auth | `get_current_user()` → modelo `TokenData` Pydantic |
| Prompt Injection | Llama Prompt Guard 2 via Groq API |
| PII Detection | DNI/NIE, telefonos, emails, cuentas bancarias espanolas |
| Content Moderation | Llama Guard 4 (14 categorias de riesgo), API gratuita Groq |
| Audit Logger | Registro inmutable de eventos de seguridad en formato JSON |

### PWA (Progressive Web App)

- Service worker manual (no vite-plugin-pwa)
- Network-first para llamadas API, cache-first para assets estaticos
- Instalable en movil y escritorio

### Cumplimiento Legal

- vanilla-cookieconsent v3, conforme a AEPD / LSSI-CE / RGPD
- Politica de privacidad, terminos de servicio, transparencia IA (AI Act)
- Derechos RGPD: exportar y eliminar datos desde el perfil
- 428 documentos RAG oficiales (PDFs + Excel) de AEAT y CCAA

## Arquitectura Multi-Agente

```
+------------------+
|    Frontend      |  React 18 + Vite + TypeScript
|  /chat           |  SSE streaming
|  /guia-fiscal    |  Tax Guide Wizard + LiveEstimatorBar
|  /workspaces     |  File management
+--------+---------+
         |
         v  JWT + Rate Limit + Guardrails
+------------------------------------------------------------+
|                  FastAPI Backend                           |
|                                                            |
|  Security Pipeline:                                        |
|  Rate Limit -> Headers -> JWT -> Prompt Inject ->          |
|  PII -> Content Mod -> Semantic Cache -> Guardrails        |
|                                                            |
|  +--------------------------------------------------+     |
|  |           CoordinatorAgent (Router)              |     |
|  |         Microsoft Agent Framework 1.0.0b         |     |
|  +----+------------+------------+----------+--------+     |
|       |            |            |          |              |
|  +----v----+  +----v----+  +---v----+  +---v------+       |
|  | TaxAgent|  |Payslip  |  |Notif.  |  |Workspace |       |
|  |         |  |Agent    |  |Agent   |  |Agent     |       |
|  +---------+  +---------+  +--------+  +----------+       |
|                                                            |
|  +--------------------------------------------------+     |
|  |            9 Tools Fiscales                      |     |
|  |  simulate_irpf   | calculate_irpf               |     |
|  |  discover_deduc. | autonomous_quota             |     |
|  |  modelo_303      | modelo_130                   |     |
|  |  analyze_payslip | calculate_isd                |     |
|  |  search_regulations                             |     |
|  +--------------------------------------------------+     |
+------------------------------------------------------------+
       |          |          |         |          |
       v          v          v         v          v
  +--------+ +--------+ +------+ +-------+ +--------+
  | Turso  | |Upstash | |OpenAI| |Stripe | |Resend  |
  | SQLite | | Redis  | | LLM  | |Payments| |Email  |
  +--------+ +--------+ +------+ +-------+ +--------+
```

### Stack Tecnologico

**Backend:**
- FastAPI (API REST + SSE)
- Microsoft Agent Framework 1.0.0b (orquestacion multi-agente)
- Turso (SQLite distribuido)
- Upstash Redis (cache + rate limiting)
- Upstash Vector (semantic cache)
- OpenAI API (GPT-5-mini / GPT-5, embeddings text-embedding-3-large)
- Groq API (Llama Guard 4 + Prompt Guard — gratuito: 14.400 req/dia)
- PyMuPDF4LLM (extraccion PDF optimizada para LLMs)
- ReportLab (generacion de PDF)
- Stripe (suscripciones y pagos)
- Resend (envio de emails)
- Prometheus + structlog (metricas y logging estructurado)

**Frontend:**
- React 18
- Vite 5 (build tool)
- TypeScript 5.2
- React Router
- Axios (con auto-refresh de token en 401)
- Lucide React (iconos)
- vanilla-cookieconsent v3
- React Bits (componentes: CountUp, GradientText, SpotlightCard, StarBorder, FadeContent)

## Quick Start

### Requisitos Previos

- Python 3.12+
- Node.js 18+
- OpenAI API Key
- Cuenta Turso (base de datos)
- Cuenta Upstash (Redis + Vector) — opcional pero recomendado
- Groq API Key — gratuito, para moderacion de contenido
- Stripe API Key — para suscripciones
- Resend API Key — para envio de emails

### 1. Clonar Repositorio

```bash
git clone https://github.com/Nambu89/Impuestify.git
cd Impuestify
```

### 2. Configurar Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Crea `.env` en la raiz del proyecto:

```bash
# OpenAI
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-5-mini

# Groq (moderacion de contenido, gratuito)
GROQ_API_KEY=gsk_...
ENABLE_CONTENT_MODERATION=true

# Turso Database
TURSO_DATABASE_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your_token

# Upstash Redis (cache + rate limiting)
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token

# Upstash Vector (semantic cache)
UPSTASH_VECTOR_REST_URL=https://your-vector.upstash.io
UPSTASH_VECTOR_REST_TOKEN=your_token
ENABLE_SEMANTIC_CACHE=true
SEMANTIC_CACHE_THRESHOLD=0.93

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here  # openssl rand -hex 32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Stripe (suscripciones)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_PARTICULAR=price_...
STRIPE_PRICE_ID_AUTONOMO=price_...

# Resend (email a asesores)
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=noreply@impuestify.com

# CORS
ALLOWED_ORIGINS=https://your-frontend.railway.app
```

Inicializar base de datos y datos de referencia:

```bash
python scripts/seed_estatal_scale.py
python scripts/seed_deductions.py
python scripts/seed_deductions_territorial.py
```

Iniciar backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Configurar Frontend

```bash
cd frontend
npm install
```

Crea `.env` en `/frontend`:

```bash
VITE_API_URL=http://localhost:8000
```

Iniciar frontend:

```bash
npm run dev
```

La aplicacion estara en `http://localhost:5173`

## Uso

### Registro y Login

1. Accede a `http://localhost:5173`
2. Registra una cuenta nueva (o usa el chat de demo publico)
3. Suscribete al plan adecuado (Particular o Autonomo)
4. Inicia sesion

### Chat Fiscal

El agente responde con tono conversacional citando fuentes oficiales de la AEAT.

```
Usuario: "Soy autonomo en regimen de estimacion directa. ¿Que puedo deducir este trimestre?"

Impuestify: "Para el Modelo 130 de este trimestre, los gastos deducibles
en estimacion directa incluyen: suministros del local (si esta afecto
a la actividad), cuotas a la Seguridad Social (RETA incluida), amortizacion
de equipos, gastos de telefonia proporcionales..."
```

### Guia Fiscal Interactiva

1. Accede a `/guia-fiscal` (requiere autenticacion y suscripcion)
2. Completa los 7 pasos: Personal, Trabajo, Ahorro, Inmuebles, Familia, Deducciones, Resultado
3. La barra inferior muestra la estimacion IRPF en tiempo real mientras rellenas
4. Al finalizar, guarda los datos en tu perfil fiscal para usarlos en el chat

### Analisis de Nominas y Notificaciones

1. Haz clic en el boton de adjuntar en el chat
2. Sube un PDF de nomina o notificacion de la AEAT
3. El sistema extrae automaticamente los datos clave
4. Haz preguntas sobre el documento

### Workspaces

1. Ve a la seccion Workspaces y crea un espacio de trabajo (ej: "Empresa 2025")
2. Sube facturas o documentos fiscales (drag & drop)
3. Selecciona el workspace en el chat y pregunta: "¿Cuanto IVA he pagado este trimestre?"

### Dashboard (Solo Admins)

Accede a `/dashboard` para ver documentos indexados, embeddings, tiempo de respuesta y cache.

### Panel de Administracion (Solo Owner)

Accede a `/admin/users` para gestionar usuarios y planes de suscripcion.

## Deployment en Railway

### Preparacion

El proyecto incluye:
- `railway.toml` — configuracion de servicios
- `.railwayignore` — archivos excluidos
- Scripts de build optimizados

### Configurar Servicios

Railway detecta automaticamente 2 servicios:

**Backend:**
- Root: `/backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Frontend:**
- Root: `/frontend`
- Build: `npm install && npm run build`
- Start: `npm run preview -- --host 0.0.0.0 --port $PORT`

### Variables de Entorno

Anade todas las variables del `.env` en Railway Dashboard para cada servicio. Railway despliega automaticamente en cada push a `main`.

## Seguridad

Impuestify implementa un pipeline de 12 capas de proteccion:

1. **Rate Limiting** — SlowAPI + Upstash Redis. 5 violaciones → bloqueo 60 min
2. **Security Headers** — CSP, X-Frame-Options, XSS Protection, Referrer-Policy
3. **JWT Auth** — tokens de acceso de corta duracion + refresh tokens
4. **Prompt Injection** — Llama Prompt Guard 2 via Groq
5. **PII Detection** — DNI/NIE, telefonos, emails y cuentas bancarias espanolas
6. **SQL Injection** — consultas parametrizadas + deteccion de patrones OWASP
7. **Content Moderation** — Llama Guard 4 (14 categorias de riesgo), falla abierto si Groq no disponible
8. **Complexity Router** — clasifica queries para optimizar `reasoning_effort`
9. **Content Restriction** — contenido autonomo bloqueado para plan Particular
10. **Semantic Cache** — Upstash Vector, umbral 0,93, TTL 24h
11. **Guardrails** — validacion de input/output, prevencion de alucinaciones
12. **Audit Logger** — registro inmutable de eventos de seguridad

Ver [SECURITY.md](SECURITY.md) para mas detalles.

## Testing

### Backend

```bash
cd backend
pytest tests/ -v                         # 1083+ tests PASS
pytest tests/test_security.py -v        # Tests de seguridad
pytest tests/test_deductions.py -v      # Tests motor deducciones (600+ deducciones)
pytest tests/test_workspace_components.py -v  # Workspaces
pytest tests/test_crypto.py -v          # Criptomonedas + trading
pytest tests/test_crawler.py -v         # Doc crawler (50+ tests)
```

### Frontend

```bash
cd frontend
npm run build  # Verifica que compila sin errores TypeScript
# Expected: Build OK
```

## Estructura del Proyecto

```
TaxIA/
+-- backend/
|   +-- app/
|   |   +-- agents/           # Multi-agent system
|   |   |   +-- coordinator_agent.py
|   |   |   +-- tax_agent.py
|   |   |   +-- payslip_agent.py
|   |   |   +-- notification_agent.py
|   |   |   +-- workspace_agent.py
|   |   +-- tools/            # 9 Agent tools
|   |   |   +-- irpf_simulator_tool.py
|   |   |   +-- irpf_calculator_tool.py
|   |   |   +-- deduction_discovery_tool.py
|   |   |   +-- autonomous_quota_tool.py
|   |   |   +-- modelo_303_tool.py
|   |   |   +-- modelo_130_tool.py
|   |   |   +-- isd_calculator_tool.py
|   |   |   +-- payslip_analysis_tool.py
|   |   |   +-- search_tool.py
|   |   +-- services/         # Business logic
|   |   |   +-- deduction_service.py
|   |   |   +-- report_generator.py   # ReportLab PDF
|   |   |   +-- email_service.py      # Resend
|   |   |   +-- workspace_service.py
|   |   |   +-- workspace_embedding_service.py
|   |   |   +-- file_processing_service.py
|   |   |   +-- invoice_extractor.py
|   |   +-- routers/          # API endpoints
|   |   |   +-- auth.py
|   |   |   +-- chat_stream.py        # SSE v3.0
|   |   |   +-- irpf_estimate.py      # POST /api/irpf/estimate
|   |   |   +-- fiscal_profile.py
|   |   |   +-- workspaces.py
|   |   |   +-- subscription.py       # Stripe
|   |   |   +-- export.py             # PDF + email
|   |   |   +-- admin.py              # Owner-only
|   |   +-- security/         # 12-layer security pipeline
|   |   +-- utils/
|   |   |   +-- irpf_simulator.py     # Motor IRPF completo
|   |   +-- database/
|   |       +-- turso_client.py       # Schema + Turso client
|   +-- scripts/              # Seed y mantenimiento
|   |   +-- seed_deductions.py
|   |   +-- seed_deductions_territorial.py
|   |   +-- seed_estatal_scale.py
|   +-- tests/                # Test suite
|   +-- requirements.txt
+-- frontend/
|   +-- src/
|   |   +-- pages/
|   |   |   +-- TaxGuidePage.tsx      # Wizard 7 pasos
|   |   |   +-- AdminUsersPage.tsx
|   |   |   +-- SubscribePage.tsx
|   |   |   +-- WorkspacesPage.tsx
|   |   +-- components/
|   |   |   +-- LiveEstimatorBar.tsx  # Estimacion IRPF en tiempo real
|   |   |   +-- DeductionCards.tsx
|   |   |   +-- ReportActions.tsx
|   |   |   +-- CookieConsent.tsx     # AEPD/RGPD compliant
|   |   +-- hooks/
|   |   |   +-- useIrpfEstimator.ts   # Debounced IRPF calls
|   |   |   +-- useTaxGuideProgress.ts
|   |   |   +-- useSubscription.ts
|   |   |   +-- useFiscalProfile.ts
|   |   +-- components/reactbits/    # CountUp, GradientText, etc.
|   +-- public/
|   |   +-- sw.js                    # Service worker manual (PWA)
|   |   +-- manifest.json
|   +-- package.json
+-- docs/                     # 428 documentos RAG (PDF + Excel)
+-- data/                     # FAISS embeddings, knowledge_updates/
+-- .claude/
|   +-- commands/             # 14 slash commands
|   +-- skills/               # Modulos de conocimiento
|   +-- subagents/            # Personas de agente
+-- memory/                   # Memoria persistente de agentes
+-- agent-comms.md            # Canal de comunicacion inter-agentes
+-- .gitignore
+-- .railwayignore
+-- railway.toml
+-- README.md
```

## v3.3 - Marzo 2026 (Sesion 15)

### Novedades principales

**Guia Fiscal Adaptativa por Rol** — La guia `/guia-fiscal` ahora muestra pasos diferentes segun el plan: Particular (7 pasos simplificados), Creator (8 pasos con grid de plataformas, IAE, IVA intracomunitario, withholding tax, M349, DAC7), Autonomo (8 pasos con actividad economica). Resultado con obligaciones especificas por rol.

**Calculadora Sueldo Neto Autonomo** — Nueva pagina `/calculadora-neto`. La unica calculadora en Espana que cubre automaticamente los 5 regimenes fiscales: comun (IVA 21%), Canarias (IGIC 7%), Ceuta/Melilla (IPSI 4% + deduccion 60%), Pais Vasco (escala foral 7 tramos) y Navarra (11 tramos). Cuota SS auto-calculada por ingresos reales (15 tramos, RDL 13/2022). 21 tests.

**Ruflo v3.5 Integration** — Plataforma de orquestacion multi-agente para el workflow de desarrollo. 10 agentes registrados, 13 hooks lifecycle, memoria semantica HNSW, background daemon workers. Mejora la productividad del equipo de desarrollo.

**Research de Necesidades** — Investigacion exhaustiva de las necesidades de particulares, autonomos y creadores. Cobertura: 70% particular, 60% autonomo, 90% creador.

---

## v3.2 - Marzo 2026 (Sesion 12)

### Novedades principales

**Plan Creator (49 EUR/mes)** — Nuevo segmento para influencers, YouTubers, streamers y bloggers. Contexto TaxAgent especializado: CNAE 60.39, IAE 8690, IVA por plataforma (Google/Meta/YouTube/Twitch), Modelo 349, DAC7. Landing `/creadores-de-contenido` con SEO-GEO.

**Sistema de Feedback Completo** — Widget de rating en chat, ChatRating component, Admin Dashboard (3 nuevas pages: Feedback, Contacto, Dashboard). Dropdown admin en Header.

**XSD Modelo 100 ~100%** — 339 deducciones oficiales AEAT. Cobertura granular de gastos, módulos, royalties, IAE lookup integrado.

**Comparativa Tributación Conjunta** — Tool `compare_joint_individual` para 4 escenarios (individual vs conjunta, ambos). TaxAgent integrado.

**Modelos CCAA-aware** — Modelo 303→300 (Gipuzkoa), F69 (Navarra), 420 IGIC (Canarias), IPSI (Ceuta/Melilla). Labels dinámicos en UI.

**Perfiles Multi-rol Fiscal** — Campo `roles_adicionales` (no excluyentes). Adaptativo por CCAA, REGIMEN. Soporta combinaciones: asalariado+autónomo, creador+particular, etc.

**Push Notifications** — VAPID keys configuradas. Alertas 15d, 5d, 1d antes de plazos fiscales.

**Crawler 90 URLs** — 23 territorios + documentos creadores/influencers. Drift analyzer integrado.

**Fecha Renta Corregida** — 8 de abril 2026 (no 5 de abril). Actualizado en calendario + emails.

---

## v3.0 - Marzo 2026 (Sesion 9-11)

**Simulador IRPF completo** — Motor clase-base con cobertura de todos los territorios espanoles. Phase 1 (pensiones, hipoteca, maternidad, familia numerosa, donativos) y Phase 2 (tributacion conjunta, alquiler pre-2015, rentas imputadas). Endpoint REST sin LLM para respuestas de ~50-100ms.

**Guia Fiscal Interactiva** — Wizard de 7 pasos en `/guia-fiscal` con estimacion IRPF en tiempo real (LiveEstimatorBar), persistencia en localStorage y sincronizacion con el perfil fiscal.

**Motor de Deducciones** — 600+ deducciones totales. `simulate_irpf` encadena automaticamente `discover_deductions`.

**Suscripciones Stripe** — Plan Particular (5 EUR/mes) y Autonomo (39 EUR/mes IVA incluido). Checkout, Customer Portal y subscription guard integrados.

**Perfil Fiscal Adaptativo por CCAA** — 90+ campos dinamicos. Perfil foral con validaciones especializadas.

**Export PDF + Email** — Informes IRPF en PDF via ReportLab. Envio al asesor via Resend.

**Soporte Ceuta/Melilla** — Deduccion del 60% cuota integra automatica.

**PWA** — Service worker manual, instalable en movil y escritorio.

**Cumplimiento legal** — vanilla-cookieconsent v3 (AEPD/LSSI-CE/RGPD).

---

## v2.8 - Workspaces (Enero 2026)

**Workspaces** — Espacios de trabajo por usuario para organizar documentos fiscales con embeddings semanticos y busqueda por similaridad coseno.

| Feature | Tecnologia |
|---------|------------|
| Workspaces CRUD | Turso SQLite |
| File Upload drag & drop | FastAPI + PyMuPDF4LLM |
| Invoice Extractor (30+ regex) | Python regex |
| Embeddings 3072 dim | OpenAI text-embedding-3-large |
| Semantic Search | Cosine similarity, threshold 0.7 |
| Chat Context | WorkspaceAgent |

---

## v2.7 - Security & Optimization (Diciembre 2024)

**Llama Guard 4** — Moderacion de contenido IA (14 categorias de riesgo, API Groq gratuita).

**Semantic Cache** — Cache por similaridad semantica con Upstash Vector, reduce costes OpenAI ~30%.

**Complexity Router** — Clasificacion automatica de queries (simple/moderate/complex) para optimizar reasoning effort.

**Audit Logger** — Registro inmutable de eventos de seguridad en formato JSON.

**PyMuPDF4LLM** — Extraccion de PDF optimizada para LLMs con soporte de tablas y layouts multi-columna.

---

## Contribucion

1. Fork el proyecto
2. Crea una rama: `git checkout -b feature/nueva-feature`
3. Commit: `git commit -m 'feat: descripcion'`
4. Push: `git push origin feature/nueva-feature`
5. Abre un Pull Request

### Convenciones de commits

- `feat:` — nueva funcionalidad
- `fix:` — correccion de bug
- `docs:` — documentacion
- `style:` — formato, no afecta codigo
- `refactor:` — refactorizacion
- `test:` — tests
- `chore:` — mantenimiento

## Troubleshooting

| Problema | Solucion |
|----------|----------|
| Backend no conecta a Turso | Verifica `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN` |
| Redis no funciona | Opcional — el sistema funciona sin el. Verifica `UPSTASH_REDIS_REST_URL` |
| `/api/irpf/estimate` sin datos | Ejecuta los tres scripts de seed en `backend/scripts/` |
| Escala estatal IRPF no encontrada | Ejecuta `python scripts/seed_estatal_scale.py` |
| Frontend no conecta al backend | Verifica `VITE_API_URL` en `.env` y CORS en `backend/app/main.py` |
| Deducciones no aparecen | Ejecuta `seed_deductions.py` y `seed_deductions_territorial.py` |
| CORS errors en produccion | Verifica que `ALLOWED_ORIGINS` incluye la URL del frontend |
| CSP header error (Railway) | El ultimo directive en CSP no debe tener punto y coma final |
| UnicodeEncodeError en Windows | Ejecuta con `PYTHONUTF8=1` (emojis en print() fallan en cp1252) |
| Usuarios de test QA | Ejecuta `python scripts/seed_test_users.py` |

## Monitorización

```bash
# Health check
curl http://localhost:8000/health

# Logs Railway
railway logs

# Logs locales
tail -f logs/taxia.log
```

Metricas Prometheus disponibles en `/metrics`. Logs en formato JSON estructurado via structlog.

---

## Licencia

MIT License — ver archivo `LICENSE` para detalles.

## Disclaimer Legal

Impuestify es una herramienta de asistencia informativa. **No constituye asesoramiento fiscal profesional**. Siempre consulta con un asesor fiscal cualificado para decisiones importantes.

## Soporte

- Issues: [GitHub Issues](https://github.com/Nambu89/Impuestify/issues)
- Discusiones: [GitHub Discussions](https://github.com/Nambu89/Impuestify/discussions)

---

**Fernando Prada - AI Engineer - Senior Consultant**

**Impuestify - Haciendo la fiscalidad espanola mas accesible**
