---
name: workspace
description: Manage user workspaces (create, list, delete) via REST API
disable-model-invocation: true
---

# /workspace - Gestionar Workspaces del Usuario

Ayuda al usuario a gestionar sus espacios de trabajo (workspaces) para organizar documentos fiscales.

## Contexto

Los workspaces permiten a los usuarios:
- Organizar sus archivos fiscales (nominas, facturas, declaraciones)
- Tener contexto personalizado en las consultas al chat
- Calcular IVA, IRPF y proyecciones basadas en sus documentos

## Acciones Disponibles

Cuando el usuario ejecute `/workspace`, pregunta que accion desea realizar:

### 1. Listar workspaces
```
GET /api/workspaces
```
Muestra todos los workspaces del usuario con:
- Nombre e icono
- Numero de archivos
- Fecha de creacion

### 2. Crear workspace
```
POST /api/workspaces
Body: { "name": "Mi Empresa 2025", "description": "Facturas y nominas", "icon": "briefcase" }
```
Iconos disponibles: briefcase, home, building, user, folder

### 3. Ver detalles de workspace
```
GET /api/workspaces/{id}
```
Muestra:
- Informacion del workspace
- Lista de archivos con estado de procesamiento
- Resumen de datos extraidos

### 4. Eliminar workspace
```
DELETE /api/workspaces/{id}
```
Elimina el workspace y todos sus archivos asociados.

## Archivos Relevantes

**Backend:**
- `backend/app/routers/workspaces.py` - Endpoints CRUD
- `backend/app/services/workspace_service.py` - Logica de negocio
- `backend/app/agents/workspace_agent.py` - Agente IA para consultas

**Frontend:**
- `frontend/src/pages/WorkspacesPage.tsx` - Pagina de gestion
- `frontend/src/hooks/useWorkspaces.ts` - Hook de estado
- `frontend/src/components/WorkspaceSelector.tsx` - Selector en chat

## Flujo de Trabajo

1. Usuario crea workspace con `/workspace` o desde la UI
2. Sube archivos (PDFs de nominas, facturas, declaraciones)
3. Sistema extrae texto y datos automaticamente
4. En el chat, selecciona el workspace activo
5. Las consultas usan el contexto de los documentos

## Ejemplo de Uso

```
Usuario: /workspace
Claude: Que accion deseas realizar con tus workspaces?
        1. Listar mis workspaces
        2. Crear nuevo workspace
        3. Ver detalles de un workspace
        4. Eliminar workspace

Usuario: 2
Claude: Vamos a crear un nuevo workspace. Necesito:
        - Nombre (ej: "Mi Empresa 2025")
        - Descripcion (opcional)
        - Icono (briefcase/home/building/user/folder)
```
