# AESIA Self-Assessment — Impuestify (mayo 2026)

> Documento de cumplimiento alineado con las Guías Técnicas 13 y 14 de la
> **Agencia Española de Supervisión de la Inteligencia Artificial (AESIA)**,
> publicadas en diciembre 2025, y con el Reglamento (UE) 2024/1689 (EU AI Act).
>
> Estado del documento: **Borrador inicial — primera evaluación**.
> Próxima revisión obligatoria: 2026-11-05 (semestral).

## Identificación del sistema

| Campo | Valor |
|---|---|
| Nombre del sistema | Impuestify |
| Operador / proveedor | Fernando Prada (persona física, próxima constitución SL) |
| Dominio | impuestify.com |
| Versión actual evaluada | sprint-3 main commit `<HASH>` |
| Tipo de sistema IA | Asistente conversacional con RAG + multi-agent |
| Modelo principal | OpenAI GPT-5-mini (alojado por OpenAI, no on-premise) |
| Idioma principal | Español (España) |
| Mercado | España (B2C — particulares, autónomos, creadores de contenido) |

## Clasificación de riesgo (EU AI Act)

**Determinación: NO high-risk.**

Razonamiento:

- Annex III (high-risk) cubre: biometría, infraestructura crítica, educación,
  empleo, servicios esenciales y privados (incluye credit scoring),
  law enforcement, migración, justicia y democracia.
- Impuestify **informa** al usuario sobre fiscalidad para que prepare su
  declaración manualmente. **No decide** elegibilidad de crédito, no
  evalúa solvencia, no autoriza pagos, no dicta resoluciones.
- El usuario revisa y firma su declaración con AEAT. Impuestify es una
  herramienta de cálculo + búsqueda asistida, equivalente a una
  calculadora avanzada con explicaciones.

**Aplican obligaciones de transparencia (Art. 50 EU AI Act)** al ser un
sistema conversacional con humanos:
- Informar al usuario que interactúa con un sistema de IA.
- Etiquetar contenido generado por IA.
- Disclaimers visibles ante consejos potencialmente delicados.

## AESIA Guía 14 — Plan de cumplimiento por capítulo

### 1. Gestión del riesgo

| Riesgo identificado | Probabilidad | Severidad | Mitigación implementada | Estado |
|---|---|---|---|---|
| Hallucination de citas legales | Media | Alta (consejo fiscal incorrecto) | Citation verifier (sprint 1 #4) flagrea citas no presentes en RAG | ✅ |
| Prompt injection (role hijack) | Alta | Media | Pipeline 6 capas (regex + Llama Prompt Guard + topic classifier) | ✅ |
| Indirect injection vía docs RAG poisoned | Media | Alta | Spotlighting + trust_level tags + ingest sanitize (sprint 1) | ✅ |
| Multi-turn jailbreak (Crescendo) | Baja | Media | Trajectory analyzer (sprint 2 #3) | ✅ |
| Cost runaway (LLM10) | Baja | Media | Token budget per user + cost anomaly alert (sprint 1+2) | ✅ |
| Robo de tokens / sesión | Baja | Alta | Refresh token rotation + reuse detection (sprint 3 #2) | ✅ |
| Filtrado de PII en chat | Media | Alta | PII detector pre-LLM (Llama Guard S7) | ✅ |
| Caída del servicio (DoS) | Media | Media | SlowAPI rate limiting + Cloudflare Turnstile + velocity check (sprint 3 #6) | ✅ |
| RAG drift (calidad respuestas baja) | Media | Media | RAGAS daily eval + email alert (sprint 3 #3) | ✅ |
| Datos personales no borrados (RGPD) | Baja | Alta | GDPR cascading delete en `user_rights.py` | ✅ |

Revisión semestral del registro de riesgos. Owner anota nuevos riesgos
detectados en `memory/incidents/`.

### 2. Gobernanza de datos

**Datos de entrenamiento:** ninguno. No fine-tuneamos modelos. Usamos
modelos genéricos de OpenAI (GPT-5-mini) y Groq (Llama Guard, Llama Prompt
Guard, llama-3.1-8b-instant).

**Datos de RAG:**
- 463 documentos, 92 393 chunks, 85 587 embeddings.
- Fuentes oficiales (AEAT, BOE, normativa foral, normativa autonómica)
  trazables vía `documents.trust_level`.
- Sanitización en ingesta (sprint 1 #2): NFKC + zero-width strip + control
  chars antes de embedding.
- Backfill manual para 463 docs ejecutado 2026-05-05.

**Datos de usuario (interacciones):**
- Conversaciones almacenadas en Turso (cifrado en reposo gestionado por Turso).
- `reasoning_trails` con qué chunks/tools/security se usaron por respuesta
  — retención 24 meses (sprint 2 #5).
- PII en chat: pipeline rechaza preguntas con DNI/IBAN antes del LLM.
- Documentos workspace del usuario (facturas, nóminas): cifrados con
  AES-GCM (DefensIA storage), retención según preferencia del usuario.

**Derecho de borrado RGPD Art. 17:**
- Endpoint `/user-rights/delete-account` con cascade en users + sessions
  + conversations + workspace_files + reasoning_trails.

### 3. Documentación técnica

Documentos vivos:
- `CLAUDE.md` — visión general del sistema.
- `backend/CLAUDE.md` — arquitectura backend, agentes, tools, DB schema.
- `frontend/CLAUDE.md` — arquitectura frontend, hooks, componentes.
- ADRs en `docs/adr/` para decisiones arquitectónicas.
- `docs/incident-response/nis2-runbook.md` — respuesta a incidentes.
- Este documento — self-assessment AESIA.

Trazabilidad código:
- Repo público `github.com/Nambu89/Impuestify`.
- Commits firmados (TODO: pendiente activar GPG signing en commits).
- CI: security.yml (Bandit + Semgrep + pip-audit + npm audit + Trivy + ZAP).

### 4. Mantenimiento de registros (logs)

| Log | Destino | Retención | Contiene |
|---|---|---|---|
| HTTP access logs | Railway | Según plan Railway (~7 días) | Request lines, no body |
| Audit log seguridad | `app.security.audit_logger` (JSONL) | 24 meses | Login fails, security_pipeline blocks, PII detection |
| `reasoning_trails` | Turso | 24 meses (purge cron) | rag_chunks IDs, tools called, security layer outcome, fiscal profile snapshot (whitelist) |
| `usage_metrics` | Turso | Indefinido (admin dashboard) | tokens, model, costs |
| Mail outgoing | Resend dashboard | Según plan Resend | Subject + recipients |

### 5. Transparencia hacia el usuario

Implementado:
- Banner persistente en `/chat` (sprint 1 #6): "Impuestify usa IA. Las
  respuestas son orientativas y no sustituyen al asesoramiento de un
  profesional. Reglamento UE de IA, Art. 50."
- `aria-label="Respuesta generada por IA"` en cada mensaje del asistente.
- Disclaimer al final de cada respuesta del LLM (system prompt regla):
  "Cálculo orientativo — consulta con un asesor para tu caso concreto."
- Citation verifier añade footer "No he podido verificar esta cita en mis
  fuentes — contrasta con el BOE" cuando la cita no está en RAG (sprint 1 #4).

Pendiente:
- [ ] Página `/transparencia-ia` con detalles del sistema (qué modelos
      usamos, fuentes RAG, política de retención, derecho de explicación).

### 6. Supervisión humana (human oversight)

**Modelo: human-in-the-loop, no human-out-of-the-loop.**

- Usuario decide qué hacer con la respuesta. Impuestify NO presenta
  declaraciones a la AEAT por su cuenta.
- Owner monitoriza el sistema vía:
  - Dashboard admin `/admin` (KPIs uso).
  - Dashboard `/admin/rag-quality` (métricas faithfulness, etc.).
  - Email alerts de cost anomaly (sprint 2 #4).
  - Email alerts de RAG quality breach (sprint 3 #3).
  - Email alerts de token reuse detection (sprint 3 #2).
  - Promptfoo CI nightly red-team (sprint 2 #1).
  - Feedback rating en chat → AdminFeedbackPage.

**Right-to-explanation (AI Act Art. 86):**
- Endpoint `/admin/reasoning-trail/{message_id}` (TODO frontend) lista
  los chunks RAG y tools usados para una respuesta concreta. Datos
  ya persistidos en `reasoning_trails`.

Pendiente:
- [ ] UI admin para consultar reasoning trail de una respuesta.
- [ ] Endpoint público (autenticado) para que el usuario consulte
      su propio reasoning trail.

### 7. Robustez técnica y ciberseguridad

Resumen del stack defensivo (mayo 2026):

| Capa | Componente | Implementado |
|---|---|---|
| Frontend | Cloudflare Turnstile (login/register) | ✅ |
| Frontend | CSP + X-Frame-Options + XSS-Protection headers | ✅ |
| Edge | Railway HTTPS (Caddy) | ✅ |
| Network | Rate limiting SlowAPI + Upstash Redis | ✅ |
| Network | Velocity check anti-flooding (sprint 3 #6) | ✅ |
| Auth | JWT HS256 con `JWT_SECRET_KEY` | ✅ |
| Auth | MFA TOTP | ✅ |
| Auth | WebAuthn passkeys (sprint 2 #2, NIST SP 800-63-4) | ✅ |
| Auth | Refresh token rotation + reuse detection (sprint 3 #2) | ✅ |
| App | Pipeline seguridad 6 capas (sprint 1+2) | ✅ |
| App | PII detector (Llama Guard 4 S7) | ✅ |
| App | Trajectory analyzer multi-turn | ✅ |
| App | Citation verifier hallucinations | ✅ |
| App | Token budget per user | ✅ |
| App | Output filter post-LLM (drift detection) | ✅ |
| Data | Turso encryption at rest | ✅ |
| Data | DefensIA storage AES-GCM | ✅ |
| Data | Sanitización RAG ingesta | ✅ |
| Data | Source-trust tags + Spotlighting RAG | ✅ |
| Ops | Audit log inmutable JSONL | ✅ |
| Ops | Cost anomaly cron + email alert | ✅ |
| Ops | RAG quality cron + email alert | ✅ |
| Ops | Reasoning trail log 24m | ✅ |
| CI | Bandit + Semgrep + pip-audit + npm audit + Trivy + ZAP | ✅ |
| CI | Promptfoo nightly red-team | ✅ |
| Incident | Runbook NIS2/CRA documentado | ✅ |

Vulnerabilidades conocidas y aceptadas:
- JWT HS256 (no RS256). Aceptado: single-issuer, single-audience SaaS,
  no public API. Reevaluar si exponemos public API.
- Turnstile bypass para CI vía `/auth/login-bot` con secret + whitelist.
  Riesgo: si secret leakea + whitelist email queda comprometida →
  acceso al user qa-redteam (autonomo plan, no owner).

### 8. Precisión, robustez y rendimiento

- Tests automatizados: 200+ tests backend.
- Promptfoo nightly red-team: 35+ ataques + 5 preguntas legítimas.
- RAG quality benchmark: 30 preguntas ground truth, métricas faithfulness
  / context_relevance / answer_correctness / response_quality.
- Performance objetivo: respuesta SSE primer chunk <2s, completa <30s.

### 9. Plan de mejora continua

Roadmap próximos 6 meses:
- [ ] Sprint 4: UI admin para reasoning trail.
- [ ] Sprint 4: Página `/transparencia-ia` pública.
- [ ] Sprint 4: Activar GPG signing de commits.
- [ ] Sprint 4: HHEM-2.1 hallucination filter (si memoria Railway permite).
- [ ] Q3 2026: simulacro NIS2 anual.
- [ ] Q4 2026: revisión semestral este documento.

## Firma

Documento revisado y aprobado por:

| Nombre | Cargo | Fecha | Firma |
|---|---|---|---|
| Fernando Prada | Owner / Operador | 2026-05-05 | ☐ |

Próxima revisión obligatoria: **2026-11-05**.
