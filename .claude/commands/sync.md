---
name: sync
description: Sync with other agents via git pull and agent-comms channel
disable-model-invocation: true
---

# /sync - Sincronizar con otros agentes

Este comando sincroniza tu sesión con el trabajo de otros agentes.
Ejecútalo frecuentemente cuando trabajes en paralelo con otros Claude.

## Pasos:

1. **Pull de Git** para obtener cambios de otros agentes:
```bash
git pull --rebase
```

2. **Lee el log de comunicación** para ver qué están haciendo otros:
```bash
cat agent-comms.md
```

3. **Lee el progreso general**:
```bash
cat claude-progress.txt
```

4. **Reporta** al usuario:
   - ¿Hay conflictos de Git?
   - ¿Algún agente está bloqueado esperando algo?
   - ¿Hay tareas marcadas como NEEDS_REVIEW?
   - ¿Algún cambio reciente afecta tu trabajo actual?

5. **Sugiere** próximos pasos basándote en el estado de los otros agentes.