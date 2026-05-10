# Auditoría IPSI — Impuesto sobre la Producción, los Servicios y la Importación (2026-05)

**Tributo**: IPSI (no es competencia AEAT)
**Norma marco**: Ley 8/1991, de 25 de marzo (Arbitrio sobre la Producción y la Importación) + Ley 13/1996, de 30 de diciembre (renombra a IPSI y añade gravámenes complementarios)
**Reglamentación**: Ordenanzas fiscales de cada Ciudad Autónoma, aprobadas por el Pleno y publicadas anualmente en el BOCCE (Ceuta) y BOME (Melilla)
**Modelos**:
- Ceuta: **Modelo 001** (autoliquidación general operaciones interiores) + Modelo 021 y otros para importaciones / gravámenes complementarios — gestionado por el OASTC (Organismo Autónomo Servicios Tributarios de Ceuta).
- Melilla: **Modelo 420** (operaciones interiores) — gestionado por la propia Ciudad Autónoma de Melilla. (No confundir con el Modelo 420 IGIC de Canarias; son dos formularios homónimos en jurisdicciones distintas.)

**Plazos** (idénticos en ambas Ciudades):
- T1 → 1-20 abril
- T2 → 1-20 julio
- T3 → 1-20 octubre
- T4 → 1-31 enero del año siguiente (Melilla 31 días, Ceuta operativamente "20" prorrogable; varios años se ha ampliado al 30/31 enero por instrucción)
- Grandes empresas (>6 M€ volumen): mensual, 1-20 del mes siguiente.

**Estado en TaxIA**: **IMPLEMENTADO PARCIALMENTE — desviación normativa relevante en los tipos por defecto, ausencia de catálogo IAE→tipo y modelo Melilla mal etiquetado.**

---

## Fase 1 · Inventario en TaxIA

| Componente | Existe | Ubicación |
|---|---|---|
| Calculadora dedicada | SÍ | `backend/app/utils/calculators/modelo_ipsi.py` (`ModeloIpsiCalculator`) |
| Tool LLM (`calculate_modelo_ipsi`) | SÍ | `backend/app/tools/modelo_ipsi_tool.py` (registrada en `tools/__init__.py` ALL_TOOLS + TOOL_EXECUTORS) |
| Endpoint REST | SÍ | `POST /api/declarations/ipsi/calculate` (`routers/declarations.py:268`, rate-limit 30/min) |
| Generador PDF | SÍ (parcial) | `routers/export.py` admite `modelo="ipsi"` en el endpoint genérico `/api/export/modelo-pdf`. No hay separación Ceuta/Melilla ni rotulación al modelo oficial 001 / 420. |
| Plugin territorio | SÍ | `backend/app/territories/ceuta_melilla/plugin.py` (CeutaMelillaTerritory) — IPSI_RATES = {Ceuta: 0.03, Melilla: 0.04}. |
| Tests | SÍ | `backend/tests/test_modelo_ipsi.py` — 6 clases, cubre tipos, multi-tipo, importaciones, ISP, compensaciones, Q4, complementarias, structure, metadata, tool wrapper. |
| Wizard / Form frontend | NO | No existe `FormIpsi` en `frontend/src/pages/DeclarationsPage.tsx` (pendiente — el plan T6 nunca se completó en el repo público). |
| Knowledge update RAG | SÍ | `backend/data/knowledge_updates/ipsi_sage_completo.md` (texto Sage, no normativa primaria). |
| Deducción 60% IRPF Ceuta/Melilla (Art. 68.4 LIRPF) | SÍ | Aplicada vía `CeutaMelillaTerritory` (escala estatal + 60% sobre cuota íntegra). No es competencia del cálculo IPSI sino del IRPF. |

**Conclusión inventario**: TaxIA calcula la liquidación trimestral del IPSI (devengado − deducible + ajustes) con estructura sólida tipo Modelo 420 IGIC, pero **los seis tipos están "hard-codeados" como constantes Python sin parametrización por ciudad ni por epígrafe IAE**, y el modelo Melilla está etiquetado como "420" (chocando con IGIC Canarias). Falta UI de captura.

---

## Fase 2 · Normativa de referencia

**Importante**: el IPSI **no se gestiona por la AEAT**. Las fuentes primarias son las propias Ciudades Autónomas y la normativa estatal habilitante.

| Recurso | Fuente | URL | Cobertura en repo |
|---|---|---|---|
| Ley 8/1991, de 25 marzo | BOE | https://www.boe.es/buscar/act.php?id=BOE-A-1991-7645 | Citada en docstring `modelo_ipsi.py`, no descargada |
| Ley 13/1996, de 30 diciembre (renombra IPSI + complementarios tabaco/hidrocarburos) | BOE | https://www.boe.es/buscar/act.php?id=BOE-A-1996-29117 | Citada, no descargada |
| Ordenanza Fiscal IPSI Ceuta (vigente, modificada 2025) | OASTC / BOCCE | https://oac.tributosceuta.org/textos/2/O.F.IPSI.pdf | **No descargada** (WebFetch denegado en sandbox); existe versión 2018 cacheada en `tributosceuta.org/.../O.F.IPSI_corregido_28_de_mayo_2018.pdf` |
| Ordenanza Fiscal IPSI Melilla — operaciones interiores | BOME | https://www.melilla.es/melillaportal/RecursosWeb/DOCUMENTOS/1/2_17220_1.pdf | No descargada |
| Tipos impositivos vigentes Melilla | melilla.es | https://www.melilla.es/.../codbusqueda=231 | Descripción confirmada vía portal oficial |
| Modelo 001 IPSI Ceuta — autoliquidación general | OASTC | https://oac.tributosceuta.org/3webc/fichaAsunto.do?...asunto_ide=1043 | Confirmado plazo trimestral 20 abril/julio/octubre + 30 enero |
| Modelo 420 IPSI Melilla — declaración trimestral | melilla.es | https://www.melilla.es/.../contenido=3061 (Modelo 420) | Confirmado plazo trimestral 20 abril/julio/octubre + 31 enero |
| Art. 68.4 LIRPF — deducción 60% rentas Ceuta/Melilla | sede.agenciatributaria.gob.es Manual Práctico 2024 cap. 16 | https://sede.agenciatributaria.gob.es/.../deduccion-rentas-obtenidas-ceuta-melilla.html | Confirmada, aplicada en plugin territorio |
| RD 1619/2012 (facturación) — equiparación menciones IVA→IPSI | BOE | https://www.boe.es/buscar/act.php?id=BOE-A-2012-14696 | No referenciado en código |

**Estructura tipos según Ley 8/1991 art. 18 y ordenanzas vigentes**:

La Ley 8/1991 fija un rango legal **0,5 % – 10 %**. Las ordenanzas vigentes en ambas Ciudades reparten ese rango en **6 tipos efectivos**: 0,5 %, 1 %, 2 %, 4 %, 8 %, 10 %. **El "tipo general" no es único**: depende del hecho imponible.

**Operaciones interiores (servicios y producción local)**:

| Tipo | Aplicación habitual (ambas Ciudades, salvo matices ordenanza) |
|---|---|
| 0,5 % | Vivienda nueva / VPO, juegos de azar, publicidad y marketing, servicios electrónicos, transporte de pasajeros. Productos de primera necesidad (libros y prensa, alimentos básicos según anexos). |
| 1 % | Taxi, cafeterías y bares de una estrella, restaurantes 1 estrella, consumo de electricidad. |
| 2 % | Cafeterías/bares categoría especial, restaurantes 2+ estrellas, hostelería en general. |
| 4 % | **Tipo general de servicios** y reformas/mejoras de inmuebles, inmuebles en general. |
| 8 % | Telecomunicaciones, radiodifusión, televisión, servicios electrónicos B2C cualificados. |
| 10 % | Ejecución de obra de construcción inmobiliaria. |

**Importaciones (Anexo I de la ordenanza)**:

| Tipo | Aplicación |
|---|---|
| 0,5 % | Libros, prensa, productos primera necesidad. |
| 3 % (Ceuta) / 4 % (Melilla) | Tipo general de bienes importados con régimen estándar. (Ordenanza Ceuta 2018+ rebajada al 3 % para textil/calzado y muchas partidas; Melilla mantiene 4 % salvo excepciones.) |
| 5 % | Determinadas partidas intermedias (Ceuta). |
| 7,5 % – 8 % | Bienes de lujo / específicos. |
| 10 % | Tipo máximo importación, productos suntuarios. |

> **Nota**: La asignación tipo↔partida arancelaria/IAE depende de los Anexos I-II de cada ordenanza y se actualiza anualmente. La normativa marco (Ley 8/1991) **no enumera** los tipos: los fija la Asamblea de cada Ciudad. **Ningún software puede asumir que "4 % = general" para todas las operaciones**: el sujeto pasivo elige el tipo según la partida.

**Gravámenes complementarios** (Ley 13/1996):
- Tabaco labrado.
- Carburantes y combustibles derivados del petróleo.
Tienen su propia base imponible y modelos (021 Ceuta y equivalentes Melilla). **No están implementados en TaxIA**.

---

## Fase 3 · Cross-check normativa ↔ código

### 3.1 Tipos de gravamen

| Aspecto | Norma | TaxIA `modelo_ipsi.py` | Veredicto |
|---|---|---|---|
| Rango legal | 0,5 % – 10 % (Ley 8/1991) | Constantes 0.005, 0.01, 0.02, 0.04, 0.08, 0.10 | OK (cubre los 6 tipos efectivos del rango) |
| Tipos intermedios | Ordenanzas Ceuta admiten **3 %** y **5 %** en importaciones | NO existen como constantes — solo se pueden modelar vía `tipo_importaciones` libre (con clamp 0-1) | **GAP**: el desglose impreso solo muestra los 6 tipos. Una factura de importación al 3 % o 5 % se tendría que vehicular por el campo `base_importaciones` con `tipo_importaciones=0.03/0.05`, perdiendo el desglose por tipo. |
| Tipo general "automático" | Depende del hecho imponible y partida IAE — no hay un único "general" | El plugin `CeutaMelillaTerritory.IPSI_RATES = {Ceuta:0.03, Melilla:0.04}` y la docstring del calculador afirman "tipo general 4 %" / "Ceuta 3 %" | **DESVIACIÓN PARCIAL**: para servicios el general es 4 % en ambas Ciudades. Lo que difiere entre Ceuta y Melilla es el general de **importaciones** (Ceuta ~3 %, Melilla 4 %). El plugin mezcla ambas dimensiones; el comentario en `IPSI_RATES` debería diferenciar "general importaciones" vs "general servicios". |
| Catálogo IAE → tipo | Cada ordenanza publica anexos por epígrafe IAE/CN | NO existe lookup IAE→tipo en código | **GAP**: el LLM y el endpoint asumen que el usuario sabe qué tipo aplica. No hay tabla de referencia ni avisos. |
| Documentación tipos en docstring | Debe distinguir importaciones vs servicios | "Tipos IPSI: 0.5% (minimo), 1% (reducido), 2% (bonificado), 4% (general), 8% (incrementado), 10% (especial)" | **AMBIGUO**: usa terminología propia de IVA (general/reducido/incrementado) no recogida en la ordenanza. Podría inducir al LLM a aplicar 4 % por defecto a importaciones (incorrecto en Ceuta). |

### 3.2 Modelos / formularios

| Aspecto | Norma | TaxIA | Veredicto |
|---|---|---|---|
| Modelo Ceuta | **001** (operaciones interiores) | `plugin.get_indirect_tax_model("Ceuta") → "001"` | OK |
| Modelo Melilla | **420** propio Melilla (no confundir con 420 IGIC Canarias) | `plugin.get_indirect_tax_model("Melilla") → "420"` y `canarias/plugin.py` también devuelve "420" para IGIC | **COLISIÓN**: dos modelos distintos comparten número en el código. `modelo_pdf_generator.VALID_MODELOS = {"303","130","200","308","720","721","ipsi"}` no separa Ceuta/Melilla → genera el mismo PDF para ambos. Recomendación: pasar a `"ipsi_001"` y `"ipsi_420m"`. |
| Modelos importación / complementarios | Ceuta 021, gravámenes tabaco/carburantes | NO implementados | **GAP funcional** documentado. |
| Plazos | T1 20-abr, T2 20-jul, T3 20-oct, T4 30/31-ene | El tool dice literalmente "antes del día 20 del mes siguiente al trimestre" | **DESVIACIÓN MENOR**: T4 vence 30/31 de enero, no el 20. La frase del `formatted_response` es incorrecta para T4. |
| Régimen mensual >6 M€ volumen | Mensual 1-20 mes siguiente | NO contemplado (el tool solo acepta `trimestre 1-4`) | **GAP**: gran empresa Ceuta/Melilla no puede usar la herramienta. |

### 3.3 Liquidación (devengado, deducible, resultado)

| Aspecto | Norma | TaxIA | Veredicto |
|---|---|---|---|
| Devengado por tipo | Suma de cuotas por cada tipo | `total_devengado = Σ cuotas_X + cuota_importaciones + cuota_isp + mod_cuotas` | OK |
| ISP (inversión sujeto pasivo) | Aplica en operaciones B2B con destinatario en Ceuta/Melilla | Campo `base_inversion_sp` + `tipo_inversion_sp` | OK estructuralmente. Falta documentar tipos aplicables. |
| Deducible operaciones corrientes | IPSI soportado en compras destinadas a producción/exportación | `cuota_corrientes_interiores`, `cuota_inversion_interiores`, `cuota_importaciones_corrientes`, `cuota_importaciones_inversion` | OK |
| Limitación IPSI soportado en península | **NO deducible** IPSI/IVA cruzado entre territorios | NO hay validación en el calculador | **GAP**: el LLM podría introducir IVA peninsular como `cuota_corrientes_interiores`. Recomendación: añadir nota explícita en la tool description y validación en RAG. |
| Limitación deducción en ejecución de obra inmuebles | Arts. 58-59 ordenanza Ceuta — no deducible IPSI soportado en algunas operaciones inmobiliarias | NO contemplado | **GAP** documental. |
| Regularización prorrata | Solo 4T | `regularizacion_prorrata` (sin filtro Q4) | **BUG MENOR**: en Q1-Q3 el campo se suma a `total_deducible` sin restricción (a diferencia de `regularizacion_anual` que sí está condicionada a Q4). El test `test_all_deducible_concepts` lo evidencia (10 € de prorrata en Q1 se suman). |
| Regularización anual | Solo 4T | OK, condicionado a `quarter==4` | OK |
| Compensación períodos anteriores | Sin tope; piso 0 | OK | OK |
| Resultado | Devengado − deducible − compensación + reg.anual | OK | OK |
| Devolución 4T vs compensar | Q4 a devolver, Q1-Q3 a compensar | OK | OK |
| Complementaria | Resultado − resultado_anterior_complementaria | `cuota_diferencial_complementaria` | OK |

### 3.4 Encaje en pipeline TaxIA

| Aspecto | TaxIA | Veredicto |
|---|---|---|
| Tool registrada | `ALL_TOOLS` + `TOOL_EXECUTORS` | OK |
| Endpoint REST público | `POST /api/declarations/ipsi/calculate` rate-limit 30/min | OK |
| Restricción contenido autónomo | `restricted_mode` aplica `get_autonomo_block_response()` | **REVISAR**: IPSI también afecta a particulares no autónomos (compraventa de inmuebles tributa al 4 % en Melilla; usuarios particulares pueden necesitar simulación). Bloquear con mensaje "autónomo" puede confundir al usuario Particular legítimo. |
| RAG | Solo `ipsi_sage_completo.md` (texto Sage 2023) | **GAP RAG**: no hay normativa primaria (Ley 8/1991, ordenanzas vigentes Ceuta/Melilla, art. 68.4 LIRPF, art. 18 ley) ingestada como fuente. Cuando el LLM necesite citar tipos por epígrafe, no tiene fuente fiable. |
| Citación de modelo en formatted_response | Dice "Ciudad Autónoma de {territorio}" pero **no cita el número de modelo (001 / 420 Melilla)** | **GAP UX**: el usuario debería ver "Modelo 001" o "Modelo 420 (Melilla)" para saber qué formulario presentar. |

---

## Fase 4 · Casos prácticos y simulación

**Limitación**: ni Ceuta ni Melilla publican simuladores online del IPSI (a diferencia de Renta Web para IRPF). La validación se realiza contra ejemplos textuales de las propias ordenanzas, blogs especializados (Sage, Quipu, Billin, INEAF) y el manual del Modelo 420 Melilla.

### Caso 1 — Servicio de asesoría en Ceuta (4 % general servicios)

- Base imponible servicios T2: 10 000 €
- IPSI repercutido: 400 €
- IPSI soportado corrientes: 200 €

**Esperado**: a ingresar 200 €.
**TaxIA** (test `test_basic_general_rate`): `total_devengado=400`, `total_deducible=200`, `resultado_liquidacion=200` → **OK**.

### Caso 2 — Importación textil en Ceuta (3 % tras rebaja ordenanza 2018)

- Base importación: 5 000 € al 3 %
- Cuota: 150 €

**Esperado**: a ingresar 150 €.
**TaxIA**: hay que invocar `base_importaciones=5000, tipo_importaciones=0.03`. El test `test_importaciones` solo prueba 8 % y `test_tipo_importaciones_clamped` prueba clamp ≥1.0. **No hay test específico para tipo 3 %**. Funciona técnicamente (campo libre) pero no aparece en el desglose de tipos por defecto.

### Caso 3 — Restaurante 2 estrellas en Melilla (2 %)

- Servicio hostelería T3: 8 000 € al 2 %
- Cuota: 160 €

**Esperado**: a ingresar 160 €.
**TaxIA**: `base_2=8000` → cuota=160 → **OK** (cubierto por estructura).

### Caso 4 — Servicio telecom en Ceuta (8 %)

- Base T1: 25 000 € al 8 %
- Cuota: 2 000 €
- IPSI soportado: 0

**Esperado**: a ingresar 2 000 €.
**TaxIA** (test `test_two_rates` cubre la combinación 4 %+8 %): **OK**.

### Caso 5 — Construcción inmueble Melilla (10 %)

- Ejecución de obra T4: 100 000 € al 10 %
- Cuota: 10 000 €
- Soportado deducible: 1 200 €

**Esperado**: a ingresar 8 800 €. Atención: art. 58-59 ordenanza Ceuta limita la deducibilidad en ejecución de obra inmobiliaria; el calculador no aplica esa limitación (no hay forma de declarar el caso). En Melilla el régimen es similar.
**TaxIA**: `base_10=100000, cuota_corrientes_interiores=1200` → resultado 8 800 → numéricamente OK, **pero ignora restricción de deducibilidad**.

### Caso 6 — Particular vende vivienda usada en Melilla (4 %)

- Base 200 000 € al 4 %
- Cuota IPSI 8 000 €

**TaxIA**: el endpoint y el tool funcionan. **Pero** si el usuario es Particular sin plan Autónomo y `restricted_mode=True`, recibe `get_autonomo_block_response()`. **Falso positivo de bloqueo**.

### Caso 7 — Autónomo en Ceuta con prorrata especial regularizada en T1

- Devengado T1: 4 % × 50 000 = 2 000 €
- Deducible corriente: 800 €
- "Regularización prorrata": 100 € (errónea: debería ser solo en T4)

**TaxIA**: `total_deducible = 800 + 100 = 900` y `resultado = 1 100`. **BUG**: la regularización de prorrata se aplica fuera del 4T sin restricción.

### Caso 8 — T4 con resultado a devolver

- Devengado: 1 000 €
- Deducible: 1 500 €
- Resultado: −500 €

**TaxIA** (test `test_negative_result_q4_refund`): `resultado_liquidacion = -500`, mensaje correcto "puedes solicitar la devolución". OK. **Pero** el mensaje genérico añade "antes del día 20 del mes siguiente" → en T4 el plazo es 30/31 enero, no 20.

---

## Fase 5 · Simulador oficial

**No existe simulador público IPSI** ni en Ceuta ni en Melilla. La presentación es:
- Ceuta: aplicación OAC https://oac.tributosceuta.org (acceso con certificado o presencial OASTC).
- Melilla: oficina virtual https://oficinavirtual.melilla.es (formulario Modelo 420 con cl@ve / certificado).

Ambas requieren autenticación → **no automatizable cross-check** como sí ocurre con la calculadora pública de retenciones IRPF AEAT.

Se recomienda como cross-check informal:
- Ejecutar caso 1 (4 % servicios) y caso 4 (8 % telecom) en hoja de cálculo manual; cuadran con TaxIA.
- Triangular tipos por epígrafe IAE consultando ordenanza vigente PDF (Ceuta) o el listado HTML de tipos en melilla.es.

---

## Fase 6 · Veredicto y plan de mejora

### 6.1 Resumen ejecutivo

**Puntuación de alineación**: 70 / 100.

**Fortalezas**:
- Estructura del calculador correcta y testada (16 tests pasan), reproduce el flujo devengado→deducible→resultado.
- Cobertura completa de los 6 tipos efectivos del rango legal (0,5 %, 1 %, 2 %, 4 %, 8 %, 10 %).
- Soporte de ISP, importaciones, compensaciones, complementarias, regularización anual.
- Plugin `CeutaMelillaTerritory` integra correctamente IPSI con el régimen IRPF (deducción 60 % Art. 68.4 LIRPF + escala estatal).
- Plazos T1-T3 correctos, cita la Ciudad Autónoma como organismo recaudador.

**Desviaciones bloqueantes**:
1. `regularizacion_prorrata` se computa en cualquier trimestre — debe restringirse a Q4 igual que `regularizacion_anual` (BUG funcional).
2. Plazo T4 indicado como "día 20 del mes siguiente" en `formatted_response` — el real es 30/31 enero (DESVIACIÓN normativa visible al usuario).
3. `restricted_mode` bloquea IPSI con mensaje "contenido autónomo" — bloquea casos legítimos de particulares (compraventa inmueble, importaciones puntuales).
4. Modelo Melilla rotulado como "420" choca con Modelo 420 IGIC Canarias en `modelo_pdf_generator` (mismo generador para dos formularios distintos).
5. Tool description enseña al LLM que "4 % es general" sin distinguir importaciones vs servicios → riesgo de aplicar 4 % a importación en Ceuta (real: 3 %).

**Gaps funcionales no bloqueantes**:
6. Sin lookup IAE → tipo (anexos ordenanza no ingestados).
7. Sin gravámenes complementarios (tabaco, hidrocarburos — Ley 13/1996).
8. Sin régimen mensual >6 M€ de volumen.
9. RAG sin normativa primaria (Ley 8/1991, ordenanzas vigentes 2025); solo blog Sage.
10. `formatted_response` no cita el número de modelo oficial (Modelo 001 Ceuta / Modelo 420 Melilla).
11. Sin frontend `FormIpsi` (T6 del plan original sin completar).
12. Sin validación que impida introducir IVA peninsular como IPSI deducible.

### 6.2 Acciones recomendadas

| Prioridad | Acción | Archivo(s) afectados | Esfuerzo |
|---|---|---|---|
| **P0** | Restringir `regularizacion_prorrata` a Q4 | `backend/app/utils/calculators/modelo_ipsi.py:213-223` | XS |
| **P0** | Corregir mensaje plazo T4: "antes del 30/31 de enero" | `backend/app/tools/modelo_ipsi_tool.py:240-251` | XS |
| **P0** | Eliminar bloqueo `restricted_mode` para IPSI o documentarlo solo cuando hay tools de autónomo activas | `backend/app/tools/modelo_ipsi_tool.py:113-120` y `app/security/content_restriction.py` | S |
| **P1** | Renombrar identificador modelo Melilla a `ipsi_420m` o `420-mel` para no colisionar con 420 IGIC; actualizar `modelo_pdf_generator.VALID_MODELOS` y plugin | `backend/app/territories/ceuta_melilla/plugin.py:51-55`, `routers/export.py`, `modelo_pdf_generator.py` | M |
| **P1** | Reescribir tool description distinguiendo "general servicios 4 %" vs "general importaciones (Ceuta 3 % / Melilla 4 %)" + listar epígrafes habituales por tipo | `backend/app/tools/modelo_ipsi_tool.py:20-32` | S |
| **P1** | Citar modelo oficial en `formatted_response` ("Modelo 001 — IPSI Ceuta operaciones interiores" / "Modelo 420 — IPSI Melilla operaciones interiores") | `modelo_ipsi_tool.py:182` | XS |
| **P1** | Test específico `test_regularizacion_prorrata_only_q4` similar al existente para `regularizacion_anual` | `backend/tests/test_modelo_ipsi.py` | XS |
| **P2** | Añadir lookup IAE→tipo IPSI cargando anexos ordenanza Ceuta (PDF público) y Melilla (HTML público) | nueva tabla `ipsi_rates_by_iae` + script seed | L |
| **P2** | Ingestar normativa primaria al RAG: Ley 8/1991, Ley 13/1996, Ordenanza IPSI Ceuta 2025, Ordenanza IPSI Melilla 2025 | `backend/data/knowledge_updates/` + watchlist crawler | M |
| **P2** | Implementar `FormIpsi` en `frontend/src/pages/DeclarationsPage.tsx` con selector Ceuta/Melilla, campos por tipo, importaciones e ISP | frontend | M |
| **P2** | Validación calculador: warning si `cuota_corrientes_interiores > 0` y la base contiene "IVA" / detectar mismatch territorio | `modelo_ipsi.py` | S |
| **P3** | Implementar gravámenes complementarios (tabaco / carburantes) con su propio modelo y casillas | nuevo módulo | XL |
| **P3** | Régimen mensual >6 M€ — extender `quarter` a `period` (Q1-Q4 + M01-M12) | refactor calc + tool + endpoint | L |

### 6.3 Disclaimer

El IPSI es un tributo local de competencia exclusiva de las Ciudades Autónomas de Ceuta y Melilla; **no lo gestiona la AEAT**. Esta auditoría confronta el código de TaxIA con la Ley 8/1991, Ley 13/1996 y las ordenanzas fiscales vigentes en ambas Ciudades a fecha de mayo 2026, según consulta de portales oficiales (`tributosceuta.org`, `melilla.es`) y bibliografía especializada. No constituye certificación oficial. Antes de presentar cualquier autoliquidación se debe verificar el tipo aplicable a cada operación en la **última ordenanza fiscal publicada en BOCCE / BOME** del año en curso; los tipos por epígrafe IAE pueden cambiar anualmente.

---

## Fuentes consultadas

- **Ley 8/1991, de 25 de marzo** — BOE-A-1991-7645: https://www.boe.es/buscar/act.php?id=BOE-A-1991-7645
- **Ley 13/1996, de 30 de diciembre** — Renombra IPSI: https://www.boe.es/buscar/act.php?id=BOE-A-1996-29117
- **Ordenanza IPSI Ceuta — OASTC**: https://oac.tributosceuta.org/textos/2/O.F.IPSI.pdf
- **Servicios Tributarios Ceuta — info IPSI**: https://www.tributosceuta.org/index2.cfm?codigo=7110
- **Modelo 001 Ceuta — autoliquidación general**: https://oac.tributosceuta.org/3webc/fichaAsunto.do?simular=1&op=26&asunto_ide=1043
- **Ordenanza IPSI Melilla (BOME)**: https://www.melilla.es/melillaportal/RecursosWeb/DOCUMENTOS/1/2_17220_1.pdf
- **Tipos impositivos IPSI Melilla — portal oficial**: https://www.melilla.es/melillaportal/contenedor.jsp?seccion=s_fdes_d4_v1.jsp&codbusqueda=231
- **Modelo 420 IPSI Melilla**: https://www.melilla.es/melillaportal/contenedor.jsp?seccion=s_fdes_d4_v1.jsp&contenido=3061&nivel=1400&tipo=6&codMenu=340&codMenuPN=601&codMenuSN=1&codMenuTN=182
- **Manual Práctico AEAT IRPF 2024 — Cap. 16 deducción 60 % Ceuta/Melilla**: https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/irpf-2024/c16-deducciones-generales-cuota/deduccion-rentas-obtenidas-ceuta-melilla.html
- **Quipu — Tipos impositivos IPSI**: https://getquipu.com/blog/tipos-impositivos-ipsi/
- **Sage — IPSI**: https://www.sage.com/es-es/blog/ipsi-que-es-como-funciona-a-quien-afecta-este-impuesto/
- **INEAF — Tributación por IPSI en obras**: https://www.ineaf.es/tribuna/la-tributacion-por-ipsi-en-las-obras-realizadas-en-ceuta-y-melilla-iv-de-v/
- **El Faro de Ceuta — Plazo IPSI ampliado**: https://elfarodeceuta.es/autoliquidacion-ipsi-amplia-20-julio/
