---
name: project_session35_humanizer_legal
description: Sesion 35 (2026-04-20 a 2026-04-27) — outreach Ayudat/Laborai, humanizer Wikipedia 40 archivos, paginas legales con titular real, /sobre-mi, Demo/ Alfredo, Bug 85 + 86
type: project
---

# Sesion 35 — Humanizer + Legal + Outreach Ayudat (2026-04-20 a 2026-04-27)

## Contexto

Tras mergear DefensIA y Modelo 200 a main en sesion 34, entramos en fase de **commercial outreach + polish**. El detonante fue una conversacion con Alfredo Perez, CEO de Ayuda T Pymes (>20.000 clientes, ~600 empleados). Su feedback nos dio el roadmap de mejoras de la sesion:

1. "No me queda claro entrando en tu web que resuelve" → reescribimos hero + creamos seccion "Que puedes hacer".
2. "No encuentro el CIF en los terminos legales de la web" → componente LegalEntity con DNI Fernando.
3. "Si me puedes enviar una demo o video" → carpeta Demo/ con guion 7 min + 4 PDFs AEAT simulados.

## Trabajo realizado

### Outreach comercial (2026-04-20 a 2026-04-23)

- **Email 1 a Alfredo Perez** (CEO Ayudat, alfredoperez@ayudat.es): propuesta de licencia B2B2C del motor IA fiscal, con acceso a las 3 cuentas test + presentacion DOCX adjunta + propuesta de videollamada.
- **Respuesta Alfredo en LinkedIn**: pide contexto producto + empresa + demo. Ofrece su email personal y videollamada.
- **Email 2 a Alfredo**: contexto honesto (founder unico, sin SL constituida aun, fase onboarding primeros clientes), explicacion de que SI/NO hace Impuestify, accesos test, plan para video Loom 48h.
- **Mensaje LinkedIn corto**: redactado para complementar el email, listo para que Fernando lo envie.
- **Email a Laborai**: pendiente de envio (queda en backlog).

### Hotfix Bug 84 (2026-04-20)

Endpoints DefensIA frontend llamaban a `/defensia/...` sin prefix `/api/`. Producccion daba 404 al entrar a `/defensia`. Fix en 9 call sites. Ver `bugfixes-2026-04.md` Bug 84.

### Cleanup repo + landing limpia (2026-04-20)

- 23 fragmentos de codigo basura borrados del root (residuos de paste rotos: `({`, `[...prev`, `parseDeductions(content)`, etc.).
- `.gitignore` ampliado: `vectors.db`, vite timestamps, Playwright reports, QA tests por sesion/fecha.
- README reescrito con tono visual cliente, logo, screenshots Capterra, 3 pricing cards.
- DOCX comercial generado (`Impuestify_Presentacion_Cliente.docx`).
- Manual Usuario v3: nueva seccion 10bis Modelo 200 IS.

### Paginas legales con titular real (2026-04-23, Bug 85)

- Componente `LegalEntity.tsx` reusable.
- `legalData.ts` centralizado con datos titular (DNI 45308568V, Calle Monasterio Rueda 1, 50007 Zaragoza).
- Nueva pagina `/aviso-legal` (LSSI-CE Art. 10).
- Insertado en TermsPage, PrivacyPolicyPage, CookiePolicyPage.
- Footer con link "Aviso Legal".
- Cuando se constituya la SL, solo hay que actualizar `legalData.ts` con CIF + Registro Mercantil.

### Humanizer Wikipedia AI Cleanup — 3 fases (2026-04-23)

Skill basada en [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) aplicada a todo el copy visible al usuario. **40 archivos** modificados.

**Fase 1** (commit 82c63cb): Home.tsx — hero subtitle, section titles, feature cards, stats actualizadas (463 docs, 1000+ deducciones, 17 CCAA + Ceuta/Melilla).

**Fase 2** (commit 737e8f2, 5 subagentes paralelos): TaxGuidePage, CreatorsPage, ClasificadorFacturasPage, DefensIA (3 paginas + 2 componentes), Modelo200Page, Modelo202Page.

**Fase 3** (commit b88551f, 4 subagentes paralelos): Chat.tsx + 5 widgets, CookieConsent, Footer, AITransparencyModal/Page, DataRetentionPage, ContactPage, 6 calculadoras publicas, FarmaciasPage, ModelObligationsPage, emails backend (auth.py, email_service.py, push_service.py), useSEO meta en 17 paginas.

Patrones eliminados: copula avoidance, participios `-ing` superfluos, rule of three forzado, promotional language, spam verbs (Descubre/Explora/Transforma), title case en headings, emojis decorativos, em-dashes retoricos, generic positive conclusions.

### Pagina /sobre-mi (2026-04-23, commit 9bf789c)

- Nueva pagina `/sobre-mi` con la historia del fundador en primera persona.
- Sacada de la landing porque Fernando queria home limpia.
- 5 parrafos firmados "Fernando Prada, fundador" + CTA email contacto.
- Link en Footer bajo el tagline.

### Demo para Alfredo (2026-04-24)

Carpeta `Demo/` con todo el material para grabar un video de 7 minutos:
- `README.md` + `GUION_DEMO_COMPLETO.md` con timing herramienta a herramienta.
- 4 PDFs AEAT simulados generados con script reportlab (`generar_pdfs.py`):
  - Propuesta liquidacion provisional IRPF Madrid
  - Requerimiento documentacion IVA Barcelona
  - Propuesta sancionador 303 fuera de plazo Sevilla
  - Inicio comprobacion limitada IRPF Valencia
- Briefs de ejemplo para pegar en cada caso.
- Escenarios IRPF (4 perfiles) + escenarios IS (4 SL) + escenarios calculadoras publicas.
- Plantillas basadas en formato real de la AEAT (fuentes: SuperContable, OCU, Calzadilla Abogados, sede AEAT).

### Bug 86 — variantes CCAA (2026-04-27, commit 565d324)

`/declaraciones` no detectaba CCAA forales/IGIC/IPSI cuando el perfil tenia variantes ("Pais Vasco" generico, "Vizcaya" antiguo, mayusculas inconsistentes). Fix con deteccion case-insensitive + flag `isPaisVascoGenerico`. Ver `bugfixes-2026-04.md` Bug 86.

### Correccion 17 CCAA vs 15 (2026-04-23, commit a080613)

Error factual detectado por usuario: textos decian "15 CCAA + 4 forales + Ceuta/Melilla" cuando son **17 CCAA** (15 regimen comun + 2 forales: Pais Vasco y Navarra) **+ 2 ciudades autonomas**. Corregido en Home, README, DOCX comercial. Backend mantiene "15 CCAA regimen comun" porque ahi describe el subgrupo especifico.

## Commits de la sesion (en orden)

```
20bf545 fix(defensia): prefix /api/ en endpoints del frontend (Bug 84)
8f7932c feat(defensia): anadir boton "Volver a inicio" en las paginas DefensIA
fe022dd chore: cleanup repo + README visual + docs sync
0abe6b8 feat(legal): anadir identificacion del titular en paginas legales (LSSI-CE + RGPD)
3c368d7 feat(landing): clarificar que hace Impuestify en el home
12cae96 feat(landing): anadir seccion "De donde viene Impuestify" en el home
a080613 fix(copy): corregir numero de CCAA en landing y docs (17, no 15)
9bf789c feat(landing): mover "Sobre mi" a su propia pagina y limpiar el home
82c63cb style(landing): humanizar textos del home (patron Humanizer/WikiProject AI Cleanup)
737e8f2 style(ui): humanizar textos de 9 paginas clave de Impuestify (fase 2 Humanizer)
b88551f style(ui+emails+seo): humanizar chat, widgets, emails y meta SEO (fase 3 Humanizer)
565d324 fix(declaraciones): detectar variantes de CCAA en perfil para mostrar modelos forales/IGIC/IPSI
```

## Pendientes priorizados

1. **Grabar video Loom 7 min** siguiendo `Demo/GUION_DEMO_COMPLETO.md`.
2. **Enviar a Alfredo** el video + el mensaje LinkedIn con accesos test.
3. **Constituir SL** — bloqueador para enterprise B2B con Ayudat. Sin SL no hay firma.
4. **Outreach Laborai** — email pendiente de envio.
5. **Humanizer fase 4 (opcional)**: 14 paginas publicas sin `useSEO`, system prompt backend (NO tocar — tecnico), Manual Usuario v3 + README.
6. **Bug Workspace upload mobile prod** — bug abierto desde sesion 28.
