# Política de Retención de Datos

**Responsable**: Impuestify  
**Última actualización**: 3 de enero de 2026  
**Base legal**: RGPD Art. 5.1.e (Limitación de conservación)

---

## 1. Principio de Limitación

Los datos personales se conservan **únicamente durante el tiempo necesario** para los fines para los que fueron recogidos.

**Fundamento**: RGPD Art. 5.1.e

---

## 2. Plazos de Retención

### 2.1 Datos de Cuenta de Usuario

| Tipo de Dato | Plazo | Motivo | Eliminación |
|--------------|-------|--------|-------------|
| **Email** | Hasta baja voluntaria | Autenticación | Inmediata tras baja |
| **Contraseña (hash)** | Hasta baja voluntaria | Seguridad | Inmediata tras baja |
| **Nombre** | Hasta baja voluntaria | Personalización | Inmediata tras baja |
| **is_admin** | Hasta baja voluntaria | Control acceso | Inmediata tras baja |

**Eliminación automática**: Al eliminar cuenta, todos los datos asociados se eliminan en **máximo 24 horas**.

### 2.2 Conversaciones y Mensajes

| Tipo de Dato | Plazo | Motivo | Control Usuario |
|--------------|-------|--------|-----------------|
| **Historial de chat** | Hasta eliminación por usuario | Continuidad servicio | ✅ Usuario puede borrar |
| **Conversación individual** | Hasta eliminación por usuario | Acceso a historial | ✅ Borrar conversación |
| **Metadata conversación** | Hasta eliminación | Estadísticas | ✅ Se borra con conversación |

**Importante**: Las conversaciones se conservan indefinidamente **salvo que el usuario las elimine**.

### 2.3 Documentos PDF Subidos

| Tipo de Documento | Plazo | Motivo | Luego |
|-------------------|-------|--------|-------|
| **Nóminas** | **24 horas** | Procesamiento temporal | Eliminación automática |
| **Notificaciones AEAT** | **24 horas** | Procesamiento temporal | Eliminación automática |

**Proceso**:
1. Usuario sube PDF
2. Sistema extrae texto
3. Texto procesado por IA
4. **PDF original eliminado tras 24h**
5. Texto extraído queda en conversación (hasta que usuario la borre)

### 2.4 Logs de Seguridad

| Tipo de Log | Plazo | Motivo | Eliminación |
|-------------|-------|--------|-------------|
| **Access logs** | **90 días** | Auditoría seguridad | Automática |
| **Error logs** | **90 días** | Debugging | Automática |
| **Security events** | **90 días** | Compliance | Automática |
| **Rate limit violations** | **90 días** | Anti-abuso | Automática |

**Fundamento**: Equilibrio entre seguridad y minimización de datos.

### 2.5 Cache y Datos Temporales

| Tipo de Cache | Plazo (TTL) | Motivo | Renovación |
|---------------|-------------|--------|------------|
| **Redis conversation cache** | **1 hora** | Rendimiento | Automática si usuario activo |
| **Semantic cache (Upstash Vector)** | **24 horas** | Reducción costes OpenAI | No se renueva |
| **Session tokens** | **30 min (access) / 7 días (refresh)** | Seguridad | Automática |

**Eliminación**: Automática al expirar TTL.

---

## 3. Excepciones Legales

En ciertos casos, podemos conservar datos **más allá** de los plazos indicados:

### 3.1 Obligación Legal

Si existe **obligación legal** de conservar datos (ej: requerimiento judicial), los conservaremos el tiempo exigido.

**Base legal**: RGPD Art. 6.1.c

### 3.2 Litigios o Reclamaciones

Si hay **litigio pendiente**, los datos relacionados se conservan hasta resolución.

**Fundamento**: Defensa de derechos legales (RGPD Art. 17.3.e)

### 3.3 Datos Anonimizados

Los datos **completamente anonimizados** (sin identificación posible) pueden conservarse indefinidamente para **estadísticas**.

**No aplica RGPD**: Datos anonimizados no son personales.

---

## 4. Proceso de Eliminación

### 4.1 Eliminación por Usuario (Derecho de Supresión)

**Cómo ejercerlo**:
1. Configuración > Eliminar cuenta
2. Email a privacy@impuestify.com

**Plazo**: Máximo **1 mes** desde solicitud (RGPD Art. 12.3)

**Qué se elimina**:
- ✅ Cuenta de usuario (email, contraseña hash)
- ✅ Todas las conversaciones
- ✅ Documentos subidos (si aún existen)
- ✅ Preferencias de usuario
- ✅ Logs asociados (se anonimizan)

**Qué NO se elimina**:
- ❌ Logs anónimos de auditoría (sin identificación)
- ❌ Datos bajo obligación legal de conservar

### 4.2 Eliminación Automática

| Tipo | Cuándo | Método |
|------|--------|--------|
| **PDFs** | 24h tras upload | Cron job diario |
| **Cache** | Al expirar TTL | Redis/Vector DB automático |
| **Logs** | 90 días | Cron job semanal |
| **Tokens expirados** | 7 días | Limpieza automática |

### 4.3 Eliminación Segura

**Método**: Eliminación irreversible (DROP TABLE / DELETE sin backup).

**No aplicamos**:
- ❌ Soft delete (marcar como eliminado)
- ❌ Archivado long-term

---

## 5. Backups y Restauración

### 5.1 Backups de Base de Datos

**Frecuencia**: Diaria (Turso automático)  
**Retención**: **30 días**  
**Después**: Eliminación permanente

**Importante**: Si usuario solicita borrado, **también se elimina de backups** en siguiente ciclo (máximo 30 días).

**RGPD Art. 17.1**: Incluye "detener difusión", aplicable a backups.

### 5.2 Restauración

En caso de restauración desde backup:
- ✅ Se respetan políticas de retención actualizadas
- ✅ Datos que exceden plazo se eliminan inmediatamente

---

## 6. Notificaciones de Eliminación

### A los Usuarios

**Email de confirmación** cuando:
- Usuario elimina su cuenta
- Conversaciones se eliminan
- PDFs procesados se borran (opcional)

### Terceros (Encargados de Tratamiento)

Si compartimos datos con terceros (OpenAI, etc.) y usuario solicita borrado, **notificamos** a esos terceros (RGPD Art. 19).

**Proveedores notificados**:
- OpenAI: No almacena datos de API (política OpenAI)
- Turso/Upstash: Eliminación en sus sistemas

---

## 7. Revisión y Actualización

Esta política se revisa **trimestralmente** para:
- ✅ Asegurar plazos adecuados
- ✅ Cumplir nueva normativa
- ✅ Ajustar según feedback usuarios

**Próxima revisión**: Marzo 2026

---

## 8. Derecho a Solicitar Información

Puede solicitar información sobre:
- ✅ Qué datos conservamos sobre usted
- ✅ Cuándo serán eliminados
- ✅ Motivo de conservación

**Contacto**: privacy@impuestify.com

---

## 9. Contacto

**Dudas sobre retención**: privacy@impuestify.com  
**Solicitar eliminación**: privacy@impuestify.com  
**Reportar problema**: support@impuestify.com

---

**Impuestify se compromete a conservar sus datos solo el tiempo estrictamente necesario.**
