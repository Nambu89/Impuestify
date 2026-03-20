---
name: Stripe subscription upgrade/downgrade per role change
description: COMPLETADO sesion 17 — validacion plan-role en SettingsPage con UpgradePlanModal
type: project
---

## Regla: Validar plan compatibility al cambiar roles — COMPLETADO

**Estado:** DONE (sesion 17, 2026-03-20, commit `8440917`)

Los 3 planes Stripe tienen restricciones por rol:
- **Particular** (5 EUR): asalariado, pensionista, desempleado
- **Creator** (49 EUR): + creador, influencer, youtuber, streamer
- **Autonomo** (39 EUR): sin restriccion (superset)

## Implementacion completa

1. **Backend:** `validate_plan_role_compatibility()` en `subscription_service.py` — devuelve 403 `plan_incompatible`
2. **Frontend hook:** `useFiscalProfile.ts` detecta 403 y set `planUpgradeNeeded` state
3. **UpgradePlanModal:** Componente completo con precio, descripcion, boton "Ver planes"
4. **SettingsPage:** Modal se renderiza al intentar cambiar a rol incompatible. onClose revierte form. onUpgrade guarda `requested_role` en localStorage + navega a `/subscribe?highlight=plan`
5. **Post-upgrade:** SettingsPage lee `requested_role` de localStorage al montar y muestra mensaje de confirmacion
6. **TaxGuidePage:** No necesita gate — wizard se adapta automaticamente por `userPlan`

**Why:** Sin validacion, usuario particular podia completar perfil de autonomo pero no acceder a herramientas.

**How to apply:** Ya implementado. Si se añaden nuevos planes o roles, actualizar `PLAN_ALLOWED_ROLES` en `subscription_service.py`.
