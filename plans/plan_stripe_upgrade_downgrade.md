# Plan: Stripe Plan Compatibility Validation (Upgrade/Downgrade)

> Fecha: 2026-03-19 | Prioridad: CRITICA | Sesion: 14
> Plan-checker: PASS (v2 — issues corregidos)

## Problema

Un usuario con plan Particular (5 EUR/mes) puede guardar un perfil fiscal de autonomo/creator sin restriccion. Despues, al preguntar en chat sobre temas de autonomo, se bloquea sin entender por que. La validacion existe en chat (content_restriction.py) pero NO en el endpoint de perfil fiscal.

## Objetivo

Validacion bidireccional: bloquear en el momento del cambio de perfil (no solo en chat), y ofrecer upgrade claro al usuario.

## Reglas de compatibilidad plan-rol

| Plan | Roles permitidos | situacion_laboral |
|------|-----------------|-------------------|
| particular | Particular, Pensionista, Desempleado | asalariado, pensionista, desempleado |
| creator | Creator, Particular | creador, influencer, youtuber, streamer, asalariado |
| autonomo | Autonomo, Creator, Particular | autonomo, profesional, empresarial, creador |
| null (sin suscripcion) | Igual que particular | asalariado, pensionista, desempleado |

**Regla clave:** Un plan superior incluye los inferiores. Autonomo > Creator > Particular. Plan null = particular.

## Tareas

### T1: Backend — Helper de compatibilidad plan-rol
- **Archivo:** `backend/app/services/subscription_service.py`
- **Accion:** Crear funcion `validate_plan_role_compatibility(plan_type: str | None, situacion_laboral: str, is_owner: bool = False) -> dict | None`
  - Retorna `None` si compatible
  - Retorna `{"required_plan": "autonomo", "current_plan": "particular"}` si incompatible
- **Mapeo:**
  - `None` o `particular` permite: `asalariado`, `pensionista`, `desempleado`, `null`/vacio
  - `creator` permite: lo anterior + `creador`, `influencer`, `youtuber`, `streamer`
  - `autonomo` permite: todo
  - `is_owner=True`: siempre retorna `None` (bypass)
- **Test unitario directo** de esta funcion incluido en T3

### T2: Backend — Validacion en update_fiscal_profile
- **Archivo:** `backend/app/routers/user_rights.py`
- **Accion:** En funcion `update_fiscal_profile()`:
  1. Si `situacion_laboral` viene en el request
  2. Usar `SubscriptionService.check_access(user_id)` para obtener `access.is_owner` y `access.plan_type` (patron establecido en `chat_stream.py`)
  3. Llamar `validate_plan_role_compatibility(access.plan_type, situacion, access.is_owner)`
  4. Si incompatible: devolver HTTP 403 con body:
     ```json
     {
       "detail": "plan_incompatible",
       "message": "Tu plan Particular no incluye el perfil de autonomo",
       "required_plan": "autonomo",
       "current_plan": "particular",
       "upgrade_url": "/subscribe"
     }
     ```
  5. Si compatible o si `situacion_laboral` no viene en request: continuar normalmente
- **IMPORTANTE:** No hacer query directo a tabla `users` — usar `check_access()` que resuelve plan real desde tabla `subscriptions`

### T3: Backend — Tests
- **Archivo:** `backend/tests/test_plan_compatibility.py` (NUEVO)
- **Escenarios (10 tests):**
  1. `validate_plan_role_compatibility("particular", "asalariado")` = None (unit test helper)
  2. `validate_plan_role_compatibility("particular", "autonomo")` = dict incompatible (unit test)
  3. `validate_plan_role_compatibility(None, "autonomo")` = dict incompatible (null plan = particular)
  4. Endpoint: Particular + asalariado = OK (200)
  5. Endpoint: Particular + autonomo = BLOCKED (403 con body correcto)
  6. Endpoint: Particular + creador = BLOCKED (403)
  7. Endpoint: Creator + creador = OK (200)
  8. Endpoint: Creator + autonomo = BLOCKED (403)
  9. Endpoint: Autonomo + autonomo = OK (200)
  10. Endpoint: Owner + autonomo (plan particular) = OK (200, bypass)

### T4: Frontend — Hook para manejar 403 plan_incompatible
- **Archivo:** `frontend/src/hooks/useFiscalProfile.ts`
- **Accion:** En la funcion `save()` / `updateProfile()`:
  1. Hacer `fetch` manual (no `apiRequest`) para el PUT `/api/users/me/fiscal-profile`
  2. Si response.status === 403: parsear body JSON completo
  3. Si `body.detail === "plan_incompatible"`: guardar en state `planUpgradeNeeded: { required_plan, current_plan, message }`
  4. NO mostrar error generico, devolver el objeto para que el componente muestre modal
- **Razon:** `useApi.apiRequest` destruye el body JSON en errores no-401, convirtiendo todo en string. Para preservar `required_plan` y `current_plan`, necesitamos acceso al body raw. Opcion: fetch manual con header Authorization del token actual.

### T5: Frontend — UpgradePlanModal component
- **Archivo:** `frontend/src/components/UpgradePlanModal.tsx` (NUEVO)
- **Props:** `isOpen`, `onClose`, `requiredPlan`, `currentPlan`
- **UI:**
  - Titulo: "Necesitas actualizar tu plan"
  - Texto: "El perfil de {rol} requiere el plan {required_plan} ({precio}/mes)"
  - Precios: particular=5, creator=49, autonomo=39
  - Boton primario: "Ver planes" → navega a `/subscribe?highlight={required_plan}`
  - Boton secundario: "Cancelar" → cierra modal, no guarda el perfil
- **Estilo:** Reusar patron de modales existentes (ShareReportModal como referencia)
- **Ortografia:** Tildes obligatorias en todos los strings visibles

### T6: Frontend — Integrar modal en SettingsPage
- **Archivo:** `frontend/src/pages/SettingsPage.tsx`
- **Accion:**
  1. Cuando `useFiscalProfile.save()` devuelve `planUpgradeNeeded`
  2. Mostrar `<UpgradePlanModal>` con datos del error
  3. Revertir el cambio de `situacion_laboral` en el form (no guardar estado incompatible)

### T7: Frontend — Gate en TaxGuidePage paso 1
- **Archivo:** `frontend/src/pages/TaxGuidePage.tsx`
- **Accion:** En step 1 (datos personales), cuando usuario selecciona situacion_laboral:
  1. Validacion optimista contra `planType` de `useSubscription()`
  2. Mapeo frontend (constante `PLAN_ALLOWED_ROLES`) sincronizado con T1 backend
  3. Si incompatible: mostrar UpgradePlanModal antes de avanzar al paso 2
  4. No bloquear la seleccion, solo bloquear el avance ("Siguiente")
- **NOTA:** La validacion frontend es optimista (UX rapida). La autoritativa es el backend (T2). Si se anade un nuevo plan/rol, actualizar AMBOS sitios. Documentar con comentario `// SYNC: backend/app/services/subscription_service.py:validate_plan_role_compatibility`

## Archivos a modificar (7)
1. `backend/app/services/subscription_service.py` — helper validate_plan_role_compatibility
2. `backend/app/routers/user_rights.py` — validacion 403 usando check_access()
3. `backend/tests/test_plan_compatibility.py` — 10 tests (NUEVO)
4. `frontend/src/hooks/useFiscalProfile.ts` — fetch manual para manejar 403 body
5. `frontend/src/components/UpgradePlanModal.tsx` — modal (NUEVO)
6. `frontend/src/pages/SettingsPage.tsx` — integrar modal
7. `frontend/src/pages/TaxGuidePage.tsx` — gate paso 1 con PLAN_ALLOWED_ROLES

## Dependencias
- T1 antes de T2, T2 antes de T3
- T4 y T5 pueden ser paralelos
- T6 y T7 dependen de T4+T5

## Criterio de verificacion
- `pytest tests/test_plan_compatibility.py -v` — 10 tests PASS
- `npm run build` — sin errores
- Manual: cambiar perfil a autonomo con plan particular → modal aparece

## Riesgos
- Usuarios existentes con perfil incompatible: NO migrar, solo validar cambios futuros
- Owner siempre bypass (no bloquear a fernando.prada@proton.me)
- Plan null (sin suscripcion): tratar como particular
- Suscripcion grace_period/past_due: seguir permitiendo segun plan_type (la validacion es sobre el tipo, no el estado de pago)
