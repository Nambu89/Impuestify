# Impuestify — Business Plan 2026

> Actualizado: 2026-03-25 (Sesion 21)
> Incluye: B2C (Particulares, Creadores, Autonomos) + B2B (Asesorias/Gestorias)

---

## 1. Vision y Mision

**Vision:** Ser la herramienta fiscal con IA de referencia en Espana, cubriendo los 21 territorios fiscales (incluidos forales) con precision, accesibilidad y cumplimiento normativo.

**Mision:** Democratizar el asesoramiento fiscal inteligente para particulares, autonomos, creadores de contenido y asesorias fiscales, usando IA + RAG sobre fuentes oficiales (AEAT, BOE, haciendas forales).

---

## 2. Mercado Objetivo

### 2.1 B2C — Contribuyentes individuales (mercado actual)

| Segmento | Tamano | Plan | Precio |
|----------|--------|------|--------|
| Particulares (asalariados, pensionistas) | ~20M declarantes | Particular | 5 EUR/mes |
| Creadores de contenido (YouTubers, streamers, influencers) | ~285K en Espana | Creator | 49 EUR/mes |
| Autonomos (freelancers, profesionales) | ~3.3M en Espana | Autonomo | 39 EUR/mes IVA incl. |

### 2.2 B2B — Asesorias y Gestorias fiscales (nuevo segmento)

| Segmento | Tamano | Plan | Precio |
|----------|--------|------|--------|
| Micro-gestorias (1-2 personas) | ~23,500 empresas | Starter | 49 EUR/mes |
| Gestorias pequenas (3-5 personas) | ~13,100 empresas | Professional | 99 EUR/mes |
| Gestorias medianas (6-15 personas) | ~10,500 empresas | Enterprise | 199 EUR/mes |

**Total mercado asesorias:** ~52,400 empresas, facturacion total ~10,000M EUR/ano

---

## 3. Propuesta de Valor

### 3.1 B2C
- Asistente fiscal con IA que cubre **21 territorios** (incluidos 4 forales + Ceuta/Melilla)
- Simulador IRPF con **~1,000 deducciones** automaticas
- Chat con RAG sobre **456+ documentos oficiales**
- Guia fiscal adaptativa por rol (7-8 pasos)
- Calculadora neto para autonomos (5 regimenes fiscales)
- Cobertura foral completa (Pais Vasco + Navarra) — **TaxDown NO cubre esto**

### 3.2 B2B — Diferenciacion clave
- **Precio 6-10x menor que A3/Sage** (49-199 EUR/mes vs 3,500-5,500 EUR/ano)
- **IA nativa** (no bolt-on como a3Pilot o Sage Copilot)
- **Descubrimiento proactivo de deducciones** para cartera de clientes — nadie lo ofrece
- **Consulta fiscal con fuentes citadas** — respuestas con Art., Ley, casilla AEAT
- **21 territorios** incluyendo forales (A3 no simula forales)
- **Posicionamiento: complemento**, no reemplazo de A3/Sage

---

## 4. Ventaja Competitiva

### 4.1 vs TaxDown (B2C)
| Factor | TaxDown | Impuestify |
|--------|---------|------------|
| Forales (Pais Vasco/Navarra) | NO cubre | **4 territorios completos** |
| Ceuta/Melilla | Parcial | **Completo (IPSI + 60%)** |
| Canarias | Parcial | **IGIC + ZEC + REF** |
| Deducciones | ~250 (motor Rita) | **~1,008** |
| IA | Chatbot basico | **RAG + 456 docs oficiales** |
| Precio | 35-50 EUR declaracion | **5-49 EUR/mes** |

### 4.2 vs A3/Sage (B2B)
| Factor | A3 ASESOR | Sage Despachos | Impuestify |
|--------|-----------|----------------|------------|
| Precio anual | 3,500-5,500 EUR | 2,000-6,600 EUR | **588-2,388 EUR** |
| IA | a3Pilot (bolt-on) | Sage Copilot | **RAG nativa** |
| Simulacion multi-territorial | Basica | No | **21 territorios** |
| Descubrimiento deducciones | No | No | **Proactivo** |
| Consulta fiscal con fuentes | No | No | **Chat + citas** |
| VeriFactu | Si | Si | Pendiente |
| Gestion multi-cliente | Si (core) | Si (core) | **A construir** |

### 4.3 vs IAFiscal (B2B directo)
| Factor | IAFiscal | Impuestify |
|--------|----------|------------|
| Precio | desde 29.99 EUR/mes | desde 49 EUR/mes |
| Modelos AEAT | 50+ | ~15 (expandiendo) |
| Simulacion | No multi-territorial | **21 territorios** |
| Deducciones | No | **~1,008** |
| RAG/fuentes | No | **456+ docs** |
| Forales | No | **Si** |

---

## 5. Modelo de Ingresos

### 5.1 B2C (actual)

| Plan | Precio | ARPU mensual | Target subs Y1 | MRR Y1 |
|------|--------|-------------|-----------------|---------|
| Particular | 5 EUR/mes | 5 | 500 | 2,500 |
| Creator | 49 EUR/mes | 49 | 50 | 2,450 |
| Autonomo | 39 EUR/mes | 39 | 200 | 7,800 |
| **Total B2C** | | | **750** | **12,750 EUR/mes** |

### 5.2 B2B (nuevo — lanzamiento Q3 2026)

| Plan | Precio | Clientes max | Target subs Y1 | MRR Y1 |
|------|--------|-------------|-----------------|---------|
| Starter | 49 EUR/mes | 50 clientes | 100 | 4,900 |
| Professional | 99 EUR/mes | 200 clientes | 50 | 4,950 |
| Enterprise | 199 EUR/mes | Ilimitados | 15 | 2,985 |
| **Total B2B** | | | **165** | **12,835 EUR/mes** |

### 5.3 Proyeccion combinada

| Metrica | Y1 (2027) | Y2 (2028) | Y3 (2029) |
|---------|-----------|-----------|-----------|
| Suscriptores B2C | 750 | 2,500 | 8,000 |
| Suscriptores B2B | 165 | 600 | 2,000 |
| MRR | 25,585 EUR | 85,000 EUR | 280,000 EUR |
| ARR | 307,020 EUR | 1,020,000 EUR | 3,360,000 EUR |
| Churn mensual | 8% | 5% | 3% |

---

## 6. Estructura de Costes

| Concepto | Coste mensual | Notas |
|----------|---------------|-------|
| OpenAI API (GPT-5-mini) | ~500-2,000 EUR | Variable por uso, ~0.5 EUR/usuario activo |
| Railway (hosting) | 20-100 EUR | Frontend + Backend + Workers |
| Turso DB | 0-29 EUR | Free tier hasta 9GB |
| Upstash (Redis + Vector) | 0-20 EUR | Free tier generoso |
| Stripe comisiones | 1.4% + 0.25 EUR | Por transaccion |
| Groq (LlamaGuard4) | 0 EUR | Free tier 14,400 req/dia |
| Resend (emails) | 0-20 EUR | Free tier 3K/mes |
| Dominio + Cloudflare | ~15 EUR/mes | impuestify.com |
| **Total infra** | **~600-2,200 EUR/mes** | |

**Unit economics B2C:** ARPU ~17 EUR/mes, coste marginal ~0.5 EUR → margen ~97%
**Unit economics B2B:** ARPU ~78 EUR/mes, coste marginal ~2 EUR → margen ~97%

---

## 7. Roadmap Producto

### Q2 2026 (actual) — B2C Consolidacion
- [x] Motor IRPF 21 territorios (~1,008 deducciones)
- [x] Chat RAG con 456+ documentos oficiales
- [x] 3 planes suscripcion (Particular/Creator/Autonomo)
- [x] 13 capas seguridad (Turnstile, MFA, LlamaGuard4)
- [ ] GP transmision inmuebles (venta propiedad)
- [ ] 2o declarante conjunta
- [ ] Mejorar RAG quality (context relevance)

### Q3 2026 — B2B MVP
- [ ] Dashboard multi-cliente para asesorias
- [ ] Gestion de cartera (N clientes con perfil fiscal)
- [ ] Exportacion masiva informes IRPF
- [ ] Multi-usuario por despacho (roles: admin, asesor, becario)
- [ ] Alerta proactiva: "3 clientes pueden deducir X"
- [ ] API REST para integracion con A3/Sage

### Q4 2026 — Compliance
- [ ] VeriFactu (obligatorio sociedades 01/01/2027)
- [ ] Factura electronica (Ley Crea y Crece)
- [ ] Historial multi-ejercicio por cliente

### 2027 — Crecimiento
- [ ] App movil (React Native)
- [ ] VeriFactu autonomos (obligatorio 01/07/2027)
- [ ] Integracion bancaria (PSD2/Open Banking)
- [ ] ML: prediccion fiscal + optimizacion
- [ ] B2B Enterprise: white-label para grandes despachos

---

## 8. Go-to-Market B2B

### 8.1 Estrategia de entrada
- **Posicionamiento:** Complemento inteligente a herramientas existentes (no reemplazo)
- **Mensaje:** "Ahorra 5h/semana en consultas fiscales y descubrimiento de deducciones"
- **Canal primario:** Marketing directo a micro-gestorias via LinkedIn + SEO
- **Canal secundario:** Partnerships con colegios de asesores fiscales (AECE, CGE)
- **Evento clave:** Accountex Espana (noviembre 2026)

### 8.2 Timing
- **Febrero:** Mes optimo para captacion (pre-campana renta)
- **Abril-Junio:** Demostraciones en campana renta (valor inmediato)
- **Septiembre:** Lanzamiento B2B plan Starter
- **Noviembre:** Accountex Espana — stand + demo

### 8.3 Primeros 100 clientes B2B
1. Beta cerrada con 10 gestorias (amigos/referidos) — Q3 2026
2. Oferta early bird: 50% descuento primer ano
3. Case studies con metricas de ahorro de tiempo
4. Referral program: 1 mes gratis por referido

### 8.4 Decision factors para cambio de herramienta
1. **ROI demostrable** — "ahorra X horas/semana" con datos concretos
2. **Confianza/precision** — citas a fuentes oficiales (no-negociable)
3. **Facilidad de adopcion** — <30 minutos hasta primer valor
4. **Complemento, no reemplazo** — se integra con A3/Sage existente

---

## 9. Equipo y Recursos

| Rol | Persona | Dedicacion |
|-----|---------|-----------|
| CEO / Producto / Dev | Fernando Prada | Full-time |
| IA / Backend | Claude Code (Opus 4.6) | Agente continuo |
| Multi-agente | RuFlo V3.5 (259 tools) | Workflow automatizado |
| QA | Playwright + agentes QA | Automatizado |
| Marketing | Redes sociales (3 canales) | Part-time |

### Necesidades de contratacion (post-revenue)
- Developer frontend/mobile (Q3 2026)
- Sales B2B / Account manager (Q4 2026)
- Customer success para gestorias (2027)

---

## 10. Metricas Clave (KPIs)

### B2C
- MAU (Monthly Active Users)
- Conversion rate (free → paid)
- Churn mensual (<5% target)
- NPS (>50 target)
- RAG quality score (>80% target)

### B2B
- Gestorias activas
- Clientes gestionados por gestoria
- Tiempo ahorrado por gestoria/semana
- Revenue per gestoria (ARPU)
- Logo retention (>90% annual)

---

## 11. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|-------------|---------|------------|
| AEAT lanza herramienta propia con IA | Media | Alto | Diferenciacion en UX, forales, deducciones proactivas |
| TaxDown entra en B2B | Media | Medio | First-mover en forales, pricing agresivo |
| Regulacion IA (AI Act) | Alta | Medio | Cumplimiento proactivo, transparencia en fuentes |
| Alucinaciones fiscales | Media | Muy alto | RAG con fuentes, disclaimer, 13 capas seguridad |
| Escalabilidad costes OpenAI | Media | Medio | Modelos ligeros (mini), cache semantica, limites |
| VeriFactu complejidad tecnica | Media | Medio | Priorizar sociedades primero, autonomos despues |

---

## 12. Business Model Canvas (Actualizado)

```
+-------------------+-------------------+-------------------+-------------------+-------------------+
| ASOCIACIONES      | ACTIVIDADES       | PROPUESTA VALOR   | REL. CLIENTES     | SEGMENTOS         |
| CLAVE             | CLAVE             |                   |                   | CLIENTE           |
|                   |                   |                   |                   |                   |
| OpenAI/Groq       | Motor IRPF        | B2C: Asistente    | Chat IA 24/7      | Particulares      |
| AEAT/BOE          | (+1000 deducc.)   | fiscal IA 21      | Guia fiscal 7     | (20M declarantes) |
| Cloudflare        | Crawler docs      | territorios       | pasos             |                   |
| Stripe            | (90 URLs)         | (incl. forales)   | Alertas plazos    | Creadores         |
| Railway           | Auditorias CCAA   | +1000 deducciones | Sistema feedback  | (285K en Espana)  |
| Resend            | IA multi-agente   | 1/30 coste asesor |                   |                   |
| Upstash           |                   | Cumplimiento RGPD | B2B: Dashboard    | Autonomos         |
|                   | B2B: Dashboard    |                   | multi-cliente     | (3.3M)            |
|                   | multi-cliente     | B2B: Consulta IA  | API integracion   |                   |
|                   | VeriFactu         | para asesorias    | Alertas proact.   | Gestorias         |
|                   | API integracion   | 6-10x mas barato  | deducciones       | (52,400 empresas) |
|                   |                   | que A3/Sage       |                   |                   |
+-------------------+-------------------+-------------------+-------------------+-------------------+
| RECURSOS CLAVE    |                                                           | CANALES           |
|                   |                                                           |                   |
| Stack: FastAPI +  |                                                           | App web PWA       |
| React + GPT-5     |                                                           | (impuestify.com)  |
| 456+ docs RAG     |                                                           | Landings SEO      |
| Motor 1000 deducc |                                                           | territoriales     |
| Railway/Turso     |                                                           | LinkedIn+IG+TikTok|
| 13 capas segurida |                                                           | Accountex Espana  |
|                   |                                                           | Colegios asesores |
+-------------------+-------------------+-------------------+-------------------+-------------------+
| ESTRUCTURA DE COSTES                  | FUENTES DE INGRESOS                                     |
|                                       |                                                          |
| API OpenAI (variable, ~0.5 EUR/user)  | B2C: Particular 5 EUR/mes, Creator 49, Autonomo 39      |
| Hosting Railway (~100 EUR/mes)        | B2B: Starter 49, Professional 99, Enterprise 199 EUR/mes|
| DB Turso (free-29 EUR/mes)            | Target Y1 MRR: 25,585 EUR (B2C 12,750 + B2B 12,835)    |
| Comisiones Stripe (1.4%)              | Target ARR Y3: 3,360,000 EUR                            |
| Desarrollo (1 persona + IA)           |                                                          |
+---------------------------------------+----------------------------------------------------------+
```

---

## 13. Resumen Ejecutivo

Impuestify es el unico asistente fiscal con IA en Espana que cubre los 21 territorios fiscales, incluyendo los 4 territorios forales del Pais Vasco y Navarra que TaxDown no cubre (~1.6M declarantes sin alternativa digital).

Con ~1,000 deducciones automaticas, 456+ documentos oficiales indexados y un simulador IRPF validado en 4 territorios (Aragon, Melilla, Canarias, Bizkaia), la plataforma esta lista para escalar de B2C a B2B.

El segmento B2B de asesorias fiscales (52,400 empresas) esta desatendido por herramientas asequibles con IA. A3 ASESOR cuesta 3,500-5,500 EUR/ano y no tiene IA nativa. Impuestify puede ofrecer el mismo valor a 588-2,388 EUR/ano con IA integrada, descubrimiento proactivo de deducciones y cobertura territorial completa.

**Objetivo 2027:** 750 suscriptores B2C + 165 asesorias B2B = 25,585 EUR MRR = 307K EUR ARR.
