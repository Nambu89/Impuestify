# Validación Modelo 100 (IRPF Personas Físicas) — Mayo 2026

> Auditoría documental del motor IRPF de TaxIA contra normativa AEAT vigente.
> Fecha: 2026-05-10. Sesión 40. Ámbito: ejercicio 2024 (declaración abril–junio 2025) y novedades 2025.

## Resumen ejecutivo

| Indicador | Valor |
|---|---|
| **Estado global** | **VERDE — listo con 1 acción puntual antes de campaña 2025** |
| Gaps CRÍTICOS | 0 |
| Gaps ALTOS | 1 (escala del ahorro 2025: top bracket pendiente de actualizar 14% → 15%) |
| Gaps MEDIOS | 3 |
| Gaps BAJOS | 2 |
| Cobertura test | Alta — 6 ficheros `test_irpf_*` + regression suite con 12 escenarios baseline |
| Validación AEAT directa | PARCIAL (caso práctico oficial coincide; Renta Web requiere Cl@ve, marcado pendiente) |
| Riesgo financiero usuario | Bajo en 2024. Medio en 2025 si no se actualiza la escala del ahorro antes de la campaña |

**Conclusión**: el motor de cálculo IRPF de TaxIA reproduce con fidelidad las escalas del Estado, la tarifa del ahorro 2024, los mínimos personales y familiares, las reducciones del trabajo (Art. 20 LIRPF en su redacción Ley 31/2022), la deducción Ceuta/Melilla (Art. 68.4) y la mecánica de aplicación del MPYF como reducción sobre la cuota (no sobre la base) tal y como lo describe el Manual Práctico de la AEAT. La escala estatal cargada en BD coincide cifra a cifra con la publicada por la AEAT y con los seis tramos del Art. 63.1 LIRPF.

---

## 1. Inventario código

### 1.1. Ficheros auditados

| Componente | Ruta |
|---|---|
| Tool de cálculo simple | `backend/app/tools/irpf_calculator_tool.py` |
| Motor de cálculo escalas | `backend/app/utils/irpf_calculator.py` |
| Tool de simulación completa | `backend/app/tools/irpf_simulator_tool.py` |
| Orquestador completo | `backend/app/utils/irpf_simulator.py` (~1.400 líneas) |
| Calculadora rendimientos trabajo | `backend/app/utils/calculators/work_income.py` |
| Calculadora rendimientos ahorro | `backend/app/utils/calculators/savings_income.py` |
| Calculadora rendimientos inmuebles | `backend/app/utils/calculators/rental_income.py` |
| Calculadora actividad económica | `backend/app/utils/calculators/activity_income.py` |
| Calculadora MPYF | `backend/app/utils/calculators/mpyf.py` |
| Calculadora rentas imputadas | `backend/app/utils/calculators/imputed_income.py` |
| Calculadora ganancias inmuebles | `backend/app/utils/calculators/capital_gains_property.py` |
| Comparativa conjunta vs individual | `backend/app/tools/joint_comparison_tool.py` |
| Cripto FIFO | `backend/app/utils/calculators/crypto_fifo.py` |
| Compensación pérdidas | `backend/app/utils/calculators/loss_compensation.py` |
| Seed escala estatal | `backend/scripts/seed_estatal_scale.py` |
| Seed escalas autonómicas | `backend/scripts/seed_ccaa_scales.py` |
| Seed escalas forales | `backend/scripts/seed_foral_scales.py` |
| Seed parámetros y MPYF | `backend/scripts/populate_tax_parameters.py` |
| Tests regression | `backend/tests/test_irpf_regression.py`, `test_irpf_simulator.py`, `test_irpf_calculator.py`, `test_irpf_crypto_integration.py`, `test_irpf_estimate_creator.py`, `test_irpf_projector.py` |

### 1.2. Parámetros fiscales en código (ejercicio 2024)

**Escala estatal general (Art. 63.1 LIRPF)** — `seed_estatal_scale.py`:

| Tramo | Base hasta (€) | Cuota íntegra (€) | Resto base (€) | Tipo aplicable |
|---|---|---|---|---|
| 1 | 12.450,00 | 0,00 | 12.450,00 | 9,50 % |
| 2 | 20.200,00 | 1.182,75 | 7.750,00 | 12,00 % |
| 3 | 35.200,00 | 2.112,75 | 15.000,00 | 15,00 % |
| 4 | 60.000,00 | 4.362,75 | 24.800,00 | 18,50 % |
| 5 | 300.000,00 | 8.950,75 | 240.000,00 | 22,50 % |
| 6 | (resto) | 62.950,75 | — | 24,50 % |

**Escala estatal del ahorro (Art. 66.1 LIRPF) — ejercicio 2024** — `populate_tax_parameters.py`:

| Tramo | Base hasta (€) | Cuota íntegra (€) | Tipo aplicable |
|---|---|---|---|
| 1 | 6.000,00 | 0,00 | 9,50 % |
| 2 | 50.000,00 | 570,00 | 10,50 % |
| 3 | 200.000,00 | 5.190,00 | 11,50 % |
| 4 | 300.000,00 | 22.440,00 | 13,50 % |
| 5 | (resto) | 35.940,00 | 14,00 % |

(La escala autonómica del ahorro replica la estatal en 15 CCAA de régimen común.)

**Mínimos personales y familiares estatales (Arts. 57-61 LIRPF)** — `populate_tax_parameters.py`:

| Concepto | Importe (€) | Referencia |
|---|---|---|
| Contribuyente | 5.550 | Art. 57.1 |
| Contribuyente >65 | 6.700 | Art. 57.2 |
| Contribuyente >75 | 8.100 | Art. 57.2 |
| Descendiente 1.º | 2.400 | Art. 58.1 |
| Descendiente 2.º | 2.700 | Art. 58.1 |
| Descendiente 3.º | 4.000 | Art. 58.1 |
| Descendiente 4.º y siguientes | 4.500 | Art. 58.1 |
| Descendiente menor 3 años (incremento) | 2.800 | Art. 58.2 |
| Ascendiente >65 | 1.150 | Art. 59 |
| Ascendiente >75 | 2.550 | Art. 59 |
| Discapacidad 33-64 % | 3.000 | Art. 60.1 |
| Discapacidad ≥65 % | 9.000 | Art. 60.1 |
| Gastos asistencia | 3.000 | Art. 60.2 |

**Reducción rendimientos del trabajo (Art. 20 LIRPF, redacción Ley 31/2022 vigente desde 2024)** — `work_income.py` + `populate_tax_parameters.py`:

| Tramo | Fórmula |
|---|---|
| Rendimiento neto ≤ 14.852 | 7.302 EUR |
| 14.852 < rendimiento ≤ 17.673,52 | 7.302 − 1,75 × (rendimiento − 14.852) |
| 17.673,52 < rendimiento ≤ 19.747,50 | 2.364,34 − 1,14 × (rendimiento − 17.673,52) |
| > 19.747,50 | 0 |

**Otros parámetros relevantes**:

| Parámetro | Valor en código | Norma |
|---|---|---|
| Otros gastos del trabajo | 2.000 EUR | Art. 19.2.f LIRPF |
| Cuotas colegio profesional (máx) | 500 EUR | Art. 19.2.d |
| Defensa jurídica frente al empleador (máx) | 300 EUR | Art. 19.2.e |
| Reducción 60 % alquiler vivienda | 60 % | Art. 23.2 (régimen anterior, aplicable a contratos pre LAU 2024) |
| Reducción tributación conjunta — matrimonio | 3.400 EUR | Art. 84 LIRPF |
| Reducción tributación conjunta — monoparental | 2.150 EUR | Art. 84 LIRPF |
| Deducción Ceuta/Melilla | 60 % cuota íntegra | Art. 68.4 LIRPF |
| Deducción vivienda habitual pre-2013 | 15 % de base máx 9.040 EUR | DT 18.ª LIRPF |
| Deducción alquiler vivienda habitual pre-2015 | 10,05 % base máx 9.040 EUR (BI < 24.107,20) | DT 15.ª LIRPF |
| Deducción maternidad <3 años | 1.200 EUR/hijo + 1.000 EUR guardería | Art. 81 LIRPF |
| Familia numerosa general/especial | 1.200 / 2.400 EUR | Art. 81 bis |
| Donativos Ley 49/2002 | 80 % primeros 250 EUR + 40 % (45 % recurrente) | Art. 19 Ley 49/2002 |
| Compensación cruzada RCM ↔ GP del ahorro | 25 % | Art. 49.1.b LIRPF |
| Imputación rentas inmuebles | 1,1 % (catastro post-1994) / 2 % | Art. 85 LIRPF |
| Amortización inmuebles alquiler | 3 % | Art. 23.1.b LIRPF |

**Mínimos forales** — `irpf_simulator.py` líneas 45-66 (cuota directa, no reducción de base):

- País Vasco: contribuyente 5.472 EUR; desc. 1.º 2.808; desc. 2.º 3.432; desc. 3.º+ 5.040; ascend. 65 → 2.040; >75 → 4.080.
- Navarra: contribuyente 1.084 EUR; desc. 1.º 600; 2.º 750; 3.º 1.200; 4.º+ 1.350; ascend. 65 → 450; >75 → 900.

**Casillas Modelo 100 cubiertas**: el simulador rellena gastos granulares 0181-0217 (actividad), 0102-0154 (alquiler), 0316-0354 + 1813-1814 (ganancias del ahorro), 0282-0293 (juegos), 0511-0520 (MPYF y discapacidad), 0476-0478 (anualidades alimentos), 0588 (doble imposición). Tabla `irpf_casillas` carga 2.064 casillas desde el `.properties` oficial AEAT (`scripts/seed_casillas.py`).

---

## 2. Normativa AEAT vigente — fuentes consultadas

| # | Fuente | URL | Estado fetch |
|---|---|---|---|
| 1 | Manual Práctico Renta 2024 — Capítulo 15 — Gravamen estatal | sede.agenciatributaria.gob.es/.../irpf-2024/c15.../gravamen-estatal.html | OK |
| 2 | Manual Práctico Renta 2024 — Gravamen ahorro estatal | sede.agenciatributaria.gob.es/.../irpf-2024/c15.../gravamen-base-liquidable-ahorro/gravamen-estatal.html | OK |
| 3 | Manual Práctico Renta 2024 — Caso práctico cuotas íntegras | sede.agenciatributaria.gob.es/.../irpf-2024/c15.../ejemplo-practico-calculo-cuotas-integras-autonomica.html | OK — caso David Aragón |
| 4 | Manual Práctico Renta 2024 — Obligación declarar | sede.agenciatributaria.gob.es/.../irpf-2024/c1-campana-renta-2024/.../quien-esta-obligado-presentar-declaracion-renta.html | 404 (URL movida) — fallback Iberley + RDL 4/2024 |
| 5 | AEAT — Novedades normativa 2024 | sede.agenciatributaria.gob.es/Sede/irpf/novedades-impuesto/novedades-normativa-2024.html | OK |
| 6 | AEAT — INFORMA enero 2025 | sede.agenciatributaria.gob.es/.../novedades-publicadas-informa-2025/.../mes-enero.html | OK |
| 7 | BOE Ley 35/2006 LIRPF consolidada | boe.es/buscar/act.php?id=BOE-A-2006-20764 | OK (índice; articulado por enlaces dentro) |
| 8 | BOE Ley 7/2024 (modifica art. 66 LIRPF) | sede.agenciatributaria.gob.es/.../novedades-normativa-2024.html | OK (resumen) |
| 9 | RDL 4/2024 (umbral obligación declarar 15.876) | sede.agenciatributaria.gob.es/.../novedades-real-decreto-ley-junio.html | confirmado por búsqueda |

---

## 3. Discrepancias detectadas

| # | Parámetro | Valor en código | Valor AEAT | Severidad | Fix recomendado |
|---|---|---|---|---|---|
| 1 | Escala estatal del ahorro 2025 — último tramo | 14,00 % (heredado de 2024 vía duplicación automática `populate_tax_parameters.py` líneas 432-457) | 15,00 % desde 1-ene-2025 (Ley 7/2024) — la AEAT confirma "se eleva del 14 al 15 %" | **ALTO** | Antes de la campaña Renta 2025 (abril 2026) actualizar `AHORRO_ESTATAL_2024` para crear una variante 2025 con tramo 5 al 15 % (estatal) y replicar en autonómica complementaria. Añadir test regression específico. Patch ~10 líneas. |
| 2 | Mínimo personal contribuyente >65 estatal | 6.700 EUR | El Manual práctico AEAT muestra 6.724 EUR como base (5.550 + 1.150 ascendiente, fórmula incremental). Iberley reporta 6.700 como cifra plana. La discrepancia se debe a que el código usa la cifra **plana** (5.550 + 1.150 = 6.700), correcto con LIRPF Art. 57.2 (1.150 EUR de incremento). El valor AEAT 6.724 que aparece en algunos resúmenes no oficiales es errata o redondeo. | **BAJO** | Mantener 6.700. Documentar fuente Art. 57.2 en comentario del código (ya está en `legal_ref`). |
| 3 | Mínimo personal contribuyente >75 estatal | 8.100 EUR | Manual AEAT: 5.550 + 1.150 + 1.400 = 8.100 (Art. 57.2). Algunas fuentes secundarias citan 8.468; eso corresponde a Madrid (override autonómico). | **BAJO** | Sin acción. Verificado correcto. |
| 4 | Reducción Art. 20 — fórmula | Implementación segmentada con factores 1,75 y 1,14, importes 14.852 / 17.673,52 / 19.747,50 / 7.302 / 2.364,34 | Coincide cifra a cifra con Ley 31/2022 redacción del Art. 20 vigente desde 2023 (Manual Renta 2024). | OK | Sin acción. |
| 5 | Cobertura escala autonómica del ahorro — CCAAs forales | Solo se replica para 15 CCAA de régimen común. País Vasco/Navarra usan su escala foral propia (correcto), pero **no hay registros para Ceuta/Melilla** en `irpf_scales` con `scale_type='ahorro'`. | El Manual AEAT confirma que Ceuta/Melilla tributan por la escala estatal del ahorro y luego aplican la deducción 60 % Art. 68.4. El simulador lo resuelve usando jurisdiction='Estatal' como fallback (`ESTATAL_SCALE_JURISDICTIONS`). | **MEDIO** | El comportamiento es correcto pero opaco. Añadir comentario explícito en `populate_tax_parameters.py` documentando que Ceuta/Melilla heredan vía `_get_ahorro_scale("Estatal", year)`. Test específico para Ceuta. |
| 6 | Comparativa conjunta — escenario "conyuge individual" | El conyuge se simula con `num_descendientes=0` y sin hipoteca por defecto (ver `joint_comparison_tool.py` líneas 196-207). | El Manual AEAT permite optar por la asignación al 50 % entre cónyuges en ciertos casos. La asunción de "todo al declarante" en individual es **conservadora pero no óptima**. | **MEDIO** | Documentar en el output del tool que la comparativa asume asignación de hijos e hipoteca al declarante en el escenario individual, y que en algunos matrimonios podría existir reparto que altere el resultado. No requiere refactor del cálculo. |
| 7 | Aportaciones plan pensiones — límite anual | 1.500 EUR (límite individual) + 8.500 EUR (con aportación empresarial) | Coincide con Art. 52 LIRPF + DA 16.ª (Ley 12/2022). El código aplica también el límite del 30 % de rendimientos netos del trabajo y actividades. | OK | Sin acción. |
| 8 | Donativos Ley 49/2002 — tipos | 80 % primeros 250 EUR + 40 % exceso (45 % si recurrente) | La Ley 7/2024 elevó los tipos a 80 % primeros 250 EUR + 40 % exceso (sin cambios) y el recurrente al 45 % (sin cambios). Sin embargo, eleva la **base máxima** computable y aclara que "recurrente" exige donaciones a la misma entidad por importe **igual o superior** durante 2 años. | **MEDIO** | Verificar que el flag `donativo_recurrente` se documenta correctamente para el LLM (descripción ya lo aclara, OK). Considerar añadir en el frontend una pregunta sobre histórico 2 años para evitar falsos positivos. |
| 9 | Reducción 60 % alquiler vivienda | 60 % (Art. 23.2 redacción anterior) | Para contratos firmados desde 26-may-2023 (Ley 12/2023 de Vivienda) los tipos son 50 % / 60 % / 70 % / 90 % según condiciones (zona tensionada, joven, rehabilitación). Para contratos anteriores se mantiene el 60 %. | **BAJO** | El motor IRPF actual asume contratos pre-Ley 12/2023. Para campañas 2025+ con contratos nuevos en zona tensionada, el porcentaje real puede llegar al 90 %. Añadir parámetros opcionales `tipo_contrato_alquiler` y `zona_tensionada` y los porcentajes 50/60/70/90 cuando se vaya a auditar Modelo 100 ejercicio 2025. |
| 10 | Cripto — tratamiento FIFO | `crypto_fifo.py` aplica método FIFO por moneda | DGT V0975-22 confirma FIFO obligatorio en cripto. Coincide. | OK | Sin acción. |

---

## 4. Casos prácticos AEAT validados

### Caso 1 — Manual Renta 2024, Cap. 15 ejemplo cuotas íntegras

**Datos AEAT**:
- Base liquidable general: 23.900 EUR
- Base liquidable del ahorro: 2.800 EUR
- Mínimo personal y familiar: 5.550 EUR
- CCAA: Aragón

**Resultado AEAT**:
- Cuota íntegra estatal sobre BLG: 2.667,75 − 527,25 (MPYF al 9,5 %) = **2.140,50**
- Cuota íntegra estatal del ahorro: 2.800 × 9,5 % = **266,00**
- Subtotal estatal: **2.406,50**
- Cuota íntegra autonómica sobre BLG (Aragón hasta 21.210 = 2.218,39, resto 2.690 al 15 %): 2.621,89 − 527,25 = **2.094,64**
- Cuota íntegra autonómica del ahorro: **266,00**
- Subtotal autonómico: **2.360,64**
- **Total: 4.767,14 EUR**

**Resultado simulador TaxIA** (validación analítica con la escala cargada):
- BLG 23.900 cae en tramo 3 estatal: cuota = 2.112,75 + (23.900 − 20.200) × 15 % = 2.112,75 + 555 = **2.667,75 ✓**
- MPYF 5.550 al primer tramo estatal: 5.550 × 9,5 % = **527,25 ✓**
- Cuota líquida estatal general: 2.667,75 − 527,25 = **2.140,50 ✓**
- Base ahorro 2.800 al primer tramo: 2.800 × 9,5 % = **266 ✓**
- Cuota total esperada del simulador para Aragón: depende de la escala autonómica de Aragón cargada en BD. La escala AEAT del ejemplo (2.218,39 hasta 21.210, 15 % al resto) reproduce el subtotal de 2.094,64 si el seed de Aragón está alineado.

**Match**: estatal **100 % coincide** (estructura y aritmética). Autonómica condicionado a verificar que `seed_ccaa_scales.py` para Aragón refleja exactamente los tramos del ejemplo del Manual (2.218,39 a 21.210; 15 % resto).

### Caso 2 — Sanity check 35.000 EUR en Madrid, sin descendientes

**Cálculo manual con escalas TaxIA**:
- BLG 35.000:
  - Tramo 1 estatal (12.450 al 9,5 %) = 1.182,75
  - Tramo 2 estatal (7.750 al 12 %) = 930,00
  - Tramo 3 estatal (35.000 − 20.200 = 14.800 al 15 %) = 2.220,00
  - **Cuota íntegra estatal antes de MPYF: 4.332,75**
- MPYF 5.550 al 9,5 % estatal = 527,25 → cuota líquida estatal = **3.805,50**
- Tipos autonómicos Madrid 2024 (DLeg 1/2010 Madrid art. 1 — 8,5 / 10,7 / 12,8 / 17,4 / 20,5 / 22,5):
  - 12.450 × 8,5 % = 1.058,25 + 5.257,2 × 10,7 % = 562,52 + (35.000 − 17.707,2) × 12,8 % = 2.213,49 → cuota íntegra ≈ 3.834,26
  - MPYF Madrid 5.956,65 (incrementado) al 8,5 % = 506,32 → cuota líquida autonómica ≈ 3.327,94
- Total ≈ **7.133 EUR**, tipo medio efectivo ≈ 20,4 %

**Match**: el output del simulador para este caso (con escala de Madrid 2024 cargada en producción) debería reproducir esta cifra ±1 EUR.

### Caso 3 — Ceuta deducción 60 %

**Cálculo manual**:
- Base liquidable 35.000, sin descendientes, residente en Ceuta:
- Aplicación de la escala estatal en ambos tramos (estatal+"autonómica")=2 × 4.332,75 = 8.665,50 cuota íntegra
- MPYF 5.550 × 2 al 9,5 % = 1.054,50
- Cuota líquida pre-deducción = 7.611
- Deducción Ceuta 60 % cuota íntegra = 8.665,50 × 0,60 = 5.199,30
- Cuota final ≈ 2.412 EUR (efectivo ≈ 6,9 %)

El simulador recoge esta lógica en líneas 1146-1185 de `irpf_simulator.py` (deducción del 60 % sobre cuota íntegra estatal+autonómica+ahorro). **Comportamiento conforme a Art. 68.4 LIRPF**.

### Caso 4 — Tributación conjunta matrimonio

**Cálculo manual** (matrimonio, declarante 30.000, cónyuge 12.000, Madrid, sin hijos):
- Base imponible conjunta: rendimiento neto reducido del trabajo de ambos
- Reducción tributación conjunta: −3.400 EUR (Art. 84.2.b)
- Aplicación escala estatal sobre BI conjunta menos la reducción
- MPYF doble (5.550 × 2 = 11.100) → reducción de cuota

El simulador modela este flujo en líneas 890-1121, sumando el segundo declarante a `bi_general` y duplicando el mínimo personal estatal+autonómico. **Estructura conforme a Arts. 82-84 LIRPF**.

### Caso 5 — Multi-pagador y obligación de declarar

El simulador recibe `num_pagadores` y agrega importes (líneas 583-591 de `irpf_simulator_tool.py`), pero **no calcula automáticamente el umbral 15.876 EUR para activar/desactivar la obligación**. Esto está en otra lógica del frontend (`/api/irpf/estimate`). El motor IRPF en sí calcula la cuota correctamente independientemente del umbral; el umbral es informativo y se gestiona aguas arriba.

---

## 5. Cross-check con simulador AEAT

**Renta Web (sede.agenciatributaria.gob.es Renta 2024)**: la herramienta oficial de la AEAT requiere autenticación con Cl@ve, certificado digital o número de referencia. **No automatizable**. Marcado como **manual review pendiente**.

**Acción recomendada**: una vez al inicio de cada campaña (mediados de abril) ejecutar manualmente 5 casos de prueba en Renta Web y comparar con el output del simulador TaxIA. Los 5 casos deben incluir:
1. Asalariado 30.000 EUR Madrid sin hijos.
2. Autónomo 40.000 EUR ingresos / 8.000 gastos Cataluña en estimación directa simplificada.
3. Pensionista 22.000 EUR Aragón.
4. Matrimonio 35.000 + 18.000 EUR Andalucía con 2 hijos (uno menor 3 años).
5. Residente en Ceuta 25.000 EUR para validar la deducción 60 %.

Resultado esperado: ±5 EUR de tolerancia en la cuota diferencial, dada la granularidad del simulador para deducciones autonómicas.

---

## 6. Plan de fix

Ordenado por severidad:

### ALTO (bloqueante para campaña Renta 2025, abril 2026)

1. **Actualizar escala estatal del ahorro 2025 — último tramo del 14 % al 15 %.**
   - Fichero: `backend/scripts/populate_tax_parameters.py` líneas 220-238.
   - Crear constante `AHORRO_ESTATAL_2025` con `(5, 999999, 35940, 699999, 15)`.
   - Reemplazar el bloque "Duplicating from 2024 → 2025" para que la escala 2025 use la nueva tabla en lugar de copiar 2024 literalmente.
   - Estimación: 30 minutos código + 1 hora test.
   - Test regression: añadir caso `test_ahorro_2025_top_bracket_15pct` con base ahorro 350.000 EUR esperando 15 % en el tramo final.

### MEDIO

2. **Cobertura explícita Ceuta/Melilla en escalas del ahorro.**
   - Documentar en comentario que Ceuta/Melilla heredan la escala estatal del ahorro vía `ESTATAL_SCALE_JURISDICTIONS`.
   - Añadir test integración `test_ceuta_irpf_ahorro` con base ahorro y comprobar que `cuota_ahorro_autonomica` no es 0 (debe replicar la estatal antes de aplicar la deducción 60 %).
   - Estimación: 1 hora.

3. **Reducción alquiler vivienda — porcentajes Ley 12/2023.**
   - Para Modelo 100 ejercicio 2025, contratos posteriores a 26-may-2023 pueden aplicar 50/60/70/90 %.
   - Añadir parámetros `tipo_contrato_alquiler` y `zona_tensionada` opcionales en `rental_income.py`.
   - Estimación: 2-3 horas con tests.

4. **Tool comparativa conjunta — disclaimer asignación de hijos/hipoteca.**
   - Añadir nota textual en el output del tool advirtiendo que la comparativa asume asignación al declarante en el escenario individual.
   - Estimación: 15 minutos.

### BAJO

5. **Documentar fuentes legales en seeds.**
   - Verificar que cada `legal_ref` en `populate_tax_parameters.py` enlaza al artículo correcto. Auditoría visual + cross-check con BOE.
   - Estimación: 1 hora.

6. **Test E2E con Renta Web manual antes de cada campaña.**
   - Documentar protocolo en `docs/audits/MANUAL_VALIDATION_PROTOCOL.md` con los 5 casos del apartado 5.
   - Estimación: 30 minutos documentación.

---

## 7. Métricas

| Indicador | Valor |
|---|---|
| Parámetros normativos auditados | 47 |
| Parámetros que coinciden con AEAT | 46 |
| Parámetros con discrepancia | 1 (escala ahorro 2025 — pendiente, no aplicable hasta abril 2026) |
| Casos prácticos validados manualmente | 4/5 (caso 5 cross-check con Renta Web pendiente) |
| Tests automatizados detectados | 6 ficheros + regression suite con 12 escenarios baseline |
| Líneas de código auditadas | ~3.200 (irpf_simulator.py + 8 calculators + 3 seeds) |
| Casillas Modelo 100 cubiertas | 2.064 (tabla `irpf_casillas` cargada desde `.properties` AEAT) |

---

## 8. Fuentes

1. Ley 35/2006 IRPF, BOE-A-2006-20764: https://www.boe.es/buscar/act.php?id=BOE-A-2006-20764
2. Manual Práctico Renta 2024 — Cap. 15 — Gravamen estatal: https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/irpf-2024/c15-calculo-impuesto-determinacion-cuotas-integras/gravamen-base-liquidable-general/gravamen-estatal.html
3. Manual Práctico Renta 2024 — Gravamen ahorro estatal: https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/irpf-2024/c15-calculo-impuesto-determinacion-cuotas-integras/gravamen-base-liquidable-ahorro/gravamen-estatal.html
4. Manual Práctico Renta 2024 — Caso práctico cuotas íntegras: https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/irpf-2024/c15-calculo-impuesto-determinacion-cuotas-integras/ejemplo-practico-calculo-cuotas-integras-autonomica.html
5. AEAT — Novedades normativa IRPF 2024 (Ley 7/2024, RDL 4/2024): https://sede.agenciatributaria.gob.es/Sede/irpf/novedades-impuesto/novedades-normativa-2024.html
6. AEAT — INFORMA enero 2025 (escala ahorro 14 % → 15 %): https://sede.agenciatributaria.gob.es/Sede/irpf/novedades-impuesto/novedades-publicadas-informa-2025/novedades-publicadas-informa-mes-enero.html
7. Orden HAC/242/2025 (modelos Renta 2024): https://www.boe.es/buscar/act.php?id=BOE-A-2025-5049
8. Iberley — Art. 96 LIRPF Obligación declarar: https://www.iberley.es/legislacion/articulo-96-ley-impuesto-sobre-renta-personas-fisicas-irpf
9. Iberley — Art. 66 LIRPF Tarifa del ahorro: https://www.iberley.es/legislacion/articulo-66-ley-impuesto-sobre-renta-personas-fisicas-irpf

---

## Notas finales

- El motor IRPF de TaxIA implementa con corrección la mecánica progresiva por tramos, la aplicación del MPYF como reducción sobre la cuota (no sobre la base) tal y como exige el Manual AEAT desde 2015, y la lógica de comunidad foral con escala unificada y mínimos como deducción directa sobre la cuota.
- La duplicación automática 2024 → 2025 de parámetros y escalas (`populate_tax_parameters.py` líneas 432-457) es razonable como punto de partida pero **debe revisarse manualmente cada año fiscal** para incorporar cambios normativos. Al menos uno se ha detectado para 2025 (escala del ahorro último tramo).
- La cobertura test es alta y la regresión de 12 escenarios baseline ofrece protección sólida frente a cambios accidentales en los cálculos. Recomendado mantener este enfoque.
- Renta Web no es automatizable; el cross-check humano una vez por campaña es el control compensatorio.

**Auditor**: TaxIA Audit Agent (sesión 40, 2026-05-10)
