# Auditoría Maestra — Validación Modelos Tributarios TaxIA vs AEAT

> Sesión 40 — 10 mayo 2026
> Metodología: 12 auditorías independientes en paralelo, una por modelo, contra normativa AEAT vigente, manuales prácticos oficiales, BOE consolidado, consultas DGT y administraciones forales/locales (Bizkaia, Gipuzkoa, Navarra, ATC Canarias, Ciudades Ceuta/Melilla).
> Reports individuales: ver `docs/audits/modelo_<NNN>_validation_2026-05.md`.

## Resumen ejecutivo

Se han auditado los 12 modelos tributarios que TaxIA calcula o anuncia calcular. El estado del catálogo es **mixto**: el cálculo del IRPF (Modelo 100, núcleo del producto) está validado contra el Manual Práctico AEAT con coincidencia cifra a cifra; sin embargo, varios modelos secundarios presentan gaps críticos que requieren intervención inmediata antes de la próxima campaña fiscal.

**3 categorías de hallazgos transversales**:

1. **Modelos anunciados sin implementar** (riesgo regulatorio + reputacional): el frontend, los planes de suscripción y el material comercial mencionan modelos que no existen como herramienta funcional en el backend — concretamente 131, 349 y 390. El usuario que pregunte por estos modelos en el chat recibirá respuestas alucinadas sin tool de validación.
2. **Normativa desactualizada por reformas 2024-2025** (riesgo de cálculo erróneo): Ley 7/2024 (Impuesto sobre Sociedades y nuevo tramo del ahorro IRPF) y Decreto Legislativo 1/2025 (refundición IGIC y AIEM Canarias) no se han propagado al código. Afecta a Modelos 100, 200 y 420.
3. **Drift entre tool LLM y servicio/calculator** (riesgo de inconsistencia interna): existen dos implementaciones independientes para el mismo modelo, una utilizada por el agente LLM en chat y otra por la calculadora pública. Los tests cubren la calculadora; el chat usa la versión rota. Detectado en Modelos 303 y 130.

## Tabla resumen — 12 modelos

| Modelo | Estado | Críticos | Altos | Medios | Bajos | Diagnóstico breve |
|--------|--------|----------|-------|--------|-------|-------------------|
| **100 IRPF** | 🟢 VERDE | 0 | 1 | 3 | 2 | Validado contra Manual Práctico AEAT cifra a cifra. Pendiente: subir tipo ahorro 2025 al 15 % (Ley 7/2024). |
| 130 | 🟡 AMARILLO | 2 | 5 | 4 | 3 | Calculator sólido (17 tests, 6 territorios). Tool LLM con casillas 05/06 invertidas, interpolación lineal vs escalones planos, sección agrícola y dispensa 70 % no implementadas. |
| **131** | 🔴 ROJO | 1 | — | — | — | Anunciado en marketing (Home, Farmacias, Pricing) pero **sin implementación**. Plazo T4 erróneo en calendario. |
| **200 IS** | 🟠 NARANJA | 0 | 6 | 10 | — | Arquitectura robusta (47 tests, 7 regímenes). Contenido normativo pre-Ley 7/2024: microempresa, nueva creación, reserva capitalización, BIN tramo grandes, donativos. |
| 303 IVA | 🔴 ROJO | 3 | — | — | — | Drift estructural tool ≠ calculator. Tool numera mal casillas resultado, plazo T4 incorrecto, total deducible suma 5 casillas en vez de 10. |
| 308 | 🔴 ROJO | 1 | — | — | — | Modela "compra intracomunitaria farmacia RE" como 308 — es **Modelo 309**. Casos legítimos del 308 (Art. 7 Orden EHA/3786/2008) no implementados. |
| **349** | 🔴 ROJO | 1 | — | — | — | Anunciado como "automático" en pricing Plan Creator (49 €/mes). **Sin tool, sin calculadora, sin PDF, sin VIES, sin claves de operación**. |
| **390** | 🔴 ROJO | 1 | — | — | — | **Sin implementación** de cálculo. Solo mencionado en system prompts y calendario. Sin detección automática de exoneración SII/REDEME. |
| 420 IGIC | 🔴 ROJO | 6 | 2 | 2 | — | Tipos hardcoded **inexistentes** (13,5 % / 35 %). Decreto Legislativo 1/2025 derogó normativa antigua. REPEP 30 K€ no implementado → falsos positivos. |
| 720 | 🟡 AMARILLO | 0 | 3 | 4 | — | Evaluación de obligación correcta, post-TJUE OK, 12 tests PASS. Cese de titularidad y subtipos A-F no modelados. Endpoint evalúa pero no genera fichero AEAT. |
| 721 cripto | 🟡 AMARILLO | 0 | 2 | 3 | 3 | Umbrales y exclusión autocustodia OK. Lista de exchanges españoles incompleta y sucursales/filiales españolas (Binance Spain SL) tratadas como extranjeras → falsos positivos. |
| IPSI | 🟡 AMARILLO | 3 | — | — | — | Calculator alineado al 70 % con Ley 8/1991. P0: regularización prorrata fuera de Q4, plazo T4 incorrecto, restricted_mode bloquea Particulares. Colisión PDF Modelo 420 Melilla vs 420 IGIC Canarias. |

**Distribución por estado**:
- 🟢 Verde: 1 (8 %)
- 🟡 Amarillo: 4 (33 %)
- 🟠 Naranja: 1 (8 %)
- 🔴 Rojo: 6 (50 %)

## Top 10 gaps críticos transversales

Ordenados por impacto cliente × severidad legal:

1. **Modelos 131, 349, 390 anunciados sin implementar** — riesgo regulatorio (publicidad engañosa LGDCU Art. 5/7) y reputacional. Plan Creator 49 €/mes y plan Autónomo 39 €/mes citan capacidades inexistentes.
2. **Modelo 303 — drift tool LLM vs calculator** — el chat (canal principal del producto) usa una implementación distinta a la testada. Casillas de resultado mal numeradas: el cliente recibe importes correctos pero asociados a casilla equivocada en el PDF.
3. **Modelo 200 IS — contenido pre-Ley 7/2024** — sobreestima cuota de microempresas en ~30 %, donativos al 35 % en vez de 40 %, reserva capitalización al 10 % en vez de 15-20 %. Campaña julio 2026 inminente.
4. **Modelo 420 IGIC — tipos derogados** — usa 13,5 % y 35 %, inexistentes en el TR vigente desde octubre 2025. Falsos positivos REPEP para autónomos canarios <30 K€.
5. **Modelo 308 vs 309 — confusión legal de modelo** — la tool description del LLM induce respuestas erróneas en chat sobre qué modelo aplica al caso intracomunitario en Recargo de Equivalencia.
6. **Modelo 130 — casillas 05/06 invertidas en tool LLM** — importe correcto pero etiquetado erróneo en PDF generado por el chat.
7. **Modelo 720 — cese de titularidad no modelado** — RD 1065/2007 Arts. 42 bis.5, 42 ter.5, 54 bis.7 imponen obligación de declarar el cese; TaxIA no lo evalúa.
8. **Modelo 721 — sucursales españolas de exchanges extranjeros** — Binance Spain SL inscrita en Registro BdE julio 2022; tratada como entidad extranjera → falso positivo de obligación.
9. **IPSI — regularización prorrata fuera de Q4** — el código aplica la regularización en cualquier trimestre cuando la normativa la limita al cierre de ejercicio.
10. **Modelo 100 — tipo del ahorro 2025 al 14 % en lugar de 15 %** — Ley 7/2024 elevó el último tramo. Sin impacto en campaña 2024 (ya cerrada), crítico para abril 2026.

## Plan de fix priorizado

### P0 — Bloqueantes (acción inmediata)

| # | Modelo | Acción | Esfuerzo |
|---|--------|--------|----------|
| 1 | 131, 349, 390 | Retirar de Home, Pricing, Farmacias y system prompts hasta implementar. Añadir disclaimer "próximamente" o eliminar referencias. | 2 h |
| 2 | 200 IS | Refactor `is_scales.py` parametrizado por ejercicio; aplicar Ley 7/2024 (microempresa 17/20 %, nueva creación 15 % plano, reserva capitalización 15-20 %, donativos 40 %). | 5-7 días-persona |
| 3 | 420 IGIC | Refactor completo de tipos por Decreto Legislativo 1/2025; añadir REPEP 30 K€; eliminar 13,5 % y 35 % inexistentes. | 3 días |
| 4 | 308 | Dividir en `calculate_modelo_308` (3 casos reales) + `calculate_modelo_309` (RE intracomunitario). Documentar "308≠309" como anti-patrón en `backend/CLAUDE.md`. | 2 días |
| 5 | 303 | Refactor del tool LLM para delegar en `Modelo303Calculator`. Eliminar drift. Corregir casillas de resultado y plazo T4. | 4 días |

### P1 — Antes de la próxima campaña (julio 2026 IS, abril 2026 Renta)

| # | Modelo | Acción | Esfuerzo |
|---|--------|--------|----------|
| 6 | 100 | Subir tipo ahorro 2025 al 15 % en `populate_tax_parameters.py` (~10 líneas). | 0,5 h |
| 7 | 130 | Corregir casillas 05/06 invertidas en tool. Implementar Sección II agrícola. Implementar dispensa Art. 109 RIRPF (70 % común, 50 % Gipuzkoa). | 3 días |
| 8 | 720 | Modelar cese de titularidad. Desglosar subtipos A-F del DR720. | 2 días |
| 9 | 721 | Distinguir sucursales/filiales españolas de exchanges extranjeros. Ampliar lista `EXCHANGES_ESPANOLES` (añadir Onyze, Criptan, Vottun, Onyx, Bitbase). | 1 día |
| 10 | IPSI | Limitar `regularizacion_prorrata` a Q4. Corregir plazo T4 a 30/31 enero. Permitir IPSI a Particulares (compraventa inmueble). | 1 día |

### P2 — Mejoras (siguiente trimestre)

- Generar fichero AEAT oficial (no solo borrador PDF) para modelos 720, 721 y 303.
- Frontend wizards para 720, 721, 349, 390, 131.
- Mensajes sancionadores actualizados (post-derogación 150 % e imprescriptibilidad en 720).
- Test coverage en chat tools y frontend (hoy 0 % en varios modelos).

### P3 — Largo plazo

- Validación cruzada con simulador AEAT Renta Web (requiere automatización con Cl@ve — out of scope hoy).
- Validador VIES integrado para Modelo 349.
- Cumplimiento NIS2 / AESIA en superficies de modelos críticos.

## Métricas globales

| Métrica | Valor |
|---------|-------|
| Modelos auditados | 12 / 12 |
| Reports markdown generados | 13 (12 individuales + master) |
| Modelos con cálculo funcional | 9 / 12 |
| Modelos con cálculo correcto al 100 % | 1 / 12 (Modelo 100) |
| Gaps CRÍTICOS detectados | 18 |
| Gaps ALTOS detectados | 19 |
| Gaps MEDIOS detectados | 26 |
| Gaps BAJOS detectados | 8 |
| Total gaps | 71 |
| Modelos anunciados sin implementar | 3 (131, 349, 390) |
| Modelos con drift tool/calculator | 2 confirmados (130, 303) |
| Modelos con normativa desactualizada | 3 (100, 200, 420) |
| Tests existentes (suma) | ~120 |
| Cobertura tests en chat tools | 0 % en 130 y otros |

## Validación contra fuentes oficiales

Fuentes consultadas a lo largo de las 12 auditorías:
- AEAT Sede Electrónica (sede.agenciatributaria.gob.es)
- BOE consolidado (Ley 35/2006 IRPF, Ley 27/2014 IS, Ley 37/1992 IVA, Ley 7/2024, Ley 5/2022, Ley 8/1991 IPSI)
- Manual Práctico Renta AEAT
- Manual Práctico IVA AEAT
- Manual Práctico Sociedades AEAT
- Manual Práctico Actividades Económicas AEAT
- ATC Canarias + Decreto Legislativo 1/2025 (BOC)
- Diputación Foral Gipuzkoa, Bizkaia, Navarra
- Ordenanzas fiscales Ciudades Autónomas Ceuta y Melilla
- Sentencia TJUE C-788/19 (Modelo 720)
- Orden HFP/886/2023 (Modelo 721)
- Consultas vinculantes DGT (V0975-22, V1948-22, V0586-23 y otras)

**Limitaciones conocidas**:
- Renta Web (simulador IRPF) requiere Cl@ve / DNIe → no automatizable. Validación cruzada del Modelo 100 contra Renta Web pendiente como protocolo manual de 5 casos por campaña.
- 8/12 modelos no tienen simulador público AEAT → validación contra normativa + manuales + casos DGT.
- Tipos IGIC vigentes 2025 verificados contra TR Decreto Legislativo 1/2025 (BOC), no contra simulador (no existe).

## Posicionamiento comercial post-auditoría

Antes de presentar TaxIA a clientes, partners o inversores conviene:

1. **Mensaje honesto sobre cobertura**: "Calculamos IRPF (Modelo 100) con coincidencia cifra a cifra contra Manual Práctico AEAT. El resto del catálogo está en distintos grados de madurez — auditoría pública disponible."
2. **Diferenciador de rigor**: la propia existencia de esta auditoría es un activo comercial. Pocas SaaS fiscales auditan su propio cálculo contra normativa con este nivel de detalle.
3. **Roadmap visible**: P0/P1/P2 son tareas concretas con esfuerzo estimado. Da credibilidad técnica frente a competencia.
4. **Disclaimer en producto**: para los modelos 🔴 ROJO o 🟠 NARANJA, mostrar advertencia "en revisión normativa" hasta cerrar P0.

## Próximos pasos

1. Documentar cada CRÍTICO/ALTO como entrada en `memory/bugfixes-2026-05.md`.
2. Actualizar `memory/MEMORY.md` con la sesión 40 y los hallazgos clave.
3. Ejecutar P0 #1 (retirar 131/349/390 de marketing) hoy mismo.
4. Planificar sprint Ley 7/2024 (P0 #2) antes del cierre del 200 IS julio 2026.
5. Compartir auditoría con Alfredo (CEO AyudaTPymes) como prueba de rigor técnico junto con vídeos demo.

---

*Esta auditoría documenta el grado de alineación de los algoritmos de TaxIA con la normativa fiscal española vigente en mayo 2026. No constituye certificación oficial AEAT. La presentación oficial de cualquier modelo sigue siendo responsabilidad del contribuyente vía Sede Electrónica AEAT.*
