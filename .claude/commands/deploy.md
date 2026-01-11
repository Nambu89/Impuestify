# /deploy - Preparar y desplegar a Railway

Prepara el proyecto para deployment en Railway:

1. Primero, verifica que no hay cambios sin commitear:
```bash
git status
```

2. Si hay cambios, pregunta si debe hacer commit primero (usa /commit).

3. Ejecuta los tests para verificar que todo funciona:
```bash
cd backend && pytest tests/ -v --tb=short
```

4. Verifica que el frontend compila:
```bash
cd frontend && npm run build
```

5. Si todo está OK, push a la rama actual:
```bash
git push origin $(git branch --show-current)
```

6. Informa al usuario que Railway hará deploy automático desde el push.

7. Proporciona el enlace para monitorear el deploy:
   - Backend: https://railway.app (ver logs del servicio backend)
   - Frontend: https://railway.app (ver logs del servicio frontend)

8. Actualiza claude-progress.txt con fecha/hora del deploy.
