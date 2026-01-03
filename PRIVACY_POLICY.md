# Política de Privacidad - Impuestify

**Última actualización**: 3 de enero de 2026  
**Versión**: 1.0

---

## 1. Información del Responsable del Tratamiento

**Razón Social**: Impuestify  
**Domicilio**: [Pendiente completar]  
**Email**: privacy@impuestify.com  
**Contacto DPO**: No requerido (RGPD Art. 37)

---

## 2. Información que Recogemos

### 2.1 Datos Proporcionados por el Usuario

- **Email**: Para autenticación y comunicaciones
- **Contraseña**: Almacenada con hash seguro (bcrypt/argon2)
- **Nombre** (opcional): Para personalización
- **Consultas fiscales**: Conversaciones con el asistente IA
- **Documentos PDF**: Nóminas y notificaciones AEAT (procesamiento temporal)

###2.2 Datos Recopilados Automáticamente

- **Dirección IP**: Para seguridad y rate limiting
- **Cookies técnicas**: Para mantener sesión
- **Logs de acceso**: Timestamps, endpoints utilizados
- **Metadatos de conversación**: Duración, modelo IA usado

### 2.3 Datos que NO Recogemos

- ❌ Datos bancarios completos
- ❌ Números de identificación fiscal (DNI/NIE) salvo voluntario
- ❌ Contraseñas en texto plano
- ❌ Datos de navegación web fuera de la aplicación

---

## 3. Finalidad del Tratamiento

Procesamos sus datos personales para:

1. **Prestación del servicio** (Base legal: Ejecución de contrato - Art. 6.1.b RGPD)
   - Autenticación de usuarios
   - Gestión de conversaciones
   - Respuestas a consultas fiscales mediante IA

2. **Seguridad** (Base legal: Interés legítimo - Art. 6.1.f RGPD)
   - Prevención de fraude y abusos
   - Rate limiting y DDoS protection
   - Auditoría de seguridad

3. **Mejora del servicio** (Base legal: Consentimiento - Art. 6.1.a RGPD)
   - Análisis de calidad de respuestas IA
   - Estadísticas anónimas de uso

4. **Cumplimiento legal** (Base legal: Obligación legal - Art. 6.1.c RGPD)
   - Respuesta a requerimientos judiciales
   - Cumplimiento normativa fiscal

---

## 4. Base Legal del Tratamiento

Según el **RGPD Art. 6**, procesamos datos bajo:

- ✅ **Consentimiento** (Art. 6.1.a): Al crear cuenta y aceptar términos
- ✅ **Ejecución de contrato** (Art. 6.1.b): Prestación del servicio
- ✅ **Interés legítimo** (Art. 6.1.f): Seguridad y prevención fraude

Puede **retirar el consentimiento** en cualquier momento contactando privacy@impuestify.com.

---

## 5. Destinatarios de los Datos

Sus datos pueden ser compartidos con:

### 5.1 Proveedores de Servicios (Encargados de Tratamiento)

| Proveedor | Servicio | Ubicación | Garantías |
|-----------|----------|-----------|-----------|
| **OpenAI** | Modelo IA (GPT-4o-mini) | USA 🇺🇸 | Cláusulas contractuales estándar UE-USA |
| **Turso** | Base de datos | Global (Región UE disponible) | Servers en Frankfurt 🇩🇪 |
| **Upstash** | Cache Redis | Global (Región UE disponible) | Servers en Frankfurt 🇩🇪 |
| **Railway** | Hosting aplicación | USA/Global 🇺🇸 | TLS encryption, ISO 27001 |
| **Groq** | Moderación contenido (Llama Guard) | USA 🇺🇸 | Privacy-first, no training |

### 5.2 Transferencias Internacionales

⚠️ **Importante**: Algunos proveedores procesan datos fuera del Espacio Económico Europeo (EEE).

**Garantías aplicadas (RGPD Art. 44-49)**:
- ✅ Cláusulas Contractuales Estándar (SCC) de la Comisión Europea
- ✅ Evaluación de impacto de transferencia (TIA)
- ✅ Medidas adicionales de seguridad (cifrado end-to-end)

**OpenAI específicamente**:
- Data Processing Agreement (DPA) firmado
- No utiliza datos de API para training (política OpenAI)
- Certificaciones: SOC 2 Type II, ISO 27001

### 5.3 NO Compartimos Datos Con

- ❌ Empresas de marketing
- ❌ Brokers de datos
- ❌ Terceros para publicidad
- ❌ Redes sociales (salvo integración explícita)

---

## 6. Conservación de Datos

**Principio**: Los datos se conservan **solo el tiempo necesario** (RGPD Art. 5.1.e)

| Tipo de Dato | Plazo de Conservación | Motivo |
|--------------|----------------------|---------|
| **Cuenta de usuario** | Hasta eliminación por usuario | Prestación servicio |
| **Conversaciones** | Hasta eliminación por usuario | Historial del usuario |
| **PDFs subidos** | 24 horas tras procesamiento | Procesamiento temporal |
| **Logs de seguridad** | 90 días | Auditoría y seguridad |
| **Cache conversaciones** | 1 hora (TTL automático) | Rendimiento |
| **Semantic cache** | 24 horas | Optimización costes |

**Tras periodo de conservación**: Eliminación automática irreversible.

---

## 7. Derechos de los Usuarios (RGPD Art. 12-23)

Usted tiene derecho a:

### 7.1 Derecho de Acceso (Art. 15)
- ✅ Solicitar copia de sus datos personales
- ✅ Información sobre cómo se procesan
- **Cómo ejercerlo**: Email a privacy@impuestify.com

### 7.2 Derecho de Rectificación (Art. 16)
- ✅ Corregir datos inexactos
- ✅ Completar datos incompletos
- **Cómo ejercerlo**: Configuración de perfil o email

### 7.3 Derecho de Supresión "Derecho al Olvido" (Art. 17)
- ✅ Eliminar su cuenta y todos sus datos
- ✅ Excepciones si hay obligación legal de conservar
- **Cómo ejercerlo**: Configuración > Eliminar cuenta

### 7.4 Derecho de Portabilidad (Art. 20)
- ✅ Recibir sus datos en formato estructurado (JSON)
- ✅ Transferir a otro servicio
- **Cómo ejercerlo**: Configuración > Exportar datos

### 7.5 Derecho de Oposición (Art. 21)
- ✅ Oponerse al procesamiento por interés legítimo
- ✅ Oponerse a marketing directo
- **Cómo ejercerlo**: Email a privacy@impuestify.com

### 7.6 Derecho a la Limitación del Tratamiento (Art. 18)
- ✅ Solicitar suspensión del procesamiento
- **Cómo ejercerlo**: Email a privacy@impuestify.com

### 7.7 Derecho a No Ser Objeto de Decisiones Automatizadas (Art. 22)
- ✅ **Impuestify NO toma decisiones automatizadas** que produzcan efectos jurídicos
- ✅ La IA es **asistente**, no decide por usted
- ✅ Siempre hay supervisión humana recomendada

**Plazo de respuesta**: Máximo **1 mes** desde la solicitud (Art. 12.3)

---

## 8. Seguridad de los Datos

Implementamos medidas técnicas y organizativas (RGPD Art. 32):

### Técnicas
- ✅ Cifrado TLS/HTTPS en tránsito
- ✅ Cifrado en reposo (base de datos)
- ✅ Hashing seguro de contraseñas (Argon2/bcrypt)
- ✅ Rate limiting y DDoS protection
- ✅ Validación de inputs (anti SQL-injection, XSS)
- ✅ Moderación de contenido IA (Llama Guard 4)

### Organizativas
- ✅ Acceso basado en roles (RBAC)
- ✅ Logs de auditoría inmutables
- ✅ Revisiones periódicas de seguridad
- ✅ Política de respuesta a incidentes (SECURITY.md)

**Brecha de seguridad**: En caso de violación de datos, notificaremos a la AEPD en **72 horas** y a usuarios afectados **sin dilación indebida** (Art. 33-34)

---

## 9. Cookies y Tecnologías Similares

### 9.1 Cookies Esenciales (no requieren consentimiento)

| Cookie | Finalidad | Duración |
|--------|-----------|----------|
| `access_token` | Autenticación JWT | 30 minutos |
| `refresh_token` | Renovación sesión | 7 días |

### 9.2 Cookies Analíticas (requieren consentimiento)

Actualmente **NO utilizamos** cookies de analytics, marketing o terceros.

### 9.3 Su Derecho

Puede **configurar o eliminar cookies** desde su navegador.

---

## 10. Menores de Edad

**Impuestify NO está dirigido a menores de 16 años** (RGPD Art. 8).

Si detectamos datos de menores, los **eliminaremos inmediatamente**.

Padres/tutores: Si creen que un menor ha registrado cuenta, contacten privacy@impuestify.com.

---

## 11. Modificaciones a esta Política

Nos reservamos el derecho a actualizar esta política.

**Cambios sustanciales**: Notificación por email 30 días antes.  
**Cambios menores**: Publicación en web.

**Versión actual**: 1.0 (3 enero 2026)  
**Historial**: [Pendiente implementar]

---

## 12. Autoridad de Control

Tiene derecho a presentar reclamación ante:

**Agencia Española de Protección de Datos (AEPD)**
- Web: https://www.aepd.es
- Sede electrónica: https://sedeagpd.gob.es
- Teléfono: 901 100 099 / 912 663 517
- Dirección: C/ Jorge Juan, 6 - 28001 Madrid

---

## 13. Contacto

**Dudas sobre privacidad**: privacy@impuestify.com  
**Ejercicio de derechos**: privacy@impuestify.com  
**Soporte general**: support@impuestify.com

**Plazo de respuesta**: Máximo 1 mes (RGPD Art. 12.3)

---

## 14. Ley Aplicable

Esta política se rige por:
- **Reglamento (UE) 2016/679 (RGPD)**
- **Ley Orgánica 3/2018 de Protección de Datos (LOPDGDD) - España**
- **Ley 34/2002 de Servicios de la Sociedad de la Información (LSSI)**

**Jurisdicción**: Tribunales de España.

---

**Impuestify se compromete a proteger su privacidad y cumplir con la legislación vigente.**

Para cualquier duda, contacte: **privacy@impuestify.com**
