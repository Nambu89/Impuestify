# /files - Gestionar Archivos del Workspace

Ayuda al usuario a gestionar los archivos dentro de un workspace activo.

## Contexto

Los archivos en un workspace son documentos fiscales que el sistema procesa para:
- Extraer texto con PyMuPDF4LLM
- Clasificar automaticamente (nomina, factura, declaracion, otro)
- Proporcionar contexto al agente IA para consultas personalizadas

## Tipos de Archivos Soportados

| Tipo | Extensiones | Procesamiento |
|------|-------------|---------------|
| PDF | .pdf | PyMuPDF4LLM (Markdown) |
| Excel | .xlsx, .xls | Pendiente implementar |
| Imagen | .jpg, .png | Pendiente implementar (OCR) |

## Acciones Disponibles

Cuando el usuario ejecute `/files`, pregunta que workspace usar y que accion:

### 1. Listar archivos
```
GET /api/workspaces/{workspace_id}/files
```
Muestra:
- Nombre del archivo
- Tipo (nomina/factura/declaracion/otro)
- Estado de procesamiento (pending/completed/error)
- Fecha de subida

### 2. Subir archivo
```
POST /api/workspaces/{workspace_id}/files
Content-Type: multipart/form-data
- file: archivo PDF/Excel
- file_type: nomina|factura|declaracion|otro (opcional, auto-detectado)
```

### 3. Ver contenido extraido
Lee el texto extraido de un archivo procesado para verificar la extraccion.

### 4. Eliminar archivo
```
DELETE /api/workspaces/{workspace_id}/files/{file_id}
```

## Archivos Relevantes

**Backend:**
- `backend/app/routers/workspaces.py` - Endpoints de archivos
- `backend/app/services/file_processing_service.py` - Procesamiento
- `backend/app/utils/pdf_extractor.py` - Extraccion PDF
- `backend/app/services/payslip_extractor.py` - Parser de nominas

**Frontend:**
- `frontend/src/components/FileUploader.tsx` - Drag & drop upload
- `frontend/src/pages/WorkspacesPage.tsx` - Lista de archivos

## Clasificacion Automatica

El sistema detecta el tipo de archivo por nombre:
- `nomina`, `nómina`, `payslip`, `salario` → nomina
- `factura`, `invoice` → factura
- `modelo`, `declaracion`, `303`, `390` → declaracion
- Otros → otro

## Estados de Procesamiento

| Estado | Descripcion |
|--------|-------------|
| `pending` | Archivo subido, esperando procesamiento |
| `completed` | Texto extraido correctamente |
| `error` | Fallo en la extraccion |

## Ejemplo de Uso

```
Usuario: /files
Claude: Primero, selecciona un workspace:
        1. Mi Empresa 2025 (3 archivos)
        2. Personal 2025 (1 archivo)

Usuario: 1
Claude: Workspace "Mi Empresa 2025" seleccionado.
        Que deseas hacer?
        1. Ver archivos existentes
        2. Subir nuevo archivo
        3. Ver contenido extraido de un archivo
        4. Eliminar archivo

Usuario: 1
Claude: Archivos en "Mi Empresa 2025":

        | Archivo | Tipo | Estado | Fecha |
        |---------|------|--------|-------|
        | nomina_enero.pdf | nomina | completed | 2025-01-15 |
        | factura_001.pdf | factura | completed | 2025-01-16 |
        | modelo303_4t.pdf | declaracion | pending | 2025-01-17 |
```

## Tamano Maximo

- Limite por defecto: 10 MB por archivo
- Configurable en FileUploader.tsx (prop `maxSizeMB`)
