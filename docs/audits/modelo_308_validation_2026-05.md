# Auditoria Modelo 308 — Solicitud de Devolucion IVA

> Fecha: 2026-05-10
> Auditor: subagente fiscal-tecnico (TaxIA)
> Codigo auditado: `backend/app/tools/modelo_308_tool.py` + `backend/tests/test_modelo_308.py`
> Veredicto global: **CRITICO — confusion entre Modelo 308 y Modelo 309. Calculo y casos de uso desalineados con Orden EHA/3786/2008.**

---

## 1. Inventario del codigo actual

### Tool registrado

- Funcion: `calculate_modelo_308` (registrada en `app/tools/__init__.py` lineas 25, 51, 76, 121-122).
- Firma: 13 parametros opcionales + `periodo` requerido (`1T`/`2T`/`3T`/`4T`/`0A`).
- Soporte CCAA: ninguno (asume territorio comun).
- Restricted mode: SI (bloquea plan Particular via `get_autonomo_block_response()`).

### Operaciones que el tool dice cubrir

El tool agrupa cuatro tipologias bajo el Modelo 308:

1. Adquisiciones intracomunitarias de bienes (Art. 30 bis.1 RIVA) a tipos 21/10/4% + RE 5,2/1,4/0,5%.
2. Inversion del sujeto pasivo (ISP) a los mismos tipos.
3. Exportaciones y entregas intracomunitarias exentas (recuperacion del RE soportado).
4. Entrega intracomunitaria de medios de transporte nuevos (sujetos ocasionales).

### Calculo

- Tipos RE hardcoded: `general (21/5,2)`, `reducido (10/1,4)`, `superreducido (4/0,5)`. **No incluye 5,1% intermedio** (1,75% labores tabaco no aplica al 308).
- Logica: `IVA devengado intra/ISP = IVA deducible intra/ISP` → neto cero. Solo `re_soportado_exportaciones` y `iva_soportado_transporte` generan devolucion neta.
- Compensacion periodos anteriores: floor a 0 si negativo, resta directa.

### Tests

- 27 tests, 7 clases (`Basic`, `ZeroRefund`, `MultipleOps`, `NegativeRejected`, `Validation`, `Compensacion`, `FormattedResponse`, `PharmacyProfile`, `ToolRegistration`, `RErates`).
- Cobertura legal: ninguna (no hay test que valide que el caso modelado encaja en la Orden EHA/3786/2008).
- Caso "pharmacy_intra_community_purchase": **caso real esta MAL encuadrado** (ver hallazgo H1).

---

## 2. Normativa aplicable (fetch verificado)

### Orden EHA/3786/2008 (Art. 7) — modelos 303 y 308

Sujetos legitimados para presentar Modelo 308 (cita literal Art. 7 + sintesis):

1. **Sujetos pasivos ocasionales** que realicen entregas exentas de medios de transporte nuevos (Art. 25.uno y dos LIVA), para solicitar la devolucion del IVA soportado en su adquisicion.
2. **Sujetos pasivos en regimen simplificado de IVA dedicados al transporte de viajeros o de mercancias por carretera** que adquieran vehiculos afectos a la actividad y soliciten la devolucion del IVA soportado deducible.
3. **Sujetos pasivos en regimen especial del recargo de equivalencia** que hayan efectuado **devoluciones a viajeros** del IVA soportado en compras realizadas en territorio espanol (Art. 21.2 LIVA — `tax-free shopping`), para reembolsarse las cantidades devueltas a esos viajeros.

Plazos:

- Sujetos ocasionales (medios de transporte nuevos): **30 dias naturales desde la fecha de la entrega**.
- Transportistas en simplificado: **20 primeros dias naturales del mes siguiente al de la adquisicion**.
- Recargo de equivalencia con devolucion a viajeros: **20 primeros dias naturales del mes siguiente al periodo trimestral**, o **30 de enero** para el 4T/anual.

### Modificaciones posteriores

- **Orden HAP/2215/2013**: elimina presentacion en papel del 308, modifica Arts. 1, 3 y 7.1.
- Versiones posteriores integradas en `Orden HAC/...` (sede AEAT no responde — pendiente verificacion manual de la version vigente 2025).

### LIVA Arts. 154-163 (RE) y Art. 30 bis.1 RIVA

- Tipos RE vigentes: **5,2% (general), 1,4% (reducido), 0,5% (superreducido), 1,75% (labores del tabaco)** — Art. 156 LIVA.
- Operaciones en las que el comerciante en RE liquida IVA propio (Art. 154.dos LIVA):
  - Adquisiciones intracomunitarias de bienes.
  - Importaciones.
  - Operaciones con inversion del sujeto pasivo.
  - Entregas intracomunitarias exentas de medios de transporte nuevos.
  - Transmision del patrimonio empresarial.

**Estos casos NO se autoliquidan ni se devuelven via Modelo 308**, sino via **Modelo 309 (declaracion-liquidacion no periodica)**. El 309 tambien recoge la transmision de inmuebles con renuncia a la exencion por sujetos en regimenes especiales y otros supuestos.

### Diferencia 308 vs 309 (clave)

| Caso | Modelo |
|------|--------|
| Comerciante en RE compra intracomunitaria de mercancia | **309** (autoliquidacion) |
| Comerciante en RE recibe servicio con ISP (Art. 84.uno.2.º LIVA) | **309** |
| Comerciante en RE entrega medio de transporte nuevo intracomunitario | **309** (autoliquidar) + **308** (pedir devolucion del IVA soportado al adquirirlo) |
| Comerciante en RE devuelve IVA a viajero extranjero (tax-free) | **308** (reembolso) |
| Particular (sujeto ocasional) entrega medio de transporte nuevo intracomunitario | **308** (devolucion del IVA soportado en su adquisicion) |
| Transportista en regimen simplificado adquiere vehiculo afecto | **308** (devolucion IVA deducible) |

---

## 3. Hallazgos

### H1 — CRITICO: confusion 308 vs 309 en el caso central de farmacias

El test `test_pharmacy_intra_community_purchase` modela la compra intracomunitaria de medicamentos por una farmacia en RE como Modelo 308. **Esto es Modelo 309**, no 308. El docstring del tool y la descripcion para el LLM (lineas 39-58) reproducen la misma confusion ("Adquisiciones intracomunitarias de bienes" como caso del 308).

Impacto: usuario farmaceutico que pregunta "que modelo presento por compras intracomunitarias" recibira respuesta **incorrecta** (308 en vez de 309). Si exporta el calculo a sede AEAT como 308, AEAT lo rechazara o exigira reclasificacion.

**Fix**: separar tools `calculate_modelo_308` (con los 3 casos legitimos) y `calculate_modelo_309` (autoliquidaciones no periodicas RE/regimenes especiales).

### H2 — CRITICO: caso "devoluciones a viajeros" (RE) no implementado

El supuesto principal del 308 para sujetos en RE — reembolso de devoluciones a viajeros (`tax-free shopping`, Art. 21.2 LIVA) — **no esta modelado**. El tool no acepta el campo basico necesario: `iva_devuelto_a_viajeros`.

Impacto: las farmacias y comercios minoristas que SI usan legitimamente el 308 (cuando devuelven IVA a turistas extracomunitarios) no pueden calcularlo.

### H3 — CRITICO: caso "transportista regimen simplificado" no implementado

El segundo supuesto legitimado (transporte viajeros/mercancias por carretera en regimen simplificado adquiriendo vehiculos) no aparece como rama del tool ni en tests. Es uno de los tres casos del Art. 7 de la Orden.

### H4 — ALTA: plazos en `formatted_response` incompletos y parcialmente erroneos

El texto generado dice: "Plazo de presentacion: los 20 primeros dias del mes siguiente al periodo (o 30 de enero para el 4T/anual)". Esto solo aplica al supuesto 3 (RE viajeros). Faltan:

- Sujetos ocasionales transporte nuevo: **30 dias desde la entrega**, no trimestral.
- Transportistas simplificado: 20 dias del mes siguiente a la **adquisicion del vehiculo**, no por trimestre.

Mostrar el plazo trimestral por defecto induce a error en los otros dos casos.

### H5 — ALTA: tipo recargo 1,75% (labores del tabaco) ausente

`TIPOS_RE` no incluye el cuarto tipo de recargo (1,75% para labores del tabaco, Art. 156.3.º LIVA). Aunque su uso es marginal y no afecta directamente al 308 (afecta al 309), si en el futuro se reusan estos tipos para 309, el dato esta incompleto.

### H6 — MEDIA: parametro `periodo` no aplica a sujetos ocasionales

Para sujetos ocasionales por entrega de transporte nuevo, no existe trimestre — el modelo se presenta puntualmente. Forzar `1T`/`2T`/`3T`/`4T`/`0A` distorsiona el caso.

### H7 — MEDIA: descripcion del tool al LLM refuerza el error

Lineas 37-58: la `description` instruye al LLM a usar el tool "OBLIGATORIO" cuando el usuario sea farmacia preguntando por devolucion en operaciones especificas, citando intracomunitarias e ISP. Esto **aumenta la probabilidad de respuesta incorrecta** en chat. El system prompt del TaxAgent debe corregirse en paralelo.

### H8 — BAJA: no hay validacion CCAA / forales

Los territorios forales (Pais Vasco, Navarra) tienen modelos analogos propios. El tool no advierte ni redirige.

### H9 — BAJA: sin referencia legal en respuesta formateada

El texto cita "Art. 30 bis.1 RIVA" y "Art. 153.dos LIVA" pero no la Orden EHA/3786/2008 ni Art. 7. La Orden es la base normativa especifica del 308.

### H10 — INFO: consultas DGT no verificadas

El acceso a `petete.tributos.hacienda.gob.es` esta bloqueado en el entorno de auditoria. Pendiente busqueda manual de DGT V0XXX-23/24 sobre 308 para incluir en el RAG.

---

## 4. Casos practicos de referencia (para futura cobertura)

| Caso | Modelo correcto | Cubierto hoy |
|------|----------------|--------------|
| Particular vende coche nuevo a comprador frances (1 mes de antiguedad, <6.000 km) | **308** sujeto ocasional | NO |
| Transportista autonomo regimen simplificado compra furgoneta 25.000 EUR + IVA | **308** transportista | NO |
| Farmacia Madrid devuelve 84 EUR de IVA a turista japones (compras 500 EUR) | **308** RE viajeros | NO |
| Farmacia Madrid compra 50.000 EUR de medicamentos a laboratorio aleman | **309** (NO 308) | SI, mal encuadrado |
| Estanco compra labores del tabaco intracomunitarias | **309** + RE 1,75% | NO |

---

## 5. Estado del simulador

- No existe simulador frontend para Modelo 308 (no hay pagina `/calculadora-308` ni endpoint `/api/modelo-308/...`).
- El tool solo se invoca via chat / function calling. No hay `irpf_simulator_tool.py`-like para 308.
- Sin UI publica → el dano del bug H1 se limita a respuestas de chat. **Aun asi es critico**: el chat es el canal principal del producto.

---

## 6. Acciones recomendadas

### Prioridad P0 (semana 1)

1. Renombrar/dividir el tool: `calculate_modelo_308` (3 casos legales) y crear `calculate_modelo_309` (RE intracomunitarias + ISP + medios de transporte autoliquidacion).
2. Corregir `description` del tool y `formatted_response` para reflejar los 3 casos reales del 308.
3. Anadir parametros `iva_devuelto_a_viajeros` (caso RE→viajeros) y `iva_soportado_vehiculo_simplificado`.
4. Actualizar tests: marcar `test_pharmacy_intra_community_purchase` como caso del **309** (mover a `test_modelo_309.py` cuando exista) o eliminar.
5. Plazos por caso (no global trimestral por defecto).
6. Documentar en `backend/CLAUDE.md` la regla "308 != 309" como anti-patron permanente.

### Prioridad P1 (proximas 2 semanas)

7. Anadir tipo RE 1,75% (labores tabaco) en `TIPOS_RE` para reutilizacion en 309.
8. Ingestar en RAG: Orden EHA/3786/2008 (texto vigente), Art. 154-163 LIVA, Art. 30 bis RIVA.
9. Buscar y agregar 3-5 consultas DGT vinculantes 2022-2024 sobre 308/309/RE al corpus.
10. Incluir advertencia explicita en respuesta cuando usuario sea de territorio foral.

### Prioridad P2 (backlog)

11. Crear simulador `/calculadora-modelo-308` publico (lead magnet farmacias / sujetos ocasionales transporte).
12. Generador PDF Modelo 308 (extender `POST /api/export/modelo-pdf`).

---

## 7. Conclusion

El tool `calculate_modelo_308` actual **modela con precision aritmetica un caso que NO corresponde al Modelo 308 (corresponde al 309)** y **omite los 3 casos que SI son del 308** segun la Orden EHA/3786/2008. Aritmetica de IVA/RE correcta; encuadre legal incorrecto. Veredicto: rehacer el tool antes de promocionar la funcionalidad a usuarios farmaceuticos, comerciantes minoristas o sujetos ocasionales. Riesgo regulatorio si el usuario actua sobre la respuesta del chat.

**Score**: 3/10 (calculo correcto, casos de uso erroneos, normativa mal citada).
