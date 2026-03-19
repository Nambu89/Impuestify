---
name: Stripe subscription upgrade/downgrade per role change
description: CRITICO — cuando usuario cambia rol (e.g., particular→creator), validar subscription plan compatible
type: project
---

## Regla: Validar plan compatibility al cambiar roles

**Hecho:** Los 3 planes Stripe tienen restricciones por rol:
- **Particular** (5 EUR): solo rol "Particular" (Modelo 100 basico)
- **Creator** (49 EUR): rol "Creator" (Modelo 100 creator, IAE, IVA trimestral)
- **Autonomo** (39 EUR): rol "Autonomo" (Modelos 303/420/130, RETA, estimacion trimestral)

Si usuario tiene subscription plan Particular pero intenta cambiar su rol a "Creator" o "Autonomo", necesita upgrade.

## Accion pendiente (Sesion 13)

1. **Backend:** Añadir validacion en `DynamicFiscalForm` POST: si `roles_adicionales` incluye nuevo rol, validar que `subscription_plan` es compatible.
2. **UI:** Si plan incompatible → Modal "Necesitas upgrade a plan Creator/Autonomo" con boton a `/subscribe`.
3. **Redireccion post-upgrade:** Guardar `requested_role` en localStorage, post-pago redirigir a perfil fiscal con ese rol ya seleccionado.

## Why
Sin esta validacion, un usuario particular puede completar un perfil de autonomo pero luego no podra usar herramientas de autonomo porque su plan no tiene acceso.

## How to apply
Cuando usuario hace POST a actualizar su perfil fiscal (`update_fiscal_profile` endpoint) con nuevos `roles_adicionales`, verificar que `subscription_plan` lo permite. Si no, devolver 403 con mensaje "plan_incompatible" y detalles de upgrade requerido.

**Sesion:** 12, fecha 2026-03-17
**Prioridad:** CRITICA (proxima sesion 13)
