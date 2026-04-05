# TaxIA (Impuestify) — Decisions Log (ADR)

> Architecture Decision Records del proyecto. Cada decision importante se documenta aqui para referencia futura.

---

## ADR-001: Migracion de subagents/ a agents/ con YAML frontmatter
- **Fecha**: 2026-03-05
- **Estado**: Aceptada
- **Contexto**: El sistema multi-agente original usaba `.claude/subagents/` con archivos markdown planos. El patron de referencia de [claude-code-best-practice](https://github.com/shanraisshan/claude-code-best-practice) recomienda `.claude/agents/` con YAML frontmatter para habilitar Agent Teams features (nombre, tools, modelo, permisos, skills).
- **Opciones consideradas**:
  1. Mantener subagents/ tal cual — Sin YAML frontmatter, sin metadata estructurada
  2. Migrar a agents/ con frontmatter — Estructura Command -> Agent -> Skill
- **Decision**: Migrar a `.claude/agents/` con YAML frontmatter. Mantener `.claude/subagents/` temporalmente para backward compatibility.
- **Consecuencias**:
  - 7 archivos de agente en `.claude/agents/` (6 migrados + 1 nuevo PM)
  - Los commands (`/backend`, `/frontend`, etc.) apuntan ahora a `.claude/agents/`
  - Contenido de cada agente preservado intacto, solo se anade frontmatter

## ADR-002: Nuevo agente PM Coordinator
- **Fecha**: 2026-03-05
- **Estado**: Aceptada
- **Contexto**: Faltaba un agente con vision estrategica del proyecto completo. Terminal 7 (Coordinacion) era generico. Se necesita un Project Manager que pueda investigar, delegar, gestionar roadmap y documentar decisiones.
- **Opciones consideradas**:
  1. Mantener Terminal 7 generico — Sin rol definido
  2. Crear PM Coordinator con skills de research y roadmap — Rol completo de PM
- **Decision**: Crear `pm-coordinator` con skills `project-research` y `roadmap-manager`. Usa WebFetch, WebSearch, Read, Write, Edit, Bash, Task.
- **Consecuencias**:
  - Nuevo comando `/pm` para activar el coordinador
  - `plans/DECISIONS.md` (este archivo) como log de decisiones
  - Workflow RPI (Research -> Plan -> Implement) formalizado

## ADR-003: Estructura de Skills con subdirectorios SKILL.md
- **Fecha**: 2026-03-05
- **Estado**: Aceptada
- **Contexto**: Las skills existentes eran archivos planos en `.claude/skills/`. El patron de referencia recomienda subdirectorios con `SKILL.md` para progressive disclosure y mejor organizacion.
- **Opciones consideradas**:
  1. Mantener skills como archivos planos — Mas simple, funcional
  2. Nuevas skills con subdirectorios, existentes intactas — Hibrido pragmatico
- **Decision**: Las 2 nuevas skills (`project-research`, `roadmap-manager`) usan subdirectorios con `SKILL.md`. Las 6 skills existentes se mantienen como estan (funcionan bien).
- **Consecuencias**:
  - Coexisten ambos formatos: `skills/irpf-calculation.md` y `skills/project-research/SKILL.md`
  - Se migraran las existentes cuando se haga mantenimiento

## ADR-004: Agente QA Tester con Playwright (MCP + Scripts)
- **Fecha**: 2026-03-05
- **Estado**: Aceptada
- **Contexto**: Necesitamos probar la app como un usuario real en dos perfiles (particular y autonomo), detectar bugs, problemas UX y generar reportes para el PM. La app tiene chat SSE, JWT auth, export PDF, cookies consent y panel admin.
- **Opciones consideradas**:
  1. Solo Playwright MCP Server — Interaccion en vivo via MCP, sin tests reutilizables
  2. Solo scripts Playwright — Tests `.spec.ts` ejecutables, sin interaccion en vivo
  3. Hibrido: MCP Server + Skill con scripts — Lo mejor de ambos mundos
- **Decision**: Enfoque hibrido. Playwright MCP Server (`@playwright/mcp@latest`) para exploracion en vivo y debugging visual. Skill `playwright-testing` con patrones para generar tests `.spec.ts` reutilizables en `tests/e2e/`.
- **Consecuencias**:
  - Nuevo agente `qa-tester` con comando `/qa`
  - Configuracion MCP en `.mcp.json` (raiz del proyecto)
  - Directorio `tests/e2e/` para tests reutilizables
  - Reportes QA en `plans/qa-report-YYYY-MM-DD.md`
  - 10 flujos de test definidos (T01-T10) cubriendo landing, auth, chat SSE, export, workspace, cookies, admin

## ADR-005: Calculadora ISD (Sucesiones y Donaciones)
- **Fecha**: 2026-03-06
- **Estado**: En desarrollo
- **Contexto**: El roadmap marca ISD como PRIORIDAD ALTA. Los usuarios preguntan sobre donaciones (ej: madre dona 60.000 EUR para vivienda en Aragon) y el sistema no puede calcular. Cada CCAA tiene bonificaciones muy diferentes (Madrid 99%, Aragon 99% para < 500k, PV casi exento).
- **Opciones consideradas**:
  1. Solo RAG (respuestas informativas sin calculo) — Insuficiente
  2. Tool de calculo completa con tarifa estatal + bonificaciones CCAA — Mejor UX
- **Decision**: Crear `isd_calculator_tool.py` con tarifa estatal (Art. 21 Ley 29/1987), coeficientes multiplicadores, y bonificaciones de al menos 8 CCAA + 4 forales. Integrar con TaxAgent.
- **Consecuencias**:
  - Nueva tool `calculate_isd` registrada en `tools/__init__.py`
  - Cubre donaciones y sucesiones
  - Variaciones por CCAA y grupo de parentesco
  - Se complementa con RAG para explicaciones detalladas

## ADR-006: Expansion deducciones territoriales a 17 CCAA
- **Fecha**: 2026-03-06
- **Estado**: En desarrollo
- **Contexto**: Tenemos 48 deducciones de 8 CCAA. TaxDown tiene 250+ (motor Rita). Para competir necesitamos cubrir las 17 CCAA. Las 9 CCAA faltantes (Galicia, Asturias, Cantabria, La Rioja, Aragon, CyL, CLM, Extremadura, Murcia, Baleares, Canarias) tienen entre 5-15 deducciones cada una.
- **Decision**: Crear `seed_deductions_territorial_v2.py` con ~55-60 deducciones nuevas. Objetivo: pasar de 64 a ~120+ deducciones totales.
- **Consecuencias**:
  - Cobertura completa de todas las CCAA de Espana
  - Argumento comercial: "Cubre TODAS las comunidades autonomas"
  - Mas cerca de paridad con TaxDown (250+)

## ADR-007: Landing pages SEO para territorios especiales
- **Fecha**: 2026-03-06 | **Actualizado**: 2026-03-07
- **Estado**: Completada
- **Contexto**: TaxDown NO cubre forales (~1.6M declarantes). Canarias tiene regimen fiscal unico (IGIC, ZEC, RIC). Necesitamos captar estos segmentos con paginas SEO optimizadas.
- **Decision**: 3 landings publicas: `/territorios-forales`, `/ceuta-melilla`, `/canarias`. Hero images 4K generadas con Nano Banana (Gemini 3 Pro). Disenos UI validados con Google Stitch. Tablas comparativas vs competencia.
- **Herramientas usadas**: Nano Banana MCP (3 hero images 4K), Google Stitch MCP (4 screens mobile+desktop)
- **Consecuencias**:
  - 3 rutas publicas en App.tsx (sin auth) con SEO meta tags
  - Hero sections con fondo oscuro (#0f172a) + ilustraciones isometricas 4K
  - Territory chips clickables en Home.tsx (6 territorios enlazados)
  - Footer con links a las 3 paginas territoriales
  - CanariasPage: 8 secciones (hero, ventajas IGIC/ZEC/RIC/IRPF, tabla comparativa, ZEC steps, tool comparison, FAQ, CTA)
  - Pendiente: comprimir imagenes para produccion (actualmente 7-8MB)

## ADR-008: Push Notifications en PWA
- **Fecha**: 2026-03-09
- **Estado**: Propuesta (pendiente aprobacion)
- **Contexto**: Impuestify necesita notificar a usuarios sobre plazos AEAT, nuevos documentos del crawler, y cambios normativos. La app ya es PWA con SW manual (`public/sw.js`) para caching. Falta el componente push.
- **Opciones consideradas**:
  1. **pywebpush** (v2.3.0) — Maduro, Critical Project PyPI, 1 call API, mas dependencias legacy
  2. **webpush** (v1.0.6) — Moderno, tipado Pydantic, menos deps, pero nuevo y menos probado
  3. **Firebase Cloud Messaging (FCM)** — Vendor lock-in, SDK pesado, overkill para nuestro volumen
- **Decision**: `pywebpush` para envio + APScheduler para scheduling + hook custom React + extender SW existente
- **Justificacion**: pywebpush es el estandar de facto, proyecto critico PyPI con auditorias. APScheduler evita infra extra (ya corremos en Railway). El SW existente solo necesita 2 event listeners nuevos (push + notificationclick).
- **Consecuencias**:
  - Nueva tabla `push_subscriptions` en Turso (endpoint, p256dh, auth, user_id)
  - 2 endpoints: POST /api/push/subscribe, DELETE /api/push/unsubscribe
  - VAPID keys en .env (VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CONTACT)
  - Hook `usePushNotifications.ts` en frontend
  - Pre-prompt UX (no pedir permiso en primera visita)
  - iOS requiere PWA instalada en Home Screen para recibir push
  - Estimacion: 7-11h de desarrollo total

## ADR-007: Evaluación Coolify como alternativa a Railway
- **Fecha**: 2026-03-28
- **Estado**: Rechazada (reevaluar cuando Railway >50 €/mes)
- **Contexto**: Railway auto-deploy estuvo roto varias sesiones. Se evaluó migrar a Coolify (PaaS open-source self-hosted en VPS propio) para reducir costes y eliminar dependencia de Railway.
- **Opciones consideradas**:
  1. **Coolify self-hosted en Hetzner CPX32** (8 GB, ~13 €/mes) — Ahorro 35-87 %, Docker Compose nativo, GitHub Apps auto-deploy, SSL automático, cero vendor lock-in
  2. **Mantener Railway** (~20-100 €/mes) — Zero ops, managed, SLA implícito, auto-deploy ya arreglado
  3. **Coolify Cloud** ($5/mes + VPS) — Coolify gestionado por ellos, pero mismo VPS propio
- **Decisión**: Mantener Railway. No migrar a Coolify por ahora.
- **Justificación**:
  - **11 CVEs críticos en enero 2026** (CVSS 9.4-10.0): bypass auth, RCE, container escape. Inaceptable para app fiscal con datos sensibles (DNI, IBAN, importes)
  - **Coolify sigue en beta** (v4.0.0-beta). v5 rewrite al 0 % sin fecha
  - **Ahorro marginal a uso bajo**: ~7 €/mes de ahorro no compensa el overhead operacional (OS updates, security patches, incidentes)
  - **Equipo de 1 persona**: tiempo en DevOps = tiempo que no se invierte en producto
  - **Railway auto-deploy ya arreglado**: el bloqueador principal ya no existe
- **Condiciones para reevaluar**:
  - Railway supere 50 €/mes de forma consistente (3+ meses)
  - Coolify salga de beta (v4 estable o v5)
  - Equipo crezca a 2+ desarrolladores
- **Datos de la investigación**:
  - Coolify: 52K+ GitHub stars, 555+ contributors, 20K+ Discord
  - VPS recomendado: Hetzner CPX32 (4 vCPU, 8 GB RAM) ~13 €/mes
  - Coolify consume ~1 GB RAM solo, necesita mínimo 8 GB para nuestro stack
  - Turso, Upstash, Stripe, OpenAI, Groq no cambiarían (SaaS externos)
  - Migración estimada: ~2-4 horas + Dockerfiles + docker-compose.yml

## ADR-009: Gemini 3 Flash para OCR de facturas de usuario (Phase 3)
- **Fecha**: 2026-04-05
- **Estado**: Aceptada
- **Contexto**: Phase 3 del roadmap de contabilidad necesita un motor OCR para que los usuarios suban facturas y el sistema las clasifique en el PGC. Azure Document Intelligence (prebuilt-invoice) era la opcion inicial, pero escala con el numero de usuarios ($0.01/factura). Se necesita una alternativa economica para uso recurrente. Azure DI se mantiene para ingesta RAG interna (gasto puntual, no recurrente).
- **Opciones consideradas**:
  1. **Azure DI prebuilt-invoice** — $0.01/factura, 96% accuracy, campos pre-entrenados. Ya configurado. Caro a escala.
  2. **Gemini 3 Flash Vision** — $0.0003/factura (~33x mas barato), 95% accuracy, JSON estructurado nativo, soporta PDF directo. Preview pero GA inminente.
  3. **GPT-5-mini Vision** — $0.0007/factura, ya integrado en el proyecto. Buena opcion pero no abre la puerta a multi-provider.
  4. **Mindee** — $0.08/factura, especializado en facturas. 250 free/mes. Mas caro que LLMs.
  5. **marker-pdf + Surya OCR** — Gratis, open source. No extrae campos estructurados de facturas.
- **Decision**: Gemini 3 Flash Vision (`gemini-3-flash-preview`) como motor primario de extraccion de facturas de usuario. SDK: `google-genai`. Validacion post-extraccion (NIF checksum + cuadre IVA). Azure DI se mantiene SOLO para ingesta RAG interna.
- **Consecuencias**:
  - Nueva dependencia: `google-genai` en requirements.txt
  - Nueva env var: `GOOGLE_GEMINI_API_KEY` (Vertex AI habilitado)
  - `InvoiceOCRService` usa Gemini en vez de Azure DI
  - Coste estimado: 50 facturas/mes/usuario = ~$0.015/mes (vs $0.50 con Azure DI)
  - Scope ampliado: clasificacion PGC + Libro Diario + Mayor + exportacion Registro Mercantil
  - Riesgo: modelo Preview (mitigar con fallback a gpt-5-mini si falla)

## ADR-010: Contabilidad completa con libros para Registro Mercantil
- **Fecha**: 2026-04-05
- **Estado**: Aceptada
- **Contexto**: Phase 3 originalmente contemplaba solo "libro registro de facturas". El usuario quiere ampliar a contabilidad real: clasificacion PGC, asientos contables, y exportacion de libros oficiales para deposito en el Registro Mercantil.
- **Decision**: Ampliar Phase 3 para incluir:
  1. Clasificacion automatica en cuentas PGC (6xx gastos, 7xx ingresos)
  2. Generacion de asientos contables (Libro Diario)
  3. Libro Mayor (saldos por cuenta)
  4. Balance de Sumas y Saldos
  5. Cuenta de Perdidas y Ganancias
  6. Exportacion CSV/Excel para Registro Mercantil
- **Consecuencias**:
  - Nueva tabla `asientos_contables` (debe/haber por factura)
  - Ampliacion de `pgc_accounts` con cuentas de balance (grupos 1-5), no solo PyG (6-7)
  - Servicio `ContabilidadService` para generacion de libros
  - Frontend: pagina `/contabilidad` con vista de libros + exportacion
  - Disclaimer legal obligatorio: "informacion orientativa, no sustituye a un contable"
