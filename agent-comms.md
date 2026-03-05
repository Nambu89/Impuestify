# Agent Communication Log - TaxIA
# =================================
# Canal de comunicacion entre agentes.
# Cada agente debe leerlo al inicio y escribir al terminar una tarea.
#
# Formato:
# [TIMESTAMP] [AGENT] [STATUS] - Mensaje
# STATUS: 🟢 DONE | 🟡 IN_PROGRESS | 🔴 BLOCKED | 📢 NEEDS_REVIEW

## Historial Completado (Resumen)

[2026-03-05] PWA + Landing + DeductionCards + Favicon + ReportActions + ShareReportModal — 🟢 DONE
[2026-03-05] Motor Deducciones (16 estatales + 48 territoriales) + Export PDF + Email Resend — 🟢 DONE
[2026-03-04] Ceuta/Melilla ventajas fiscales autonomos — Backend 🟢 DONE
[2026-03-03] Suscripciones Stripe (backend + frontend) — 🟢 DONE
[2026-03-03] Perfil fiscal autonomo + Panel admin — 🟢 DONE
[2026-03-03] Cookies LSSI-CE + RGPD — 🟢 DONE
[2026-03-02] Crawler sesiones 1-12 (428 archivos RAG) — 🟢 DONE
[2026-03-02] Streaming SSE v3.0 + FormattedMessage + StreamingTimeline — 🟢 DONE

> Para detalles completos de tareas completadas, ver `agent-comms-archive.md`

---

## 📢 INSTRUCCIONES PARA BACKEND — Diseños de Registro / Modelos AEAT

> **Contexto**: AEAT **NO usa XSD** (excepto Modelo 200). Usa ficheros planos de posiciones fijas. Los diseños de registro están en `docs/AEAT/Modelos/DisenosRegistro/`.

### Archivos disponibles

| Archivo | Modelo | Prioridad |
|---------|--------|-----------|
| `DR303_e2026.xlsx` | 303 - IVA trimestral | **ALTA** |
| `DR130_e2019.xls` | 130 - Pagos fraccionados IRPF ED | **ALTA** |
| `DR131_e2025.xlsx` | 131 - Pagos fraccionados IRPF EO | MEDIA |
| `DR111_e2019.xls` | 111 - Retenciones trabajo/prof. | MEDIA |
| `DR115_e2019.xls` | 115 - Retenciones alquileres | BAJA |
| `DR190_e2025.pdf` | 190 - Resumen anual retenciones | MEDIA |
| `DR200_e2024.xls` | 200 - IS (TIENE XSD) | **ALTA** |
| `DR202_e2025.xlsx` | 202 - Pagos fraccionados IS | MEDIA |
| `DR390_e2025.xlsx` | 390 - Resumen anual IVA | MEDIA |
| `DR347_e2025.pdf` | 347 - Operaciones terceros | BAJA |
| `DR349_e2020.pdf` | 349 - Op. intracomunitarias | BAJA |
| `DR714_e2024.xls` | 714 - Patrimonio | BAJA |
| `DR720.pdf` | 720 - Bienes extranjero | BAJA |
| `Instrucciones_Modelo650_ISD.pdf` | 650 - ISD Sucesiones | MEDIA |
| `Instrucciones_Modelo651_ISD.pdf` | 651 - ISD Donaciones | MEDIA |

### Implementación recomendada

**Opción A (recomendada): Tools de cálculo/simulación**
- Crear tools que calculen campos del modelo (no que generen fichero)
- Ejemplo: `calculate_modelo_303(base_imponible, iva_deducible, ...)` → casillas 01-89
- Diseños de registro como especificación de campos

**Opción B: Generación de ficheros** (futuro)
- Generar ficheros planos conformes al diseño de registro
- Requiere parsear Excel para posiciones/longitudes

**Prioridad:**
1. Modelo 303 IVA → tool cálculo casillas
2. Modelo 130 → pago fraccionado IRPF autónomos
3. Modelo 200 IS → parser XSD

**Excepciones:**
- Modelo 200: Único con XSD (`mod2002024.xsd`) para XML
- Modelos 650/651: Solo formulario web, sin diseño de registro
- Transición XML/XSD: Orden HAC/747/2025, enero 2027

### URLs referencia
- Diseños de registro: https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro.html
- Portal desarrolladores: https://www.agenciatributaria.es/AEAT.desarrolladores/

---

## Pendientes RAG

- Manual Práctico Renta 2025 Tomo 1+2 (AEAT) — 404 a fecha 3/3/2026
- Orden HAC Modelo 100 ejercicio 2025 — antes del 8 abril 2026

---

## Tareas activas

[2026-03-05] [BACKEND] 🟢 DONE — Fix: TaxAgent ahora verifica situacion_laboral antes de usar herramientas de autonomos. System prompt actualizado con reglas de clarificacion obligatoria. `tax_agent.py` modificado.

[2026-03-05] [BACKEND] 🟢 DONE — Fix: FOREIGN KEY constraint en message_sources. `conversation_service.py` ahora valida chunk_ids antes de insertar. Degrada gracefully si chunks no existen en BD.

[2026-03-05] [FRONTEND] 🟢 DONE — Fix: Renderizado markdown en chat. Instalado `remark-gfm` para soporte GFM (tablas, tachado, task lists). Eliminado `white-space: pre-wrap` que causaba doble salto de línea. Añadidos estilos para tablas, bloques de código, blockquotes, hr, listas anidadas.

---

## Dependencias Pendientes
---
# [AGENT_ESPERANDO] espera a [AGENT_TRABAJANDO] para [TAREA]

## Conflictos Detectados
---
# Si un agente detecta que otro modificó el mismo archivo, lo registra aquí

## Instrucciones para Agentes
---
1. Al INICIAR una tarea: Añade línea con 🟡 IN_PROGRESS
2. Si estás BLOQUEADO esperando a otro: 🔴 BLOCKED
3. Al TERMINAR: Cambia a 🟢 DONE
4. Si necesitas review: 📢 NEEDS_REVIEW
5. SIEMPRE `git pull` antes de empezar
