---
name: review
description: Code review of pending git changes with quality checklist
disable-model-invocation: true
---

# /review - Code review de los cambios actuales

Realiza un code review de los cambios pendientes:

1. **Muestra los archivos modificados**:
```bash
git diff --name-only
```

2. **Para cada archivo modificado**, revisa:
   - ¿El código sigue las convenciones del proyecto?
   - ¿Hay errores de lógica evidentes?
   - ¿Faltan tests para la nueva funcionalidad?
   - ¿Hay código duplicado que debería refactorizarse?
   - ¿Los imports están ordenados correctamente?
   - ¿Hay hardcoded values que deberían ser configuración?

3. **Muestra el diff completo** con contexto:
```bash
git diff
```

4. **Busca problemas comunes**:
   - `console.log` / `print` statements que quedaron
   - Comentarios TODO sin resolver
   - Variables no utilizadas
   - Imports no utilizados

5. **Genera un resumen** con:
   - ✅ Lo que está bien
   - ⚠️ Sugerencias de mejora
   - ❌ Problemas que deben corregirse antes del commit

6. Si todo está OK, sugiere usar `/commit` para guardar los cambios.
