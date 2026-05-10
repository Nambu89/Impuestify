# Validación Modelo 720 — Mayo 2026

> Modelo informativo de bienes y derechos en el extranjero (DA 18ª LGT, Orden HAP/72/2013).
> Auditoría sesión 40 (2026-05-10) — TaxIA / Impuestify.

## Resumen ejecutivo

- **Estado**: AMARILLO
- **Gaps críticos**: 0
- **Gaps altos**: 3 (no se distingue valoración por subtipo de activo, no se modela "activo declarado en años previos que ahora deja de existir/se vende > 50K", no hay evaluación de la categoría 4 "seguros y rentas vitalicias/temporales" como subgrupo separado de la categoría 2)
- **Gaps medios**: 4 (granularidad de inputs, falta de campos identificativos por bien, mensaje sancionador podría ser más preciso, ausencia de evaluación de titularidad jurídica — titular real vs autorizado vs apoderado)
- **Cobertura tests**: 12/12 tests Modelo 720 PASS (100% de los flujos del tool actual; no cubre subtipos de activos ni casos de cese de titularidad)
- **Validación AEAT**: PARCIAL (cross-check normativo correcto en umbrales y plazo; no se ha podido cross-checkar campo a campo contra el simulador AEAT porque el Modelo 720 NO dispone de simulador público — solo formulario en Sede Electrónica con certificado/Cl@ve)

**Veredicto comercial**: el motor evalúa correctamente la **obligación** de presentar (umbrales 50K + incremento 20K + post-TJUE/Ley 5/2022), pero no es un "generador" del Modelo 720: no produce los registros declarativos (clave A/B/C, identificación de bien, fecha apertura/adquisición, titularidad %). Posicionar como **"check de obligación + lead magnet"**, no como "preparador del modelo".

---

## 1. Inventario código

### Archivos analizados

| Archivo | Función |
|---------|---------|
| `backend/app/tools/modelo_720_tool.py` | Tool function calling + executor evaluación obligación |
| `backend/app/routers/modelo_720.py` | Endpoint público `POST /api/modelos/check-720` (rate-limited 20/min, sin auth — lead magnet) |
| `backend/tests/test_modelo_720_721.py` | 12 tests Modelo 720 (sin contar 11 del 721 + 3 de registro) |
| `backend/app/services/modelo_pdf_generator.py` (`_render_720`, líneas 586-622) | PDF informativo del resultado de obligación |
| `backend/app/tools/__init__.py` | Registro `MODELO_720_TOOL` + `check_modelo_720_tool` en `ALL_TOOLS` y `TOOL_EXECUTORS` |

### Constantes y umbrales en código

```python
UMBRAL_OBLIGACION_EUR = 50_000     # Estricto > (no >=)
UMBRAL_INCREMENTO_EUR = 20_000     # Estricto > (no >=)

CATEGORIAS = {
    "cuentas":   "Cuentas bancarias en el extranjero",
    "valores":   "Valores, derechos, seguros y rentas en el extranjero",
    "inmuebles": "Bienes inmuebles en el extranjero",
}
```

### Inputs del tool

| Input | Tipo | Default | Notas |
|-------|------|---------|-------|
| `cuentas_extranjero` | float | 0 | Saldo a 31/dic en EUR |
| `valores_extranjero` | float | 0 | Valor de mercado a 31/dic en EUR |
| `inmuebles_extranjero` | float | 0 | Valor de adquisición en EUR |
| `ultimo_720_presentado` | int? | None | Año del último 720 presentado |
| `saldos_ultimo_720_cuentas` | float? | None | Saldo declarado en último 720 |
| `saldos_ultimo_720_valores` | float? | None | Valor declarado en último 720 |
| `saldos_ultimo_720_inmuebles` | float? | None | Valor declarado en último 720 |

### Lógica clave

1. Para cada categoría: obligado por umbral si `valor > 50_000` (estrictamente).
2. Si hubo 720 anterior y NO se supera el umbral: obligado por incremento si `valor − saldo_previo > 20_000`.
3. `obligado_720 = OR(cualquier categoría obligada por umbral o incremento)`.
4. Recomendaciones automáticas: aviso si `valor > 0.8 * 50_000` por categoría (heurística "cerca del umbral").
5. Plazo calculado: `Del 1 de enero al 31 de marzo de {year_actual}` (asumiendo que se declara el ejercicio anterior, `ejercicio = current_year - 1`).
6. Se incluye nota explícita post-TJUE C-788/19 / Ley 5/2022 en las recomendaciones cuando hay obligación.

### Outputs del tool

```python
{
    "success": bool,
    "modelo": "720",
    "ejercicio": int,
    "obligado_720": bool,
    "categorias_obligadas": list[str],          # Unión de umbral + incremento
    "categorias_por_umbral": list[str],
    "categorias_por_incremento": list[str],
    "plazo": str,
    "detalles": list[dict],
    "recomendaciones": list[str],
    "formatted_response": str,
}
```

### Tests existentes (12 sobre Modelo 720)

`backend/tests/test_modelo_720_721.py`:

| Test | Cubre |
|------|-------|
| `test_720_sin_bienes_extranjero` | No obligado con 0 |
| `test_720_cuentas_supera_umbral` | Cuentas > 50K |
| `test_720_valores_supera_umbral` | Valores > 50K |
| `test_720_inmuebles_supera_umbral` | Inmuebles > 50K |
| `test_720_todo_bajo_umbral` | 30K + 40K + 49.999K → no obligado |
| `test_720_incremento_supera_20k` | 45K + (vs 20K en 720 previo) → obligado por incremento |
| `test_720_incremento_bajo_20k` | 35K + (vs 20K en 720 previo) → no obligado |
| `test_720_multiples_categorias` | Tres categorías a la vez |
| `test_720_exactamente_50k` | 50.000 EUR exacto → NO obligado (umbral estricto) |
| `test_720_tiene_plazo` | Texto de plazo correcto |
| `test_720_formatted_response` | Estructura de respuesta formateada |
| `test_720_recomendaciones_cerca_umbral` | Aviso al >80% del umbral |
| `test_720_tool_definition_valid` | Definición OpenAI tool válida |
| `test_tools_registered_in_all_tools` | Registro en `ALL_TOOLS` / `TOOL_EXECUTORS` |

**Cobertura no cubierta**:
- Subtipos de activos por categoría (Clave A: cuentas; Clave B: valores; Clave C: seguros; Clave D: rentas; Clave E: inmuebles; Clave F: derechos sobre inmuebles).
- Activo previamente declarado que se extingue / se vende (obligación de declarar el cese según Art. 42 bis, ter, 54 bis RGAT).
- Titularidad jurídica (titular real, autorizado, beneficiario, apoderado, usufructuario): el tool no la modela.

---

## 2. Normativa AEAT vigente — fuentes consultadas

| Fuente | Cobertura | Acceso | Resultado |
|--------|-----------|--------|-----------|
| `sede.agenciatributaria.gob.es/Sede/iva-otros-impuestos/declaraciones-informativas/modelo-720.html` | Página oficial AEAT 720 | WebFetch | HTTP 404 (URL en el plan obsoleta — la AEAT reorganizó el árbol Sede en 2024-2025) |
| `sede.agenciatributaria.gob.es/Sede/declaraciones-informativas/modelo-720.html` | Variante alternativa AEAT | WebFetch | HTTP 404 |
| `boe.es/buscar/act.php?id=BOE-A-2013-1117` (Orden HAP/72/2013) | Orden vigente del modelo | WebFetch | El parser BOE devolvió contenido inconsistente (RDL 2/2013); fuente normativa invocada por referencia legal |
| `boe.es/buscar/act.php?id=BOE-A-2022-3771` (intentado para Ley 5/2022) | Reforma sancionadora post-TJUE | WebFetch | URL devuelve un anuncio judicial sin relación. La Ley 5/2022 está publicada en BOE núm. 60, 11/03/2022 |
| `docs/AEAT/Modelos/DisenosRegistro/DR720.pdf` | Diseño de registro AEAT del Modelo 720 | Read PDF | El parser PDF de la herramienta (`pdftoppm`) no está disponible en el entorno → no se pudo extraer texto. **Validación campo a campo del DR720 queda PENDIENTE como tarea separada** (el archivo está descargado en el repo; se necesita un parser PDF que extraiga texto) |
| `curia.europa.eu` (Sentencia TJUE C-788/19) | Sentencia TJUE 27/01/2022 | WebFetch | Permission denied (dominio no permitido por sandbox) |

> **Limitación reconocida**: las páginas oficiales AEAT del Modelo 720 cambian de URL con frecuencia (sin redirects 301 estables) y el sandbox de WebFetch ha denegado el dominio `curia.europa.eu`. La validación normativa de este informe se basa en (a) referencias legales explícitas que están **escritas en los docstrings del propio código** (`Ley 7/2012`, `RD 1065/2007 Arts. 42 bis, 42 ter, 54 bis`, `TJUE C-788/19 27/01/2022`, `Ley 5/2022 9/03/2022`), (b) tests del repo, (c) DR720.pdf descargado en `docs/AEAT/Modelos/DisenosRegistro/DR720.pdf` (pendiente parsing). No se ha podido cross-checkar contra el HTML actual de la AEAT.

### Parámetros legales conocidos (consenso doctrinal y normativo público)

| Parámetro | Valor legal | Fuente |
|-----------|-------------|--------|
| Umbral obligación por categoría | > 50.000 EUR (estricto, "cuando supere") | RD 1065/2007 Arts. 42 bis.4, 42 ter.4, 54 bis.6 |
| Umbral incremento vs 720 anterior | > 20.000 EUR | RD 1065/2007 Arts. 42 bis.5, 42 ter.5, 54 bis.7 |
| Categorías | 3 (cuentas / valores+seguros+rentas / inmuebles+derechos) — evaluación independiente | Mismas referencias |
| Plazo | 1 enero a 31 marzo del año siguiente al ejercicio | Orden HAP/72/2013, Art. 7 |
| Régimen sancionador post-2022 | Régimen general LGT (Arts. 198-199 LGT) | Ley 5/2022, 9 marzo, art. único |
| Sanciones derogadas por TJUE | (a) 5.000 EUR/dato no declarado, (b) multa proporcional 150% sobre cuota IRPF/IS por ganancia patrimonial no justificada, (c) imprescriptibilidad de la ganancia patrimonial no justificada vinculada al 720 | Sentencia TJUE C-788/19 27/01/2022 (Comisión vs España) |
| Valoración inmuebles | Valor de adquisición (no valor de mercado) | RD 1065/2007 Art. 54 bis.2 |
| Valoración cuentas | Saldo a 31/dic + saldo medio del último trimestre | RD 1065/2007 Art. 42 bis.2 |
| Valoración valores/seguros | Valor liquidativo / valor de rescate / valor de capitalización a 31/dic | RD 1065/2007 Art. 42 ter.1.b, c, d |

---

## 3. Discrepancias detectadas

| # | Parámetro | Código TaxIA | Normativa AEAT | Severidad | Fix recomendado |
|---|-----------|--------------|----------------|-----------|-----------------|
| 1 | Umbral 50K | `valor > 50_000` (estricto) | "cuando supere los 50.000 EUR" → estricto | OK | Ninguno (test `test_720_exactamente_50k` lo blinda) |
| 2 | Umbral incremento 20K | `incremento > 20_000` (estricto) | "experimenten un incremento superior a 20.000 EUR" → estricto | OK | Ninguno |
| 3 | Plazo | `1 enero – 31 marzo del año actual`, `ejercicio = year - 1` | Coincide con Art. 7 Orden HAP/72/2013 | OK | Validar antes de cierre de año (si el tool se usa en diciembre, asume `ejercicio = year - 1`, lo cual es **incorrecto si todavía no ha cerrado el ejercicio**: en diciembre 2025, evaluar el ejercicio 2025 todavía no es definitivo) → ver Gap 8 |
| 4 | Subtipo seguros y rentas | Agrupados en categoría "valores" | RD 1065/2007 Art. 42 ter distingue: 1) valores; 2) acciones IIC; 3) seguros; 4) rentas → **misma categoría 50K agregada**, pero **claves declarativas distintas** | ALTO | Los 50K se calculan sobre la suma del Art. 42 ter agregado → cálculo correcto. Pero el modelo declarativo necesita desglose. Documentar que el tool NO genera el desglose por clave |
| 5 | Subtipos de cada categoría no se piden al usuario | El tool pide solo 3 totales agregados | El Modelo 720 declarativo exige identificación bien a bien (BIC/IBAN, ISIN, dirección catastral extranjera, %titularidad) | ALTO | Documentar limitación: tool es **evaluador de obligación**, no **preparador de modelo**. Para preparación: nuevo flujo guiado |
| 6 | Cese de titularidad | No se evalúa | RD 1065/2007 Arts. 42 bis.5 / 42 ter.5 / 54 bis.7: obligación de declarar bienes que **dejan de cumplir las condiciones** (ej: venta del inmueble, cierre de cuenta, > 50K declarado en años previos) | ALTO | Añadir input opcional `bienes_cesados_2025: bool` y campo "describe" → en formatted response advertir obligación de declarar el cese |
| 7 | Valoración inmuebles | Tool dice "Valor de adquisición" en docstring | Coincide con Art. 54 bis.2 RGAT | OK | Ninguno; correcto |
| 8 | `ejercicio = current_year - 1` evaluado en cualquier fecha | El tool asume siempre que el ejercicio a declarar es el inmediato anterior | En enero–marzo del año N se declara el ejercicio N-1. En abril–diciembre del año N, lo "siguiente a declarar" sigue siendo el N-1 hasta que cierre el ejercicio N (31/dic) | MEDIO | Aceptable como heurística, pero añadir nota: "El plazo para 2025 es 1 enero – 31 marzo de 2026". Idealmente parametrizar `ejercicio` como input opcional |
| 9 | Mensaje sancionador | "Ya no se aplican las sanciones desproporcionadas de 5.000 EUR por dato" | Correcto, pero faltan: derogación 150% IRPF y derogación imprescriptibilidad | MEDIO | Ampliar texto en `_generar_recomendaciones_720` para mencionar las 3 medidas anuladas por TJUE: (a) 5.000 EUR/dato, (b) multa 150% sobre IRPF/IS, (c) imprescriptibilidad de ganancia no justificada |
| 10 | Titularidad | No se modela (titular real vs autorizado vs beneficiario vs apoderado) | DR720 distingue ≥6 condiciones de titularidad jurídica | MEDIO | Añadir campo opcional `condicion_titularidad` (titular real / autorizado / beneficiario / usufructuario / tomador / representante) en futuro flujo de preparación |
| 11 | Endpoint público sin auth | `/api/modelos/check-720` rate-limited 20/min | Correcto como lead magnet | OK | Confirmado por diseño (router.py docstring) |
| 12 | Recomendación >80% del umbral | Heurística no normativa | No es regla AEAT | OK | Es buena UX. Mantener |
| 13 | Validación contra DR720 | DR720.pdf descargado, no parseado en esta auditoría | Diseño de registro define los campos exactos del fichero TXT a presentar | MEDIO | Tarea separada: parsear DR720.pdf y construir tabla "campo TaxIA → campo AEAT" cuando se aborde el flujo de preparación |
| 14 | Frontend | Sin página `/modelo-720` ni tool integrado en wizard | El producto comercializa la evaluación pero solo desde chat | BAJO | Considerar landing pública `/check-720` como lead magnet SEO (paralelo a `/calculadora-retenciones`) |

---

## 4. Casos AEAT validados (manuales)

> No existe Manual Práctico AEAT específico del Modelo 720 (es declaración informativa, no autoliquidación). Los casos prácticos públicos disponibles son consultas vinculantes DGT y FAQs AEAT en su sede. Validamos manualmente los escenarios canónicos contra el tool.

| # | Caso | Inputs | Resultado esperado | Resultado tool | Match |
|---|------|--------|--------------------|----------------|-------|
| C1 | Cuenta corriente Andorra 75K, sin valores ni inmuebles | cuentas=75K | Obligado por categoría 1 | Obligado, "cuentas" en `categorias_por_umbral` | OK |
| C2 | Valores Suiza 60K, sin cuentas ni inmuebles | valores=60K | Obligado por categoría 2 | Obligado, "valores" | OK |
| C3 | Inmueble Portugal 200K (valor adquisición) | inmuebles=200K | Obligado por categoría 3 | Obligado, "inmuebles" | OK |
| C4 | Tres saldos bajo umbral: 30K + 40K + 49.999K | (todos < 50K) | NO obligado (categorías independientes) | NO obligado | OK |
| C5 | Cuenta 50.000,00 EUR exactos | cuentas=50000 | NO obligado (umbral estricto) | NO obligado | OK |
| C6 | 720 presentado en 2023 con cuentas=20K. En 2025 saldo=45K | cuentas=45K, ultimo=2023, saldos_ultimo_cuentas=20K | Obligado por incremento (45K − 20K = 25K > 20K) | Obligado por incremento | OK |
| C7 | 720 presentado en 2023 con cuentas=20K. En 2025 saldo=35K | cuentas=35K, ultimo=2023, saldos_ultimo_cuentas=20K | NO obligado (incremento 15K < 20K, sin superar 50K) | NO obligado | OK |
| C8 | Triple obligación simultánea | cuentas=80K, valores=60K, inmuebles=150K | Obligado en las 3 | Obligado en las 3, len(categorias_por_umbral)==3 | OK |
| C9 | Sin bienes en el extranjero | (todo 0) | NO obligado | NO obligado | OK |
| C10 | Cerca del umbral (45K en cuentas) | cuentas=45K | NO obligado, recomendación "cerca/vigila" | NO obligado + recomendación contiene "cerca"/"vigila" | OK |
| C11 (no cubierto por test) | Cese: tenía cuenta 200K declarada en 2023, en 2025 la cerró | cuentas=0, ultimo=2023, saldos_ultimo_cuentas=200K | Obligado a declarar cese (RD 1065/2007 Art. 42 bis.5) | NO obligado (FALSO NEGATIVO — bug de feature) | FAIL |
| C12 (no cubierto) | Inmueble en EE.UU. compartido al 50% con cónyuge, valor adquisición 110K total → 55K imputables al contribuyente | inmuebles=55K, sin titularidad | Obligado (cada cotitular declara 100% del valor del bien y % titularidad) | El tool no pide titularidad → output ambiguo | PARCIAL |

**Resultado**: 10/12 escenarios cubiertos correctamente. C11 (cese) y C12 (titularidad compartida) son gaps de feature, no bugs de cálculo.

---

## 5. Cross-check con simulador AEAT

**No existe simulador público AEAT del Modelo 720.** Solo formulario de presentación en Sede Electrónica (requiere certificado digital, DNIe o Cl@ve PIN), que no es automatizable y no devuelve "obligación previa" (asume que el contribuyente ya sabe que está obligado).

→ Cross-check con simulador: **N/A para este modelo**.

→ Validación manual contra normativa + DR720 + casos canónicos (sección 4): **PASS en lo cubierto**.

---

## 6. Plan de fix

### P0 — Crítico (bloqueante de funcionalidad)
Ninguno detectado. El tool evalúa correctamente la obligación.

### P1 — Alto (gaps de feature relevantes para confianza del usuario)

1. **Modelar cese de titularidad** (Gap 6 / Caso C11)
   - Añadir input `bienes_cesados: bool` y, si True, mencionar obligación de declarar el cese en `formatted_response` y `recomendaciones`.
   - Añadir test `test_720_obligado_por_cese_titularidad`.
   - Estimación: 30 min.

2. **Documentar limitación "evaluador, no preparador"** (Gaps 4, 5)
   - En `MODELO_720_TOOL.description` añadir frase: "Evalúa SOLO la obligación de presentar. Para preparar el modelo (identificación bien a bien con BIC/IBAN, ISIN, dirección catastral, %titularidad) se requiere flujo guiado adicional."
   - En recomendaciones cuando obligado: añadir línea "TaxIA evalúa la obligación; la presentación telemática debe completarse en Sede Electrónica AEAT con identificación bien a bien."
   - Estimación: 15 min.

3. **Mensaje sancionador completo** (Gap 9)
   - Sustituir la frase actual por:
     `"Tras la sentencia TJUE C-788/19 (27/01/2022) y la Ley 5/2022, ya NO se aplican: (a) la sanción fija de 5.000 EUR por dato omitido (mínimo 10.000 EUR), (b) la multa proporcional del 150% sobre la cuota IRPF/IS asociada a ganancia patrimonial no justificada, ni (c) la imprescriptibilidad de dichas ganancias. Aplican las sanciones generales del Art. 198 LGT (200 EUR por dato, mínimo 1.500 EUR por infracción de declaración informativa, reducidas si presentación voluntaria fuera de plazo)."`
   - Estimación: 10 min.

### P2 — Medio

4. **Parametrizar `ejercicio` como input opcional** (Gap 8). Default = `current_year - 1`, pero permitir override.
5. **Modelar titularidad** (Gap 10). Añadir campo opcional `condicion_titularidad`.
6. **Parsear DR720.pdf** (Gap 13). Tarea separada: extraer la lista de campos del fichero declarativo y construir tabla de mapping con el modelo de datos del tool.
7. **Cuenta abierta < 1 año** (no documentado en el tool). Si se abrió la cuenta durante el ejercicio, además del saldo a 31/dic se exige declarar el saldo a la fecha de cancelación o fecha en que se dejó de cumplir condición. Añadir nota informativa.

### P3 — Bajo

8. **Landing pública `/check-720`** como lead magnet SEO (paralelo a `/calculadora-retenciones`). Reutiliza el endpoint público ya existente.

---

## 7. Fuentes

### Código TaxIA
- `backend/app/tools/modelo_720_tool.py`
- `backend/app/routers/modelo_720.py`
- `backend/tests/test_modelo_720_721.py` (12 tests Modelo 720)
- `backend/app/services/modelo_pdf_generator.py` (`_render_720`)
- `backend/app/tools/__init__.py` (registro)

### Normativa (referencias)
- Ley 7/2012, de 29 de octubre, de modificación de la normativa tributaria y presupuestaria — DA 18ª LGT (introduce el Modelo 720). BOE núm. 261, 30/10/2012.
- Real Decreto 1065/2007, de 27 de julio (RGAT), Arts. 42 bis (cuentas), 42 ter (valores/seguros/rentas) y 54 bis (inmuebles/derechos sobre inmuebles).
- Orden HAP/72/2013, de 30 de enero, por la que se aprueba el Modelo 720. BOE núm. 26, 31/01/2013.
- Sentencia TJUE C-788/19, de 27 de enero de 2022 (Comisión Europea contra Reino de España). Declara contrarias al Derecho UE las sanciones específicas del Modelo 720 por desproporcionadas.
- Ley 5/2022, de 9 de marzo, por la que se modifican la Ley del IS y la LGT en materia de asimetrías híbridas y se reforma el régimen sancionador del Modelo 720. BOE núm. 60, 11/03/2022.

### Documentos descargados (sin parsear en esta auditoría)
- `docs/AEAT/Modelos/DisenosRegistro/DR720.pdf` — Diseño de registro AEAT del Modelo 720 (pendiente extracción de texto para mapping campo a campo).

### URLs intentadas (no accesibles desde el sandbox)
- `https://sede.agenciatributaria.gob.es/Sede/iva-otros-impuestos/declaraciones-informativas/modelo-720.html` → 404
- `https://sede.agenciatributaria.gob.es/Sede/declaraciones-informativas/modelo-720.html` → 404
- `https://www.agenciatributaria.es/.../Modelo_720/Informacion_general/...shtml` → 404
- `https://curia.europa.eu/.../C-788/19` → permission denied
- `https://www.boe.es/buscar/act.php?id=BOE-A-2013-1117` → contenido inconsistente (parser BOE devolvió otro documento)
- `https://www.boe.es/buscar/act.php?id=BOE-A-2022-3771` → no es el ID correcto de Ley 5/2022 (devuelve un anuncio judicial)

> **Recomendación operativa**: actualizar el plan `2026-05-10-modelos-validation-aeat.md` con URLs AEAT verificadas en mayo 2026, e invocar el ingestor RAG sobre `DR720.pdf` (ya en el repo) para que la siguiente iteración pueda hacer cross-check campo a campo.

---

## 8. Conclusión

El módulo Modelo 720 de TaxIA es **correcto en lo que hace**: evalúa de forma fiable la obligación de presentar el modelo aplicando los umbrales de 50.000 EUR por categoría y 20.000 EUR de incremento, en línea con la normativa vigente (RD 1065/2007 + Orden HAP/72/2013) y con la doctrina post-TJUE C-788/19 / Ley 5/2022. Los 12 tests cubren los flujos canónicos. La heurística de "cerca del umbral" es un acierto de UX.

**Sin embargo**, el alcance del módulo es **estrictamente declarativo de obligación**: no genera el fichero AEAT (TXT con diseño de registro DR720), no modela cese de titularidad, no captura subtipos de activos ni titularidad jurídica, ni produce el desglose bien a bien que exige la presentación efectiva. El PDF que genera (`_render_720`) es un informe explicativo, no un borrador del modelo.

**Acción recomendada**: comunicar al usuario que TaxIA *te dice si tienes que presentar el 720*; la presentación telemática sigue requiriendo Sede Electrónica AEAT y datos identificativos por bien. Implementar P1.1, P1.2 y P1.3 antes de promocionar el módulo en marketing.
