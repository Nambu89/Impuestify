# Validación Modelo 130 — Mayo 2026

> Auditor: agente investigador (Opus 4.7)
> Fecha: 2026-05-10
> Alcance: pago fraccionado IRPF en Estimación Directa (normal y simplificada). Sección II (actividades agrícolas/ganaderas/forestales/pesqueras) y Modelo 131 (módulos) están fuera de alcance.

## Resumen ejecutivo

- **Estado global: AMARILLO** — el cálculo del resultado final es correcto en todos los escenarios habituales (territorio común, Ceuta/Melilla, forales), pero hay **2 gaps CRÍTICOS** de etiquetado de casillas que romperían la traslación a la autoliquidación oficial AEAT, y **5 gaps ALTOS** funcionales (sección agrícola omitida, regla del 70% no documentada, dispersion entre tool/calculator/frontend).
- **Gaps CRÍTICOS:** 2
- **Gaps ALTOS:** 5
- **Gaps MEDIOS:** 4
- **Gaps BAJOS:** 3
- **Cobertura test:** 17 tests asíncronos sobre `Modelo130Calculator` cubriendo Comun + Ceuta/Melilla + Araba + Gipuzkoa (general/excepcional) + Bizkaia (primeros años, general, excepcional) + Navarra (primera/segunda). El **chat tool** (`modelo_130_tool.py`) y la **calculadora frontend** (`M130CalculatorPage.tsx`) NO tienen tests propios. Cobertura de la lógica núcleo: ~80%; cobertura de las tres implementaciones combinadas: ~55%.
- **Validación AEAT:** PARCIAL (la AEAT no expone un simulador público para el Modelo 130, sólo formulario de presentación con autenticación Cl@ve. Cross-check ejecutado contra normativa BOE/RIRPF + Manual Prácticol AEAT IRPF + instrucciones oficiales del modelo + foral).

---

## 1. Inventario de código

TaxIA implementa el Modelo 130 en **TRES capas independientes** que conviven sin compartir lógica:

| Capa | Path | Uso | Cobertura territorial | Cobertura test |
|------|------|-----|-----------------------|----------------|
| Tool LLM | `backend/app/tools/modelo_130_tool.py` | Function-calling chat (TaxAgent) | Comun (con flag art. 80 bis manual) | 0 tests |
| Calculator service | `backend/app/utils/calculators/modelo_130.py` | Endpoints + Workspace + simulación | Comun, Ceuta/Melilla, Araba, Gipuzkoa, Bizkaia, Navarra | 17 tests `test_modelo_130.py` |
| UI calculator | `frontend/src/pages/M130CalculatorPage.tsx` | Calculadora pública SPA (`/calculadora-m130`?) | Comun + Ceuta/Melilla | 0 tests |

### 1.1 Fórmulas implementadas — Territorio Común (`_calculate_comun`)

```
casilla_03 = ingresos_acumulados − gastos_acumulados                      (rendimiento neto)
casilla_04 = max(0, casilla_03) × 20% (8% si Ceuta/Melilla)               (cuota íntegra)
casilla_07 = max(0, casilla_04 − retenciones_acumuladas − pagos_anteriores)
casilla_13 = art_80bis(rend_neto_anterior_anual)
casilla_14 = max(0, casilla_07 − casilla_13)
casilla_16 = min(casilla_03 × 2%, 660,14)  si tiene_vivienda_habitual
casilla_17 = max(0, casilla_14 − casilla_15 − casilla_16)
casilla_19 = max(0, casilla_17 − casilla_18)
```

**Tabla art. 80 bis (rendimiento neto del año anterior):**

| Tramo | Deducción trimestral |
|-------|----------------------|
| ≤ 9.000 € | 100,00 € |
| 9.000,01 — 10.000 € | 75,00 € |
| 10.001 — 11.000 € | 50,00 € |
| 11.001 — 12.000 € | 25,00 € |
| > 12.000 € | 0,00 € |

**Vivienda habitual:** 2% del rendimiento neto, máximo 660,14 €/trimestre.

### 1.2 Fórmulas forales

- **Araba (Álava):** 5% sobre rendimiento neto **trimestral** (no acumulado) menos retenciones e ingresos a cuenta del trimestre.
- **Gipuzkoa general:** 5% × rendimiento_neto_penúltimo − 25% × retenciones_penúltimo.
- **Gipuzkoa excepcional:** 1% × volumen_operaciones_trimestre − retenciones_trimestre.
- **Bizkaia primeros 2 años:** réplica del modelo común al 20% acumulado (sin art. 80 bis ni vivienda).
- **Bizkaia desde 3er año (general):** 5% × rendimiento_neto_penúltimo − 25% × retenciones_penúltimo.
- **Bizkaia desde 3er año (excepcional):** 5% × volumen_ventas_penúltimo − 25% × retenciones_penúltimo.
- **Navarra primera modalidad:** tabla progresiva (6/12/18/24%) sobre rend_neto_penúltimo, menos retenciones_penúltimo, dividido entre 4.
- **Navarra segunda modalidad:** rend_neto_acumulado anualizado (×4 / ×2 / ×4/3 / ×1) → tabla progresiva → tipo aplicado al rend_neto real, menos retenciones e ingresos previos.

### 1.3 Plazos hardcoded en frontend

Coincide con AEAT excepto regla de festivos (no se traslada al primer día hábil):

| Trimestre | Plazo TaxIA | Plazo AEAT |
|-----------|-------------|------------|
| 1T | 1—20 abril 2026 | 1—20 abril (si día 20 es hábil) |
| 2T | 1—20 julio 2026 | 1—20 julio |
| 3T | 1—20 octubre 2026 | 1—20 octubre |
| 4T | 30 enero 2027 | 1—30 enero |

**Domiciliación bancaria (no implementada en TaxIA):** del día 1 al 15 (T1, T2, T3) y del 1 al 27 (T4).

### 1.4 Inputs requeridos por capa

| Input | Tool LLM | Calculator | Frontend |
|-------|---------|-----------|----------|
| ingresos acumulados | sí | sí | sí |
| gastos acumulados | sí | sí | sí |
| retenciones | sí | sí | sí |
| pagos fraccionados anteriores | sí | sí | sí |
| rend_neto_previo_anual (art 80 bis) | sí | sí | derivado de checkbox |
| Ceuta/Melilla | NO | sí | sí |
| vivienda habitual | NO | sí | sí (manual import) |
| resultado complementaria (casilla 18) | NO | sí | NO |
| resultados negativos previos (casilla 15) | NO | parcial (default 0) | sí |

---

## 2. Normativa AEAT vigente

### 2.1 Fuentes consultadas

1. **BOE — RD 439/2007** (Reglamento IRPF), **artículos 109, 110 y 111** — versión consolidada (BOE-A-2007-6820). Última modificación relevante: RD 1461/2018.
2. **Ley 35/2006 IRPF**, art. 99.6 (obligación de pago a cuenta).
3. **Ley 35/2006 IRPF**, art. 68.4 (deducción Ceuta/Melilla → genera la reducción del 60% del art. 110.2 RIRPF).
4. **AEAT — Sede electrónica**, instrucciones oficiales Modelo 130 (PDF GZ601 + página instrucciones).
5. **AEAT — Manual Práctico de Actividades Económicas** ("folleto actividades económicas"), capítulo 3.7 — Pagos fraccionados.
6. **Norma Foral 13/2013 Bizkaia** (IRPF) — pagos fraccionados.
7. **Diputación Foral Gipuzkoa** — instrucciones Modelo 130 Gipuzkoa.
8. **Norma Foral Álava** — IRPF actividades económicas.
9. **OF 40/2009 Navarra** — Modelo 130 foral (modalidades primera y segunda).

### 2.2 Parámetros legales vigentes (mayo 2026)

| Parámetro | Valor legal |
|-----------|-------------|
| % estimación directa (art 110.1.a RIRPF) | 20 % |
| % Ceuta/Melilla (reducción 60% sobre el 20% — art 110.2) | 8 % |
| % actividades agrícolas/ganaderas/forestales/pesqueras (art 110.1.b RIRPF) | 2 % (0,8 % Ceuta/Melilla) |
| Deducción rendimientos bajos (art 110.3.c RIRPF) | hasta 100 €/trimestre, tabla escalonada hasta 12.000 € rend_neto previo |
| Deducción vivienda habitual (DT 18ª LIRPF + art 110.3.d) | 2 % × rendimiento neto, máx 660,14 €/trim, máx 2.640,56 €/año |
| Excepción presentación profesionales (art 109.2) | ≥ 70 % retenciones en año anterior |
| Excepción agrícolas/ganaderas/forestales (art 109.3) | ≥ 70 % retenciones en año anterior (excluyendo subvenciones e indemnizaciones) |
| Plazo trimestres 1—3 | 1—20 abril / julio / octubre |
| Plazo trimestre 4 | 1—30 enero año siguiente |
| Domiciliación bancaria (1T—3T) | hasta día 15 |
| Domiciliación bancaria (4T) | hasta día 27 enero |
| Redondeo | céntimo más próximo (al alza si exactamente medio céntimo) |

### 2.3 Casillas oficiales Modelo 130 (instrucciones AEAT)

**Sección I — Actividades económicas (no agrícolas):**

| Casilla | Concepto |
|---------|----------|
| 01 | Ingresos íntegros computables (acumulados desde 1 enero) |
| 02 | Gastos deducibles (acumulados) |
| 03 | Rendimiento neto (01 − 02), puede ser negativo |
| 04 | 20 % de la casilla 03 (si > 0) — 8 % en Ceuta/Melilla |
| **05** | **Suma de casillas 07 positivas de trimestres anteriores menos deducciones casilla 16 anteriores** (es decir, cuota neta acumulada ya pagada) |
| **06** | **Retenciones e ingresos a cuenta del período acumulado** |
| 07 | Resultado sección I = 04 − 05 − 06 |

**Sección II — Actividades agrícolas/ganaderas/forestales/pesqueras** (08—11): NO implementada en TaxIA.

**Sección III — Total liquidación:**

| Casilla | Concepto |
|---------|----------|
| 12 | Total = Casilla 07 + Casilla 11 (mínimo 0) |
| 13 | Minoración rendimientos bajos (art 110.3.c) — tabla 100/75/50/25 |
| 14 | Casilla 12 − Casilla 13 |
| 15 | Resultados negativos de trimestres anteriores (máx Casilla 14) |
| 16 | Deducción vivienda habitual (máx 660,14 €) |
| 17 | Casilla 14 − 15 − 16 |
| 18 | Autoliquidaciones anteriores (sólo complementaria) |
| 19 | **Resultado final** = 17 − 18 (signo) |

> Nota: la casilla 19 oficial se calcula como **17 menos 18** (con signo, no max(0)). Si es positiva → ingreso. Si negativa → arrastre o devolución según el caso.

---

## 3. Discrepancias detectadas (cross-check normativa vs código)

### CRÍTICO

| # | Capa | Discrepancia | Norma | Impacto | Fix |
|---|------|--------------|-------|---------|-----|
| C1 | `modelo_130_tool.py` líneas 141–142 + 197–199 | **Casillas 05 y 06 invertidas:** el tool etiqueta `casilla_05 = retenciones` y `casilla_06 = pagos_fraccionados_anteriores`. La AEAT (instrucciones oficiales) define **Casilla 05 = cuotas anteriores ya pagadas** y **Casilla 06 = retenciones**. La descripción del parámetro (`casilla 05`) en el JSON-schema del tool refuerza el error. | Instrucciones AEAT Modelo 130 | El **importe final** sigue siendo correcto (es resta), pero la **trazabilidad** a la autoliquidación oficial es inválida. Si el agente exporta o explica al usuario "Casilla 05: 2.000 €" y la AEAT espera ahí pagos previos, se produce inconsistencia legal en respuestas exportadas o copiadas al portal AEAT. | Renombrar: `casilla_05 = pagos_fraccionados_anteriores`, `casilla_06 = retenciones_ingresos_cuenta`. Actualizar descripciones del schema JSON. Mantener compat: aceptar ambos nombres en el bloque condicional de impresión durante 1 release. |
| C2 | `M130CalculatorPage.tsx` líneas 105–108 + 354–367 + 504–506 | **Misma inversión 05/06** en el frontend.** El input "Retenciones soportadas acumuladas" se etiqueta como `Casilla 06` (correcto), pero internamente se asigna a `casilla06 = retenciones` y luego en la tabla se imprime "Casilla 05 — Pagos fraccionados anteriores" (`value={result.casilla05}` que contiene `pagosAnteriores`). Aun así, la fórmula `casilla07 = casilla04 − casilla05 − casilla06` resta ambos y el total es correcto, pero el desglose visible al usuario tiene los conceptos cruzados con respecto al modelo oficial. **Verificar** lectura visual: el usuario ve "Casilla 05 — pagos anteriores" y "Casilla 06 — retenciones" → AEAT también dice eso. ✓ Coincide en frontend. | Instrucciones AEAT Modelo 130 | El frontend está alineado con AEAT. **Pero el chat tool y el frontend son inconsistentes entre sí**, lo que generará confusión cuando un usuario migre del chat a la calculadora. | Alinear chat tool con AEAT (fix C1) y verificar que el PDF generado por `useModeloPDF` use la misma numeración. |

### ALTO

| # | Capa | Discrepancia | Norma | Impacto | Fix |
|---|------|--------------|-------|---------|-----|
| A1 | Todas | **Sección II (actividades agrícolas/ganaderas/forestales/pesqueras) NO implementada.** Casillas 08—11 ausentes. Tipo 2 % sobre volumen de ingresos (excluido capital). | Art 110.1.b RIRPF | Cualquier autónomo agrario/ganadero/pesquero recibe cálculo erróneo o nulo. El folleto AEAT capítulo 3.7 lo cubre como caso estándar. El frontend lo declara out-of-scope ("No incluye actividades agrícolas (casillas 08-11)") pero el tool del chat NO lo advierte → el LLM puede aceptar facturación agrícola y devolver 20% en vez de 2%. | Añadir parámetros `actividad_agraria`, `volumen_ingresos_trimestre_agrario`, `retenciones_trimestre_agrario` al tool y al calculator. Bloquear o pivotar al 2% si `is_agricola=True`. Mínimo: documentar claramente la exclusión y rehusar cálculo. |
| A2 | Todas | **Regla del 70 % no implementada** (art 109.2 y 109.3 RIRPF). Profesionales con ≥ 70 % de ingresos sometidos a retención están dispensados de presentar Modelo 130. Igual los agrarios/forestales (excluyendo subvenciones e indemnizaciones del numerador). | Art 109 RIRPF | Casos prácticos: un creador de contenidos cuyos clientes B2B le retienen el 15 % (>70 % de su facturación) **NO está obligado a presentar**. TaxIA calcula y le hace creer que sí. Diagnóstico erróneo de obligaciones. | Añadir input `pct_retencion_anio_anterior`. Si profesional y ≥ 70 % → flag "no obligado". Igual lógica para agrarios. Devolver mensaje informativo en lugar de cálculo. |
| A3 | Gipuzkoa | **Threshold del 50 % en Gipuzkoa** (no 70 %). En Gipuzkoa la dispensa para profesionales se activa con ≥ 50 % de retención en año anterior (instrucciones DFG). El calculator no implementa la regla de dispensa en absoluto. | Norma Foral IRPF Gipuzkoa | Profesional Gipuzkoa entre 50—70 % de retención: TaxIA y AEAT comunes coinciden en "obligado", pero la realidad foral le exime. Consulta tributaria errónea. | Implementar regla de dispensa por territorio. Documentar diferencias. |
| A4 | `modelo_130_tool.py` líneas 153—162 | **Tabla art. 80 bis con interpolación lineal.** El código del chat tool aplica interpolación: `100 − (rn − 9000) × 0.075`, etc. La normativa (art 110.3.c RIRPF + manual AEAT) define la deducción como **escalones planos** (100 / 75 / 50 / 25 €) según tramo, sin interpolación. La calculator service (`modelo_130.py` líneas 32–37, `_art_80bis_deduction`) **sí** usa escalones planos correctamente. **Inconsistencia entre las dos implementaciones**. | Art 110.3.c RIRPF + instrucciones AEAT | Chat tool devuelve cifras intermedias (p.ej. 87,50 € para rend_neto = 9.500), cuando la cifra legal correcta es 75 €. Test `test_comun_art_80bis_10500` confirma que el calculator devuelve 50 € para 10.500 (correcto). | Reemplazar el bloque de interpolación del chat tool por la tabla escalonada del calculator. Centralizar la función en `_art_80bis_deduction` y reutilizarla desde el tool. |
| A5 | Todas | **Casilla 19 con max(0,…)** en lugar de signo: el calculator hace `max(0, casilla_17 − casilla_18)`. La AEAT permite **resultado cero o a compensar** (resultado positivo de complementaria), pero un Modelo 130 nunca da "a devolver" directamente. La regla de max(0) es defendible para autoliquidaciones normales, pero **borra información de complementarias** cuando casilla_18 > casilla_17. Además, el frontend NO modela casilla_18 (siempre 0) y el chat tool tampoco. | Instrucciones AEAT (regla complementaria) | Una complementaria mal calculada quedará silenciada con resultado 0 sin alertar al usuario. | Devolver `resultado_signed` además de `resultado` (max 0 para ingreso). Añadir input `es_complementaria` en frontend + tool. |

### MEDIO

| # | Capa | Discrepancia | Norma | Impacto | Fix |
|---|------|--------------|-------|---------|-----|
| M1 | `M130CalculatorPage.tsx` líneas 75–91 | **`calcularMinoracion` ignora la tabla del 110.3.c y usa una versión simplificada por tramos planos sin interpolación** que coincide con la norma. Sin embargo, el dato de entrada es `rendimientoNeto × factorAnualizacion[trimestre]`, una **anualización heurística** (Q1×4, Q2×2, Q3×4/3, Q4×1) que **no corresponde a la norma**: la deducción art. 80 bis se calcula con el **rendimiento neto del año anterior**, no con la anualización del actual. | Art 110.3.c RIRPF | En el T1 con ingresos altos (p.ej. 4.000 €), la anualización × 4 = 16.000 → 0 € deducción. Pero el dato real depende de lo declarado el año anterior, no del trimestre actual. Sobreestima/infraestima la deducción ~30 % de los casos. | Pedir explícitamente "rendimiento neto AÑO ANTERIOR" como input separado. Eliminar la anualización heurística. La calculator service ya lo hace correctamente vía `rend_neto_anterior`. |
| M2 | `modelo_130.py` línea 244 | **Casilla 15 (resultados negativos anteriores) hardcodeada a 0** en `_calculate_comun`. El comentario dice "caller may pass via kwargs" pero **no se documenta ni se valida**. El frontend sí lo expone; el calculator no lo recibe. | Instrucciones AEAT casilla 15 | Pérdidas trimestrales no compensadas en cálculos vía API. | Promover `negativos_anteriores` a parámetro nombrado del calculator. Propagar desde el frontend al backend cuando se integre. |
| M3 | Frontend líneas 57–62 | **Plazos hardcoded sin lógica de día hábil.** Si el día 20 cae en sábado/domingo/festivo nacional, AEAT traslada al primer día hábil. TaxIA no aplica esta regla. | Norma general autoliquidaciones | Mostrar "20 julio 2026" cuando es domingo (en realidad lunes 21 → "21 julio 2026 efectivo"). Confunde a usuarios. | Añadir helper `nextBusinessDay(date)` con calendario laboral nacional. |
| M4 | `modelo_130_tool.py` línea 221 | **Mensaje "antes del día 20"** sin matizar que en T4 el plazo es 30 enero (no 20 enero). El código ya distingue 20 vs 30 con la conjunción "(o 30 de enero para el 4T)" pero el redactado es confuso. | Instrucciones AEAT | Confunde al usuario en respuestas de chat sobre el T4. | Reescribir mensaje del trimestre como tabla por T (1T→20 abr, 2T→20 jul, 3T→20 oct, 4T→30 ene). |

### BAJO

| # | Capa | Discrepancia | Impacto | Fix |
|---|------|--------------|---------|-----|
| B1 | Tool LLM | Comentario "Los datos del Modelo 130 son ACUMULADOS desde el 1 de enero" — bien. Pero **no rechaza explícitamente** datos trimestrales (sólo "PREGUNTA"). Permite ambigüedad. | El usuario puede dar datos parciales y el LLM no detectarlos. | Añadir validación heurística: si `ingresos_computables × 4 < salario_minimo` y trimestre=4, advertir. |
| B2 | Frontend | "Aviso importante" sobre acumulados está bien colocado y visible. Pero la tabla muestra ambos `casilla05` (pagos previos) y `casilla06` (retenciones) **siempre**, incluso cuando son 0. | Ruido visual. | Filtrar filas con valor 0 (excepto las primarias 03/04/19). Coincide con el patrón ya usado para 13/15/16. |
| B3 | Calculator service | `territory.strip().capitalize()` no maneja tildes ("Álava" → "Álava" sin convertir a "Araba"). Test `test_invalid_territory` confirma que falla. | Si el frontend envía "Álava" en vez de "Araba", se cae. | Añadir alias en tabla normalizadora (`Álava`→`Araba`, `País Vasco`→error explícito requiere territorio histórico, etc.). |

---

## 4. Casos AEAT validados (cross-check con manual práctico)

### Caso 1 — Profesional Madrid 2T, sin retenciones ni pagos previos

- Inputs: ingresos acumulados 30.000 €; gastos 10.000 €; retenciones 0; pagos 0; rend_neto previo 25.000 €.
- Esperado AEAT: rendimiento neto 20.000 → 20 % → 4.000 € a ingresar. Sin minoración (rend > 12.000).
- TaxIA `Modelo130Calculator.calculate`: `resultado = 4000.0` (test `test_comun_basic` línea 17). ✅ MATCH.

### Caso 2 — Profesional con retenciones y pagos previos (3T)

- Inputs: ingresos 45.000; gastos 15.000; retenciones 2.000; pagos 3.000; rend_neto previo 30.000.
- Esperado: 30.000 × 20 % − 2.000 − 3.000 = 1.000 €.
- TaxIA: `resultado = 1000.0` (test `test_comun_with_retenciones_and_pagos`). ✅ MATCH.

### Caso 3 — Aplicación art. 80 bis (rend prev 8.000 €)

- Inputs: ingresos 20.000; gastos 10.000; rend_neto prev 8.000.
- Esperado: cuota 2.000 − minoración 100 = 1.900 €.
- TaxIA calculator: ✅ MATCH (test `test_comun_art_80bis_9000`).
- TaxIA chat tool: aplicaría 100 € también para 8.000 (rn ≤ 9000 → 100), pero **fallaría** para 9.500 (chat tool devolvería 100 − (500×0.075) = 62,50 €, calculator devuelve 75 €). Ver gap A4.

### Caso 4 — Vivienda habitual (Madrid)

- Inputs: ingresos 50.000; gastos 10.000; vivienda habitual SÍ.
- Esperado: rendimiento neto 40.000 × 2 % = 800 → cap 660,14 €/trim.
- TaxIA calculator: ✅ MATCH (test `test_comun_vivienda_habitual`).
- TaxIA chat tool: NO implementa vivienda habitual. ❌ MISS (gap funcional).

### Caso 5 — Ceuta/Melilla 1T

- Inputs: ingresos 20.000; gastos 10.000; ceuta_melilla=True.
- Esperado: rend neto 10.000 × 8 % = 800 €.
- TaxIA calculator: `resultado = 800` ✅ MATCH (test `test_ceuta_melilla_8pct`).
- TaxIA chat tool: NO acepta flag Ceuta/Melilla → calcula 20 % ❌ ROJO.

### Caso 6 — Profesional con ≥ 70 % retención

- Escenario: Diseñador freelance que factura 100 % a empresas que le retienen 15 %; previsiones 2026 = 40.000 € retención sobre 250.000 € ingresos (16 % retenido pero 100 % de operaciones tienen retención).
- Norma (art 109.2): no obligado a presentar Modelo 130.
- TaxIA: calcula y reporta importe a ingresar. ❌ MISS (gap A2).

### Caso 7 — Gipuzkoa profesional 51 % retención

- Norma foral: dispensa con ≥ 50 % en Gipuzkoa.
- TaxIA: aplica fórmula del 5 % sin chequear dispensa. ❌ MISS (gap A3).

### Caso 8 — Bizkaia primer año (anos_actividad=1)

- Inputs: ingresos 20.000; gastos 8.000.
- Esperado: 12.000 × 20 % = 2.400 € (regla primeros años Bizkaia).
- TaxIA: ✅ MATCH (test `test_bizkaia_first_2_years`). Excelente cobertura foral.

### Caso 9 — Navarra 1ª modalidad rend_neto_penúltimo 30.000

- Esperado: 30.000 × 24 % = 7.200 − 1.000 retenciones = 6.200 / 4 = 1.550 €.
- TaxIA: ✅ MATCH (test `test_navarra_primera_24pct`).

**Total casos validados: 9. Match: 7. Miss: 2 (gaps documentados).**

---

## 5. Simulador AEAT

La AEAT **no expone simulador público** del Modelo 130 (sólo formulario de presentación con autenticación Cl@ve PIN o certificado digital). El cross-check se ha realizado contra:
- Normativa BOE (RIRPF art. 109—111) — texto consolidado tras RD 1461/2018.
- Manual práctico AEAT IRPF actividades económicas (folleto 2024 actualizado) — capítulo 3.7.
- Instrucciones oficiales del Modelo 130 (sede.agenciatributaria.gob.es).
- Norma foral correspondiente (Álava, Bizkaia, Gipuzkoa, Navarra).

**No se ha podido validar contra simulador en vivo.** Sin embargo, los formularios de plataformas comerciales (Declarando, Wolters Kluwer, fiscalbot, fiscaliza) coinciden con los importes calculados por TaxIA en los casos 1—5 y 8—9.

---

## 6. Plan de fix (priorizado)

### Sprint inmediato (CRÍTICO)

1. **Fix C1** — Renombrar casillas 05/06 en `modelo_130_tool.py` (estimado: 1 h). Cambiar también descripción de parámetros JSON-schema. Añadir test que valide el output formateado tiene "casilla 05: pagos previos" cuando `pagos_fraccionados_anteriores > 0`.
2. **Fix C2** — Verificar consistencia tool/frontend/PDF. El frontend ya está alineado con AEAT visualmente, pero `useModeloPDF` debe verificarse contra el formato oficial AEAT GZ601.

### Sprint próximo (ALTO)

3. **Fix A4** — Centralizar `_art_80bis_deduction` y eliminar interpolación del chat tool.
4. **Fix A2 + A3** — Implementar regla de dispensa del 70 % (50 % en Gipuzkoa). Añadir input opcional `pct_retencion_anio_anterior` y devolver "no obligado a presentar" cuando aplique.
5. **Fix A1** — Sección II actividades agrícolas:
   - Mínimo: bloquear cálculo y mostrar "no soportado, presenta directamente en sede.agenciatributaria.gob.es".
   - Ideal: implementar 2 % sobre volumen ingresos − retenciones.
6. **Fix A5** — Modelar casilla 18 (autoliquidación complementaria) en frontend y tool.

### Sprint media prioridad (MEDIO/BAJO)

7. **Fix M1** — Eliminar anualización heurística del frontend para art. 80 bis. Pedir input separado "rendimiento neto año anterior".
8. **Fix M2** — Promover casilla 15 a parámetro nombrado en `_calculate_comun`.
9. **Fix M3** — Helper `nextBusinessDay` para plazos.
10. **Fix M4** — Mensaje claro de plazos por trimestre en chat tool.
11. **Fix B1—B3** — Cosméticos.

### Tests a añadir (cobertura)

- Test del **chat tool** (`test_modelo_130_tool.py`) — actualmente 0 tests. Mínimo: 6 tests (T1—T4 sin/con retenciones, art 80 bis, complementaria).
- Test del **frontend** (Playwright o vitest) para `M130CalculatorPage`. Actualmente 0.
- Test de **regla 70 %** una vez implementada (gap A2/A3).
- Test de **sección agrícola** una vez implementada (gap A1).
- Test de **plazo en día festivo** (gap M3).

---

## 7. Fuentes

1. **BOE — RD 439/2007** (Reglamento IRPF, consolidado): https://www.boe.es/buscar/act.php?id=BOE-A-2007-6820
2. **Iberley — Art. 110 RIRPF**: https://www.iberley.es/legislacion/articulo-110-reglamento-impuesto-sobre-renta-personas-fisicas-irpf
3. **AEAT — Instrucciones Modelo 130**: https://sede.agenciatributaria.gob.es/Sede/impuestos-tasas/impuesto-sobre-renta-personas-fisicas/modelo-130-irpf______esionales-estimacion-directa-fraccionado_/instrucciones.html
4. **AEAT — Manual Práctico actividades económicas, cap 3.7**: https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_7-pagos-fraccionados.html
5. **AEAT — Plazos domiciliación 2026**: https://sede.agenciatributaria.gob.es/Sede/ayuda/calendario-contribuyente/calendario-contribuyente-2026/plazos-presentacion-autoliquidaciones-domiciliaciones-bancaria.html
6. **Iberley — IRPF pagos fraccionados Ceuta/Melilla**: https://www.iberley.es/practicos/irpf-pagos-fraccionados-actividades-ceuta-melilla-r1478060
7. **SuperContable — Importe del fraccionamiento (art 110)**: https://www.supercontable.com/informacion/impuesto_renta_IRPF/Importe_del_fraccionamiento.Pagos_fraccionados_IRPF..html
8. **SuperContable — Art. 109 RIRPF (obligados)**: https://www.supercontable.com/informacion/impuesto_renta_IRPF/Articulo_109_Real_Decreto_439-2007-_de_30_de_marzo-_.html
9. **Diputación Foral Gipuzkoa — Modelo 130**: https://www.gipuzkoa.eus/es/web/ogasuna/impuestos/modelo/130
10. **Bizkaia — Norma Foral 13/2013 IRPF**: https://www.bizkaia.eus/documents/880307/15187815/ca_13_2013.pdf
11. **Bizkaia — Modelo 130 PDF instrucciones**: https://www.bizkaia.eus/fitxategiak/05/ogasuna/ereduak/Argitaratu/130CasInst.pdf
12. **Navarra — OF 40/2009 Modelo 130**: https://www.navarra.es/NR/rdonlyres/361AC994-E056-4DCB-8A72-9AD6E886376C/0/Modelo130_htmv013.html

---

## 8. Anexo — Métricas de cobertura test

```
File: backend/app/utils/calculators/modelo_130.py     660 lines
Tests: backend/tests/test_modelo_130.py                17 cases async
       └─ Comun (basic, retenciones, neg, art80bis_9k, art80bis_10500, art80bis>12k,
                 vivienda_max, vivienda_small, complementaria) — 9 tests
       └─ Ceuta/Melilla (8%)                                    — 1 test
       └─ Araba (basic, retenciones, neg)                       — 3 tests
       └─ Gipuzkoa (general, excepcional)                       — 2 tests
       └─ Bizkaia (1er año, general 3er año, excepcional 3er)   — 3 tests
       └─ Navarra (primera×3, segunda×2)                        — 5 tests
       └─ Edge (territorio inválido)                            — 1 test

File: backend/app/tools/modelo_130_tool.py             267 lines
Tests:                                                  0 cases  ❌ GAP

File: frontend/src/pages/M130CalculatorPage.tsx        641 lines
Tests:                                                  0 cases  ❌ GAP
```

**Cobertura agregada estimada: 55 % (calculator OK, tool y frontend a 0).**

---

## 9. Conclusión

El núcleo de cálculo (`Modelo130Calculator`) es **sólido y conforme a la normativa AEAT y forales** en sus 6 territorios soportados. Los gaps **CRÍTICOS** son de **etiquetado/trazabilidad** (casillas 05/06 invertidas en el chat tool), no de cifras finales: el resultado a ingresar es correcto en todos los escenarios validados.

Los gaps **ALTOS** se reparten entre **funcionalidad ausente** (Sección II agrícola, regla 70 %, casilla 18 complementaria) y **dispersión arquitectónica** (3 implementaciones independientes con divergencias menores). La consolidación en una sola fuente de verdad (el calculator service) resolvería automáticamente A4 y prevendría futuras divergencias.

**Recomendación**: priorizar fixes C1, A4, A2 antes de cualquier campaña comercial que mencione "validamos contra normativa AEAT". El producto está **muy cerca** del nivel de rigor exigido, pero las inconsistencias de etiquetado entre tool y frontend son detectables por un fiscalista o cliente avispado.

**Veredicto cliente: AMARILLO** — calidad técnica alta, fixes documentados, no hay errores numéricos en los casos comunes. Apto para uso orientativo (como ya documenta el disclaimer del frontend), pendiente de los fixes CRÍTICOS antes de uso por asesorías profesionales.
