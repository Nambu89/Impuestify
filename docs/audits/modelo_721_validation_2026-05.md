# Auditoría técnico-normativa Modelo 721 (TaxIA)

> Fecha: 2026-05-10
> Auditor: agente investigación TaxIA
> Alcance: `backend/app/tools/modelo_721_tool.py`, `backend/tests/test_modelo_720_721.py` (11 tests M721), `backend/app/services/modelo_pdf_generator.py` (`_render_721`)
> Versión código auditada: rama `main` post sesión 39 (2026-05-10)

---

## 1. Inventario funcional implementado

| Elemento | Implementado | Ubicación |
|----------|--------------|-----------|
| Umbral 50.000 EUR a 31/dic | Sí | `modelo_721_tool.py:33` `UMBRAL_OBLIGACION_EUR = 50_000` |
| Regla incremento >20.000 EUR vs último 721 | Sí | `modelo_721_tool.py:34` `UMBRAL_INCREMENTO_EUR = 20_000` |
| Comparador estricto `>` (no `>=`) | Sí | `modelo_721_tool.py:153,161` (validado test `test_721_exactamente_50k`) |
| Lista exchanges extranjeros conocidos | Sí (17 plataformas) | `modelo_721_tool.py:37-41` |
| Lista exchanges españoles excluidos | Sí (Bit2Me, Bitnovo) | `modelo_721_tool.py:44-46` |
| Exclusión autocustodia (hardware/software wallet) | Sí (mención en recomendaciones) | `modelo_721_tool.py:275-279` |
| Plazo presentación 1 enero - 31 marzo año siguiente | Sí | `modelo_721_tool.py:166` |
| Tool definition para function calling OpenAI | Sí | `modelo_721_tool.py:52-104` |
| Generador PDF con `_render_721` | Sí | `modelo_pdf_generator.py:625-671` |
| Tests obligación + edge cases + autocustodia | Sí (11 tests) | `test_modelo_720_721.py:218-358` |
| Simulador / wizard interactivo | **NO implementado** | — |

---

## 2. Normativa aplicable (cross-check)

| Norma | Implementado en código | Referencia |
|-------|------------------------|------------|
| **Real Decreto 249/2023, de 4 abril** (introduce DA 18ª LGT) | Sí, citado | `modelo_721_tool.py:7` |
| **Orden HFP/886/2023, de 26 julio** (BOE 31 julio 2023, aprueba modelo y plazos) | Sí, citado | `modelo_721_tool.py:8` |
| **Ley 11/2021 antifraude** (introduce obligación) | Sí, citado en docstring | `modelo_721_tool.py:7-8` |
| **DA 18ª LGT** (régimen sancionador asimilado al M720 *post* STJUE 27-ene-2022) | **No mencionado** en recomendaciones | — |
| **Reglamento IRPF Art. 39 bis** (clasificación criptos como elementos patrimoniales) | No mencionado (sí ganancia/pérdida casillas 1813/1814) | `modelo_721_tool.py:282-284` |
| **Consultas DGT V0975-22, V1948-22** (clasificación criptos / utilidad token) | No referenciadas | — |
| **Orden HFP/823/2022** (precursor M172/M173 — exchanges españoles) | Mencionado conceptualmente | `modelo_721_tool.py:264` |
| **MiCA (Reg. UE 2023/1114)** + transposición DORA | No mencionado (no impacta M721 directamente, OK) | — |

**Hallazgo normativo confirmado**: umbral 50.000 EUR (saldo 31/dic), regla incremento 20.000 EUR, plazo 1 enero - 31 marzo año siguiente, exclusión autocustodia, exclusión exchanges con sede en España (informan vía M172 saldos / M173 operaciones). Coincide con la implementación.

---

## 3. Cross-check de reglas críticas

### 3.1 Umbral estricto > 50.000 EUR

| Caso | Esperado | Test | Resultado |
|------|----------|------|-----------|
| 50.000,00 EUR exacto | NO obligado | `test_721_exactamente_50k` | PASS |
| 50.000,01 EUR | Obligado | (no cubierto) | Cobertura recomendable |
| 80.000 EUR | Obligado | `test_721_crypto_supera_umbral` | PASS |
| 30.000 EUR | NO obligado | `test_721_crypto_bajo_umbral` | PASS |
| 0 EUR | NO obligado | `test_721_sin_valor` | PASS |

**Veredicto**: comparador `>` correcto según Art. 42 quater.5 RGAT.

### 3.2 Determinación de "extranjero"

| Regla DGT/AEAT | Implementado | Notas |
|----------------|--------------|-------|
| Entidad gestora (custodio) **no residente** en España → declarable | Sí (vía exchange list) | Lista hardcoded — no maneja exchanges no listados |
| **Sucursal española** de exchange extranjero (ej. Binance Spain SL inscrita en RGSE Banco España) → **NO declarable** | **NO contemplado** | **GAP CRÍTICO** |
| Exchange español puro (Bit2Me, Bitnovo) → NO declarable | Sí | Solo 2 entradas — falta Onyze, 2gether (cesado), Criptan, Onyx, Vottun |
| Wallet de autocustodia → NO declarable | Sí (recomendación textual) | No bloquea cálculo si usuario lo pasa por error |

**Hallazgo crítico (gap 1)**: la lógica clasifica como "extranjero" cualquier exchange no listado en `EXCHANGES_ESPANOLES`. Si Binance opera en España vía sucursal o filial registrada en el Registro de Proveedores de Servicios sobre Criptoactivos del Banco de España (Binance se registró en julio 2022), las criptos custodiadas por esa filial **no irían al M721** sino al M172/M173 que la propia entidad presenta. La heurística actual produciría **falsos positivos**.

**Hallazgo (gap 2)**: lista `EXCHANGES_ESPANOLES` muy corta. Debería ampliarse o, mejor, sustituirse por una pregunta al usuario: "¿Está la entidad gestora inscrita en el Registro del Banco de España como proveedor de servicios sobre criptoactivos?".

**Hallazgo (gap 3)**: la heurística no contempla **NFTs** (Consulta DGT V1948-22 los califica como bienes inmateriales — discutida su inclusión en M721; criterio AEAT actual: solo monedas virtuales en sentido estricto, NFTs fuera). El docstring no aclara que NFTs quedan excluidos.

### 3.3 Casillas Modelo 721

El M721 no usa "casillas" numeradas como el M100. Se rellena por **registro** (un registro por cada moneda virtual en cada custodio):
- NIF declarante
- Tipo de declaración (1=normal, 2=complementaria, 3=sustitutiva)
- Identificación entidad gestora (denominación, NIF/identificación fiscal país)
- País residencia entidad gestora (código ISO)
- Tipo de moneda virtual (código BTC, ETH, etc.)
- Número de unidades a 31/dic
- Valoración en euros a 31/dic (cotización media plataforma)
- Saldos medios trimestre 4T (opcional según versión técnica)

**Implementado**: la recomendación 7 (`modelo_721_tool.py:271-274`) menciona "tipo, saldo en unidades y euros, exchange y país". Cobertura conceptual OK; no hay generador de fichero XML/AEAT (fuera de alcance del tool, se ofrece solo PDF informativo). Aceptable como tool de evaluación de obligación, no como presentador.

### 3.4 Régimen sancionador

Tras STJUE 27-ene-2022 (asunto C-788/19) que declaró desproporcionadas las sanciones específicas del antiguo M720, el **nuevo régimen** del M721 aplica las **sanciones generales de la LGT** (Art. 198 LGT — no presentar declaración informativa: 20 EUR por dato con mín 300 / máx 20.000 EUR; reducción 50% si presentación fuera de plazo sin requerimiento previo).

**Hallazgo (gap 4)**: la implementación **no menciona el régimen sancionador**. Convendría añadir recomendación tipo: "Si no presentas en plazo: sanción mínima 300 EUR (Art. 198 LGT), reducible al 50% si lo regularizas voluntariamente antes de requerimiento".

---

## 4. Casos prácticos / consultas DGT 2024

Búsqueda no exhaustiva (sin acceso PETETE/INFORMA público sin auth). Consultas relevantes que **deberían** integrarse vía RAG y citarse desde el tool:

| Consulta | Tema | Estado en código |
|----------|------|------------------|
| **V0975-22** | Calificación cripto como elemento patrimonial (no moneda de curso legal) | No citada |
| **V1948-22** | NFTs — naturaleza jurídica | No citada |
| **V0586-23** | Staking y M721 (rendimiento del capital mobiliario) | No citada |
| **V2500-23** *(estimada)* | Préstamo de criptos en exchange — ¿entra en M721? | No citada |
| **V0066-24** *(estimada)* | Custodia compartida (multi-sig) — quién declara | No citada |

**Recomendación**: añadir en `recomendaciones` un bloque "Consultas DGT relevantes" cuando el usuario resulte obligado, con 2-3 enlaces a INFORMA/PETETE.

---

## 5. Simulador

**Estado**: **no existe** simulador interactivo M721 (a diferencia del simulador IRPF en `/api/irpf/estimate`). El tool actual hace evaluación binaria de obligación, no genera el fichero de presentación. No hay endpoint REST público equivalente (solo function calling vía LLM).

**Recomendación de roadmap**:
1. Endpoint POST `/api/modelo-721/check` (sin LLM, ~50ms) replicando `check_modelo_721_tool` para integración con wizard frontend.
2. Wizard frontend `/modelo-721/calculadora` con: paso 1 (saldo a 31/dic), paso 2 (lista de exchanges con autocompletado contra lista española extendida + Registro Banco España), paso 3 (¿presentaste 721 anterior?), paso 4 (resultado + plazo + recordatorio Calendar).
3. (V2) Generador de fichero presentable (formato AEAT registro a registro) — alta complejidad, requiere XSD oficial M721.

---

## 6. Hallazgos consolidados y recomendaciones

### Bugs / gaps por prioridad

| # | Prioridad | Gap | Fix sugerido | Archivo |
|---|-----------|-----|--------------|---------|
| 1 | **ALTA** | No contempla sucursales/filiales españolas de exchanges extranjeros (Binance registrado en BdE) → falsos positivos | Añadir parámetro `entidad_inscrita_bde: bool` o pregunta wizard | `modelo_721_tool.py:78-85` |
| 2 | **ALTA** | Lista `EXCHANGES_ESPANOLES` incompleta (faltan Onyze, Criptan, Vottun, Onyx, Bitbase) | Ampliar lista o consultar Registro BdE dinámicamente | `modelo_721_tool.py:44-46` |
| 3 | **MEDIA** | No menciona régimen sancionador (Art. 198 LGT, 300-20.000 EUR) | Añadir recomendación específica si obligado y plazo cerca/vencido | `_generar_recomendaciones_721` |
| 4 | **MEDIA** | No aclara tratamiento de NFTs (excluidos del M721 según criterio AEAT actual) | Añadir nota en `description` del tool y en recomendaciones | `modelo_721_tool.py:60-66` |
| 5 | **MEDIA** | No cita Consultas DGT relevantes (V0975-22, V1948-22, V0586-23) | Bloque "Más información" en recomendaciones | `_generar_recomendaciones_721` |
| 6 | **BAJA** | Falta test edge `valor = 50_000.01` (justo por encima umbral) | Añadir test parametrizado | `test_modelo_720_721.py` |
| 7 | **BAJA** | Falta test que verifique exclusión Bit2Me **resta** del cómputo (actualmente se contabilizan en `crypto_extranjero_valor` pase lo que pase) | El parámetro debería excluir explícitamente saldo en exchanges españoles, no solo clasificarlos | `check_modelo_721_tool` |
| 8 | **BAJA** | No existe endpoint REST `/api/modelo-721/check` (solo function calling) | Crear router análogo a `irpf_estimate.py` | nuevo `modelo_721_check.py` |
| 9 | **BAJA** | No existe simulador frontend / wizard | Roadmap M721 calculator (ver §5) | `frontend/src/pages` |
| 10 | **BAJA** | Comparador `>` correcto pero docstring dice "supera 50.000 EUR" sin aclarar estricto vs ≥ | Añadir nota: "estrictamente superior" | docstrings |

### Anti-patrones / riesgos no técnicos

- **Falso positivo de obligación** por gap 1+2: usuario con cripto en Binance Spain SL recibiría "OBLIGADO" cuando realmente no debe presentar M721 (la propia entidad presenta M172/M173). Riesgo reputacional.
- **Falso negativo** menos probable: lista hardcoded de extranjeros no es exhaustiva, pero el código clasifica como "afectado" cualquier exchange **no listado** como español. Esto es conservador (mejor false positive que false negative en informativos).

### Aspectos correctamente implementados

- Umbral estricto `>` 50.000 (alineado con criterio AEAT y test PASS).
- Regla de incremento solo aplica si `not obligado_umbral` (evita doble cómputo redundante).
- Plazo dinámico calculado por `datetime.now().year - 1` (correcto: declaración 2025 sobre ejercicio 2024 entre 1-ene-2025 y 31-mar-2025).
- Mención explícita autocustodia en recomendaciones cuando obligado (test `test_721_autocustodia_mencion` lo verifica).
- Aclaración M721 informativo + ganancias/pérdidas en IRPF casillas 1813/1814 (`modelo_721_tool.py:281-284`).
- Tool registrado en `ALL_TOOLS` y `TOOL_EXECUTORS` (test `test_tools_registered_in_all_tools`).
- Generador PDF (`_render_721`) coherente con campos del tool.

---

## 7. Veredicto global

**Estado**: **APTO con reservas** para uso conversacional vía LLM. **NO APTO** como simulador autoritativo público sin resolver gaps 1-2 (clasificación sucursales BdE).

**Calidad código**: 7/10. Estructura limpia, separación tool/helpers/format, tests razonables (11 tests M721 PASS).

**Cobertura normativa**: 6/10. Falta régimen sancionador, NFTs, sucursales BdE, consultas DGT.

**Cobertura tests**: 7/10. Faltan 2-3 edge cases (limítrofe 50.000,01; combinación umbral+incremento; exclusión efectiva en cómputo).

**Acción inmediata recomendada**:
1. Implementar gap 1 (parámetro `entidad_inscrita_bde`) — 1h.
2. Ampliar lista `EXCHANGES_ESPANOLES` con Registro BdE actualizado — 30min.
3. Añadir bloque sancionador en recomendaciones — 30min.
4. Añadir test `test_721_limite_estricto_50k_01` — 15min.

**Acción media plazo**:
- Endpoint `/api/modelo-721/check` + wizard frontend (alineado con `/calculadora-neto` y `/calculadora-retenciones` ya existentes).
- Ingestar Orden HFP/886/2023 + Consultas DGT V0975-22, V1948-22, V0586-23 al RAG (tag `modelo_721`).
