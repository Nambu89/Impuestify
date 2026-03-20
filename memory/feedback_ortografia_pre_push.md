---
name: Verificacion ortografia (tildes) pre-push obligatoria
description: Regla: siempre validar que todos los strings visibles al usuario usan tildes correctas antes de hacer push
type: feedback
---

## Regla: ORTOGRAFIA PRE-PUSH OBLIGATORIA

Antes de hacer push a main o crear un PR, **SIEMPRE** verificar que TODOS los strings visibles al usuario (labels, placeholders, botones, mensajes, etc.) tienen tildes correctas.

## Palabras comunes con tildes (español)

- `autonomo` → `autónomo`
- `nomina` → `nómina`
- `declaracion` → `declaración`
- `estimacion` → `estimación`
- `metodo` → `método`
- `calculo` → `cálculo`
- `situacion` → `situación`
- `numero` → `número`
- `regimen` → `régimen`
- `imposicion` → `imposición`
- `deduccion` → `deducción`
- `cuota` → `cuota` (ya correcta)
- `impuesto` → `impuesto` (ya correcta)
- `contribuyente` → `contribuyente` (ya correcta)

## Why

Session 11 (2026-03-11) corregimos 27+ tildes faltantes en frontend (Bug 11). Usuarios reportan que la app se ve "rota" o "poco profesional" si hay faltas ortograficas visibles. Es especialmente critico para una app fiscal en español.

## How to apply

1. **Pre-commit:** Ejecutar busqueda visual o grep para detectar palabras comunes sin tildes en archivos modificados.
2. **Pre-push:** Revisar diff de archivos con strings (`.tsx`, `.ts`, `.py` con labels de UI).
3. **Regla global:** Si ves una falta de ortografia, corrigela ANTES de hacer commit.

**Anti-patron:** "Voy a dejar las tildes para despues" → termina olvidandose y llega a produccion.

**Sesion:** 12, fecha 2026-03-17
**Prioridad:** Alta (reputacion de marca)
