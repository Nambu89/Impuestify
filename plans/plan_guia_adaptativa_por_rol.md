# Plan: Guia Fiscal Adaptativa por Rol

> **Feature**: La guia fiscal (/guia-fiscal) muestra pasos, campos y contenido diferente segun el plan del usuario (particular, creator, autonomo).
> **Estado**: PENDIENTE APROBACION
> **Fecha**: 2026-03-19

## Problema

Actualmente la guia fiscal es **identica para los 3 planes**:
- Un particular ve campos de actividad economica que no necesita
- Un creator no ve campos especificos de su actividad (plataformas, IVA intracomunitario, withholding tax)
- Un autonomo ve todo mezclado sin priorizacion

## Solucion

Configuracion de pasos (steps) por rol. Cada rol tiene su propio flujo de wizard con pasos y campos relevantes.

### Flujo por rol

#### PARTICULAR (5 EUR/mes) — 7 pasos simplificados
| Paso | Contenido |
|------|-----------|
| 0 | Datos personales (CCAA, edad, tributacion conjunta) |
| 1 | Rendimientos del trabajo (salario, SS, retenciones, pagas) |
| 2 | Ahorro e inversiones (intereses, dividendos, fondos, cripto) |
| 3 | Inmuebles y alquileres |
| 4 | Familia (descendientes, ascendientes, discapacidad, maternidad) |
| 5 | Deducciones y reducciones (planes pensiones, hipoteca, donativos, CCAA) |
| 6 | Resultado |

**Diferencia vs actual**: Se OCULTA la seccion "Actividad economica" del Step 1 (checkbox "Tengo ingresos por actividad economica" desaparece).

#### CREATOR (49 EUR/mes) — 8 pasos con seccion plataformas
| Paso | Contenido |
|------|-----------|
| 0 | Datos personales (CCAA, edad, tributacion conjunta) |
| 1 | Rendimientos del trabajo (si tiene empleo por cuenta ajena) |
| 2 | **Actividad como creador** (NUEVO contenido adaptado) |
| 3 | Ahorro e inversiones |
| 4 | Inmuebles |
| 5 | Familia |
| 6 | Deducciones y reducciones + CCAA |
| 7 | Resultado |

**Step 2 Creator incluye**:
- Ingresos por plataforma (YouTube/AdSense, Twitch, TikTok, Instagram, OnlyFans, Patreon, Substack, otros)
- Epigrafe IAE (selector: 8690 otros servicios, 9020 publicidad, 6010.1 comercio menor)
- Regimen de estimacion (directa simplificada por defecto)
- Gastos deducibles tipicos de creadores (equipo, software, coworking, transporte, formacion)
- IVA plataformas: resumen visual (Google Ireland = inversion sujeto pasivo, TikTok UK = no sujeta, etc.)
- Withholding tax W-8BEN (porcentaje retenido por plataforma USA)
- Modelo 349 (operaciones intracomunitarias — si factura a Google Ireland, Meta Ireland, etc.)
- Cuota autonomos (RETA)
- Pagos fraccionados (Modelo 130)

#### AUTONOMO (39 EUR/mes) — 8 pasos con actividad economica completa
| Paso | Contenido |
|------|-----------|
| 0 | Datos personales (CCAA, edad, tributacion conjunta) |
| 1 | Rendimientos del trabajo (si tiene empleo por cuenta ajena simultaneo) |
| 2 | **Actividad economica** (version completa actual) |
| 3 | Ahorro e inversiones |
| 4 | Inmuebles |
| 5 | Familia |
| 6 | Deducciones y reducciones + CCAA |
| 7 | Resultado |

**Step 2 Autonomo incluye** (lo que ya existe hoy):
- Ingresos actividad, gastos, cuota autonomos
- Amortizaciones, provisiones, otros gastos
- Regimen estimacion (directa simplificada/normal/objetiva)
- Inicio actividad, cliente unico
- Retenciones actividad, pagos fraccionados 130

## Tareas de implementacion

### Fase 1: Frontend — Configuracion de pasos por rol (4 archivos)

**T1. useTaxGuideProgress.ts — Step labels y configuracion por rol**
- Anadir parametro `userPlan: 'particular' | 'creator' | 'autonomo'` al hook
- Crear 3 configuraciones de STEP_LABELS:
  ```
  STEP_LABELS_PARTICULAR = ['Datos personales', 'Trabajo', 'Ahorro e inversiones', 'Inmuebles', 'Familia', 'Deducciones', 'Resultado']
  STEP_LABELS_CREATOR = ['Datos personales', 'Trabajo', 'Actividad como creador', 'Ahorro e inversiones', 'Inmuebles', 'Familia', 'Deducciones', 'Resultado']
  STEP_LABELS_AUTONOMO = ['Datos personales', 'Trabajo', 'Actividad economica', 'Ahorro e inversiones', 'Inmuebles', 'Familia', 'Deducciones', 'Resultado']
  ```
- Seleccionar labels segun `userPlan`
- Anadir al `TaxGuideData` nuevos campos creator:
  ```typescript
  // Creator-specific
  plataformas_ingresos: Record<string, number>  // { youtube: 5000, twitch: 2000, ... }
  epigrafe_iae: string  // '8690' | '9020' | '6010.1'
  tiene_ingresos_intracomunitarios: boolean
  ingresos_intracomunitarios: number  // para Modelo 349
  withholding_tax_pagado: number  // retenciones plataformas USA
  gastos_equipo: number
  gastos_software: number
  gastos_coworking: number
  gastos_transporte: number
  gastos_formacion: number
  ```
- Mantener `EMPTY_TAX_DATA` con defaults 0/false para nuevos campos

**T2. TaxGuidePage.tsx — Renderizado condicional por rol**
- Obtener `planType` del usuario via `useSubscription()` (NO useAuth — User no tiene plan_type)
- Pasar `userPlan` a `useTaxGuideProgress(userPlan)`
- En el switch de renderizado de steps, mapear step index al contenido correcto segun rol:
  - Particular: step 1 = trabajo SIN seccion actividad economica
  - Creator: step 2 = nuevo componente `StepCreadorActividad`
  - Autonomo: step 2 = seccion actividad economica actual (mover a step 2)
- Crear componente inline `StepCreadorActividad` con:
  - Grid de plataformas (icono + nombre + input EUR)
  - Selector epigrafe IAE con descripcion
  - Seccion gastos deducibles tipicos
  - Info card IVA intracomunitario
  - Info card withholding tax
  - Toggle Modelo 349
- Actualizar `canProceed` para validar step 2 creator (al menos 1 plataforma con ingresos > 0)
- Actualizar `getEffectiveIngresos()` para sumar plataformas creator

**T3. TaxGuidePage.css — Estilos step creador**
- Grid de plataformas (2 columnas desktop, 1 mobile)
- Icono + label + input inline
- Info cards (IVA, withholding) con borde izquierdo azul
- Badge IAE con tooltip

**T4. useIrpfEstimator.ts — Nuevos campos creator en IrpfEstimateInput**
- Anadir campos creator al interface `IrpfEstimateInput`
- Mapear `plataformas_ingresos` a `ingresos_actividad` (suma total) para el endpoint existente
- Pasar `gastos_*` individuales como `gastos_actividad` (suma total)
- Pasar `withholding_tax_pagado` como `retenciones_actividad`

### Fase 2: Backend — Soporte campos creator (2 archivos)

**T5. irpf_estimate.py — Nuevos campos en IRPFEstimateRequest**
- Anadir campos opcionales:
  ```python
  plataformas_ingresos: Optional[dict] = None  # {"youtube": 5000, ...}
  epigrafe_iae: Optional[str] = None
  tiene_ingresos_intracomunitarios: Optional[bool] = False
  ingresos_intracomunitarios: Optional[float] = 0
  withholding_tax_pagado: Optional[float] = 0
  gastos_equipo: Optional[float] = 0
  gastos_software: Optional[float] = 0
  gastos_coworking: Optional[float] = 0
  gastos_transporte: Optional[float] = 0
  gastos_formacion: Optional[float] = 0
  ```
- Si `plataformas_ingresos` presente, calcular `ingresos_actividad = sum(plataformas_ingresos.values())`
- Si `gastos_*` individuales presentes, calcular `gastos_actividad = sum(gastos_equipo + gastos_software + ...)`
- Mantener backward compatibility: campos existentes siguen funcionando igual

**T6. irpf_estimate.py — Enriquecer respuesta para creators**
- Anadir al response:
  ```python
  plataformas_desglose: Optional[dict] = None  # desglose por plataforma
  modelo_349_requerido: Optional[bool] = None  # si intracomunitarios > 0
  iae_recomendado: Optional[str] = None
  ```
- Logica: si `tiene_ingresos_intracomunitarios` y suma > 0, marcar `modelo_349_requerido = True`

### Fase 3: Resultado adaptativo (1 archivo)

**T7. TaxGuidePage.tsx Step Resultado — Contenido adaptativo**
- Particular: resultado estandar (cuota, deducciones, tipo medio)
- Creator: resultado + seccion "Obligaciones del creador":
  - Alerta Modelo 349 si intracomunitarios > 0
  - Alerta Modelo 130 trimestral
  - Info DAC7 (plataformas reportan a AEAT)
  - Resumen IVA por plataforma
  - Epigrafe IAE seleccionado
- Autonomo: resultado + seccion "Obligaciones del autonomo":
  - Modelo 130/131 trimestral
  - Modelo 303 IVA trimestral
  - Cuota RETA mensual

### Fase 4: Tests (2 archivos)

**T8. Tests backend — Nuevos campos creator**
- Test endpoint con `plataformas_ingresos` (suma correcta)
- Test con `gastos_*` individuales
- Test `modelo_349_requerido` logica
- Test backward compatibility (sin campos nuevos = funciona igual)
- **Minimo 10 tests nuevos**

**T9. Frontend build + verificacion visual**
- `npm run build` sin errores
- Verificar 3 flujos en dev: particular, creator, autonomo
- Verificar modo quick sigue funcionando para todos los roles

## Archivos a modificar

| Archivo | Cambio | Riesgo |
|---------|--------|--------|
| `frontend/src/hooks/useTaxGuideProgress.ts` | Nuevos campos + step labels por rol | BAJO |
| `frontend/src/pages/TaxGuidePage.tsx` | Renderizado condicional + StepCreadorActividad | MEDIO |
| `frontend/src/pages/TaxGuidePage.css` | Estilos creator step | BAJO |
| `frontend/src/hooks/useIrpfEstimator.ts` | Nuevos campos input | BAJO |
| `backend/app/routers/irpf_estimate.py` | Campos opcionales + logica creator | BAJO |
| `backend/tests/test_irpf_estimate_creator.py` | Tests nuevos | NUEVO |

## Restricciones

- **EXTEND, NEVER REFACTOR** el simulador IRPF (regla CLAUDE.md)
- Campos nuevos con default 0/null (backward compatible)
- No romper modo quick (2 pasos, identico para todos)
- No romper flujo existente de autonomo
- Ortografia obligatoria en todos los strings visibles

## Dependencias

- Ninguna — todo se construye sobre la infraestructura existente
- El research de necesidades de usuarios (en paralelo) puede anadir campos adicionales al Step Creator

## Criterios de aceptacion

1. Particular ve 7 pasos SIN actividad economica
2. Creator ve 8 pasos CON step "Actividad como creador" (plataformas, IAE, IVA info)
3. Autonomo ve 8 pasos CON step "Actividad economica" (version actual)
4. Modo quick funciona igual para los 3 roles
5. Backend acepta nuevos campos creator sin romper requests existentes
6. `npm run build` PASS
7. `pytest tests/ -v` PASS (10+ tests nuevos)
8. Resultado adaptativo muestra obligaciones segun rol
