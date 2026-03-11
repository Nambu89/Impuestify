---
name: test
description: Run backend pytest suite and frontend build check
disable-model-invocation: true
---

# /test - Ejecutar tests del proyecto

Ejecuta los tests del backend y reporta resultados:

1. Navega al directorio backend:
```bash
cd backend
```

2. Activa el entorno virtual:
```bash
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Ejecuta pytest con output verbose:
```bash
pytest tests/ -v --tb=short
```

4. Si hay fallos, analiza los errores y sugiere correcciones.

5. Si todos pasan, actualiza claude-progress.txt indicando que los tests están pasando.

6. Opcionalmente, ejecuta con cobertura:
```bash
pytest tests/ --cov=app --cov-report=term-missing
```
