# Estado del Analisis Competitivo — Impuestify

> Ultima actualizacion: 2026-03-05
> Agente: `/competitive` (Competitive Intelligence Analyst)

## Ultimos hallazgos

- [2026-03-04] **TaxDown actualizado**: 2M+ usuarios, ~40M EUR funding total, 10M+ EUR ingresos anuales
- [2026-03-04] **TaxDown rondas 2025**: +5.8M (mar) + 4M (may) — inversores Bonsai Partners, Atresmedia, Mediaset
- [2026-03-04] **TaxDown Trustpilot bajado**: de 4.7 a 4.3/5 — 11% de reviews son 1-estrella (quejas precio oculto)
- [2026-03-04] **TaxDown expansion Mexico**: 600K+ usuarios MX, primera solucion fiscal digital aceptada por SAT
- [2026-03-04] **TaxDown autonomos**: ahora ofrece trimestrales completos (303/130) a 29.90-59.90 EUR/mes
- [2026-03-04] **TaxDown crypto**: partnership con CoinTracking para declarar criptomonedas
- [2026-03-04] **TaxDown B2B**: white-label + GaaS (Government as a Service) para empresas
- [2026-03-04] **TaxDown Renta 2026**: evento con Comunidad de Madrid el 26 marzo 2026
- [2026-03-04] **Pricing ajustado**: de 15 EUR/mes a 5 EUR/mes (60 EUR/ano) — ahora competitivo vs TaxDown 35-65 EUR/ano
- [2026-03-03] TaxDown lanzo AsesorIA (chatbot fiscal gratuito basado en ChatGPT) — competidor directo
- [2026-03-03] Declarando cobra 70-100 EUR/mes (vs nuestro modelo freemium) — muy caro para autonomos
- [2026-03-03] AEAT NO tiene API REST publica — usa SOAP/XML con certificados (barrera alta)
- [2026-03-03] APImpuestos.es ofrece API white-label como alternativa a ser Colaborador Social

## Competidores rastreados

| Competidor | Ultima revision | Usuarios | Funding | Precio desde | Cambios detectados |
|-----------|----------------|----------|---------|--------------|-------------------|
| TaxDown    | **2026-03-04** | **2M+** | **~40M EUR** | 0 EUR (free) | Rondas 2025 (+9.8M), Trustpilot baja a 4.3, Mexico 600K+, autonomos trimestrales, crypto CoinTracking |
| Declarando | 2026-03-03     | 70K+     | N/A       | 70 EUR/mes   | Sin cambios recientes |
| Taxfix     | 2026-03-03     | N/A      | Internacional | 39.90 EUR/mes | Rebranding desde TaxScouts |
| Xolo       | 2026-03-03     | N/A      | EU fintech | 15 EUR/mes  | Entrada mercado espanol |

## Analisis completados

- [2026-03-04] **Analisis profundo Rita (motor deducciones TaxDown)**:
  - Rita NO es IA generativa — es rules engine + decision tree + ML classifier
  - Entrenada con 40,000+ declaraciones historicas
  - Cruza ~3,000 preguntas con ~338 deducciones (16 estatales + 322 autonomicas)
  - **NO cubre territorios forales (PV/Navarra)** — oportunidad clave para Impuestify
  - Solo 33% de usuarios consigue ahorro real (dato BBVA)
  - Ahorro medio: 350-500 EUR
  - Depende de importacion datos via Cl@ve (obligatorio)
  - Nuestro sistema actual tiene CERO identificacion de deducciones
  - Roadmap de 5 fases escrito para Backend → ver `agent-comms.md`
- [2026-03-04] **Comparativa detallada Impuestify vs TaxDown** → ver `docs/competitive/taxdown_comparison.md`
  - 22 categorias comparadas (10 Impuestify, 13 TaxDown, 1 empate)
  - Pricing analizado en detalle — problema critico identificado
  - AsesorIA analizado (debilidades y fortaleza clave: gratis sin registro)
  - DAFO completo
  - 12 recomendaciones priorizadas
- [2026-03-03] Comparativa de features 22 categorias (todos los competidores)
- [2026-03-03] Identificacion de gaps (9 principales) y ventajas unicas (8)
- [2026-03-03] Base de datos de competidores creada en `backend/app/tools/competitor_analysis_tool.py`
- [2026-03-03] Agente Python para chat creado en `backend/app/agents/competitor_analysis_agent.py`
- [2026-03-03] Informacion sobre AEAT Colaborador Social (requisitos, proceso, alternativas)

## Ventajas unicas de Impuestify (ningun competidor las tiene)

1. **RAG sobre 428+ PDFs oficiales** — documentacion fiscal completa de todos los territorios
2. **Sistema multi-agente IA** — TaxAgent + PayslipAgent + WorkspaceAgent + NotificationAgent
3. **Analisis automatico de nominas** — extraccion + proyeccion IRPF anual
4. **Analisis notificaciones AEAT con IA** — competidores usan humanos
5. **Guardrails de seguridad IA** — Llama Guard 4 + prompt injection + PII filtering
6. **Cache semantico** — ~30% reduccion costes OpenAI
7. **Perfil fiscal conversacional** — aprende de conversaciones, source tracking manual/conversation
8. **IRPF simulator con todos los territorios** — 17 CCAA + 4 forales + Ceuta/Melilla
9. **PWA instalable** — manifest + service worker + offline fallback
10. **Landing diferenciadora** — cobertura foral destacada + comparativa visual vs chatbots genéricos
11. **Tarjetas visuales de deducciones** — DeductionCards con animaciones en chat

## Gaps principales (lo que nos falta vs mercado)

| # | Gap | Quien lo tiene | Dificultad | Impacto | Prioridad |
|---|-----|---------------|------------|---------|-----------|
| 1 | Presentacion telematica AEAT | Todos | Muy alta | Muy alto | CRITICA |
| 2 | Importacion datos via Clave | Todos | Muy alta | Muy alto | CRITICA |
| 3 | Motor de deducciones (250+) | TaxDown (Rita) | Alta | Muy alto | ALTA |
| 4 | ~~App movil (iOS/Android)~~ PWA implementada | Todos | ~~Media-alta~~ ✅ | Alto | ~~ALTA~~ DONE |
| 5 | Free tier / modelo freemium | TaxDown, AsesorIA | Baja | Muy alto | **CRITICA** |
| 6 | Asesores humanos | TaxDown, Declarando, Taxfix | Alta (RRHH) | Alto | MEDIA |
| 7 | Facturacion/contabilidad | Declarando, Taxfix, Xolo | Media | Alto | MEDIA |
| 8 | B2B/Enterprise API | TaxDown (500+ empresas) | Media | Alto | ALTA |
| 9 | Crypto/DeFi declaracion | TaxDown (CoinTracking) | Media | Medio | MEDIA |
| 10 | Marca/reconocimiento | TaxDown (2M+ usuarios) | N/A (tiempo) | Muy alto | CRITICA |

## Recomendaciones — Estado de implementación

### Prioridad CRITICA — Motor de Deducciones ✅ COMPLETADO
1. ~~**Deduction Registry**~~ ✅ tabla `deductions` en Turso + 16 estatales + 48 territoriales (8 CCAA)
2. ~~**Deduction Discovery Tool**~~ ✅ `discover_deductions()` con soporte territorial completo
3. ~~**TaxAgent proactivo**~~ ✅ pregunta activamente + prompt actualizado
4. ~~**Deducciones forales PV/Navarra**~~ ✅ Araba, Bizkaia, Gipuzkoa, Navarra implementados
5. ~~**Integrar en IRPFSimulator**~~ ✅ simulate_irpf auto-chain discover_deductions end-to-end

### Prioridad ALTA — Export + Compartir ✅ COMPLETADO
6. ~~**Export simulacion IRPF como PDF**~~ ✅ POST /api/export/irpf-report + ReportActions.tsx
7. ~~**Compartir con asesor via email**~~ ✅ POST /api/export/share-with-advisor + ShareReportModal.tsx
8. ~~**Informe de deducciones**~~ ✅ incluido automáticamente en la simulación IRPF
9. **Checklist documental** — 🟡 PENDIENTE (que aportar para cada deducción)
10. ~~**GTM nicho foral PV/Navarra**~~ ✅ DONE — Landing page con cobertura foral destacada (21 territorios, forales con badge especial)
11. ~~**PWA movil**~~ ✅ DONE — manifest.json + service worker + favicon SVG/PNG + offline fallback

### Frontend — ✅ COMPLETADO (2026-03-05)
- ~~**PWA**~~ ✅ manifest.json, service worker (network-first API, cache-first assets), offline.html, meta tags
- ~~**Tarjetas visuales deducciones**~~ ✅ DeductionCards.tsx con CountUp + FadeContent + icons por categoría
- ~~**Landing page rediseño**~~ ✅ Hero GradientText + Stats CountUp + Cobertura territorial + Comparativa SpotlightCard + CTA StarBorder
- ~~**Favicon**~~ ✅ SVG profesional (gradiente #1a56db→#06b6d4, escudo con "I") + PNG 32/192/512
- React Bits: CountUp, GradientText, SpotlightCard, StarBorder, FadeContent (custom IntersectionObserver)

### Prioridad MEDIA — Pendiente
12. Guia interactiva presentacion Renta WEB
13. Calendario fiscal personalizado con alertas
14. B2B API para gestores/asesorias (Impuestify como herramienta del gestor)

### DESCARTADO (no interesa de momento)
- ~~Integracion APImpuestos~~ — no queremos presentacion telematica
- ~~Colaborador Social AEAT~~ — no es prioritario
- Posicionamiento: complemento del asesor, no sustituto

## Analisis de Pricing (2026-03-06)

- [2026-03-06] **Investigacion precios plan Autonomo** — completado. Informe en `plans/pricing-research-autonomo-2026-03.md`
  - Precios actualizados: TaxDown (29.90/59.90 EUR/mes), Declarando (29.90-49.90 EUR/mes oferta), Taxfix (39.90 EUR/mes), Abaq (39 EUR/mes), Fiscaliza (25.90-60.90 EUR/mes)
  - Asesores tradicionales: 40-80 EUR/mes basico, 80-150 EUR/mes estandar
  - Software de facturacion (competencia indirecta): 10-50 EUR/mes
  - **Recomendacion**: 39 EUR/mes (fase actual, sin presentacion AEAT) — 59 EUR/mes con Colaborador Social
  - **NO recomendado 200 EUR/mes** en fase actual sin presentacion telematica
  - Nicho foral (1.6M declarantes PV+Navarra) sigue siendo diferenciador principal

## Pendiente para proxima sesion

- [ ] Comparativa detallada vs Declarando (siguiente competidor)
- [ ] Comparativa detallada vs Taxfix
- [ ] Comparativa detallada vs Xolo
- [ ] Investigar nuevo competidor: OnlyTax (content creators)
- [ ] Probar AsesorIA de TaxDown en vivo (benchmark preguntas fiscales)
- [ ] Analizar trafico web competidores (SimilarWeb)
- [ ] Analizar estrategia SEO de competidores
- [ ] Investigar posibles competidores IA nuevos (GestorIA, CAIFIS, otros)
