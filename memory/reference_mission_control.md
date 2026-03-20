---
name: Mission Control — dashboard orquestacion agentes IA
description: Herramienta futura para monitorizar, testear y coordinar 6 agentes IA del proyecto (backend, frontend, python, docs, plan-checker, verifier)
type: reference
---

## Referencia: Mission Control

Herramienta futura (no existente aun, 2026-03-17) que permitira:

1. **Monitoreo de agentes:** Ver estado actual de cada agente (last activity, status, memory)
2. **Trigger tareas:** Invocar subagentes desde UI (backend agent, frontend agent, plan-checker, verifier)
3. **Ver resultados:** Output de ejecuciones anteriores, logs, errores
4. **Gestionar memoria:** Ver/editar archivos de memoria de cada agente
5. **Metricas:** Tests PASS/FAIL, PRs abiertos, issues blockeados

## Ubicacion esperada
- Frontend: `/admin/mission-control` (owner-only)
- Backend: Endpoint `/api/admin/mission-control/agents` (GET status, POST trigger task)

## Why
Con 6 agentes ejecutando tareas concurrentemente, necesitaremos una forma centralizada de orquestar, monitorizar y debuggear. Sin Mission Control, cada agente trabaja "a ciegas" sin saber que estan haciendo los otros.

## How to apply
Cuando necesites correr multiples agentes en paralelo (ej: backend agent + frontend agent + verifier en una sesion), usa Mission Control para: (1) ver que estan haciendo, (2) esperar a que terminen, (3) leer sus outputs sin necesidad de revisar 5 terminales diferentes.

**Sesion:** 12, fecha 2026-03-17
**Prioridad:** Baja (futura, cuando >3 agentes corran simultaneamente)
