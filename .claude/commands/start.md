# /start - Iniciar sesión de desarrollo

Este comando se ejecuta al inicio de cada sesión de Claude Code.
Sigue estos pasos para ponerte al día:

1. **Ejecuta init.sh** para verificar el estado del entorno:
```bash
bash init.sh
```

2. **Lee el archivo de progreso** para saber qué se hizo en sesiones anteriores:
```bash
cat claude-progress.txt
```

3. **Revisa los últimos commits** para contexto reciente:
```bash
git log --oneline -10
```

4. **Lee README.md y CLAUDE.md** si es la primera vez o necesitas contexto completo.

5. **Verifica si hay tests fallando**:
```bash
cd backend && pytest tests/ -v --tb=short
```

6. **Reporta** al usuario el estado actual:
   - Rama actual
   - Últimos cambios
   - Estado de tests
   - Cualquier problema detectado

7. **Compacting strategy**: If context was compressed, re-read:
   - `CLAUDE.md` + relevant descendant (`backend/CLAUDE.md` or `frontend/CLAUDE.md`)
   - `memory/MEMORY.md` for project state
   - `agent-comms.md` for pending inter-agent tasks
   - `claude-progress.txt` for session history

8. **Pregunta** qué tarea quiere abordar en esta sesión.
