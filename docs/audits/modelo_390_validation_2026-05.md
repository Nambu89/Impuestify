# Auditoría Modelo 390 — Resumen Anual IVA (2026-05)

**Modelo**: 390 (Declaración-resumen anual del IVA)
**Norma**: Orden EHA/3111/2009 (modelo 390) + modificaciones (Orden HFP/417/2017, Orden HAC/1395/2021, etc.)
**Excepción**: Art. 71.7 RIVA (sujetos en SII / REDEME → exonerados desde 2017)
**Plazo**: 1 al 30 de enero del año siguiente
**Estado en TaxIA**: **GAP FUNCIONAL — NO HAY IMPLEMENTACIÓN**

---

## Fase 1 · Inventario en TaxIA

Búsqueda exhaustiva (`Glob backend/**/modelo_390*` + `Grep "390" backend/`):

| Componente | Existe | Ubicación / Comentario |
|---|---|---|
| Calculadora dedicada (`modelo_390.py`) | NO | No existe en `backend/app/utils/calculators/` (solo 303, 130, 420, ipsi). |
| Tool LLM (`calculate_modelo_390`) | NO | No registrada en `app/tools/__init__.py` (no existe carpeta `app/tools/` siquiera para algunas refs; sólo tools listadas no incluye 390). |
| Endpoint REST | NO | `routers/export.py` `/api/export/modelo-pdf` excluye 390: `VALID_MODELOS = {"303","130","200","308","720","721","ipsi"}` (`modelo_pdf_generator.py:32`). |
| Generador PDF | NO | `ModeloPDFGenerator` no contempla 390. |
| Simulador / wizard frontend | NO | `frontend/src/pages/ModelObligationsPage.tsx` solo lo menciona en SEO meta-tags, sin UI de cálculo. |
| Seed deadlines | SÍ | `scripts/seed_estatal_deadlines.py:211-218` registra obligación anual `model="390"` con plazo enero. |
| Calendario obligaciones (`territories/base.py`) | SÍ (mención) | `is_390 → resumen_390 → "2026-01-30"` listado en `DEADLINES_2026`. |
| Sustitución foral / Canarias | PARCIAL | `territories/canarias/plugin.py:79` añade resumen 425 IGIC en lugar de 390 (correcto). País Vasco / Navarra: sin equivalente explícito. |
| Exoneración SII / RE (farmacéutico) | SÍ (texto) | `modelo_303.py:60` y `tax_agent.py:925` documentan que farmacéuticos en RE no presentan 390. NO hay exoneración explícita por SII / REDEME / grandes empresas. |
| Cross-check casillas 303→390 | NO | No existe módulo de proyección/sumatorio anual. |

**Conclusión inventario**: TaxIA **reconoce** la obligación 390 (calendario + system prompts) pero **NO calcula, NO genera PDF y NO simula** este modelo.

---

## Fase 2 · Normativa de referencia

Fuentes consultadas (no fetched online — solo URLs registradas en `scripts/doc_crawler/watchlist.py`):

| Recurso | URL | Estado en repo |
|---|---|---|
| Sede AEAT Modelo 390 | https://sede.agenciatributaria.gob.es/Sede/iva-otros-impuestos/declaraciones-informativas/modelo-390.html | No descargado |
| Instrucciones Modelo 390 2025 (PDF) | `static_files/Sede/Programas_Ayuda/Modelo390/2025/Instrucciones_Modelo390_2025.pdf` | Watchlist `status="active"`, pendiente publicación AEAT |
| Diseño Registro DR390 e2025 | `DR390_e2025.xlsx` | Watchlist `status="future"` |
| Orden EHA/3111/2009 | BOE | No en repo |
| Art. 71.7 RIVA (exoneración) | RD 1624/1992 | No en repo |
| Orden HFP/417/2017 (SII) | BOE | No en repo |

**Estructura normativa del 390** (para futura implementación):
- ~140 casillas distribuidas en 10 apartados (1 Sujeto pasivo, 2 Devengo, 3 Datos estadísticos, 4 IVA Devengado régimen general, 5 IVA Deducible, 6 Resultado liquidación anual, 7 Tributación conjunta, 8 Resultado liquidaciones, 9 Volumen operaciones, 10 Operaciones específicas).
- Sumatorio de los **4 modelos 303 trimestrales** + ajustes (regularización prorrata, bienes inversión, modificación BI).
- Datos identificativos del volumen de operaciones por epígrafe IVA, exentas, exportaciones, intracomunitarias, ISP, inversión, etc.

**Sujetos exonerados (Art. 71.7 RIVA + Disp. Adic. única HFP/417/2017)**:
1. Empresas en **SII** (volumen > 6.010.121 € + REDEME + grupos IVA).
2. Sujetos que tributan exclusivamente en **régimen simplificado** o por **arrendamiento urbano** (siempre que sustituyan el 390 por el modelo 303 4T con datos adicionales).
3. Sujetos en **Recargo de Equivalencia exclusivo** sin obligación de presentar 303.

---

## Fase 3 · Cross-check con código existente

| Mapeo esperado | Implementado | Notas |
|---|---|---|
| Σ(303 1T-4T) → casillas 390 IVA devengado/deducible | NO | `Modelo303Calculator.calculate()` solo devuelve resultado trimestral (`resultado`, `cuota_devengada`, `iva_deducible`). Falta agregador anual. |
| Detección automática de exoneración por SII | NO | El código solo exonera si `situacion_laboral == "farmaceutico"` (RE). No comprueba volumen > 6 M€ ni alta REDEME ni grupos IVA. |
| Datos estadísticos volumen operaciones (apartado 9) | NO | Modelo 303 no captura desglose anual por epígrafe ni operaciones exentas/exportaciones agregadas. |
| Regularización bienes inversión (casilla específica) | NO | No implementado en `modelo_303.py`. |
| Sustitución por Canarias (resumen 425) | SÍ | `canarias/plugin.py:79-91` ya añade 425 anual; correcto. |
| Sustitución foral (Bizkaia 391, Gipuzkoa, Álava, Navarra F-66) | NO | No hay plugins forales para resumen anual IVA. |

---

## Fase 4 · Casos prácticos

No se han ejecutado casos por **inexistencia de calculadora**. Cuando se implemente, los casos mínimos a cubrir son:

1. **Autónomo Régimen General Madrid** — sumatorio de 4 modelos 303 sin regularización prorrata.
2. **Autónomo con prorrata especial** — regularización en casillas finales.
3. **Empresa en SII (>6 M€)** — debe devolver `obligado=False` con motivo legal.
4. **Farmacéutico (RE)** — `obligado=False` (ya cubierto por `is_recargo_equivalencia()`).
5. **Sujeto en Canarias** — debe redirigir a 425 IGIC (cubierto por plugin Canarias).
6. **Régimen simplificado puro (módulos)** — exonerado, sustituido por 303 4T con datos adicionales.
7. **Operaciones intracomunitarias + exportaciones** — apartado 9 datos estadísticos volumen.

---

## Fase 5 · Simulador

**No existe simulador para Modelo 390** ni en backend (`/api/irpf/estimate` solo cubre IRPF) ni en frontend (`/calculadora-*` no incluye 390). El usuario sólo ve la obligación listada en `/modelos-obligatorios` con su plazo de enero.

---

## Fase 6 · Resultado final

### Conclusión

Modelo 390 figura en TaxIA únicamente como **referencia textual** (system prompts del TaxAgent, calendario de obligaciones, watchlist de docs AEAT, SEO meta-tags). **No hay lógica de cálculo, generación de PDF, simulador ni detección automática de exoneraciones más allá de Recargo de Equivalencia**.

### Cobertura

| Aspecto | Cobertura |
|---|---|
| Mención en sistema | 100 % |
| Calendario / plazos | 100 % |
| Cálculo / sumatorio anual | 0 % |
| PDF | 0 % |
| Simulador UI | 0 % |
| Detección exoneración SII / REDEME / grupos | 0 % |
| Sustitución Canarias (425) | 100 % |
| Sustitución foral (391/F-66) | 0 % |
| Régimen Equivalencia (no obliga) | 100 % |

### Recomendaciones (priorizadas)

1. **P0 · Detección exoneración SII**: añadir flag `obligado_sii` en `user_profiles.datos_fiscales` y campo `volumen_operaciones_ano_anterior`. Si `volumen > 6.010.121` o `alta_REDEME=True` o `grupo_iva=True` → marcar 390 como `obligado=False` con motivo Art. 71.7 RIVA. Bajo coste, alto impacto compliance.
2. **P1 · Calculadora `modelo_390.py`**: nueva clase `Modelo390Calculator` que reciba 4 instancias de resultado de `Modelo303Calculator` + ajustes prorrata + regularización bienes inversión y devuelva las ~140 casillas. Test regresión con caso AEAT sintético.
3. **P1 · Endpoint `/api/iva/resumen-anual`**: similar a `/api/irpf/estimate`, sin LLM, ~100 ms, recibe los 4 trimestres y retorna JSON con casillas + resultado anual.
4. **P2 · PDF**: extender `VALID_MODELOS` en `modelo_pdf_generator.py` y añadir template 390.
5. **P2 · Frontend wizard**: nueva ruta `/calculadora-resumen-iva` que recoja los 4 303 (manual o autocomplete desde workspace) y muestre simulación.
6. **P2 · Plugins forales**: añadir `bizkaia/plugin.py`, `gipuzkoa/plugin.py`, `alava/plugin.py`, `navarra/plugin.py` con sustitutos 391 / F-66 análogos a `canarias/plugin.py` con 425.
7. **P3 · Watchlist activa**: monitorizar `Instrucciones_Modelo390_2025.pdf` (actualmente `status="active"` pero sin publicación AEAT — verificar tras enero 2026).

### Riesgo regulatorio

**MEDIO-ALTO**: el 390 es obligación informativa anual con sanción por no presentación (Art. 198 LGT, mínimo 150 €). Si TaxIA orienta a un autónomo que ese 390 no le aplica sin verificar SII/REDEME/RE/Canarias, asume riesgo de información fiscal incorrecta.

### Acción inmediata sugerida

Añadir disclaimer en TaxAgent system prompt cuando se mencione Modelo 390:
> "Modelo 390 NO se calcula automáticamente en TaxIA. Verifica si estás exonerado (SII, REDEME, RE) consultando Art. 71.7 RIVA. Plazo: 1-30 enero."

---

**Auditor**: Subagente researcher (Opus 4.7)
**Fecha**: 2026-05-10
**Commit base**: `f16dcf8`
