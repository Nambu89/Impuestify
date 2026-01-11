# /commit - Commit descriptivo con convención

Ejecuta los siguientes pasos para hacer un commit limpio:

1. Primero, muestra el estado actual de git:
```bash
git status
```

2. Añade todos los cambios al staging:
```bash
git add .
```

3. Genera un mensaje de commit siguiendo la convención del proyecto:
- `feat:` Nueva funcionalidad
- `fix:` Corrección de bug
- `docs:` Documentación
- `style:` Formato (no afecta código)
- `refactor:` Refactorización
- `test:` Tests
- `chore:` Mantenimiento

4. Haz el commit con mensaje descriptivo basado en los cambios reales.

5. Actualiza claude-progress.txt con un resumen de lo que se commiteó.

6. Muestra el log del commit recién creado:
```bash
git log -1 --stat
```
