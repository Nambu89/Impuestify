# Auditorías de Validación — Modelos Tributarios TaxIA

Reports de validación de los modelos tributarios calculados por TaxIA contra normativa AEAT vigente, manuales prácticos oficiales y consultas vinculantes DGT.

## Sesión 40 — Mayo 2026

**Master report**: [MASTER_VALIDATION_2026-05.md](MASTER_VALIDATION_2026-05.md) — leer primero.

| Modelo | Report | Estado | Críticos | Altos |
|--------|--------|--------|----------|-------|
| 100 IRPF | [modelo_100_validation_2026-05.md](modelo_100_validation_2026-05.md) | 🟢 VERDE | 0 | 1 |
| 130 | [modelo_130_validation_2026-05.md](modelo_130_validation_2026-05.md) | 🟡 AMARILLO | 2 | 5 |
| 131 | [modelo_131_validation_2026-05.md](modelo_131_validation_2026-05.md) | 🔴 ROJO | 1 (gap funcional) | — |
| 200 IS | [modelo_200_validation_2026-05.md](modelo_200_validation_2026-05.md) | 🟠 NARANJA | 0 | 6 |
| 303 IVA | [modelo_303_validation_2026-05.md](modelo_303_validation_2026-05.md) | 🔴 ROJO | 3 | — |
| 308 | [modelo_308_validation_2026-05.md](modelo_308_validation_2026-05.md) | 🔴 ROJO | 1 (308≠309) | — |
| 349 | [modelo_349_validation_2026-05.md](modelo_349_validation_2026-05.md) | 🔴 ROJO | 1 (gap funcional) | — |
| 390 | [modelo_390_validation_2026-05.md](modelo_390_validation_2026-05.md) | 🔴 ROJO | 1 (gap funcional) | — |
| 420 IGIC | [modelo_420_validation_2026-05.md](modelo_420_validation_2026-05.md) | 🔴 ROJO | 6 | 2 |
| 720 | [modelo_720_validation_2026-05.md](modelo_720_validation_2026-05.md) | 🟡 AMARILLO | 0 | 3 |
| 721 | [modelo_721_validation_2026-05.md](modelo_721_validation_2026-05.md) | 🟡 AMARILLO | 0 | 2 |
| IPSI | [modelo_ipsi_validation_2026-05.md](modelo_ipsi_validation_2026-05.md) | 🟡 AMARILLO | 3 | — |

**Distribución**: 🟢 1 · 🟡 4 · 🟠 1 · 🔴 6 · Total gaps: 71 (18 críticos, 19 altos, 26 medios, 8 bajos).

## Metodología

Ver `plans/2026-05-10-modelos-validation-aeat.md` — 6 fases por modelo.

## Limitaciones conocidas

- Renta Web (simulador IRPF) requiere autenticación Cl@ve/DNIe → no automatizable. Validación manual del Modelo 100 pendiente como tarea separada.
- 8/12 modelos no tienen simulador AEAT público → validación contra normativa + manuales + casos DGT.
- Calculadora retenciones IRPF AEAT es la única herramienta pública sin login → único cross-check con simulador en vivo.

## Disclaimer

Estas auditorías documentan el grado de alineación de los algoritmos de TaxIA con la normativa fiscal española vigente en mayo 2026. No constituyen certificación oficial de la AEAT. La presentación oficial de cualquier modelo sigue siendo responsabilidad del contribuyente vía Sede Electrónica AEAT.
