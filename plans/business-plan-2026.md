# Impuestify -- Business Plan 2026

> Actualizado: 2026-04-15 (Sesión 33)
> Incluye: B2C (Particulares, Creadores, Autónomos) + B2B (Asesorías/Gestorías)
> Novedades: DefensIA (defensa fiscal automatizada) + Modelo 200 IS (Impuesto de Sociedades)

---

## 1. Resumen Ejecutivo

Impuestify es el único asistente fiscal con IA en España que cubre los **21 territorios fiscales**, incluyendo los 4 territorios forales del País Vasco y Navarra que TaxDown no cubre (~1,6M declarantes sin alternativa digital).

Con **~1.008 deducciones automáticas**, **463 documentos oficiales indexados** vía RAG, un simulador IRPF validado en múltiples territorios, calculadora de retenciones con algoritmo AEAT, comparador de declaración conjunta vs. individual, y conversaciones compartibles con anonimización PII, la plataforma está consolidada en B2C y lista para escalar a B2B.

**Dos nuevos modulos diferenciales lanzados en abril 2026:**

1. **DefensIA** -- Motor de defensa fiscal automatizada con arquitectura anti-alucinación (Gemini extracción -> reglas deterministas -> RAG verificador -> LLM redactor controlado). Genera escritos legales (alegaciones, TEAR, reposición) en DOCX/PDF con citas normativas verificadas. **Ninguna plataforma fiscal en España ofrece defensa fiscal automatizada con IA.**

2. **Modelo 200 IS** -- Simulador del Impuesto de Sociedades con 7 regímenes territoriales (común 25%, forales 24%, Navarra 28%, ZEC 4%, Ceuta/Melilla bonif. 50%), tipo reducido Pyme, nueva creación, pagos fraccionados (Modelo 202) y borrador PDF. Integrado con el módulo de contabilidad (auto-relleno desde PyG/Balance).

El segmento B2B de asesorías fiscales (52.400 empresas) está desatendido por herramientas asequibles con IA. A3 ASESOR cuesta 3.500-5.500 EUR/año y no tiene IA nativa. Impuestify puede ofrecer el mismo valor a 588-2.388 EUR/año con IA integrada, descubrimiento proactivo de deducciones, defensa fiscal automatizada y cobertura territorial completa.

**Objetivo 2027:** 750 suscriptores B2C + 165 asesorias B2B = 25.585 EUR MRR = 307K EUR ARR.

---

## 2. Vision y Mision

**Visión:** Ser la herramienta fiscal con IA de referencia en España, cubriendo los 21 territorios fiscales (incluidos forales) con precisión, accesibilidad y cumplimiento normativo.

**Misión:** Democratizar el asesoramiento fiscal inteligente para particulares, autónomos, creadores de contenido y asesorías fiscales, usando IA + RAG sobre fuentes oficiales (AEAT, BOE, haciendas forales).

---

## 3. Mercado Objetivo

### 3.1 B2C -- Contribuyentes individuales (mercado actual)

| Segmento | Tamaño | Plan | Precio |
|----------|--------|------|--------|
| Particulares (asalariados, pensionistas) | ~20M declarantes | Particular | 5 EUR/mes |
| Creadores de contenido (YouTubers, streamers, influencers) | ~285K en España | Creator | 49 EUR/mes |
| Autónomos (freelancers, profesionales) | ~3,3M en España | Autónomo | 39 EUR/mes IVA incl. |

### 3.2 B2B -- Asesorías y Gestorías fiscales (nuevo segmento)

| Segmento | Tamaño | Plan | Precio |
|----------|--------|------|--------|
| Micro-gestorías (1-2 personas) | ~23.500 empresas | Starter | 49 EUR/mes |
| Gestorías pequeñas (3-5 personas) | ~13.100 empresas | Professional | 99 EUR/mes |
| Gestorías medianas (6-15 personas) | ~10.500 empresas | Enterprise | 199 EUR/mes |

**Total mercado asesorías:** ~52.400 empresas, facturación total ~10.000M EUR/año

### 3.3 DefensIA -- Mercado de defensa fiscal

| Métrica | Dato |
|---------|------|
| Reclamaciones económico-administrativas anuales (España) | ~200.000 |
| Recursos de reposicion estimados | ~500.000 |
| Coste medio abogado tributarista | 300-800 EUR por escrito |
| Precio Impuestify (incluido en plan + extra) | 0-15 EUR por expediente |

---

## 4. Propuesta de Valor

### 4.1 B2C

- Asistente fiscal con IA que cubre **21 territorios** (incluidos 4 forales + Ceuta/Melilla)
- Simulador IRPF con **~1.008 deducciones** automaticas
- Chat con RAG sobre **463+ documentos oficiales** (92.393 chunks, 85.587 embeddings)
- Guía fiscal adaptativa por rol (7-8 pasos según plan)
- Calculadora de sueldo neto para autónomos (5 regímenes fiscales)
- Calculadora de retenciones IRPF (algoritmo oficial AEAT 2026, gratuita)
- Comparador de declaración conjunta vs. individual (4 escenarios)
- Compartir conversaciones con enlaces públicos y anonimización PII
- GP inmuebles: plusvalía, renta imputada, ganancias patrimoniales
- ISD en las 21 comunidades autonomas
- Modelos 720/721 (bienes y criptomonedas en el extranjero)
- Sistema de feedback integrado (widget + valoracion por respuesta)
- Cobertura foral completa (País Vasco + Navarra) -- **TaxDown NO cubre esto**
- **NUEVO: DefensIA** -- Defensa fiscal automatizada (alegaciones, TEAR, reposicion)
- **NUEVO: Modelo 200 IS** -- Simulador Impuesto de Sociedades (7 regimenes + Modelo 202)
- **NUEVO: OCR Facturas** -- Gemini 3 Flash Vision ($0,0003/factura) + contabilidad PGC completa

### 4.2 DefensIA -- Propuesta de valor única

- **Motor híbrido anti-alucinación**: 4 fases (extracción Gemini -> 30 reglas deterministas -> RAG verificador -> LLM redactor controlado)
- **9 plantillas Jinja2**: Alegaciones, recurso de reposicion, TEAR abreviado, TEAR general, solicitud suspension, ampliacion plazo, alegaciones sancionador, comparecencia, escrito generico
- **Export DOCX/PDF** con disclaimer legal obligatorio
- **5 tributos**: IRPF, IVA, ISD, ITP, Plusvalía Municipal
- **5 procedimientos**: Verificación, comprobación limitada, sancionador, reposición, TEAR
- **Citas normativas verificadas**: cada argumento referencia articulo, ley y jurisprudencia real
- **Monetización por expediente**: 1/3/5 expedientes/mes según plan + 15/12/10 EUR por extra
- **379 tests backend** + E2E verificado end-to-end

### 4.3 Modelo 200 IS -- Propuesta de valor

- **7 regímenes territoriales**: común 25%, forales 24%, Navarra 28%, ZEC 4%, Ceuta/Melilla bonif. 50%
- **Tipo reducido Pyme**: 23% primeros 50K si facturación < 1M
- **Nueva creación**: 15% primeros 50K, primeros 2 ejercicios positivos
- **Modelo 202 pagos fraccionados**: Art. 40.2 + Art. 40.3
- **Integración workspace**: auto-relleno desde PyG/Balance de contabilidad
- **Borrador PDF**: 16 casillas con formato AEAT
- **47 tests** de cobertura

### 4.4 B2B -- Diferenciación clave

- **Precio 6-10x menor que A3/Sage** (49-199 EUR/mes vs 3.500-5.500 EUR/año)
- **IA nativa** (no bolt-on como a3Pilot o Sage Copilot)
- **Descubrimiento proactivo de deducciones** para cartera de clientes -- nadie lo ofrece
- **Consulta fiscal con fuentes citadas** -- respuestas con Art., Ley, casilla AEAT
- **21 territorios** incluyendo forales (A3 no simula forales)
- **Posicionamiento: complemento**, no reemplazo de A3/Sage

---

## 5. Ventaja Competitiva

### 5.1 vs TaxDown (B2C)

| Factor | TaxDown | Impuestify |
|--------|---------|------------|
| Forales (País Vasco/Navarra) | NO cubre | **4 territorios completos** |
| Ceuta/Melilla | Parcial | **Completo (IPSI + 60 %)** |
| Canarias | Parcial | **IGIC + ZEC + REF** |
| Deducciones | ~250 (motor Rita) | **~1.008** |
| IA | Chatbot básico | **RAG + 463 docs oficiales** |
| Precio | 35-50 EUR declaración | **5-49 EUR/mes** |
| Defensa fiscal automatizada | **NO** | **DefensIA (alegaciones, TEAR, reposición)** |
| Impuesto de Sociedades | **NO** | **Modelo 200 + 202 (7 regímenes)** |
| OCR Facturas + Contabilidad | NO | **Gemini 3 Flash + PGC completo** |
| Compartir conversaciones | NO | **Sí, con anonimización PII** |
| Calculadora retenciones IRPF | NO (solo simulador) | **Algoritmo AEAT gratuito** |
| Declaración conjunta vs. individual | Parcial | **4 escenarios comparados** |

### 5.2 vs A3/Sage (B2B)

| Factor | A3 ASESOR | Sage Despachos | Impuestify |
|--------|-----------|----------------|------------|
| Precio anual | 3.500-5.500 EUR | 2.000-6.600 EUR | **588-2.388 EUR** |
| IA | a3Pilot (bolt-on) | Sage Copilot | **RAG nativa** |
| Simulación multi-territorial | Básica | No | **21 territorios** |
| Descubrimiento deducciones | No | No | **Proactivo** |
| Consulta fiscal con fuentes | No | No | **Chat + citas** |
| Defensa fiscal automatizada | No | No | **DefensIA** |
| VeriFactu | Si | Si | Pendiente |
| Gestión multi-cliente | Sí (core) | Sí (core) | **A construir** |

### 5.3 vs IAFiscal (B2B directo)

| Factor | IAFiscal | Impuestify |
|--------|----------|------------|
| Precio | desde 29,99 EUR/mes | desde 49 EUR/mes |
| Modelos AEAT | 50+ | ~15 (expandiendo) |
| Simulación | No multi-territorial | **21 territorios** |
| Deducciones | No | **~1.008** |
| RAG/fuentes | No | **463+ docs** |
| Forales | No | **Sí** |
| Defensa fiscal | No | **DefensIA** |
| Impuesto Sociedades | Básico | **7 regímenes + Modelo 202** |

### 5.4 Ventaja competitiva DefensIA

**Ningún competidor en el mercado español ofrece defensa fiscal automatizada con IA.**

- Los abogados tributaristas cobran 300-800 EUR por escrito de alegaciones
- Los contribuyentes afectados por liquidaciones paralelas/comprobaciones no tienen alternativa asequible
- DefensIA genera escritos legales verificados con citas normativas por 0-15 EUR
- Motor anti-alucinación de 4 fases garantiza precisión jurídica
- Disclaimer legal obligatorio en 4 superficies (banner, argumentos, escrito, checkbox pre-export)

---

## 6. Modelo de Ingresos

### 6.1 B2C (actual)

| Plan | Precio | ARPU mensual | Target subs Y1 | MRR Y1 |
|------|--------|-------------|-----------------|---------|
| Particular | 5 EUR/mes | 5 | 500 | 2.500 |
| Creator | 49 EUR/mes | 49 | 50 | 2.450 |
| Autonomo | 39 EUR/mes | 39 | 200 | 7.800 |
| **Total B2C** | | | **750** | **12.750 EUR/mes** |

### 6.2 DefensIA (ingresos incrementales)

| Plan | Expedientes incluidos/mes | Precio por extra | Revenue estimado extra/mes |
|------|--------------------------|------------------|---------------------------|
| Particular | 1 | 15 EUR | ~750 EUR (500 users x 10% uso x 15 EUR) |
| Autonomo | 3 | 12 EUR | ~480 EUR (200 users x 20% uso x 12 EUR) |
| Creator | 5 | 10 EUR | ~250 EUR (50 users x 50% uso x 10 EUR) |
| **Total extra DefensIA** | | | **~1.480 EUR/mes** |

**Nota:** Los expedientes incluidos refuerzan la retención (reducen churn). Los extras generan revenue incremental con margen ~99% (coste API ~0,02 EUR/expediente).

### 6.3 B2B (nuevo -- lanzamiento Q3 2026)

| Plan | Precio | Clientes max. | Target subs Y1 | MRR Y1 |
|------|--------|---------------|-----------------|---------|
| Starter | 49 EUR/mes | 50 clientes | 100 | 4.900 |
| Professional | 99 EUR/mes | 200 clientes | 50 | 4.950 |
| Enterprise | 199 EUR/mes | Ilimitados | 15 | 2.985 |
| **Total B2B** | | | **165** | **12.835 EUR/mes** |

### 6.4 Proyección combinada

| Metrica | Y1 (2027) | Y2 (2028) | Y3 (2029) |
|---------|-----------|-----------|-----------|
| Suscriptores B2C | 750 | 2.500 | 8.000 |
| Suscriptores B2B | 165 | 600 | 2.000 |
| MRR (suscripciones) | 25.585 EUR | 85.000 EUR | 280.000 EUR |
| MRR (DefensIA extras) | 1.480 EUR | 8.000 EUR | 30.000 EUR |
| MRR total | 27.065 EUR | 93.000 EUR | 310.000 EUR |
| ARR | 324.780 EUR | 1.116.000 EUR | 3.720.000 EUR |
| Churn mensual | 8 % | 5 % | 3 % |

---

## 7. Estructura de Costes

| Concepto | Coste mensual | Notas |
|----------|---------------|-------|
| OpenAI API (GPT-5-mini) | ~500-2.000 EUR | Variable por uso, ~0,5 EUR/usuario activo |
| Google Gemini API | ~50-200 EUR | OCR facturas ($0,0003/factura) + DefensIA extraccion |
| Railway (hosting) | 20-100 EUR | Frontend + Backend + Workers |
| Turso DB | 0-29 EUR | Free tier hasta 9 GB |
| Upstash (Redis + Vector) | 0-20 EUR | Free tier generoso |
| Stripe comisiones | 1,4 % + 0,25 EUR | Por transaccion |
| Groq (LlamaGuard4) | 0 EUR | Free tier 14.400 req/dia |
| Resend (emails) | 0-20 EUR | Free tier 3K/mes |
| Dominio + Cloudflare | ~15 EUR/mes | impuestify.com |
| **Total infra** | **~650-2.400 EUR/mes** | |

**Unit economics B2C:** ARPU ~17 EUR/mes, coste marginal ~0,5 EUR -> margen ~97 %
**Unit economics B2B:** ARPU ~78 EUR/mes, coste marginal ~2 EUR -> margen ~97 %
**Unit economics DefensIA:** ARPU extra ~1,5 EUR/expediente, coste ~0,02 EUR -> margen ~99 %

---

## 8. Arquitectura Técnica

### 8.1 Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | FastAPI (Python 3.12+) |
| Frontend | React 18 + Vite + TypeScript |
| Base de datos | Turso (SQLite distribuido) |
| Embeddings | OpenAI text-embedding-3-large + Upstash Vector |
| LLM principal | GPT-5-mini (OpenAI) |
| OCR | Gemini 3 Flash Preview (Google) |
| Seguridad LLM | LlamaGuard4 (Groq) |
| Hosting | Railway (auto-deploy) |
| Pagos | Stripe |
| Email | Resend |
| CDN/WAF | Cloudflare |

### 8.2 Números clave (abril 2026)

| Metrica | Valor |
|---------|-------|
| Documentos RAG | 463 |
| Chunks indexados | 92.393 |
| Embeddings | 85.587 |
| Deducciones IRPF | ~1.008 |
| Territorios cubiertos | 21/21 |
| Tests backend | ~1.800+ |
| Capas de seguridad | 13 |
| Herramientas IA (tools) | 14 |
| Modelos tributarios cubiertos | 303, 300, F69, 420, IPSI, 130, 131, 308, 720, 721, 200, 202 |
| Agentes multi-agente | CoordinatorAgent, TaxAgent, PayslipAgent, NotificationAgent, WorkspaceAgent, DefensIAAgent |
| Plantillas legales DefensIA | 9 (Jinja2) |
| Reglas deterministas DefensIA | 30 |

### 8.3 Seguridad (13 capas)

1. Cloudflare Turnstile (CAPTCHA)
2. MFA/2FA (TOTP + backup codes)
3. Rate limiting (slowapi)
4. JWT con validacion en startup
5. Prompt injection detection
6. PII filtering
7. SQL injection prevention (queries parametrizadas)
8. LlamaGuard4 (contenido inseguro)
9. Document Integrity Scanner
10. CORS hardening (produccion)
11. File upload validation (magic numbers + size limits)
12. Owner guard (endpoints admin)
13. Semantic cache poisoning prevention

---

## 9. Roadmap Producto

### Q2 2026 (actual) -- B2C Consolidación + Nuevos Módulos

- [x] Motor IRPF 21 territorios (~1.008 deducciones)
- [x] Chat RAG con 463+ documentos oficiales
- [x] 3 planes suscripcion (Particular/Creator/Autonomo)
- [x] 13 capas seguridad (Turnstile, MFA, LlamaGuard4)
- [x] Calculadora de retenciones IRPF (algoritmo AEAT 2026, 28 tests)
- [x] Compartir conversaciones (enlaces públicos + anonimización PII)
- [x] Sistema de feedback completo (widget + chat ratings + admin dashboard)
- [x] GP inmuebles: plusvalia, renta imputada, ganancias patrimoniales
- [x] ISD en 21 comunidades autónomas
- [x] Modelos 720/721 (bienes y criptomonedas en el extranjero)
- [x] Segundo declarante en declaración conjunta
- [x] Pipeline auto-ingesta RAG (crawler -> embeddings automáticos)
- [x] Múltiples pagadores (Art. 96 LIRPF, obligación declarar)
- [x] OCR facturas con Gemini 3 Flash Vision + contabilidad PGC completa
- [x] **DefensIA v1** -- Defensa fiscal automatizada (379 tests, 71 commits)
- [x] **Modelo 200 IS** -- Impuesto de Sociedades (7 regimenes, 47 tests, 11 commits)
- [x] **Modelo 202** -- Pagos fraccionados IS (Art. 40.2 + 40.3)
- [x] SEO overhaul (useSEO hook, 12 páginas con schema JSON-LD, sitemap 21 URLs)
- [x] Generador PDF de modelos tributarios (303/130/308/720/721/IPSI + forales)
- [x] Workspace dashboard visual (KPIs, graficas Recharts, tabla PGC)
- [ ] Mejorar RAG quality (context relevance)

### Q3 2026 -- B2B MVP + DefensIA Expansión

- [ ] Dashboard multi-cliente para asesorías
- [ ] Gestión de cartera (N clientes con perfil fiscal)
- [ ] Exportación masiva de informes IRPF
- [ ] Multi-usuario por despacho (roles: admin, asesor, becario)
- [ ] Alerta proactiva: "3 clientes pueden deducir X"
- [ ] API REST para integración con A3/Sage
- [ ] DefensIA: ampliar a inspección y TEAC
- [ ] DefensIA: analytics dashboard (métricas de uso, tasa de éxito)

### Q4 2026 -- Compliance + Escala

- [ ] VeriFactu (obligatorio sociedades 01/01/2027)
- [ ] Factura electrónica (Ley Crea y Crece)
- [ ] Historial multi-ejercicio por cliente
- [ ] DefensIA: contencioso-administrativo (via abogado partner)

### 2027 -- Crecimiento

- [ ] App movil (React Native)
- [ ] VeriFactu autonomos (obligatorio 01/07/2027)
- [ ] Integración bancaria (PSD2/Open Banking)
- [ ] ML: predicción fiscal + optimización
- [ ] B2B Enterprise: white-label para grandes despachos
- [ ] Modelo 100 IRPF automatizado (pre-fill desde workspace)

---

## 10. Go-to-Market

### 10.1 B2C -- DefensIA como motor de adquisición

- **Canal orgánico**: SEO en "cómo recurrir liquidación AEAT", "alegaciones Hacienda", "recurso TEAR"
- **Freemium hook**: 1 expediente/mes gratis con plan Particular (5 EUR/mes)
- **Viralización**: usuario comparte resultado exitoso (reducción/anulación de liquidación)
- **Campaña renta**: abril-junio, pico de liquidaciones paralelas -> pico de demanda DefensIA en julio-octubre

### 10.2 B2B -- Estrategia de entrada

- **Posicionamiento:** Complemento inteligente a herramientas existentes (no reemplazo)
- **Mensaje:** "Ahorra 5 h/semana en consultas fiscales y descubrimiento de deducciones"
- **Canal primario:** Marketing directo a micro-gestorías vía LinkedIn + SEO
- **Canal secundario:** Partnerships con colegios de asesores fiscales (AECE, CGE)
- **Evento clave:** Accountex España (noviembre 2026)
- **DefensIA para gestorías:** valor diferencial enorme -- automatizar escritos que hoy cuestan 300-800 EUR

### 10.3 Timing

- **Febrero:** Mes óptimo para captación (precampaña renta)
- **Abril-Junio:** Demostraciones en campaña renta (valor inmediato)
- **Julio-Octubre:** Pico DefensIA (liquidaciones post-campana)
- **Septiembre:** Lanzamiento B2B plan Starter
- **Noviembre:** Accountex España -- stand + demo

### 10.4 Primeros 100 clientes B2B

1. Beta cerrada con 10 gestorías (amigos/referidos) -- Q3 2026
2. Oferta early bird: 50% descuento primer año
3. Case studies con metricas de ahorro de tiempo
4. Referral program: 1 mes gratis por referido

---

## 11. Equipo y Recursos

| Rol | Persona | Dedicación |
|-----|---------|-----------|
| CEO / Producto / Dev | Fernando Prada | Full-time |
| IA / Backend | Claude Code (Opus 4.6) | Agente continuo |
| Multi-agente | RuFlo V3.5 (259 tools) | Workflow automatizado |
| QA | Playwright + agentes QA | Automatizado |
| Code Review | GitHub Copilot (custom instructions) | Automatizado |
| Marketing | Redes sociales (3 canales) | Part-time |

### Necesidades de contratación (post-revenue)

- Developer frontend/mobile (Q3 2026)
- Sales B2B / Account manager (Q4 2026)
- Abogado tributarista consultor para DefensIA (Q4 2026)
- Customer success para gestorías (2027)

---

## 12. Métricas Clave (KPI)

### B2C

- MAU (Monthly Active Users)
- Tasa de conversión (free -> paid)
- Churn mensual (<5 % target)
- NPS (>50 target)
- RAG quality score (>80 % target)

### DefensIA

- Expedientes procesados/mes
- Tasa de uso (% usuarios que usan DefensIA)
- Revenue incremental por expediente extra
- Tasa de éxito reportada por usuarios (reducción/anulación)
- Tiempo medio por expediente (target: <5 min vs 2-4h manual)

### B2B

- Gestorías activas
- Clientes gestionados por gestoría
- Tiempo ahorrado por gestoría/semana
- Revenue per gestoría (ARPU)
- Logo retention (>90% anual)

---

## 13. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|-------------|---------|------------|
| AEAT lanza herramienta propia con IA | Media | Alto | Diferenciación en UX, forales, deducciones proactivas, DefensIA |
| TaxDown entra en B2B o defensa fiscal | Media | Medio | First-mover en forales + DefensIA, pricing agresivo |
| Regulación IA (AI Act) | Alta | Medio | Cumplimiento proactivo, transparencia en fuentes, disclaimer |
| Alucinaciones fiscales en DefensIA | Media | Muy alto | Motor híbrido 4 fases, reglas deterministas, disclaimer obligatorio |
| Responsabilidad legal DefensIA | Media | Alto | Disclaimer en 4 superficies, "no sustituye asesoramiento profesional" |
| Escalabilidad costes OpenAI | Media | Medio | Modelos ligeros (mini), cache semántica, límites |
| VeriFactu complejidad técnica | Media | Medio | Priorizar sociedades primero, autónomos después |
| Competidor copia DefensIA | Baja | Medio | Ventaja de datos (reglas + templates), iteración rápida |

---

## 14. Business Model Canvas

```
+-------------------+-------------------+-------------------+-------------------+-------------------+
| ASOCIACIONES      | ACTIVIDADES       | PROPUESTA VALOR   | REL. CLIENTES     | SEGMENTOS         |
| CLAVE             | CLAVE             |                   |                   | CLIENTE           |
|                   |                   |                   |                   |                   |
| OpenAI/Groq       | Motor IRPF        | B2C: Asistente    | Chat IA 24/7      | Particulares      |
| Google (Gemini)   | (+1.000 deducc.)  | fiscal IA 21      | Guia fiscal 7     | (20M declarantes) |
| AEAT/BOE          | DefensIA (4 fases)| territorios       | pasos             |                   |
| Cloudflare        | Crawler docs      | (incl. forales)   | DefensIA auto     | Creadores         |
| Stripe            | (90 URLs)         | +1.000 deducciones| Alertas plazos    | (285K en España)  |
| Railway           | OCR facturas      | Defensa fiscal IA | Sistema feedback  |                   |
| Resend            | Modelo 200 IS     | 1/30 coste asesor | Compartir conv.   | Autonomos         |
| Upstash           | IA multi-agente   | IS 7 regimenes    |                   | (3,3M)            |
|                   |                   | Cumplimiento RGPD |                   |                   |
|                   | B2B: Dashboard    | B2B: Consulta IA  | B2B: Dashboard    | Gestorias         |
|                   | multi-cliente     | para asesorias    | multi-cliente     | (52.400 empresas) |
|                   | VeriFactu         | 6-10x mas barato  | API integracion   |                   |
|                   | API integracion   | que A3/Sage       | Alertas proact.   | SL/Sociedades     |
|                   |                   |                   | deducciones       | (Modelo 200)      |
+-------------------+-------------------+-------------------+-------------------+-------------------+
| RECURSOS CLAVE    |                                                           | CANALES           |
|                   |                                                           |                   |
| Stack: FastAPI +  |                                                           | App web PWA       |
| React + GPT-5    |                                                           | (impuestify.com)  |
| 463+ docs RAG     |                                                           | Landings SEO      |
| Motor 1.008 ded.  |                                                           | territoriales     |
| DefensIA 30 reglas|                                                           | LinkedIn+IG+TikTok|
| 9 templates legales|                                                          | Accountex España  |
| Railway/Turso     |                                                           | Colegios asesores |
| 13 capas seguridad|                                                           | SEO defensa fiscal|
| ~1.800 tests      |                                                           |                   |
+-------------------+-------------------+-------------------+-------------------+-------------------+
| ESTRUCTURA DE COSTES                  | FUENTES DE INGRESOS                                     |
|                                       |                                                          |
| API OpenAI (variable, ~0,5 EUR/user) | B2C: Particular 5, Creator 49, Autonomo 39 EUR/mes       |
| API Gemini (~0,0003 EUR/factura)     | B2B: Starter 49, Professional 99, Enterprise 199 EUR/mes |
| Hosting Railway (~100 EUR/mes)       | DefensIA extras: 15/12/10 EUR por expediente             |
| DB Turso (free-29 EUR/mes)           | Target Y1 MRR: 27.065 EUR                               |
| Comisiones Stripe (1,4%)             | Target ARR Y3: 3.720.000 EUR                             |
| Desarrollo (1 persona + IA)          |                                                          |
+---------------------------------------+----------------------------------------------------------+
```

---

## 15. Hitos Técnicos Alcanzados (abril 2026)

| Hito | Fecha | Detalle |
|------|-------|---------|
| MVP B2C lanzado | Ene 2026 | Chat + IRPF + 3 planes |
| 21/21 territorios cubiertos | Mar 2026 | Incluidos 4 forales + Ceuta/Melilla |
| ~1.008 deducciones IRPF | Mar 2026 | 15 CCAA + 4 forales seeded |
| 13 capas seguridad | Mar 2026 | Audit 20/21 issues resueltos |
| OCR facturas + contabilidad PGC | Mar 2026 | Gemini 3 Flash, 56 tests |
| SEO overhaul | Mar 2026 | 12 páginas schema, sitemap 21 URLs |
| DefensIA v1 | Abr 2026 | 379 tests, 71 commits, E2E verificado |
| Modelo 200 IS | Abr 2026 | 47 tests, 11 commits, 7 regímenes |
| ~1.800 tests backend | Abr 2026 | Cobertura amplia, CI/CD funcional |
| 463 docs RAG indexados | Abr 2026 | 92.393 chunks, 85.587 embeddings |

---

## 16. Próximos Pasos Inmediatos

1. **Merge DefensIA a main** -- rama claude/defensia-v1 lista (71 commits, 379 tests)
2. **Merge Modelo 200 a main** -- rama claude/modelo-200-v1 lista (11 commits, 47 tests)
3. **Deploy a producción** -- Railway auto-deploy tras merge
4. **Seed producción** -- ejecutar seeds de deducciones farmacia en Turso
5. **Beta DefensIA** -- invitar a beta testers actuales (Ramon, Juan Pablo, Jose Antonio)
6. **Preparar campaña renta** -- abril-junio 2026, pico de uso
7. **Iniciar B2B MVP** -- Q3 2026, dashboard multi-cliente
