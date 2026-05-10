# Auditoría Modelo 349 — Declaración recapitulativa de operaciones intracomunitarias

> **Fecha**: 2026-05-10
> **Auditor**: Claude Opus 4.7 (auditor fiscal técnico)
> **Alcance**: backend `app/`, frontend `src/`, scripts y RAG
> **Veredicto global**: **GAP FUNCIONAL CRÍTICO** — el frontend (CreatorsPage, IvaCreatorsPage, ModelObligationsPage, Pricing) y el system prompt del agente venden "Modelo 349 automático", pero el backend **no implementa cálculo, generación, validación VIES ni umbral 50.000 €**. Solo declara la obligación informativa y reconoce el campo en el extractor de PDFs ya rellenados.

---

## 1. Inventario de implementación encontrada

| Componente | Archivo | Qué hace | Qué NO hace |
|-----------|---------|----------|-------------|
| Obligación informativa | `backend/app/territories/base.py:295-303, 514-522` | Añade `ModelObligation(modelo="349", periodicidad="trimestral")` cuando `tiene_ops_intracomunitarias=True` para autónomos y sociedades | No distingue mensual/trimestral por umbral 50.000 €. No anual. No bimestral |
| Plugins territoriales | `territories/canarias/plugin.py:67-100`, `territories/ceuta_melilla/plugin.py:72-89` | Fuerzan `tiene_ops_intracomunitarias=False` (correcto: no es territorio IVA armonizado UE) | OK |
| Extractor PDF declaración | `services/declaration_extractor.py:233` | Mapea casillas 10 (`base_intracomunitarias`) y 12 (`cuota_intracomunitarias`) del **303**, no del 349 | No extrae 349 |
| Watchlist crawler | `scripts/doc_crawler/watchlist.py:587-595, 822-829` | Descarga `Instrucciones_Modelo349.pdf` AEAT + página HTML | Queda como doc RAG, no se parsea a estructura |
| Calendario fiscal | `scripts/sync_fiscal_calendar.py:62` | Reconoce regex `modelo\s*349` para clasificar deadlines | OK informativo |
| Defensa fiscal (DefensIA) | `services/defensia_rules/reglas_otros_tributos/R023_iva_intracomunitaria.py` | Regla R023: defensa contra denegación de exención EIB por defecto formal en VIES o 349 (doctrina C-146/05 *Collee*). 14 tests verdes | Es defensiva, no presentadora |
| Field flag estimate | `routers/irpf_estimate.py:248, 628-630` | Devuelve `modelo_349_requerido: bool` a frontend si Creator tiene `ingresos_intracomunitarios > 0` | Es solo flag booleano sin importes ni claves |
| Frontend wizard checkbox | `frontend/src/pages/ModelObligationsPage.tsx:222` | Checkbox "Operaciones intracomunitarias" y muestra obligación | No recoge importes, claves, NIF clientes |
| Frontend marketing | `pages/CreatorsPage.tsx:34, 91`, `IvaCreatorsPage.tsx:225, 644-649` | Promete "Modelo 349 automático" + menciona umbral 50.000 € + ROI | Promesa NO respaldada por backend |
| **NO existe** | `backend/app/tools/modelo_349_tool.py` | — | **Sin tool LLM** |
| **NO existe** | `backend/app/utils/calculators/modelo_349.py` | — | **Sin calculadora** |
| **NO existe** | `backend/app/services/modelo_pdf_generator.py` (349 case) | — | **Sin PDF** (solo 303/130/308/720/721/IPSI/300/F69/420) |
| **NO existe** | endpoint `/api/modelo-349/*` | — | **Sin API dedicada** |
| **NO existe** | validador VIES (`pyvies` o consulta REST) | — | **Sin verificación NIF-IVA** |
| **NO existe** | tabla `modelo_349_operaciones` | — | **Sin persistencia operaciones** |
| **NO existe** | `tests/test_modelo_349.py` | — | **Cobertura cero** |

---

## 2. Normativa aplicable (verificada)

| Norma | Contenido | URL |
|-------|-----------|-----|
| **Orden EHA/769/2010** | Aprueba modelo 349, claves de operación, plazos. Vigente con modificaciones (Orden HFP/417/2017, HAC/174/2020) | BOE-A-2010-5098 |
| **Reglamento IVA (RD 1624/1992) Art. 78-81** | Obligación de declaración recapitulativa, contenido, plazos | — |
| **Ley IVA 37/1992 Art. 25** | Exención entregas intracomunitarias (requiere NIF-IVA del adquirente en VIES) | — |
| **Directiva 2006/112/CE Art. 262-271** | Marco UE armonizado declaración recapitulativa | — |
| **STJUE C-146/05 Collee** | Sustancia > forma. Aplicada en R023 de DefensIA ✅ | — |
| **Censo VIES** | Validación NIF-IVA UE | https://ec.europa.eu/taxation_customs/vies/ |

---

## 3. Cross-check: lo que falta vs. normativa

### 3.1. Claves de operación (Art. 4 Orden EHA/769/2010)

El modelo 349 exige declarar cada operación con su clave. **TaxIA no las maneja en absoluto**:

| Clave | Significado | Implementado |
|-------|-------------|--------------|
| **E** | Entregas intracomunitarias exentas (Art. 25 LIVA) | ❌ |
| **A** | Adquisiciones intracomunitarias sujetas | ❌ |
| **T** | Operaciones triangulares (Art. 26.Tres LIVA) | ❌ |
| **S** | Prestaciones intracomunitarias de servicios (Art. 69.Uno.1º LIVA) | ❌ |
| **I** | Adquisiciones intracomunitarias de servicios | ❌ |
| **M** | Entregas tras importaciones exentas (Art. 27.12º LIVA) | ❌ |
| **H** | Entregas tras importaciones exentas — sujeto pasivo representante | ❌ |
| **R** | Transferencias destinadas a ventas en consigna (Art. 9 bis LIVA) | ❌ |
| **D** | Devoluciones de consignaciones | ❌ |
| **C** | Sustituciones de adquirente en consignaciones | ❌ |
| **N** | Rectificaciones de períodos anteriores | ❌ |

### 3.2. Periodicidad y umbrales (Art. 10 Orden EHA/769/2010)

| Periodicidad | Umbral | Plazo presentación | Implementado |
|--------------|--------|---------------------|--------------|
| **Mensual** (regla general) | EIB+PIS > 50.000 € en trimestre actual o cualquiera de los 4 anteriores | Días 1-20 mes siguiente (julio: hasta 20 ago; diciembre: hasta 30 ene) | ❌ Solo declara "trimestral" hardcoded |
| **Trimestral** | EIB+PIS ≤ 50.000 € | Días 1-20 mes siguiente al trimestre (4T: hasta 30 ene) | ⚠️ Parcial (etiqueta sin lógica de umbral) |
| **Anual** | EIB+PIS año natural ≤ 35.000 € **y** EIB exentas ≤ 15.000 € | Días 1-30 enero año siguiente | ❌ |
| **Cambio mensual mid-trimestre** | Si se supera 50.000 € en mes 1-2 del trimestre, presentar mensual desde ese mes | — | ❌ |

`base.py:302` codifica `_trimestral_deadlines("349")` sin cálculo dinámico.

### 3.3. Validación NIF-IVA / ROI

- **Requisito legal**: NIF-IVA del adquirente UE válido en VIES en el momento del devengo (Art. 25 LIVA + STJUE *Collee*).
- **Implementado en TaxIA**: 0%. La página `IvaCreatorsPage.tsx:230` solo muestra texto: "Debes estar dado de alta en el ROI". Sin verificación.
- **Recomendación**: integrar consulta REST a https://ec.europa.eu/taxation_customs/vies/services/checkVatService (SOAP/REST público, sin auth) con cache 24h.

### 3.4. Coherencia 303 ↔ 349

El 303 declara importes intracomunitarios agregados (casillas 10/12 IVA devengado por AIB; 36/37 IVA deducible por AIB; 59/60 EIB exentas). **El 349 detalla operación por operación** y la suma debe cuadrar con el 303 del mismo período. TaxIA **no implementa cuadre 303↔349**, principal causa de requerimientos AEAT.

---

## 4. Casos prácticos no cubiertos

| Caso | Estado |
|------|--------|
| Creador con ingresos Google Ireland (clave S) > 50.000 €/trim → mensual | ❌ |
| Autónomo con AIB de software EU (clave I) | ❌ |
| Operación triangular ES→DE→FR (clave T, declarante intermediario) | ❌ |
| Rectificación importe período anterior (clave N) | ❌ |
| Consignación stock Amazon FBA-DE (claves R/D/C, post Brexit + reforma 2020) | ❌ |
| EIB con NIF cliente no validado en VIES → riesgo denegación exención | ❌ (DefensIA R023 sí defiende a posteriori) |
| Plazo agosto: 4T mensual de julio se presenta en agosto (no septiembre) | ⚠️ Calendario hardcoded sin esta excepción |

Manual AEAT IVA 2025 capítulo 9 contiene 18 ejemplos prácticos de 349. Ninguno está reflejado en código.

---

## 5. Simulador y validador

- **Simulador 349**: **NO EXISTE**. No hay endpoint público `/api/modelo-349/estimate`, ni hook React, ni página `/calculadora-349`.
- **Validador VIES**: **NO EXISTE**. Pese a estar mencionado en R023 (DefensIA), el sistema no consulta VIES en runtime.
- **Generador PDF**: NO soportado por `modelo_pdf_generator.py` (solo 303/130/308/720/721/IPSI/300/F69/420 — confirmado en `CLAUDE.md` raíz).

---

## 6. Riesgos comerciales y legales

| Riesgo | Severidad | Detalle |
|--------|-----------|---------|
| **Publicidad engañosa Plan Creator** | 🔴 Alta | `CreatorsPage.tsx:34` y comparativa `IvaCreatorsPage.tsx:91` listan "Modelo 349 automático" como feature incluida en plan 49 €/mes. **No existe**. Riesgo LGDCU Art. 7 (omisiones engañosas) y Art. 5 (publicidad ilícita). |
| **Cuadre 303↔349 ausente** | 🔴 Alta | Causa nº1 de requerimientos AEAT en operadores intracomunitarios. Cliente puede recibir paralela. |
| **Sin VIES check** | 🟠 Media | Riesgo denegación exención Art. 25 LIVA si NIF cliente UE inválido. R023 defiende a posteriori, pero no previene. |
| **Periodicidad hardcoded trimestral** | 🟠 Media | Creator que supere 50.000 €/trim debe presentar mensual. TaxIA dirá "trimestral" → recargo Art. 27 LGT por presentación fuera de plazo. |
| **Canarias/Ceuta/Melilla bien resuelto** | 🟢 OK | Plugins fuerzan `False`. Frontend `IvaCreatorsPage.tsx:663-680` lo explica. |
| **Brexit/UK** | 🟢 OK | `IvaCreatorsPage.tsx` trata TikTok/Twitch UK como importación, no intracomunitario. Correcto. |
| **R023 DefensIA** | 🟢 OK | Doctrina *Collee* bien aplicada con cita semántica + RAG verificador. |

---

## 7. Recomendaciones priorizadas

### P0 — Antes de cobrar Plan Creator (49 €/mes)
1. **Retirar promesa "Modelo 349 automático"** de `CreatorsPage.tsx`, comparativa y FAQ hasta que esté implementado, o ajustar a "Aviso de obligaciones 349" (lo único real hoy).
2. **Disclaimer explícito** en `IvaCreatorsPage.tsx`: "Cálculo informativo. La presentación del 349 requiere uso de Sede AEAT".

### P1 — Backend MVP (1-2 sprints)
3. Crear `app/utils/calculators/modelo_349.py`:
   - Modelo `Operacion349 { nif_operador: str, nombre: str, clave: Literal['E','A','T','S','I','M','H','R','D','C','N'], importe: Decimal, rectificacion: Optional[...] }`
   - `calcular_periodicidad(operaciones, año) -> Literal['mensual','trimestral','anual']` con umbral 50.000 €/trim y 35.000 €/año
   - `validar_cuadre_con_303(ops_349, importes_303) -> CuadreResult`
4. Crear `app/tools/modelo_349_tool.py` registrado en `ALL_TOOLS` para que CoordinatorAgent pueda llamarlo.
5. Crear `app/services/vies_validator.py` con consulta REST a `https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number` + cache Redis 24h.
6. Endpoint `POST /api/modelo-349/estimate` (público, sin LLM, ~100ms, paralelo a `/api/irpf/estimate`).
7. Tests `tests/test_modelo_349.py`: claves operación, umbrales, cuadre 303, casos manual AEAT.

### P2 — Generación documental (3-4 sprints)
8. Soporte `349` en `modelo_pdf_generator.py` (replicar layout AEAT instrucciones).
9. Generador fichero TXT formato AEAT (registro tipo 1 cabecera + tipo 2 detalle) para presentación.
10. Wizard frontend `/modelo-349` con upload CSV operaciones + autocompletado NIF-IVA via VIES.

### P3 — Defensa preventiva
11. Pre-validar cada operación contra VIES antes de cerrar trimestre y avisar al usuario (complementa R023 DefensIA, que solo actúa post-denegación).

---

## 8. Conclusión

TaxIA tiene **arquitectura preparada** (plugin territorial, flag perfil, watchlist, regla DefensIA, campo response) pero **cero capa de cálculo y presentación** del Modelo 349. El frontend lo vende como feature core del Plan Creator. **Gap producto-marketing crítico**. La regla R023 de DefensIA es lo único técnicamente sólido del módulo y opera en defensa, no en presentación.

**Acción inmediata recomendada**: P0 (retirar promesa) hoy, P1 en sprint 40-41, P2 en sprint 42-43.
