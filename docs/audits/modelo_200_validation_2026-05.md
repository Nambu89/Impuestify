# Auditoría Modelo 200 — Impuesto sobre Sociedades (2026-05)

**Modelo**: 200 (IS anual) + 202 (pagos fraccionados)
**Norma base**: Ley 27/2014 de 27 de noviembre, del Impuesto sobre Sociedades (LIS), texto consolidado tras BOE-A-2024-26694 (Ley 7/2024, de 20 de diciembre) y RDL 4/2024.
**Forales**: Norma Foral 37/2013 (Álava), Norma Foral 11/2013 (Bizkaia), Norma Foral 2/2014 (Gipuzkoa), Ley Foral 26/2016 (Navarra). Reforma Gipuzkoa: NF 1/2025.
**Especiales**: Art. 43 Ley 19/1994 (ZEC Canarias), Art. 33.6 LIS (Ceuta y Melilla).
**Plazo IS 2024**: 1 al 25 de julio de 2025 (domiciliación hasta el 20).
**Estado en TaxIA**: **IMPLEMENTACIÓN ROBUSTA — REQUIERE ACTUALIZACIÓN URGENTE A LEY 7/2024**.

---

## Fase 1 · Inventario en TaxIA

| Componente | Existe | Ubicación |
|---|---|---|
| Calculadora núcleo | SÍ | `backend/app/utils/is_simulator.py` (371 líneas, dataclasses `ISInput` / `ISResult` / `IS202Result`, clase `ISSimulator` con pipeline 14 pasos) |
| Escalas y regímenes | SÍ | `backend/app/utils/is_scales.py` (7 regímenes: COMUN, ALAVA, BIZKAIA, GIPUZKOA, NAVARRA, CANARIAS_ZEC, CEUTA_MELILLA) |
| Tool LLM (function calling) | SÍ | `backend/app/tools/is_simulator_tool.py` (`simulate_is`, 23 parámetros) |
| Endpoints REST públicos | SÍ | `backend/app/routers/is_estimate.py` — `POST /api/irpf/is-estimate`, `POST /api/irpf/is-202` (sin auth, ~50-100ms) |
| Endpoint prefill workspace | SÍ | `GET /api/workspaces/{id}/is-prefill?ejercicio=YYYY` (auth, agrega facturas + desglose PGC) |
| Frontend wizard | SÍ | `frontend/src/pages/Modelo200Page.tsx` (4 pasos: Entidad → Resultado contable → Ajustes → Resultado), prefill desde workspace |
| Generador PDF | SÍ | `routers/export.py /api/export/modelo-pdf` con `"200"` en `VALID_MODELOS` |
| Tests backend | SÍ | `tests/test_is_simulator.py` (29 tests), `tests/test_is_estimate.py` (15 tests), `tests/test_is_prefill.py` (6 tests) — total 47+ |
| Calendario fiscal | SÍ | obligación anual IS + 3 trimestrales 202 (abril / octubre / diciembre, día 1-20) |

**Pipeline implementado**:
1. Resultado contable (directo o ingresos − gastos) → 2-3. ajustes ± → 4. reserva capitalización → 5. BI previa → 6. compensación BINs → 7. BI (floor 0) + RIC Canarias → 8. tipo gravamen por tramos → 9. cuota íntegra → 10. deducciones (límite cuota) → 11. bonificaciones (Ceuta/Melilla) → 12. cuota líquida → 13-14. retenciones + pagos fraccionados → resultado.

---

## Fase 2 · Normativa de referencia

| Recurso | URL | Usado |
|---|---|---|
| Ley 27/2014 LIS (consolidado) | https://www.boe.es/buscar/act.php?id=BOE-A-2014-12328 | SÍ (parcial, contenido truncado en WebFetch) |
| Ley 7/2024 BOE-A-2024-26694 (IS reformas) | https://www.boe.es/buscar/act.php?id=BOE-A-2024-26694 | SÍ (Disp. Final 8ª) |
| AEAT Novedades IS Ley 7/2024 | https://sede.agenciatributaria.gob.es/Sede/impuesto-sobre-sociedades/novedades-impuesto-sobre-sociedades/novedades-normativa-2024.html | SÍ |
| AEAT Manual Sociedades 2024 — Reserva Capitalización | https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/manual-sociedades-2024/principales-novedades-impuesto-sobre-sociedades-2024/reserva-capitalizacion.html | SÍ |
| Wolters Kluwer "IS 2025-2026 novedades" | https://www.wolterskluwer.com/es-es/expert-insights/impuesto-sociedades-2025-2026-novedades | SÍ |
| Hacienda Foral Bizkaia 2024-2025 | https://www.bizkaia.eus/en/sozietateen-zerga | Referencia |
| Hacienda Foral Gipuzkoa NF 1/2025 | https://www.sayma.es/en/reforma-fiscal-en-gipuzkoa-norma-foral-1-2025-cambios-clave-en-fiscalidad-y-sus-efectos-segun-la-fecha-de-entrada-en-vigor/ | Referencia |
| AEAT Modelo 200 Sede | https://sede.agenciatributaria.gob.es/Sede/iva-otros-impuestos/impuesto-sobre-sociedades/modelo-200.html | 404 (URL inválida; usar `procedimientoini/GE04.shtml`) |

**Limitación**: BOE-A-2024-26694 es PDF de gran tamaño y la Disp. Final 8ª no se renderiza limpia vía WebFetch. Datos cruzados con AEAT (fuente primaria) + WK + Cuatrecasas + Suárez Economistas (concordantes).

---

## Fase 3 · Cross-check normativa vs implementación

### 3.1 Tipos de gravamen (Art. 29 LIS)

| Régimen | Norma vigente 2024 (Modelo 200 que se presenta jul-2025) | Norma vigente 2025 (Modelo 200 que se presentará jul-2026) | TaxIA actual | Veredicto |
|---|---|---|---|---|
| **General** | 25% | 25% | 25% (`COMUN.tramos_general`) | OK |
| **Microempresa INCN<1M** | 23% sobre toda la BI (RDL 4/2024) | **Escala 17% / 20%**: 17% primeros 50.000€, 20% resto (Ley 7/2024) | **23% primeros 50k + 25% resto** (`COMUN.tramos_pyme`) | **DESACTUALIZADO** — confunde "PYME ERD" con "microempresa" y mantiene escala antigua. Para 2024 era 23% **plano**, no escala. Para 2025 deben aplicarse 17%/20%. |
| **PYME / ERD INCN<10M** | 25% (sin reducción específica salvo reserva nivelación) | Transitoria progresiva 2025-2029 hasta 20% | **No hay tramo específico**; cualquier facturación entre 1M y 10M cae al 25% general | **GAP** — TaxIA no diferencia ERD (1M ≤ INCN < 10M). Trigger en código es `facturacion_anual < 1_000_000` (`is_simulator.py:302`), por lo que ERD se grava al 25%. Falta escala transitoria. |
| **Nueva creación** | 15% (primeros 50k) / luego 25% — Art. 29.1 LIS dice **15% sobre toda la BI** los 2 primeros ejercicios con BI positiva | Igual | **15% primeros 50k + 20% resto** (`COMUN.tramos_nueva_creacion`) | **INCORRECTO** — Art. 29.1 LIS aplica 15% **plano** sobre TODA la BI (no escala), salvo que sea entidad de crédito o hidrocarburos. Los 50k+20% es contaminación con régimen pyme antiguo. |
| **Cooperativas fiscalmente protegidas** | 20% (Ley 20/1990) | 20% | **No implementado** | GAP — falta `tipo_entidad="cooperativa"` |
| **ZEC Canarias** | 4% (Art. 43 Ley 19/1994) | 4% | 4% (`CANARIAS_ZEC`) | OK |
| **Bonificación Ceuta/Melilla** | 50% cuota Art. 33.6 | 50% | 50% (`CEUTA_MELILLA.bonificacion_cuota=0.5`) | OK |

**Forales (vigente 2024-2025)**:

| Territorio | General | PYME | Microempresa | TaxIA | Veredicto |
|---|---|---|---|---|---|
| **Bizkaia** (NF 11/2013) | 24% | 20% (PE) | 20% (microempresa con tributación mínima) | 20% pyme + 24% general; sin distinción ME | OK base, **GAP**: BIN sin límite micro/pequeña empresa desde 2025 (no implementado) |
| **Gipuzkoa** (NF 2/2014 + NF 1/2025) | 24% (mantiene 2024); **2025: 19% general / 17% / 15%** según plantilla e inversiones | 20% PE | n/a | 20% pyme + 24% general | OK 2024; **DESACTUALIZADO** para 2025 (NF 1/2025: 19%/17%/15% según plantilla) |
| **Álava** (NF 37/2013) | 24% | 20% PE | n/a | 20% pyme + 24% general | OK 2024 |
| **Navarra** (LF 26/2016) | 28% (general) / 23% (PYME) | 23% | 19% (microempresa) | 23% pyme + 28% general | OK base, **GAP**: tramo microempresa 19% no implementado |

**Veredicto sección tipos**: implementación 2024 mayoritariamente correcta para régimen común y forales en su versión 2024, pero **el cambio Ley 7/2024 (microempresa 17%/20% + ERD transitoria + Art. 29.1 plano 15%) NO está reflejado**. La etiqueta "PYME" en TaxIA mezcla microempresa y ERD.

### 3.2 Reserva de capitalización (Art. 25 LIS)

| Periodo | Porcentaje vigente | Límite reducción | TaxIA |
|---|---|---|---|
| Hasta 2023 | 10% | 10% BI previa | — |
| 2024 (RDL 4/2024) | **15%** | 10% BI (general) / 25% para INCN<1M | **10%** (`IS_DEDUCCIONES_COMUN.reserva_cap_pct=10.0`) |
| 2025 (Ley 7/2024) | **20% base + 23%/26,5%/30% según incremento plantilla 2-5%/5-10%/+10%** | 20% BI (25% si INCN<1M) | **10%** (sin actualizar) |

**Bug**: el porcentaje cableado en `is_scales.py:145-148` para todos los regímenes comunes y forales es 10%. Para ejercicio **2024** debería ser 15%; para **2025** debería ser 20% (con escalado por plantilla). Límite del 10% sobre BI previa también está obsoleto (debe ser 20%/25%).

```python
# is_simulator.py:268-278  — limite hardcoded 10% obsoleto
def _calcular_reserva_capitalizacion(inp, base_previa):
    ...
    limite = base_previa * 0.10  # ← debe ser 0.20 (2025) o 0.25 (microempresa)
    return round(min(reserva, limite), 2)
```

### 3.3 Reserva de nivelación (Art. 105 LIS) — PYME/ERD

10% de la BI positiva, máximo 1.000.000€. **NO IMPLEMENTADA** en `ISInput` ni en el pipeline. Es un beneficio fiscal específico de ERD (INCN<10M) que reduce BI con compensación obligatoria en 5 años. Falta campo de entrada y lógica de aplicación.

### 3.4 Compensación BINs (Art. 26 LIS)

| Norma | TaxIA |
|---|---|
| Sin límite cuantitativo: facturación <20M (con suelo 1M€ siempre compensables) | `_calcular_bins`: `>20M → 70%; resto → 100%` |
| 70% de la BI previa: 20M ≤ INCN < 60M | OK (engloba `>20M`) |
| 50% de la BI previa: INCN ≥ 60M | **NO IMPLEMENTADO** (TaxIA aplica 70% para todos >20M) |
| Mínimo 1.000.000€ siempre compensables (Art. 26.1 párrafo 2º) | **NO IMPLEMENTADO** (TaxIA no aplica suelo de 1M en grandes) |
| Bizkaia/Gipuzkoa micro/pequeña 2025 sin límite | **NO IMPLEMENTADO** |

```python
# is_simulator.py:280-295 — falta tramo INCN≥60M (50%) y suelo 1M€
if inp.facturacion_anual > 20_000_000:
    limite = base_previa * 0.70
else:
    limite = base_previa
# Falta: if INCN >= 60M → 50%; siempre permitir min(1.000.000, BIN_pendiente)
```

### 3.5 Deducciones I+D+i (Art. 35 LIS)

| Concepto | Norma vigente | TaxIA |
|---|---|---|
| **I+D base** (Art. 35.1.b) | 25% gastos I+D | 25% (`IS_DEDUCCIONES_COMUN.id_pct=25.0`) — OK |
| **I+D adicional** (gastos > media de 2 ejercicios anteriores) | **42%** sobre el exceso | **NO IMPLEMENTADO** — TaxIA aplica 25% plano sin distinguir base/exceso |
| **I+D personal investigador** (Art. 35.1.b) | +17% adicional | **NO IMPLEMENTADO** |
| **I+D inmovilizado afecto** (Art. 35.1.b) | +8% adicional | **NO IMPLEMENTADO** |
| **Innovación tecnológica IT** (Art. 35.2) | 12% | 12% (`it_pct=12.0`) — OK |
| **Límite global** Art. 39.1 | 25% cuota íntegra (general) / **50% si I+D+IT > 10% cuota** | 25% (correcto base); **NO** se aplica el 50% ampliado |
| **Forales Bizkaia/Gipuzkoa** | I+D 30%, IT 15%, límite 35% | 30% / 15% / 35% — OK |
| **Monetización** (Art. 39.2) | I+D+i puede monetizarse con descuento del 20% si no hay cuota | **NO IMPLEMENTADO** |

### 3.6 Deducciones inversiones cinematográficas (Art. 36 LIS)

**NO IMPLEMENTADAS**. Son críticas para productoras y plataformas de creadores (cliente Creator):
- 36.1: 30% primer millón / 25% resto (producciones españolas).
- 36.2: 30% / 25% (producciones extranjeras rodadas en España).
- 36.3: 20% espectáculos en vivo.
- Límite: 20% cuota íntegra; mínimo 50% gasto en territorio español.

### 3.7 Deducción empleo trabajadores con discapacidad (Art. 38 LIS)

| Norma | TaxIA |
|---|---|
| 9.000€ por persona/año incremento media plantilla discapacidad ≥33% y <65% | 9.000€ (`empleados_discapacidad_33 * 9_000`) — OK |
| 12.000€ por persona/año incremento media plantilla discapacidad ≥65% | 12.000€ — OK |
| Sin límite sobre cuota íntegra | OK (`empleo_total` se suma fuera del bloque limitado) |
| Requisito: incremento de la **media** anual (no el total de empleados) | **GAP UX**: el campo `empleados_discapacidad_33` se documenta como "número de empleados", debería ser **incremento medio anual** |

### 3.8 Donativos mecenazgo (Ley 49/2002)

| Norma | TaxIA |
|---|---|
| 40% primeros 150€ | **NO IMPLEMENTADO** (TaxIA aplica 35% plano) |
| 35% resto | OK |
| 40% si recurrencia (mismo importe igual o superior 2 ejercicios anteriores) | **NO IMPLEMENTADO** |
| Límite: 10% BI | **NO IMPLEMENTADO** (TaxIA solo aplica límite cuota íntegra global) |

Ley 49/2002 es para personas físicas con tramo 80% / 35% / 40%. Para Sociedades (Art. 20 Ley 49/2002): **40%** general (Sociedades), no 35%. **El 35% cableado en `is_simulator.py:337` es incorrecto**.

```python
# is_simulator.py:336-337
if inp.donativos > 0:
    detalle["donativos"] = round(inp.donativos * 0.35, 2)  # ← debe ser 0.40 para Sociedades
```

### 3.9 RIC Canarias (Art. 27 Ley 19/1994)

| Norma | TaxIA |
|---|---|
| Reduce BI hasta 90% del beneficio del establecimiento permanente en Canarias **NO distribuido** | `is_simulator.py:170-173` aplica `90% resultado_contable` como límite |
| Materialización en 3 años (4 años activos fijos) | **NO TRACKEADO** |
| Reversión si no se materializa | **NO IMPLEMENTADO** |
| Compatible con ZEC pero excluyente parcial | **NO COMPROBADO** (`es_zec=True` sigue permitiendo `dotacion_ric>0`) |

### 3.10 ZEC Canarias

| Norma | TaxIA |
|---|---|
| 4% sobre tramo BI límite ZEC (límite calculado por puestos de trabajo creados, mínimo 5; el resto al tipo general) | TaxIA aplica 4% sobre **toda la BI** sin tramo |
| Mínimo 5 puestos (3 áreas remotas) | **NO VERIFICADO** |
| Inversión mínima 100.000€ (50.000€ áreas remotas) | **NO VERIFICADO** |

**Bug**: una empresa ZEC con 200.000€ BI y solo 5 trabajadores tiene límite ZEC = 1,8M€/trabajador (variable); el exceso debería tributar al 25%. TaxIA aplica 4% plano sin techo, sobreestimando el ahorro.

### 3.11 Bonificación Ceuta/Melilla (Art. 33.6 LIS)

Implementación correcta de la proporción `rentas_ceuta_melilla / resultado_contable`. Validar:
- Norma exige actividad real con establecimiento permanente y ≥1 empleado domiciliado (no verificable en simulador, OK como disclaimer).
- Bonificación 50% solo sobre cuota proporcional a rentas obtenidas allí. **OK**.

### 3.12 Pagos fraccionados (Modelo 202 — Art. 40 LIS)

| Concepto | Norma | TaxIA |
|---|---|---|
| Modalidad Art. 40.2 (cuota): 18% | 18% sobre cuota último ejercicio menos retenciones, deducciones, bonificaciones | 18% — OK |
| Modalidad Art. 40.3 (BI corriente): 17% (5/7 × tipo gravamen, redondeo defecto) | INCN<10M → 17% (5/7 × 25 ≈ 17,85, redondeo 17%) | 17% — OK |
| Modalidad Art. 40.3 obligatoria si INCN ≥ 6M | 19/20 × tipo gravamen redondeo defecto = **24%** (INCN ≥ 10M) | TaxIA aplica 24% si `>10M` — OK |
| Pago mínimo INCN ≥ 10M (DA 14ª LIS): 23% sobre resultado positivo (25% entidades crédito y hidrocarburos) | **NO IMPLEMENTADO** (TaxIA no calcula el pago fraccionado mínimo) | **GAP** |
| Calendario abril/octubre/diciembre | OK | OK |

### 3.13 Otros gaps relevantes

- **Tributación mínima** (Art. 30 bis LIS, RDL 4/2024): cuota líquida ≥ 15% BI (10% nuevas creación / 18% bancos e hidrocarburos). **NO IMPLEMENTADO**. Microempresas <1M Ley 7/2024: **15/25 × tipo gravamen** redondeo arriba = ~10,2% (escala 17/20). Implementación nula.
- **Impuesto Complementario (Pillar 2)**: para grupos > 750M€. Fuera de scope SaaS.
- **Libertad de amortización Art. 12.3 LIS**: ERD ≤120.000€/año, +20% empresas vehículos eléctricos, etc. **NO IMPLEMENTADO** (el simulador toma la diferencia entre amortización contable y fiscal como input ya calculado, pero no asiste a calcularla).
- **Gastos no deducibles Art. 15**: lista cerrada (multas, donativos sin soporte, intereses préstamos participativos intra-grupo, retribuciones FFPP, etc.). Sólo hay un input agregado (`gastos_no_deducibles`), sin desglose ni validación.
- **Limitación gastos financieros Art. 16 LIS**: 30% beneficio operativo, mínimo 1M€. **NO IMPLEMENTADO**.
- **Operaciones vinculadas (Art. 18)**: documentación obligatoria. Fuera de simulador, OK.

---

## Fase 4 · Casos prácticos (sin simulador AEAT — Manual Práctico Sociedades 2024)

### Caso 4.1 — SL Madrid 2024 ejercicio (regla "general" 25% plano)

Datos: BI 100.000€, sin ajustes, sin BINs.

| Cálculo | Esperado AEAT 2024 | TaxIA |
|---|---|---|
| Cuota íntegra | 100.000 × 25% = 25.000€ | 25.000€ (test `test_sl_basica_25pct`) |

**OK** (régimen general 25% no cambia con Ley 7/2024).

### Caso 4.2 — Microempresa INCN 800.000€ (Madrid, ejercicio 2025)

Datos: BI 100.000€, INCN periodo anterior 800.000€.

| Cálculo | Norma 2025 (Ley 7/2024) | TaxIA actual |
|---|---|---|
| Tramo 0-50.000 | 50.000 × 17% = 8.500€ | 50.000 × 23% = 11.500€ |
| Resto | 50.000 × 20% = 10.000€ | 50.000 × 25% = 12.500€ |
| Cuota íntegra | **18.500€** | **24.000€** (test `test_pyme_23_25_tramos`) |
| Diferencia | — | **+5.500€ sobreestima** (29,7%) |

**ERROR ALTO IMPACTO** para clientes microempresa 2025.

### Caso 4.3 — Nueva creación SL ejercicio 2024 (Madrid)

Datos: BI 100.000€, primer ejercicio con BI positiva.

| Cálculo | Norma vigente Art. 29.1 LIS | TaxIA |
|---|---|---|
| Cuota íntegra | 100.000 × 15% **plano** = 15.000€ | 50k×15% + 50k×20% = 17.500€ (test `test_nueva_creacion_15_20`) |
| Diferencia | — | **+2.500€ sobreestima** (16,7%) |

**ERROR**: Art. 29.1 dice expresamente "tributarán al tipo del 15 por ciento" sin escala. La estructura de tramos es contaminación.

### Caso 4.4 — Reserva capitalización 2024 (Madrid)

Datos: BI previa 100.000€, incremento FFPP 50.000€.

| Cálculo | Norma 2024 (RDL 4/2024) | TaxIA |
|---|---|---|
| Reducción potencial | 50.000 × 15% = 7.500€ | 50.000 × 10% = 5.000€ |
| Límite (10% BI previa) | 10.000€ | 10.000€ |
| Reducción aplicada | 7.500€ | 5.000€ |
| BI final | 92.500€ | 95.000€ (test `test_reserva_capitalizacion`) |
| Diferencia BI | — | **+2.500€ sobreestima** |

### Caso 4.5 — BIN compensación gran empresa INCN 65M

Datos: BI previa 5M, BINs pendientes 10M.

| Cálculo | Norma | TaxIA |
|---|---|---|
| Límite legal | 50% × 5M = 2,5M (+ siempre 1M = total compensable 1M mínimo, pero el límite porcentual es 2,5M) | 70% × 5M = 3,5M |
| Compensación aplicada | 2,5M | 3,5M (TaxIA usa tramo único `>20M=70%`) |
| BI final | 2,5M | 1,5M |
| Subdeclaración | — | **−1M BI = −250.000€ cuota** |

### Caso 4.6 — ZEC Canarias BI 500.000€ con 5 empleados

Sin saber el techo ZEC concreto (depende de inversión y empleados), TaxIA aplica 4% × 500k = **20.000€**. La regla real: 4% solo sobre tramo limitado (mínimo 1.800.000€/empleo creado por encima del mínimo legal); para una empresa nueva con 5 empleados el techo puede ser muy bajo y el exceso tributa al 25%. Para cumplir como SaaS: añadir disclaimer + campo "puestos de trabajo creados".

### Caso 4.7 — Donativos Sociedad

Donativo 10.000€ Ley 49/2002.

| Cálculo | Norma (Art. 20 Ley 49/2002) | TaxIA |
|---|---|---|
| Deducción | 40% × 10.000 = 4.000€ | 35% × 10.000 = 3.500€ |
| Subdeducción | — | **−500€** |

---

## Fase 5 · Simulador AEAT

AEAT **no publica** un simulador público del Modelo 200 (a diferencia de Renta WEB para IRPF). Existe únicamente el formulario telemático Sociedades WEB y el programa de cumplimentación, ambos requieren NIF de la entidad y certificado, no son utilizables como ground truth automatizado.

**Vías de validación**:
1. **Manual Práctico Sociedades 2024** (AEAT) — ejemplos numéricos por capítulos. Recomendado descargar y cargar como ground truth en RAG.
2. **Casos jurisprudenciales TEAC/TEAR** — útiles para reglas no obvias (operaciones vinculadas, reserva capitalización, BINs).
3. **Software comercial** (A3, Sage, Wolters Kluwer) — comparación uno-a-uno fuera de scope.
4. **Foral**: BizkaiBai, GipuzkoaTaxa, Hacienda Foral Navarra publican simuladores online accesibles para validación cruzada.

---

## Fase 6 · Resumen ejecutivo y prioridades

### Severidad ALTA (corregir antes de campaña 2025 — julio 2026)

| # | Bug | Impacto | Archivo |
|---|---|---|---|
| H1 | Microempresa Ley 7/2024 (escala 17%/20%) no implementada | Sobreestima ~30% cuota microempresas <1M | `is_scales.py:36`, `is_simulator.py:_seleccionar_tramos` |
| H2 | Nueva creación aplica 15%/20% en escala en vez de 15% plano (Art. 29.1) | Sobreestima 16% en BI > 50k | `is_scales.py:37` (todos regímenes con `tramos_nueva_creacion`) |
| H3 | Reserva capitalización al 10%/10% (debería ser 15%/10% en 2024 y 20%/20% (25% si <1M) en 2025) | Subdeducción significativa | `is_scales.py:145-148`, `is_simulator.py:277` |
| H4 | BINs sin tramo INCN ≥ 60M (50%) ni suelo de 1M€ | Subdeclaración grupos grandes | `is_simulator.py:280-295` |
| H5 | Donativos al 35% en vez de 40% (Sociedades, Art. 20 Ley 49/2002) | Subdeducción ~14% | `is_simulator.py:337` |
| H6 | Tipo gravamen ERD (1M ≤ INCN < 10M) sin escala transitoria 2025-2029 | Sobreestima clientes 1M-10M | `is_scales.py`, `is_simulator.py:_seleccionar_tramos` |

### Severidad MEDIA (siguiente sprint)

| # | Gap | Impacto |
|---|---|---|
| M1 | Reserva nivelación Art. 105 (10% BI, máx 1M, ERD) no implementada | Beneficio fiscal típico ERD no se aprovecha |
| M2 | Tributación mínima Art. 30 bis (15% BI; 10% nueva creación) no implementada | Cuota líquida puede caer por debajo del mínimo legal |
| M3 | Pago fraccionado mínimo DA 14ª (23% resultado positivo INCN ≥10M) no calculado | Cliente grande paga menos de lo legal |
| M4 | Cooperativas fiscalmente protegidas (20%) no implementadas | Segmento sin cobertura |
| M5 | I+D+i: falta 42% exceso, +17% personal, +8% inmovilizado, monetización | Subdeducción severa para empresas innovadoras |
| M6 | ZEC Canarias sin límite por empleos creados | Sobreestima beneficio ZEC |
| M7 | Microempresa Navarra (19%) y reformas Gipuzkoa NF 1/2025 (19%/17%/15%) no implementadas | Foral 2025 desactualizado |
| M8 | BIN sin límite Bizkaia/Gipuzkoa micro/pequeña 2025 no aplicado | Foral 2025 desactualizado |
| M9 | Deducciones cinematográficas Art. 36 (30%/25%) no implementadas | Segmento Creator/productora sin cobertura |
| M10 | Donativos: tramo primeros 150€ al 40% + recurrencia +5% no implementado | Subdeducción incremental |

### Severidad BAJA (mejora UX y completitud)

| # | Mejora |
|---|---|
| L1 | Campo `empleados_discapacidad_*` debería etiquetarse como "incremento medio anual de plantilla" en `is_simulator_tool.py` y frontend |
| L2 | Add disclaimer ZEC: "el simulador no calcula el techo ZEC por empleos creados; consulta tu Comité ZEC" |
| L3 | RIC: trackear materialización 3-4 años (workspace) |
| L4 | Limitación gastos financieros Art. 16 LIS (30% beneficio operativo) |
| L5 | Wizard frontend: separar "Microempresa", "PYME (ERD)" y "Gran empresa" como `tipo_entidad` (no inferir solo por facturación) |
| L6 | Documentar en system prompts y RAG la diferencia microempresa vs ERD |
| L7 | Test `test_pyme_23_25_tramos` está semánticamente equivocado: no es PYME (que usaría 25% en 2024) sino "ERD bajo régimen anterior". Renombrar y añadir tests para cada nueva escala |
| L8 | Añadir parámetro `ejercicio` al `ISInput` para seleccionar escala correcta (2024 vs 2025 vs 2026 transitoria) — actualmente solo el frontend lo recoge pero no se propaga al backend |

### Recomendación de implementación

1. **Refactor `is_scales.py`**: introducir `ISRegimen` parametrizado por `ejercicio` con función `get_is_regimen(territorio, es_zec, ejercicio)`. Mantener escala 2024 y 2025 separadas. Añadir `tramos_microempresa` y `tramos_erd_transitoria` distinguidos.
2. **Refactor `_seleccionar_tramos`**: lógica `INCN<1M → microempresa`, `1M≤INCN<10M → ERD`, `INCN≥10M → general`. `nueva_creacion` toma siempre `tramos_nueva_creacion` (15% plano si no es entidad de crédito).
3. **Añadir** `reserva_nivelacion` y `tributacion_minima` al pipeline. Insertar entre paso 12 (cuota líquida) y 13 (retenciones).
4. **Tests regresión**: 47 actuales se mantienen; añadir bloque por ejercicio (≥30 nuevos tests cubriendo Ley 7/2024 y forales 2025).
5. **Disclaimer reforzado** en `disclaimer` field: "Cálculo basado en normativa vigente en {ejercicio}. Cambios Ley 7/2024 aplicables desde 1 enero 2025. No sustituye asesoramiento fiscal."
6. **RAG ingesta**: subir Manual Práctico Sociedades 2024 (PDF AEAT) cuando se publique el de 2025 (esperado mar-abr 2026).

---

## Conclusión

El Modelo 200 en TaxIA está **arquitectónicamente bien diseñado** (pipeline 14 pasos, dataclasses claras, 47 tests pasando, prefill workspace, generador PDF, frontend wizard), pero su contenido normativo está **anclado en pre-Ley 7/2024**. Para uso comercial en campaña julio 2026 (ejercicio 2025) hay que actualizar urgentemente:

- Tipos microempresa (17%/20%) y ERD transitoria.
- Reserva capitalización (20% / 23-30% por plantilla, límite 20-25% BI).
- BINs (tramo 50% INCN≥60M + suelo 1M€).
- Nueva creación 15% plano (Art. 29.1).
- Donativos Sociedades 40%.
- Foral Gipuzkoa NF 1/2025 (19%/17%/15%).

Sin estos fixes, TaxIA produce **sobreestimaciones del 16-30%** en microempresa y nueva creación, y **subdeclaraciones** en grupos grandes (BINs) y entidades innovadoras (I+D+i 42%, monetización). El framework permite iteración incremental sin refactor mayor.

**Esfuerzo estimado**: 5-7 días-persona para Severidad Alta + Media (7+10 items), incluyendo tests regresión y actualización RAG.
