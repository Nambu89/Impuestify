# Auditoría Modelo 131 — Pago Fraccionado IRPF Estimación Objetiva (Módulos)

> **Fecha**: 2026-05-10
> **Auditor**: Subagente researcher (TaxIA)
> **Alcance**: Implementación backend + frontend del Modelo 131 en TaxIA (Impuestify)
> **Veredicto global**: **GAP CRÍTICO** — Modelo 131 anunciado comercialmente en Home/FarmaciasPage/Pricing pero **sin implementación funcional alguna** (no hay tool, calculadora, PDF, página, router ni endpoint).

---

## 1. Resumen ejecutivo

| Aspecto | Estado |
|---|---|
| Tool de cálculo (function calling) | ❌ Inexistente |
| Calculadora frontend (`/calculadora-130` análogo) | ❌ Inexistente |
| Generador PDF borrador | ❌ Inexistente (`VALID_MODELOS` no lo incluye) |
| Router REST | ❌ Inexistente |
| Cálculo trimestral en simulador IRPF | ❌ Inexistente (sólo cálculo anual a efectos Modelo 100) |
| Calendario fiscal (deadlines) | ⚠️ Parcial — seeded en 4 trimestres, plazo 4T mal (1-20 enero, debería ser 1-30 enero) |
| Mención en system prompt TaxAgent | ❌ No existe regla específica |
| Marketing/copy en frontend | ✅ Presente (Home, Pricing autónomo, FarmaciasPage, ModelObligationsPage) |
| Cálculo del rendimiento neto base módulos | ✅ Existe `ModularIncomeCalculator` pero alimenta sólo al simulador anual (Modelo 100), NO al trimestral 131 |
| Disclaimer en Modelo 130 | ✅ Modelo 130 tool excluye explícitamente módulos: *"No cubre estimación objetiva (módulos, Modelo 131)"* |

**Riesgo comercial**: cualquier usuario plan Autónomo (39 €/mes) o Creador (49 €/mes) que tribute en módulos y consulte sobre Modelo 131 obtendrá:
1. Respuesta del LLM sin tool de cálculo (riesgo de alucinación numérica).
2. Imposibilidad de exportar borrador PDF (la lista `VALID_MODELOS` rechaza "131").
3. Calendario impreciso para 4T.
4. Sin calculadora pública análoga a `/calculadora-retenciones` o futura `/calculadora-130`.

Es además el **único modelo trimestral troncal de autónomos** que el sistema deja sin cubrir (303, 130, 308, 720, 721, 200 IS, IPSI sí están).

---

## 2. Inventario funcional necesario (referencia normativa)

### 2.1 Obligados

Contribuyentes IRPF que ejerzan actividades económicas y determinen su rendimiento neto por **estimación objetiva (módulos)**, salvo que la totalidad de sus rendimientos íntegros del ejercicio anterior estuvieran sujetos a retención o ingreso a cuenta (art. 110.3 RIRPF — exención típica de profesionales). Incluye:

- Empresarios en módulos (epígrafes IAE listados en Anexo I de la Orden anual de módulos).
- Actividades agrícolas, ganaderas, forestales y pesqueras en EO (Anexo I/II según orden 2024-2026).

### 2.2 Plazos de presentación (AEAT)

| Periodo | Plazo |
|---|---|
| 1T | 1 a 20 de abril |
| 2T | 1 a 20 de julio |
| 3T | 1 a 20 de octubre |
| 4T | **1 a 30 de enero** del año siguiente |

Si se domicilia, el plazo se cierra 5 días antes (15 abril/julio/octubre y 25 enero).

### 2.3 Fórmula de la cuota (apartado I — actividades empresariales en módulos)

`Cuota_trimestral = Rendimiento_neto_modulos_anual * % según asalariados`

Donde:

- **% = 4%** si la actividad tiene **más de una persona asalariada** a 1 de enero.
- **% = 3%** si tiene **una sola persona asalariada** a 1 de enero.
- **% = 2%** si **no tiene personal asalariado**.
- El **rendimiento neto base** se calcula con los **datos-base a 1 de enero** del ejercicio (signos, índices o módulos previos a reducciones), no con datos acumulados como el 130. Si inicia actividad, datos-base del día de inicio.

### 2.4 Fórmula apartado III — actividades agrícolas, ganaderas, forestales y pesqueras

`Cuota_trimestral = 2% * volumen_ingresos_trimestre`

(Excluyendo subvenciones de capital e indemnizaciones).

> Casillas 05 (volumen ingresos) y 06 (cantidad = 2% × 05) según instrucciones AEAT.

### 2.5 Apartado II — cálculo cuando no se pueden determinar datos-base

`Cuota = 2% * volumen_ingresos_trimestre` (mismo régimen que apartado III).

### 2.6 Índices correctores (aplican al rendimiento neto, ya recogidos en `ModularIncomeCalculator`)

- Índice corrector por **población < 5.000 habitantes** (0,80 / 0,90).
- Índice corrector por **inicio de actividad** (Art. 32.3 LIRPF — 20% en primeros dos años con rendimiento positivo) ✅ ya soportado por `modulos_reduccion_general`/`inicio_actividad`.
- Índice corrector por **temporada** (1,5 / 1,35 / 1,25 según duración).
- Índice corrector por **exceso** (sobre rendimiento neto que supere magnitudes específicas por epígrafe).
- Índices correctores específicos por epígrafe (transporte, taxi, etc.).
- **Reducción general 5%** (vigente 2024-2026, Orden HFP/1359/2023, Orden HAC/1347/2024 y Orden HAC/1425/2025) ✅ ya soportada.

> ⚠️ El cálculo del Modelo 131 toma el **rendimiento neto módulos previo a reducción del 5% y antes de minoraciones especiales** según las instrucciones AEAT del modelo (línea base "datos-base"). El simulador anual del IRPF (Modelo 100) sí aplica todas las reducciones. Por tanto el 131 **no puede reutilizar tal cual** la salida de `ModularIncomeCalculator` — debe recalcular sobre los datos-base brutos.

### 2.7 Reducciones territoriales sobre el pago fraccionado

- **Ceuta y Melilla**: reducción del **60%** del pago fraccionado (art. 68.4 LIRPF aplicado proporcionalmente).
- **La Palma**: reducción del **60%** desde 4T 2025 (Orden HAC/1347/2024 y normativa específica DANA/erupción).
- **Lorca / DANA**: reducciones temporales que aplican según orden vigente.

### 2.8 Deducciones aplicables al pago fraccionado (casillas 09-12)

- **Minoración por rendimientos bajos (Disp. Adic. art. 80 bis LIRPF aplicado al 131, Anexo Orden anual modelos)**:
  - Rendimiento neto previo ≤ 9.000 €: minoración **100 €** trimestrales
  - 9.000-10.000 €: 75 €
  - 10.000-11.000 €: 50 €
  - 11.000-12.000 €: 25 €
  - > 12.000 €: 0 €

  > Nótese que los tramos del 131 son discretos (escalones de 25 €) frente a los del 130 que son lineales decrecientes (100 → 0). El tool del 130 actual aplica fórmula lineal correcta para 130 pero **no sirve para 131**.

- **Retenciones e ingresos a cuenta del trimestre** (casilla 08).
- **Deducción por inversión en vivienda habitual** (régimen transitorio pre-2013, casilla con límites específicos).
- ~~**Pagos fraccionados anteriores ya ingresados**~~ — **CORREGIDO (2026-08-24)**: esto era un error de esta auditoría. El 131 **no deduce** los pagos fraccionados de trimestres anteriores y **no tiene casilla** para ellos. El art. 110.1 RIRPF sólo lo manda en su letra a) (estimación directa, Modelo 130, casilla `[05]`), y acota el mandato a *"lo dispuesto EN ESTA LETRA"*; la letra b), que es la de este modelo, calcula sobre *"los datos-base del primer día del año"* y no acumula. Implementarlo hacía que el contribuyente ingresara **de menos**. No reponer el campo.

### 2.9 Resultado final

`Casilla 15 = Casilla 13 (cuota tras minoraciones) − Casilla 14 (resultado negativo del trimestre anterior si lo hubo)`

- Si > 0 → **a ingresar**.
- Si ≤ 0 → declaración **negativa** (presentación obligatoria igualmente).

### 2.10 Formas de pago (novedad 2025)

- Domiciliación SEPA (IBAN).
- **Bizum** y tarjeta (novedad incorporada en 2025 según AEAT).
- Efectivo (sólo presentación papel).
- NRC bancario.

### 2.11 Casuística adicional

- **Renuncia a módulos**: se realiza en diciembre del año previo o al alta censal (Modelo 036/037). Pasa el contribuyente a estimación directa — **deja de presentar 131 y empieza a presentar 130**.
- **Exclusión de oficio**: si supera límites de magnitud (volumen ingresos > 250.000 €/200.000 € agrícolas, compras > 150.000 €) queda excluido al ejercicio siguiente.
- **Concurrencia de actividades**: si una actividad pasa a ED por exclusión, todas las demás también — afecta a qué modelo se presenta.

---

## 3. Inventario actual en TaxIA

### 3.1 Backend — qué existe relacionado

| Archivo | Contenido relativo a 131 | Cobertura real |
|---|---|---|
| `backend/app/utils/calculators/modular_income.py` | Calcula rendimiento neto EO anual con índice corrector + reducción 5% + reducción inicio | Sirve para Modelo 100 anual, **NO** para cuota trimestral 131 |
| `backend/app/utils/irpf_simulator.py` | Recibe `modulos_rendimiento_neto`, `modulos_indice_corrector` y los pasa a `ModularIncomeCalculator` | Sólo simulador anual |
| `backend/app/tools/modelo_130_tool.py:232` | Disclaimer: *"No cubre estimación objetiva (módulos, Modelo 131)"* | Tool 130 explícitamente excluye módulos |
| `backend/scripts/seed_estatal_deadlines.py` | Seeds deadlines `131` para 4T/1T/2T/3T con plazos | ⚠️ Plazo 4T mal: usa 1-20 enero, debería 1-30 enero |
| `backend/scripts/doc_crawler/watchlist.py:248` | Watchlist `DR131_e2025.xlsx` con `status="future"` | Diseño de Registro AEAT no descargado todavía |
| `backend/app/tools/__init__.py` | `ALL_TOOLS` y `TOOL_EXECUTORS` | **Sin** `MODELO_131_TOOL` |
| `backend/app/services/modelo_pdf_generator.py:32` | `VALID_MODELOS = {"303","130","200","308","720","721","ipsi"}` | **No incluye "131"** — endpoint `/api/export/modelo-pdf` rechazará exportar 131 |
| `backend/app/agents/tax_agent.py` system prompt | Reglas para 130/303 | **Sin** regla específica 131 |

### 3.2 Frontend — qué existe relacionado

| Archivo | Contenido | Cobertura real |
|---|---|---|
| `frontend/src/pages/Home.tsx:183, 664` | Marketing: "303, 130, 131, 308, 349, 720 y 721" + "Modelos 303, 130, 131, 390" | Promesa comercial |
| `frontend/src/pages/FarmaciasPage.tsx:58, 340` | "Avisos del 130/131" y "Sí presentas el 130/131 por IRPF" | Promesa específica para sector farmacia (módulos) |
| `frontend/src/pages/ModelObligationsPage.tsx:61` | Listado modelos AEAT | Mención |
| `frontend/src/components/FiscalCalendar.tsx:26` | Icono Calculator si `m === '131'` | Renderiza si llegan deadlines del backend |
| `frontend/src/pages/M130CalculatorPage.tsx` | Calculadora pública 130 | **No existe `M131CalculatorPage`** |
| `frontend/src/pages/DeclarationsPage.tsx` | Declaraciones | Probable mención sin acción funcional |
| `frontend/src/App.tsx` | Rutas | **Sin** ruta `/calculadora-131` ni `/m131` |

### 3.3 Tests

- Cero tests sobre Modelo 131. `backend/tests/test_modelo_tools.py` no contempla 131.

---

## 4. Cross-check normativo

### 4.1 Fuentes oficiales verificadas

- **Orden HFP/1359/2023** de 19 de diciembre — módulos IRPF 2024 (BOE-A-2023-25882). Reducción general 5%. La Palma 20%.
- **Orden HAC/1347/2024** de 28 de noviembre — módulos IRPF 2025 (BOE-A-2024-24949). Mantiene cuantías. Mejillón en batea pasa a Anexo I.
- **Orden HAC/1425/2025** de 9 de diciembre — módulos IRPF 2026 (BOE-A-2025-25272). **Este es el aplicable al ejercicio actual 2026**.
- **Orden HAC/408/2025** — modifica índices rendimiento neto 2024 para actividades agrícolas afectadas (DANA, sequía).
- **Orden EHA/672/2007** (BOE-A-2007-6032) — aprueba modelos 130 y 131 vigentes.
- **Instrucciones AEAT Modelo 131** (sede.agenciatributaria.gob.es) — fórmula casillas 01-15, plazos, formas de pago (Bizum 2025).
- **Manual práctico Actividades Económicas — capítulo 3.7 Pagos fraccionados** (AEAT) — fórmulas, ejemplos, índices correctores.

### 4.2 Discrepancias detectadas en TaxIA

| Discrepancia | Severidad | Detalle |
|---|---|---|
| Falta tool de cálculo cuota 131 | **CRÍTICA** | Anunciado en pricing, sin implementación |
| Falta calculadora pública `/calculadora-131` | **ALTA** | Lead magnet SEO equivalente a `/calculadora-130` |
| `VALID_MODELOS` no incluye `"131"` | **ALTA** | Imposible exportar borrador PDF del 131 |
| Plazo 4T en `seed_estatal_deadlines.py` | **MEDIA** | Usa 1-20 enero; el real es 1-30 enero (igual que 4T 130, ver línea 122-125) |
| Falta lógica reducción 60% Ceuta/Melilla en pago fraccionado | **MEDIA** | Si se implementa, debe contemplar el 60% trimestral (ya hay precedente IPSI) |
| Falta reducción 60% La Palma desde 4T 2025 | **MEDIA** | Vigente normativa actual |
| Falta cálculo apartado III (agrícolas/ganaderas/forestales 2% sobre ingresos) | **CRÍTICA** | Distinto cálculo y casillas que apartado I |
| Falta minoración rendimientos bajos del 131 (escalones 100/75/50/25) | **CRÍTICA** | Tabla distinta a la del 130 (lineal). Reutilizar la del 130 daría resultado erróneo |
| Watchlist `DR131_e2025.xlsx` en `status="future"` | **BAJA** | Diseño de Registro pendiente de descarga para validar casillas |
| Sin regla en `tax_agent.py` para validar `estimacion='objetiva'` antes de invocar tool 131 | **MEDIA** | Análoga a la regla de `situacion_laboral` antes de invocar 130/303 |

---

## 5. Casos prácticos (ground truth para tests)

### Caso A — Bar pequeño, sin asalariados (Madrid)

- IAE 673.2 (bar categoría especial). Datos-base 1 enero 2026: rendimiento neto previo módulos = 18.000 € anuales.
- Asalariados: 0 → % = **2%**
- Cuota trimestral 1T 2026 = 18.000 × 2% = **360 €**
- Sin retenciones (bar no recibe retenciones de clientes particulares).
- Minoración rendimientos bajos: rendimiento previo año anterior 11.500 € → minoración **25 €/trimestre**.
- Casilla 13 = 360 − 25 = 335 €
- Resultado a ingresar 1T = **335 €**.
- Plazo: 1-20 abril 2026 (o 15 abril si domicilia).

### Caso B — Bar con 1 asalariado (Andalucía)

- Mismos datos, pero 1 asalariado a 1 enero. % = **3%**.
- Cuota = 18.000 × 3% = 540 €. Sin minoración (rendimiento previo > 12.000). **A ingresar = 540 €**.

### Caso C — Taxi en Sevilla (epígrafe 721.2)

- Datos-base 1 enero: rendimiento neto previo módulos = 12.000 €. 0 asalariados.
- Índice corrector específico taxi (no aplica reducción especial al pago fraccionado del 131 de modo lineal — se aplica al rendimiento neto base AEAT).
- Cuota = 12.000 × 2% = 240 €/trimestre.
- Minoración rendimiento bajo (rendimiento año anterior 9.500 €): tabla 131 escalón 9.000-10.000 → **75 €**.
- A ingresar trimestral = 240 − 75 = **165 €**.

### Caso D — Agricultor en Galicia (apartado III)

- Volumen ingresos 1T 2026 = 25.000 € (sin subvenciones de capital).
- Cuota = 25.000 × 2% = **500 €** (apartado III, casillas 05/06).
- Sin minoración por rendimientos bajos (no aplica a apartado III).
- Resultado a ingresar = **500 €**.

### Caso E — Bar en Ceuta

- Datos: idénticos a caso A.
- Cuota apartado I = 360 €.
- **Reducción 60% Ceuta** → 360 × (1 − 0,60) = **144 €**.
- Minoración rendimientos bajos 25 € (sí aplica antes de la reducción 60%? la AEAT aplica el 60% al final). Detalle a verificar contra Disposición Adicional 28ª LIRPF.
- A ingresar 1T = ~144 − (25 × 0,40) = ~134 €.

### Caso F — Inicio actividad 1 marzo 2026 (Comercio menor textil, IAE 651.1, Madrid)

- Datos-base al **1 de marzo 2026** (no 1 enero). Rendimiento neto previo módulos prorrateado = 8.000 € (anualizado 9.600 €).
- 0 asalariados. % = 2%.
- Cuota 1T (sólo marzo) = 8.000 × 2% × (1/3) o cálculo proporcional según instrucciones AEAT (a verificar).
- Aplica reducción inicio actividad 20% Art. 32.3 LIRPF al **rendimiento neto en Modelo 100**, NO directamente al 131. Por tanto la cuota trimestral del 131 se calcula sobre datos-base sin la reducción del 20% (ésa se aplicará en la declaración anual).

### Caso G — Sin datos-base (alta nueva sin signos definidos)

- Aplica apartado II: **2% sobre ingresos del trimestre**.
- Volumen 1T = 5.000 € → cuota = **100 €**.

---

## 6. Estado del simulador / calculadora pública

- **No existe `/calculadora-131` pública** análoga a `/calculadora-retenciones` o `M130CalculatorPage`.
- Recomendación lead magnet SEO: crear `/calculadora-131` con wizard:
  1. Tipo actividad (empresarial / agrícola-ganadera-forestal / sin datos-base).
  2. Si empresarial: nº asalariados (selector 0 / 1 / 2+).
  3. Si empresarial: rendimiento neto previo módulos (input EUR).
  4. Si agrícola: volumen ingresos trimestre (input EUR).
  5. Trimestre + año.
  6. Territorio (para reducciones Ceuta/Melilla/La Palma 60%).
  7. Rendimiento neto año anterior (para minoración rendimientos bajos).
  8. Retenciones soportadas trimestre.
  9. ~~Pagos fraccionados anteriores (sólo auxiliar).~~ **CORREGIDO (2026-08-24)**: no pedir este dato. Ver la corrección de la sección 2.8 — el 131 no lo deduce ni tiene casilla para él.

  Output: cuota a ingresar + breakdown casillas + plazo + recordatorio.

---

## 7. Plan de implementación recomendado

### Fase 1 — MVP backend (sprint 1)

1. **Crear `backend/app/utils/calculators/modelo_131.py`** con clases:
   - `Modelo131EmpresarialCalculator` (apartado I): inputs `rendimiento_neto_modulos_anual`, `num_asalariados`, retornos casillas 01-04 + 09-15.
   - `Modelo131AgricolaCalculator` (apartado III): inputs `volumen_ingresos_trimestre`, retornos casillas 05-06.
   - Función `apply_territorial_reduction(cuota, territorio)`: aplica 60% Ceuta/Melilla/La Palma.
   - Función `minoracion_rendimientos_bajos(rendimiento_anual_previo)`: devuelve 100/75/50/25/0 según escalón.

2. **Crear `backend/app/tools/modelo_131_tool.py`** con definición OpenAI function calling y executor `calculate_modelo_131_tool`. Registrar en `tools/__init__.py` (`ALL_TOOLS` + `TOOL_EXECUTORS`).

3. **Añadir regla en `backend/app/agents/tax_agent.py` system prompt**: si usuario menciona "modulos" o `estimacion_objetiva` y pregunta sobre pago trimestral → usar `calculate_modelo_131`. Si menciona estimación directa → 130. Si ambiguo → preguntar.

4. **Actualizar `VALID_MODELOS`** en `backend/app/services/modelo_pdf_generator.py` para incluir `"131"` y crear plantilla PDF (clonar `_render_modelo_130` con casillas 131).

5. **Corregir `seed_estatal_deadlines.py`** plazo 4T 131: cambiar `f"{y}-01-20"` → `f"{y}-01-30"` (línea 138). Actualizar descripción línea 143.

6. **Tests**: crear `backend/tests/test_modelo_131.py` con casos A-G del apartado 5.

### Fase 2 — Frontend (sprint 2)

1. **`frontend/src/pages/M131CalculatorPage.tsx`** + `.css` (clonar M130).
2. Ruta pública `/calculadora-131` en `App.tsx`.
3. Hook `useModelo131()` análogo a `useModeloPDF`.
4. Botón "Generar borrador 131 PDF" en `DeclarationsPage` y nueva `M131CalculatorPage`.
5. Schema JSON-LD `WebApplication` + `HowTo` para SEO (sesión 27 pattern).

### Fase 3 — RAG + ingesta (sprint 3)

1. Activar watchlist `DR131_e2025.xlsx` (`status="future"` → `"active"`) y crawler.
2. Ingestar Manual AEAT Actividades Económicas capítulo 3.7 (pagos fraccionados).
3. Ingestar Orden HAC/1425/2025 (módulos 2026).

### Fase 4 — Validación

1. Test E2E Playwright: usuario test.autonomo@impuestify.es → consulta "calcula mi 131" → tool invocado → respuesta con casillas + plazo.
2. RAG ground truth: añadir 5 preguntas sobre 131 a `rag_ground_truth.json`.
3. Verificar que `topic_classifier.py` clasifica "modelo 131" como `fiscal=true`.

---

## 8. Conclusiones

**Modelo 131 es el gap funcional crítico más visible de TaxIA**, porque:

1. Está **explícitamente prometido en pricing** (plan Autónomo y Creador) y en landing especializada (FarmaciasPage menciona "130/131" 2 veces).
2. Es **trivialmente exigible** por cualquier autónomo en módulos (sector farmacia, hostelería, taxi, comercio menor — perfiles target del SaaS).
3. La **arquitectura del 130 ya existe** y es 90% reutilizable — sólo cambia la fórmula del rendimiento (datos-base vs ingresos-gastos), los porcentajes (4/3/2 vs 20%) y la tabla de minoración (escalonada vs lineal).
4. El `ModularIncomeCalculator` ya cubre el rendimiento neto base (input principal del 131), por lo que la integración con el simulador anual es inmediata.
5. **Riesgo legal/comercial**: usuario que pague suscripción esperando 131 puede solicitar reembolso por incumplimiento de la promesa publicitaria. Documentar internamente o eliminar la mención de Home/Pricing/Farmacias hasta implementarlo.

**Acción inmediata recomendada (mismo día)**:

- Si no se va a implementar en próxima sprint: **eliminar las 5 menciones del 131** en frontend (Home línea 183, Home línea 664, FarmaciasPage 58, FarmaciasPage 340, ModelObligationsPage 61) y dejar disclaimer en `M130CalculatorPage` que cubre módulos.
- Si se implementa: priorizar Fase 1 MVP backend (≈ 2-3 días tool + tests + corrección plazo 4T).

**Severidad final**: **CRÍTICA — funcionalidad anunciada sin implementar**.

---

## Apéndice — Referencias

- Instrucciones Modelo 131: https://sede.agenciatributaria.gob.es/Sede/impuestos-tasas/impuesto-sobre-renta-personas-fisicas/modelo-131-irpf______sionales-estimacion-objetiva-fraccionado_/instrucciones.html
- Manual AEAT Actividades Económicas — 3.7 Pagos fraccionados: https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_7-pagos-fraccionados.html
- Orden HFP/1359/2023 (módulos 2024): https://www.boe.es/buscar/act.php?id=BOE-A-2023-25882
- Orden HAC/1347/2024 (módulos 2025): https://www.boe.es/buscar/act.php?id=BOE-A-2024-24949
- Orden HAC/1425/2025 (módulos 2026): https://www.boe.es/buscar/act.php?id=BOE-A-2025-25272
- Orden EHA/672/2007 (aprobación modelos 130/131): https://www.boe.es/buscar/act.php?id=BOE-A-2007-6032
- Sede Modelo 131 procedimiento: https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G602.shtml
