# Manual de Usuario - Impuestify v3.0

---

## 1. Bienvenido a Impuestify

Impuestify es tu asistente fiscal inteligente para Espana. Te ayuda a entender tus impuestos, calcular tu IRPF, clasificar tus facturas, llevar tu contabilidad y preparar tus declaraciones fiscales, todo desde una sola plataforma web accesible en **impuestify.com**. Combina inteligencia artificial con mas de 460 documentos oficiales de legislacion tributaria para darte respuestas fiables, actualizadas y adaptadas a tu comunidad autonoma.

### Para quien es Impuestify

- **Particulares**: Asalariados, pensionistas o personas con ingresos del trabajo que quieren entender su declaracion de la renta, descubrir deducciones y saber si les sale a pagar o a devolver.
- **Creadores de contenido**: Influencers, YouTubers, streamers, bloggers y creadores digitales que necesitan gestionar el IVA por plataforma, el Modelo 349, la normativa DAC7 y sus obligaciones fiscales especificas.
- **Autonomos**: Trabajadores por cuenta propia que necesitan controlar sus facturas, calcular retenciones, presentar modelos trimestrales (303, 130) y llevar su contabilidad al dia.

### Lo que Impuestify NO es

> **Aviso importante**: Impuestify es una herramienta de orientacion fiscal. No sustituye el asesoramiento profesional de un abogado, asesor fiscal o gestor. Las respuestas y calculos son orientativos y se basan en la legislacion vigente, pero cada situacion personal puede tener matices que requieran atencion profesional. Consulta siempre con un experto antes de tomar decisiones fiscales importantes.

---

## 2. Primeros Pasos

### Crear tu cuenta

1. Entra en **impuestify.com** y pulsa **Registrarse**
2. Introduce tu correo electronico y elige una contrasena segura
3. Completa la verificacion de seguridad (un pequeno reto visual que confirma que eres una persona real)
4. Recibiras un correo de confirmacion en tu bandeja de entrada
5. Ya tienes tu cuenta creada

> **Consejo**: Activa la verificacion en dos pasos (2FA) desde Ajustes para mayor seguridad. Solo necesitas una app como Google Authenticator o Authy.

### Elegir tu plan

Impuestify ofrece tres planes adaptados a cada perfil:

| Plan | Precio | Ideal para |
|------|--------|------------|
| **Particular** | 5 EUR/mes | Asalariados y pensionistas |
| **Creator** | 49 EUR/mes | Influencers, YouTubers, streamers |
| **Autonomo** | 39 EUR/mes (IVA incluido) | Trabajadores por cuenta propia |

- Sin permanencia: cancela cuando quieras
- Pago seguro a traves de Stripe
- Puedes cambiar de plan en cualquier momento desde tu perfil

### Configurar tu perfil fiscal

Una vez registrado, te recomendamos completar tu perfil fiscal. Esta informacion permite que Impuestify personalice sus respuestas y calculos a tu situacion:

- **Comunidad autonoma**: Selecciona donde resides (las 17 CCAA + Ceuta, Melilla y territorios forales)
- **Situacion laboral**: Asalariado, autonomo, pensionista, desempleado...
- **Situacion familiar**: Numero de hijos, ascendientes a cargo, discapacidad
- **Datos economicos basicos**: Rendimientos del trabajo, ahorro, inmuebles

> **Consejo**: No necesitas rellenar todo de golpe. Puedes ir completando tu perfil poco a poco y Impuestify se ira adaptando.

---

## 3. Chat con el Asistente

El corazon de Impuestify es su asistente fiscal inteligente. Funciona como un chat: le haces preguntas en lenguaje natural y te responde de forma clara y fundamentada.

### Como hacer preguntas

Escribe tu duda fiscal como se la contarias a un amigo que sabe de impuestos. Algunos ejemplos:

- "Me sale a pagar 800 EUR en la renta, hay algo que pueda deducirme?"
- "Tengo dos pagadores este ano, estoy obligado a declarar?"
- "Soy autonomo en Canarias, que modelo trimestral tengo que presentar?"
- "Me ha llegado una notificacion de Hacienda, que significa?"
- "Cuanto me retienen de IRPF en la nomina?"

### Tipos de consultas que puedes hacer

- **IRPF y declaracion de la renta**: Tramos, tipos, deducciones estatales y autonomicas
- **IVA**: Tipos impositivos, modelos trimestrales, IGIC en Canarias, IPSI en Ceuta y Melilla
- **Deducciones**: Mas de 1.000 deducciones catalogadas por comunidad autonoma
- **Nominas**: Analisis de tu nomina, retenciones, pagos en especie
- **Notificaciones de la AEAT**: Interpretacion de requerimientos, propuestas de liquidacion y sanciones
- **Criptomonedas**: Tributacion, Modelos 720/721, metodo FIFO
- **Territorios forales**: Normativa especifica de Pais Vasco y Navarra

### Fuentes citadas

Cada respuesta del asistente se apoya en fuentes oficiales. Impuestify trabaja con una base de conocimiento de mas de 460 documentos de legislacion fiscal espanola: leyes, reales decretos, manuales de la AEAT, resoluciones del TEAC y normativa autonomica. Cuando el asistente cita una fuente, puedes confiar en que la informacion proviene de documentacion oficial.

### Selector de workspace en el chat

Si tienes un workspace con facturas subidas (ver seccion 7), puedes seleccionarlo en el chat para que el asistente tenga contexto de tus documentos fiscales. Asi sus respuestas seran aun mas personalizadas.

---

## 4. Guia Fiscal Paso a Paso

Accede desde el menu **Herramientas > Guia Fiscal** o directamente en `/guia-fiscal`.

### Que es

Un asistente guiado que te lleva de la mano para calcular tu declaracion de la renta. Segun tu perfil, el wizard tiene entre 7 y 8 pasos:

**Para particulares (7 pasos):**
1. Datos personales y situacion familiar
2. Rendimientos del trabajo (salario, nominas)
3. Rendimientos del ahorro (intereses, dividendos)
4. Inmuebles (vivienda habitual, alquileres, segundas residencias)
5. Situacion familiar (hijos, ascendientes, discapacidad)
6. Deducciones aplicables a tu comunidad autonoma
7. Resultado: tu estimacion de renta

**Para creadores y autonomos (8 pasos):**
Los mismos pasos anteriores mas un paso adicional sobre tu actividad economica: ingresos por actividad, gastos deducibles, regimen de IVA, plataformas (en el caso de creadores) y epigrafe del IAE.

### Que datos necesitas preparar

Antes de empezar, te recomendamos tener a mano:

- Tu ultima nomina o certificado de retenciones
- Importes de ahorro (intereses de cuentas, dividendos, venta de acciones)
- Datos de inmuebles (valor catastral, hipoteca, alquiler cobrado o pagado)
- Libro de familia o certificados de discapacidad, si aplica
- Si eres autonomo: resumen de ingresos y gastos del ejercicio

### La barra estimadora en tiempo real

Mientras rellenas los pasos del wizard, veras una barra en la parte inferior (en movil) o lateral (en escritorio) que te muestra en tiempo real una estimacion de tu resultado:

- **Verde** = Te sale a devolver (Hacienda te devuelve dinero)
- **Rojo** = Te sale a pagar

Esta barra se actualiza automaticamente cada vez que modificas un dato, sin necesidad de pulsar ningun boton.

### Como interpretar el resultado

Al finalizar el wizard, veras un resumen completo con:

- **Cuota a pagar o a devolver**: El importe final estimado
- **Tipo efectivo**: El porcentaje real de impuestos que pagas sobre tus ingresos
- **Deducciones aplicadas**: Listado de todas las deducciones que se han tenido en cuenta
- **Desglose por tramos**: Como se reparte tu base imponible entre los distintos tramos del IRPF

> **Consejo**: Puedes descargar el resultado como PDF o compartirlo con tu asesor directamente desde la pantalla de resultados.

---

## 5. Clasificador de Facturas

Accede desde **Herramientas > Clasificador Facturas** o en `/clasificador-facturas`.

### Como funciona

1. **Sube tu factura**: Arrastra o selecciona un archivo (PDF, foto JPG/PNG o imagen desde la camara del movil)
2. **Extraccion automatica**: La inteligencia artificial lee tu factura y extrae los datos clave: proveedor, fecha, base imponible, IVA, total, NIF
3. **Clasificacion contable**: El sistema asigna automaticamente la cuenta del Plan General Contable (PGC) que corresponde a esa factura
4. **Revision y confirmacion**: Revisa los datos extraidos y confirma o corrige lo que haga falta

### Si la IA se equivoca

La clasificacion automatica acierta en la gran mayoria de casos, pero a veces puede asignar una cuenta que no es la mas adecuada. En ese caso:

- Pulsa el boton **Reclasificar** junto a la factura
- Selecciona la cuenta correcta del desplegable
- Pulsa **Aplicar** para guardar el cambio

El sistema aprende de tus correcciones para mejorar en futuras clasificaciones.

> **Consejo**: Para mejores resultados, sube facturas bien enfocadas y con buena iluminacion si usas la camara del movil. Los PDFs suelen dar los mejores resultados.

---

## 6. Contabilidad

Accede desde **Herramientas > Contabilidad** o en `/contabilidad`.

Si has subido facturas con el clasificador, Impuestify genera automaticamente tus libros contables. Tienes cuatro pestanas:

### Libro Diario

Registro cronologico de todas las operaciones contables. Cada factura clasificada genera un asiento con su fecha, concepto, cuentas de cargo y abono, e importes.

### Libro Mayor

Vision por cuenta contable. Selecciona una cuenta del PGC y veras todos los movimientos asociados, con su saldo acumulado.

### Balance de Situacion

Foto fija de tu patrimonio en un momento dado: activos (lo que tienes), pasivos (lo que debes) y patrimonio neto (la diferencia).

### Cuenta de Perdidas y Ganancias

Resumen de ingresos y gastos del periodo. Te muestra el resultado economico de tu actividad.

### Exportar datos

Puedes descargar cada libro en formato CSV o Excel para presentarlo ante el Registro Mercantil o compartirlo con tu gestor. Usa el boton de descarga que aparece en la esquina superior derecha de cada seccion.

---

## 7. Workspaces

### Que es un workspace

Un workspace es como una carpeta virtual donde organizas todos tus documentos fiscales de un periodo o actividad. Por ejemplo, puedes tener un workspace para "Renta 2025" y otro para "Facturas Q1 2026".

### Crear y gestionar workspaces

1. Ve a **Workspaces** en el menu principal
2. Pulsa **Crear workspace** y dale un nombre descriptivo
3. Sube tus documentos (facturas, nominas, certificados) arrastrando o seleccionando archivos
4. El sistema clasifica automaticamente cada documento (factura emitida o recibida, por NIF)

### Dashboard visual

Cada workspace tiene un panel de control con:

- **KPIs principales**: Ingresos totales, gastos totales, IVA repercutido y soportado
- **Grafico de IVA trimestral**: Barras comparativas por trimestre
- **Evolucion mensual**: Linea de ingresos y gastos mes a mes
- **Distribucion por cuentas PGC**: Donde se concentra tu gasto
- **Top proveedores**: Los proveedores con mayor volumen
- **Facturas recientes**: Ultimas facturas procesadas

### Conectar workspace al chat

Cuando abres el chat, puedes seleccionar un workspace activo en el desplegable superior. Asi, el asistente fiscal tendra acceso a tus documentos y podra darte respuestas mucho mas concretas, como:

- "Cuanto IVA he soportado este trimestre?"
- "Cuales son mis gastos deducibles como autonomo?"
- "Que modelo 303 me toca presentar con estos datos?"

---

## 8. Calculadoras Publicas (sin registro)

Impuestify ofrece varias herramientas gratuitas que puedes usar sin necesidad de crear una cuenta.

### Sueldo Neto para Autonomos

**Accede en**: `/calculadora-neto`

Calcula tu sueldo neto mensual y anual como trabajador autonomo. Introduce tu facturacion bruta y el sistema calcula automaticamente:

- IVA/IGIC/IPSI segun tu territorio
- Retencion de IRPF
- Cuota de Seguridad Social (15 tramos segun ingresos, RDL 13/2022)
- Tu neto mensual y anual

Cubre **5 regimenes fiscales**: regimen comun (Madrid), Andalucia, Canarias (IGIC 7%), Melilla (IPSI 4% + deduccion 60%) y Pais Vasco (7 tramos forales).

### Calculadora de Retenciones IRPF

**Accede en**: `/calculadora-retenciones`

Calcula tu tipo de retencion de IRPF con el algoritmo oficial de la AEAT para 2026. Introduce tus datos salariales y familiares y obtendras el porcentaje exacto que deberian retenerte en nomina.

### Calculadora de Umbrales Contables

**Accede en**: `/calculadora-umbrales`

Te ayuda a saber si tu empresa debe llevar contabilidad bajo el PGC Normal o si puede usar el PGC para PYMES (simplificado). Introduce tu cifra de negocios, total de activo y numero de empleados.

### Modelos Obligatorios

**Accede en**: `/modelos-obligatorios`

Responde a la pregunta "que modelos fiscales tengo que presentar?". Segun tu perfil (autonomo, sociedad, creador), te muestra los modelos obligatorios con sus plazos de presentacion.

### Obligado a Declarar

**Accede en**: `/obligado-declarar`

Te dice si estas obligado a presentar la declaracion de la renta. Tiene en cuenta tus ingresos, numero de pagadores, rendimientos del ahorro y otras circunstancias que marca la Ley del IRPF (Art. 96).

### Checklist del Borrador

**Accede en**: `/checklist-borrador`

Lista de comprobacion para revisar tu borrador de la renta antes de presentarlo. Paso a paso, te aseguras de que no te dejas nada por revisar.

---

## 9. DefensIA - Defensor Fiscal

Accede desde **Herramientas > DefensIA** o en `/defensia`.

### Que es DefensIA

DefensIA es tu herramienta para defenderte frente a la Administracion tributaria. Si has recibido una propuesta de liquidacion, una sancion, un requerimiento de comprobacion o cualquier acto administrativo con el que no estas de acuerdo, DefensIA te ayuda a construir tu defensa.

### Que tributos cubre

- Impuesto sobre la Renta de las Personas Fisicas (IRPF)
- Impuesto sobre el Valor Anadido (IVA)
- Impuesto sobre Sucesiones y Donaciones (ISD)
- Impuesto sobre Transmisiones Patrimoniales (ITP)
- Plusvalia Municipal (IIVTNU)

### Procedimientos soportados

- Verificacion de datos
- Comprobacion limitada
- Procedimiento sancionador
- Recurso de reposicion
- Reclamacion economico-administrativa ante el TEAR (abreviado y general)

### Como funciona paso a paso

1. **Sube tus documentos**: Arrastra las notificaciones, resoluciones, alegaciones previas o cualquier documento relacionado con tu expediente
2. **Extraccion automatica**: El sistema analiza los documentos y extrae los datos clave: tipo de procedimiento, tributo afectado, importes, plazos, organo que dicta
3. **Escribe tu version**: Cuenta con tus palabras que ha pasado y por que crees que la Administracion se equivoca. DefensIA no arranca el analisis juridico hasta que escribas tu version
4. **Analisis y argumentos**: El sistema cruza tu caso con legislacion vigente, jurisprudencia y doctrina administrativa para generar argumentos verificados
5. **Escrito exportable**: Obtienes un borrador de recurso o reclamacion que puedes descargar y presentar

### Limites por plan

| Plan | Expedientes incluidos/mes | Coste expediente extra |
|------|---------------------------|------------------------|
| Particular | 1 | 15 EUR |
| Autonomo | 3 | 12 EUR |
| Creator | 5 | 10 EUR |

> **Aviso importante**: DefensIA genera borradores orientativos basados en legislacion vigente y jurisprudencia. Valida siempre el escrito con un abogado o asesor fiscal antes de presentarlo. El resultado no constituye asesoramiento juridico profesional.

---

## 10. Generador de Modelos en PDF

Impuestify puede generar borradores en PDF de los principales modelos fiscales para que los revises antes de presentarlos en la sede electronica de la AEAT.

### Modelos disponibles

- **Modelo 303**: Autoliquidacion trimestral del IVA
- **Modelo 130**: Pago fraccionado del IRPF (estimacion directa)
- **Modelo 308**: Solicitud de devolucion por recargo de equivalencia, art. 30 bis y otros
- **Modelo 720**: Declaracion de bienes y derechos en el extranjero
- **Modelo 721**: Declaracion de monedas virtuales en el extranjero
- **IPSI**: Para Ceuta y Melilla

### Variantes forales

- **Modelo 300**: Equivalente al 303 en Gipuzkoa
- **Modelo F69**: Equivalente al 303 en Navarra
- **Modelo 420**: IGIC en Canarias

### Como descargar tu borrador

1. Ve a **Declaraciones** en el menu principal
2. Selecciona el modelo que quieres generar
3. Revisa los datos precargados (si tienes workspace activo, muchos campos se rellenaran automaticamente)
4. Pulsa **Generar PDF**
5. Descarga el archivo y revisalo antes de presentarlo en la AEAT

> **Consejo**: Tambien puedes generar el PDF del Modelo 130 desde la calculadora del M130, accesible en la seccion de herramientas.

---

## 11. Suscripcion y Facturacion

### Planes y precios

| Plan | Precio | Que incluye |
|------|--------|-------------|
| **Particular** | 5 EUR/mes | Guia IRPF, analisis de nominas, deducciones basicas, chat fiscal |
| **Creator** | 49 EUR/mes | Todo lo anterior + IVA por plataforma, Modelo 349, DAC7, CNAE 60.39, perfiles multi-rol |
| **Autonomo** | 39 EUR/mes (IVA incl.) | Todo lo anterior + todos los modelos (303/130/131), cripto, workspace, calendario fiscal |

### Como suscribirte

1. Pulsa **Suscribirse** en el menu o en la pagina de inicio
2. Elige el plan que mejor se adapte a ti
3. Completa el pago a traves de Stripe (tarjeta de credito o debito)
4. Tu suscripcion se activa al instante

### Gestionar tu suscripcion

Desde **Ajustes** puedes:

- Ver tu plan actual y su estado
- Cambiar de plan (upgrade o downgrade)
- Acceder al portal de Stripe para gestionar metodos de pago
- Descargar tus facturas de suscripcion
- Cancelar tu suscripcion (sin permanencia, sin preguntas)

> **Consejo**: Si cancelas, mantendras el acceso hasta que finalice el periodo ya pagado.

---

## 12. Seguridad y Privacidad

Nos tomamos muy en serio la seguridad de tus datos fiscales.

### Proteccion de datos

- **Cifrado**: Todas las comunicaciones entre tu navegador e Impuestify estan cifradas con HTTPS/TLS
- **Datos en reposo**: Tu informacion se almacena de forma segura en servidores protegidos
- **Sin acceso a terceros**: No compartimos ni vendemos tus datos fiscales a nadie

### Autenticacion segura

- **Contrasena robusta**: Requisitos de seguridad en la creacion de contrasena
- **Verificacion en dos pasos (2FA)**: Anade una capa extra de seguridad con una app de autenticacion (Google Authenticator, Authy, etc.). Al activarla, recibes codigos de respaldo por si pierdes acceso a tu telefono
- **Proteccion anti-bots**: Verificacion con Cloudflare Turnstile en el registro e inicio de sesion

### Cumplimiento normativo

Impuestify cumple con:

- **RGPD** (Reglamento General de Proteccion de Datos)
- **LOPDGDD** (Ley Organica de Proteccion de Datos y Garantia de los Derechos Digitales)
- **AI Act** (Reglamento Europeo de Inteligencia Artificial)
- **LSSI-CE** (Ley de Servicios de la Sociedad de la Informacion)

### Tus derechos

Puedes ejercer tus derechos de acceso, rectificacion, supresion (derecho al olvido), portabilidad y oposicion en cualquier momento. Escribe a **privacy@impuestify.com** y atenderemos tu solicitud en un maximo de 30 dias.

> **Importante**: Si solicitas el borrado completo de tu cuenta, se eliminaran todos tus datos, conversaciones, facturas y documentos de forma irreversible.

---

## 13. Preguntas Frecuentes (FAQ)

**P: Necesito saber de impuestos para usar Impuestify?**
R: No. Impuestify esta disenado para personas sin conocimientos fiscales. Te explica todo en lenguaje sencillo y te guia paso a paso.

**P: Las respuestas del asistente son fiables?**
R: El asistente se apoya en mas de 460 documentos oficiales de legislacion fiscal espanola. Siempre cita sus fuentes. Aun asi, recuerda que es una herramienta de orientacion y no sustituye a un asesor profesional.

**P: Puedo usar Impuestify si vivo en Pais Vasco o Navarra?**
R: Si. Impuestify cubre los 17 comunidades autonomas, las 4 diputaciones forales (Alava, Bizkaia, Gipuzkoa, Navarra) y las ciudades autonomas de Ceuta y Melilla. Cada territorio tiene su normativa especifica integrada.

**P: Mis datos fiscales estan seguros?**
R: Si. Usamos cifrado en todas las comunicaciones, autenticacion de dos factores, proteccion anti-bots y cumplimos con el RGPD y la LOPDGDD. No compartimos tus datos con terceros.

**P: Puedo cancelar mi suscripcion en cualquier momento?**
R: Si. Sin permanencia ni penalizacion. Puedes cancelar desde Ajustes y mantendras el acceso hasta que termine tu periodo pagado.

**P: Que diferencia hay entre el plan Particular y el de Autonomo?**
R: El plan Particular cubre lo esencial para asalariados y pensionistas (IRPF, nominas, deducciones). El plan Autonomo anade todo lo que necesita un trabajador por cuenta propia: modelos trimestrales (303, 130), clasificacion de facturas, contabilidad completa, workspaces y calendario fiscal.

**P: Puedo subir facturas desde el movil?**
R: Si. La aplicacion funciona perfectamente en movil. Puedes subir facturas en PDF o hacer una foto directamente con la camara de tu telefono.

**P: Que pasa si el clasificador de facturas se equivoca?**
R: Puedes corregir la clasificacion manualmente en cualquier momento con el boton de reclasificacion. El sistema aprende de tus correcciones.

**P: Impuestify presenta mis declaraciones ante la AEAT?**
R: No. Impuestify genera borradores en PDF que tu puedes revisar y presentar a traves de la sede electronica de la AEAT (sede.agenciatributaria.gob.es). La presentacion telematica requiere certificado digital o Cl@ve PIN.

**P: Que es DefensIA?**
R: Es una herramienta que te ayuda a preparar recursos y reclamaciones frente a la Administracion tributaria. Analiza tus documentos, busca argumentos juridicos verificados y genera un borrador de escrito. Siempre debes validarlo con un profesional antes de presentarlo.

**P: Puedo compartir mis consultas con mi asesor?**
R: Si. Puedes generar un enlace compartido de cualquier conversacion (con tus datos personales anonimizados automaticamente) para enviarselo a tu asesor o gestor.

**P: Impuestify funciona sin conexion a internet?**
R: Impuestify es una aplicacion web progresiva (PWA). Puedes instalarla en tu movil como si fuera una app nativa, pero necesitas conexion a internet para usar el chat y las herramientas de calculo.

**P: Como contacto con soporte si tengo un problema?**
R: Puedes usar el widget de feedback dentro de la aplicacion (el icono en la esquina inferior) o escribir a support@impuestify.com.

**P: Que metodos de pago aceptais?**
R: Aceptamos tarjetas de credito y debito a traves de Stripe. El pago es mensual y se renueva automaticamente.

---

## 14. Contacto y Soporte

Si necesitas ayuda o tienes alguna duda, estamos aqui para ti:

- **Soporte general**: support@impuestify.com
- **Privacidad y datos personales**: privacy@impuestify.com
- **Feedback dentro de la app**: Pulsa el icono de feedback (esquina inferior de cualquier pantalla cuando has iniciado sesion) para reportar un problema, sugerir una mejora o dejar un comentario

> **Consejo**: Cuando reportes un problema, incluye una descripcion de lo que estabas haciendo y, si es posible, una captura de pantalla. Nos ayuda muchisimo a resolver tu incidencia mas rapido.

### Recursos adicionales

- **Web**: impuestify.com
- **Politica de privacidad**: impuestify.com/privacidad
- **Terminos de uso**: impuestify.com/terminos
- **Transparencia IA**: impuestify.com/transparencia-ia

---

*Impuestify v3.0 - Ultima actualizacion: abril 2026*

*Este manual se actualiza periodicamente para reflejar las nuevas funcionalidades de la plataforma.*
