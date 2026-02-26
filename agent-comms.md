# Agent Communication Log - TaxIA
# =================================
# Este archivo actúa como "canal de comunicación" entre agentes.
# Cada agente debe leerlo al inicio y escribir al terminar una tarea.
# 
# Formato:
# [TIMESTAMP] [AGENT] [STATUS] - Mensaje
# STATUS: 🟢 DONE | 🟡 IN_PROGRESS | 🔴 BLOCKED | 📢 NEEDS_REVIEW

## Mensajes Activos
---
[2026-01-11 16:30] [SYSTEM] [🟢 DONE] - Sistema de comunicación entre agentes inicializado

[2026-01-11] [FRONTEND] [🟢 DONE] - CSS Responsive Mobile-First Refactoring

### Resumen de Cambios CSS

**Archivos modificados:** 13 archivos CSS

#### 1. Conversión a Mobile-First (min-width en lugar de max-width)
| Archivo | Estado Anterior | Estado Actual |
|---------|-----------------|---------------|
| `global.css` | max-width: 768px | Mobile-first (comentarios) |
| `Footer.css` | max-width: 768px | min-width: 768px |
| `Auth.css` | max-width: 480px | min-width: 480px |
| `Home.css` | max-width: 1024px/768px | min-width: 768px/1024px |
| `Dashboard.css` | max-width: 1024px/768px | min-width: 768px/1024px |
| `LegalPage.css` | max-width: 768px | min-width: 768px |

#### 2. Variables CSS Consistentes
Todos los archivos ahora usan las variables de `global.css`:
- Colores: `--color-primary`, `--color-gray-*`, `--color-error`, `--color-success`
- Espaciado: `--spacing-*`
- Bordes: `--radius-*`
- Sombras: `--shadow-*`
- Transiciones: `--transition-*`
- Z-index: `--z-*`

**Archivos actualizados con variables CSS:**
- `Header.css` - eliminados ~15 colores hardcodeados
- `Footer.css` - eliminados ~20 colores hardcodeados
- `ConversationSidebar.css` - eliminados ~12 colores hardcodeados
- `AITransparencyModal.css` - eliminados ~15 colores hardcodeados
- `ThinkingIndicator.css` - eliminados ~5 colores hardcodeados
- `Chat.css` - eliminados ~25 colores hardcodeados
- `SettingsPage.css` - eliminado :root duplicado

#### 3. Breakpoints Consistentes
- **Mobile:** 320px+ (estilos base)
- **Tablet:** 768px+ (`@media (min-width: 768px)`)
- **Desktop:** 1024px+ (`@media (min-width: 1024px)`)

#### 4. Verificación
- Build: ✅ Exitoso (`npm run build` sin errores)
- Tamaño CSS: 44.56 kB (gzip: 7.23 kB)

#### Notas para otros agentes
- La paleta de colores está en `frontend/src/styles/global.css`
- Usar siempre variables CSS en lugar de valores hardcodeados
- Seguir patrón mobile-first: estilos base para móvil, media queries para pantallas más grandes

## Estado Biblioteca RAG — Para todos los agentes
---
> Última actualización: 2026-02-25 | **394 PDFs** en `docs/`

### ✅ Cobertura actual (lo que el RAG tiene disponible para ingestar)

**Normativa foral (Bizkaia/Gipuzkoa/Araba/Navarra):**
- Reforma Fiscal 2025 completa: Gipuzkoa NF 1/2025 + Araba NF 3/2025 + Bizkaia NF 2/2025 ← CRÍTICO
- Impuesto Complementario Global (Pilar 2 OCDE): los 3 territorios cubiertos
- IRPF + IVA + IS + ISD + Autónomos forales: completo

**CCAA régimen común:**
- Todos los territorios con DLeg tributos cedidos + ley de medidas 2025
- Novedades 2025 destacadas: Murcia ITP→7.75%, Galicia Ley 5/2025, Madrid consolidado 2025, CyL dic 2025

**AEAT y Estatal:**
- Manual IVA **2025** (6.1 MB) ← actualizado
- Instrucciones Modelos 303/390 IVA 2025 + Modelo 190 retenciones
- Cuadros retenciones IRPF 2025 y 2026
- **RDL 2/2026** ← CRÍTICO para Renta 2025: imputación inmobiliaria, EV, DANA, SEPE
- **Ley 5/2025** ← deducción 340€ para SMI
- **REAF Panorama 2025** (7.5 MB) ← deducciones autonómicas completas
- Cap I-IV Tributación Autonómica 2025 (Ministerio Hacienda)
- Módulos EO 2026 (Orden HAC/1425/2025)

### 📅 Pendiente — disponible ~marzo/abril 2026
- Manual Práctico Renta 2025 Tomo 1 + Tomo 2 (AEAT) — aún no publicados
- Orden HAC Modelo 100 ejercicio 2025 — antes del 8 abril 2026

### ⚠️ Acción recomendada para Backend
**RE-INGESTA RAG necesaria** con los nuevos PDFs de sesiones 7-10 (39 documentos nuevos).
Prioridad de ingesta:
1. Reforma Fiscal 2025 forales (NF Gipuzkoa/Araba/Bizkaia) — afecta IS/IRPF/IVA
2. RDL 2/2026 y Ley 5/2025 — afectan respuestas sobre Renta 2025
3. Manual IVA 2025 + Modelos 303/390 — actualización anual IVA
4. REAF Panorama 2025 — deducciones autonómicas actualizadas

## Dependencias Pendientes
---
# Aquí los agentes registran cuando necesitan que otro complete algo primero
# Formato: [AGENT_ESPERANDO] espera a [AGENT_TRABAJANDO] para [TAREA]

## Conflictos Detectados
---
# Si un agente detecta que otro modificó el mismo archivo, lo registra aquí

## Instrucciones para Agentes
---
1. Al INICIAR una tarea: Añade línea con 🟡 IN_PROGRESS
2. Si estás BLOQUEADO esperando a otro: Añade línea con 🔴 BLOCKED
3. Al TERMINAR: Cambia tu línea a 🟢 DONE
4. Si necesitas review: Añade 📢 NEEDS_REVIEW
5. SIEMPRE haz `git pull` antes de empezar para ver cambios de otros agentes

[2026-02-22 00:00] [CRAWLER] [🟡 IN_PROGRESS] - Iniciando rastreo completo: Organización Bizkaia + descarga de docs Navarra, Gipuzkoa, Araba, CCAA régimen común y AEAT
[2026-02-23 10:00] [CRAWLER] [🟢 DONE] - Sesión 3 completada. +9 PDFs (Gipuzkoa Manual+NF3/2014+NF1/2025+DF33, Araba Manual+Instrucción, Bizkaia Instrucciones 1/2025+2/2024+2/2023). Total: 313 PDFs. Instrucciones actualizadas: nueva prioridad IS y Autónomos — iniciando descarga.
[2026-02-23 11:00] [CRAWLER] [🟢 DONE] - Sesion 4 completada. +5 PDFs (IS estatal Ley27/2014+RD634/2015, Autonomos Ley20/2007, Bizkaia IS NF11/2013+DF203/2013). Total: 318 PDFs. Pendiente: IS foral Gipuzkoa+Araba+Navarra (portales AJAX), RDL 13/2022, tablas RETA 2025. Backend: re-ingesta RAG recomendada para nuevos PDFs IS+Autonomos.
[2026-02-23 11:30] [CRAWLER] [🟢 DONE] - Sesion 4 ampliada. +3 adicionales (RDL13/2022 autonomos, Gipuzkoa IS Novedades+Modelo200). Total final: 321 PDFs. Pendiente sesion 5: IS foral Gipuzkoa(NF2/2014)+Araba(NF37/2013)+Navarra(LF26/2016) via navegador, RETA2025, Orden modulos EO.
[2026-02-23 12:00] [CRAWLER] [🟢 DONE] - Sesion 5 completada. +23 PDFs únicos (IS forales: Gipuzkoa NF2/2014+DF17/2015+OF252/2025, Araba NF37/2013+DF40/2014+Medidas2025, Navarra LF26/2016+LF22/2023+LF20/2024, Bizkaia Instrucciones IS 3+4/2023, Estatal OrdenHAC 1347+1425 modulos EO, Libro Normativa ene/mar 2025+CapII+CapIV, REAF 2024, RETA 2025). Total: 345 PDFs. IS foral 4 territorios COMPLETADO. Iniciando sesion 6: ITP-AJD autonómico + IP autonómico CCAA.
[2026-02-23 13:00] [CRAWLER] [🟢 DONE] - Sesion 6 completada. +9 PDFs (Cap I+III Tributacion Autonomica 2025, Orden HAC/242/2025 Modelos IRPF+IP, Tabla ITP CCAA, Cataluna DLeg1/2024 tributos cedidos COMPLETO, Andalucia Ley5/2021 actual, Baleares+Galicia consolidados 2024, Valencia Catedra Notarial 2025). Total: 354 PDFs. Cobertura ITP-AJD+IP+IRPF autonómico muy alta. Sesion completa — re-ingesta RAG recomendada para todos los nuevos PDFs.
[2026-02-25 09:00] [CRAWLER] [🟡 IN_PROGRESS] - Iniciando sesión 7 (rastreo completo). Objetivos: CCAA rezagadas (Aragón/Asturias/Cantabria/CyL/CLM/Extremadura/Murcia modificaciones 2023-2025), Galicia Leyes 10/2023+5/2024, Canarias ZEC+REF, Gipuzkoa IS NF2/2014 versión reciente + Reglamento IVA, Araba NF33/2013 actualizada, Estatal RD1624/1992 IVA.
[2026-02-25 16:00] [CRAWLER] [🟢 DONE] - Sesión 10 completada. +1 PDF. REAF Panorama Fiscalidad Autonómica y Foral 2025 (7.5 MB) — actualización del 2024. Deducciones autonómicas para Renta 2025: COBERTURA COMPLETA (Cap I-IV Tributación Autonómica 2025 + REAF 2025 + leyes 2025 de cada CCAA). Pendiente ~abril 2026: Manual Renta 2025 Tomo 2 Deducciones Autonómicas (AEAT, aún no publicado). Total: 394 PDFs.
[2026-02-25 15:00] [CRAWLER] [🟡 IN_PROGRESS] - Sesión 9: investigación campaña Renta 2025 (abr2026) — modelos 303/390/190, Manual IVA 2025, RDL 2/2026, Ley 5/2025.
[2026-02-25 15:30] [CRAWLER] [🟢 DONE] - Sesión 9 completada. +8 PDFs. AEAT: Manual IVA 2025(6.1MB)+Mod303 instrucciones+Mod390+Mod190 retenciones+Cuadros retenciones 2025+2026. BOE: RDL 2/2026(novedades IRPF 2025: imputación inmobiliaria 1,1% ampliada, EV/energía prorrogadas, desempleo no obliga)+Ley 5/2025(DA61 deducción 340€ SMI). Total: 393 PDFs. Pendiente ~marzo2026: Manual Renta 2025 + Orden HAC Modelo 100 ej.2025. ⚠️ IMPORTANTE para RAG: RDL 2/2026 es CRÍTICO para responder preguntas sobre Renta 2025.
[2026-02-25 14:00] [CRAWLER] [🟡 IN_PROGRESS] - Sesión 8: Araba NF 21/2025 (encontrada BOTHA 147) + CCAA rezagadas (Aragón/Asturias/Cantabria/CyL/Extremadura/Murcia leyes 2025).
[2026-02-25 14:30] [CRAWLER] [🟢 DONE] - Sesión 8 completada. +8 PDFs. Araba: NF21/2025(529KB)+DFN2/2025(390KB). CCAA: Aragón Ley3/2025 empresa familiar, Asturias Ley3/2025 mod.DLeg(dic2025), Cantabria Ley3/2024 medidas2025, CyL BOE-A-2025-27120(dic2025), Extremadura Ley1/2025, Murcia Ley3/2025 Presupuestos(ITP→7.75%). Total: 385 PDFs. Cobertura CCAA régimen común: COMPLETA. ⚠️ RE-INGESTA RAG: especialmente Murcia(ITP), CyL+Asturias(dic2025 no en consolidados).
[2026-02-25 13:00] [CRAWLER] [🟢 DONE] - Sesión 7 completada. +21 PDFs. REFORMA FISCAL 2025 FORALES: Gipuzkoa NF1/2025(integral may2025)+NF2+3(Pilar2)+4/2025+DFN1/2025, Araba NF3/2025(abr2025)+NF16(Pilar2)+17(IMIC)+26/2025, Bizkaia NF2/2025(abr2025)+NF_dic2025. CCAA: Galicia Ley10/2023+5/2024+5/2025(pub feb2026 MUY RECIENTE), Canarias REF Ley19/1994+RD1758/2007 ZEC, Madrid DLeg1/2010_2025+Ley5/2024, Andalucía Ley8/2025(Presupuestos2026)+Ley5/2021consolidado2026, Estatal RD1624/1992 ReglamentoIVA(pendiente histórico cerrado). Total: 375 PDFs. ⚠️ RE-INGESTA RAG CRÍTICA: normas reforma fiscal 2025 forales son fundamentales para consultas IS/IRPF/IVA actualizadas.
