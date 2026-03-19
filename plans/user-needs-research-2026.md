# Investigacion de Necesidades de Usuario — Impuestify 2026

> **Fecha**: 2026-03-19
> **Autor**: PM Coordinator (Research Agent)
> **Objetivo**: Identificar las necesidades, frustraciones y oportunidades para los 3 segmentos de Impuestify
> **Metodologia**: Web research en foros (Rankia, Trustpilot, OCU), prensa fiscal, blogs especializados, AEAT, Google Trends

---

## 1. PARTICULARES (Asalariados, Pensionistas)

### Top 10 Necesidades / Funcionalidades Mas Demandadas

| # | Necesidad | Frecuencia | Detalle |
|---|-----------|------------|---------|
| 1 | **Saber si estoy obligado a declarar** | MUY ALTA | Limites cambian cada ano (22.000 EUR 1 pagador, 15.876 EUR 2+ pagadores). Fuente constante de confusion. |
| 2 | **Descubrir deducciones autonomicas que no aparecen en el borrador** | MUY ALTA | El borrador de AEAT NUNCA incluye deducciones autonomicas. Perdida colectiva estimada: 9.000 millones EUR/ano. Deducciones por alquiler, guarderia, material escolar, deporte, nacimiento... varian por CCAA. |
| 3 | **Simulador rapido: "me sale a pagar o a devolver?"** | MUY ALTA | Los usuarios quieren una respuesta inmediata ANTES de confirmar el borrador. Google Trends muestra picos enormes en abril-junio. |
| 4 | **Entender si me conviene declaracion conjunta o individual** | ALTA | Matrimonios con hijos, un solo ingreso, pensionistas. Necesitan comparar 4 escenarios. |
| 5 | **Deduccion por alquiler de vivienda habitual** | ALTA | Confusion masiva: deduccion estatal (solo contratos pre-2015) vs. autonomica (contratos nuevos, varia por CCAA). Muchos inquilinos pierden >1.000 EUR/ano por desconocimiento. Madrid permite deducir hasta 1.237 EUR para <40 anos. |
| 6 | **Como declarar ingresos de segunda actividad** (Wallapop, alquiler vacacional, clases particulares) | ALTA | Economia de plataformas en auge. DAC7 obliga a plataformas a reportar. Muchos no saben que deben declarar. |
| 7 | **Verificar que el borrador no tiene errores** | ALTA | +70% de borradores contienen errores segun expertos. Datos de vivienda, situacion familiar, inmuebles no habituales mal cargados. |
| 8 | **Deducciones por eficiencia energetica y vehiculo electrico** | MEDIA-ALTA | Prorrogadas para ejercicio 2025. Placas solares, puntos de recarga, rehabilitacion energetica. Poco conocidas. |
| 9 | **Calendario y recordatorios de plazos** | MEDIA | Campana 2025: 8 abril - 30 junio 2026. Muchos lo dejan para ultimo momento. |
| 10 | **Explicacion en lenguaje simple de casillas y conceptos** | MEDIA | "Base imponible", "minimo personal y familiar", "cuota integra"... son opacos para el ciudadano medio. |

### Top 5 Frustraciones con Herramientas Actuales

| # | Frustracion | Herramienta | Detalle |
|---|-------------|-------------|---------|
| 1 | **Plan gratuito es solo simulador, no presenta** | TaxDown | La mayor queja en Trustpilot. El usuario hace todo el proceso y al final descubre que necesita pagar para presentar. Se percibe como "gancho enganoso". |
| 2 | **Cobros inesperados y dificultad para cancelar** | TaxDown | Usuarios reportan cobros dobles, upgrade forzado ("tu situacion es mas complicada, paga 3x mas"), y boton de cancelacion que "no aparece en la web". Reclamaciones en OCU. |
| 3 | **Renta Web de AEAT es hostil e incomprensible** | AEAT | Interfaz anticuada, casillas numericas sin explicacion, navegacion confusa, errores tecnicos frecuentes (Error 611, Error 527). No hay guia paso a paso. |
| 4 | **Errores en declaraciones presentadas por asesores** | TaxDown | Un usuario reporta 9 borradores distintos con fallos, aun trabajando en rectificativa. Otro fue informado erroneamente de que no estaba obligado a declarar. |
| 5 | **Atencion al cliente lenta o inexistente** | TaxDown, Declarando | Tiempos de espera largos, cambio constante de agente, hilos cerrados sin resolucion. En Declarando: "no contestan emails ni chat". |

### Quick Wins para Impuestify (Particulares)

1. **Detector de deducciones autonomicas olvidadas** — Cruzar CCAA del usuario con las ~600 deducciones del motor. ALTO IMPACTO, ya implementado parcialmente en guia fiscal.
2. **Comparador conjunta vs individual en 1 click** — Ya tenemos `compare_joint_individual`. Hacerlo mas visible y accesible.
3. **Checklist pre-confirmacion del borrador** — "Antes de confirmar tu borrador, verifica estos 10 puntos". Contenido SEO + funcionalidad en la guia.
4. **Explicador de casillas en lenguaje llano** — El RAG con 2.064 casillas ya lo permite. Exponerlo como feature visible.
5. **Alerta "tienes derecho a deduccion por alquiler"** — Si el usuario indica que vive de alquiler, mostrar automaticamente la deduccion de su CCAA.

---

## 2. AUTONOMOS (Freelancers, Profesionales)

### Top 10 Necesidades / Funcionalidades Mas Demandadas

| # | Necesidad | Frecuencia | Detalle |
|---|-----------|------------|---------|
| 1 | **Calculadora de cuota trimestral (Modelo 130/131)** | MUY ALTA | Los autonomos necesitan saber CUANTO van a pagar cada trimestre ANTES del vencimiento. Quieren meter ingresos y gastos y ver el resultado del 130. |
| 2 | **Control de gastos deducibles con claridad** | MUY ALTA | "Puedo deducir el movil? Y el coche? Y el coworking?" — Preguntas recurrentes. Necesitan una guia clara por tipo de gasto con porcentaje deducible. |
| 3 | **Calendario fiscal con recordatorios automaticos** | MUY ALTA | Enero es critico (Q4 + anuales). 4 trimestres + renta + modelos anuales (390, 347, 349). El 90% siente que la burocracia ha aumentado. |
| 4 | **Calculadora de sueldo neto real** | ALTA | "Si facturo 3.000 EUR/mes, cuanto me queda realmente?" Descontando IRPF, IVA, cuota SS (que ahora va por ingresos reales). Muy buscado en Google. |
| 5 | **Simulador de Renta anual para autonomos** | ALTA | Mas complejo que particulares: rendimientos de actividad, gastos, amortizaciones, pagos fraccionados ya realizados. |
| 6 | **Gestion de IVA (Modelo 303)** | ALTA | IVA repercutido vs soportado. Confusion con IVA intracomunitario, exenciones (sanitarios, educacion), y IGIC/IPSI en territorios especiales. |
| 7 | **Guia de gastos de dificil justificacion (7%)** | MEDIA-ALTA | Deduccion del 7% sobre rendimiento neto (max 2.000 EUR). Muchos autonomos no la conocen o no la aplican correctamente. |
| 8 | **Adaptacion a VeriFactu / factura electronica** | MEDIA-ALTA | Obligatorio desde julio 2027 para autonomos (aplazado de 2026). Multas de hasta 50.000 EUR. Genera ansiedad e incertidumbre. |
| 9 | **Dietas y gastos de viaje deducibles** | MEDIA | Limites: 53,34 EUR/dia en Espana, 91,35 EUR/dia extranjero. Poco conocidos. |
| 10 | **Estimacion directa simplificada vs normal** | MEDIA | Cuando conviene cada regimen. Umbrales, ventajas de cada uno. |

### Top 5 Frustraciones con Herramientas Actuales

| # | Frustracion | Herramienta | Detalle |
|---|-------------|-------------|---------|
| 1 | **200 horas/ano en burocracia fiscal** | General | Segun ATA (Federacion de Autonomos), cada autonomo dedica 4h/semana a tramites. Coste medio: 3.000 EUR/ano. El 90% dice que ha empeorado. |
| 2 | **Gestorias generalistas no entienden profesiones digitales** | Gestorias tradicionales | Gestores que no saben que es un ingreso de AdSense, como funciona Stripe, o que epigrafe IAE usar para un consultor SaaS. |
| 3 | **Software de facturacion caro y fragmentado** | Holded, Quipu | Holded: precios accesibles al inicio pero escalan rapido al anadir modulos. Quipu: sin 2FA (riesgo de seguridad). Ambos: soporte lento en picos. Ninguno integra bien la parte fiscal con la contable. |
| 4 | **Atencion al cliente deficiente en picos** | Declarando, Holded | Declarando: hasta 4 meses para activar servicios, emails sin responder, chat que "no funciona NUNCA". Holded: 2+ semanas sin respuesta. |
| 5 | **No saber cuanto reservar para impuestos** | General | El autonomo cobra bruto y no sabe cuanto apartar para IVA + IRPF + SS. Sorpresas desagradables cada trimestre. |

### Quick Wins para Impuestify (Autonomos)

1. **"Cuanto me queda limpio" — Calculadora de sueldo neto** — Input: facturacion bruta mensual. Output: neto despues de IVA, IRPF, SS. Viral en redes.
2. **Estimador trimestral Modelo 130** — Ya tenemos el motor IRPF. Adaptar para calculo trimestral con ingresos/gastos acumulados.
3. **Guia interactiva de gastos deducibles** — Por tipo de actividad: "Eres desarrollador? Estos son tus gastos deducibles". Con porcentajes y limites.
4. **Alerta VeriFactu** — Informar del estado actual (aplazado a julio 2027), que necesitan, y cuando actuar. Genera confianza.
5. **Dashboard fiscal trimestral** — Vista: "Q1 2026: Ingresos X, Gastos Y, IVA a pagar Z, IRPF estimado W. Proximo vencimiento: 20 abril."

---

## 3. CREADORES DE CONTENIDO (YouTubers, Streamers, Influencers)

### Top 10 Necesidades / Funcionalidades Mas Demandadas

| # | Necesidad | Frecuencia | Detalle |
|---|-----------|------------|---------|
| 1 | **"Tengo que darme de alta como autonomo?"** | MUY ALTA | Desde el primer euro de ingreso, es obligatorio. Pero la mayoria de creadores jovenes no lo saben. Multas del 50-150% del impuesto no pagado. |
| 2 | **Que epigrafe IAE elegir** | MUY ALTA | No existe epigrafe especifico para influencers. Opciones: 961.1 (produccion cinematografica), 844 (publicidad), 769.9 (telecomunicaciones). Cada uno tiene implicaciones distintas en IVA e IRPF. |
| 3 | **Como facturar a plataformas extranjeras (Google Ireland, Amazon Luxembourg)** | MUY ALTA | Operaciones intracomunitarias: alta en ROI, inversion de sujeto pasivo, factura sin IVA pero con autoliquidacion. Modelo 349 obligatorio. |
| 4 | **IVA por plataforma: cuando aplico y cuando no** | MUY ALTA | YouTube/Twitch (pagos desde Irlanda/Luxemburgo): sin IVA espanol, con Modelo 349. Sponsors espanoles: con IVA. Patrocinios internacionales: depende del pais. |
| 5 | **DAC7: que sabe Hacienda de mis ingresos** | ALTA | Desde 2023, las plataformas reportan a AEAT. YouTube, Twitch, TikTok, OnlyFans, Patreon, Etsy, Fiverr... todas reportan. Multa por omision: hasta 2% de ingresos ocultos (min 300 EUR, max 20.000 EUR). |
| 6 | **Withholding tax de YouTube/AdSense** | ALTA | Google retiene hasta 30% sobre ingresos de EEUU si no se envian datos fiscales. Convenio doble imposicion Espana-EEUU reduce a 0-15%. Muchos no saben que pueden reclamarlo. |
| 7 | **Cuanto tengo que pagar de impuestos en total** | ALTA | Calculadora que integre: IRPF + IVA + SS = "De los 5.000 EUR que ganaste en YouTube, te quedan X limpios." |
| 8 | **Multi-plataforma y multi-ingreso** | MEDIA-ALTA | Un creador tipico tiene ingresos de YouTube + Twitch + sponsors + merch + cursos + afiliados. Cada fuente tributa diferente. |
| 9 | **Gastos deducibles especificos de creadores** | MEDIA-ALTA | Equipo (camara, micro, PC, iluminacion), software (Adobe, OBS), internet, parte proporcional de vivienda, viajes a eventos. |
| 10 | **Residencia fiscal y mudanza a Andorra/Portugal** | MEDIA | Tema recurrente en comunidad de creadores. Implicaciones del exit tax, convenios de doble imposicion, minimo de 183 dias. |

### Top 5 Frustraciones con Herramientas Actuales

| # | Frustracion | Herramienta | Detalle |
|---|-------------|-------------|---------|
| 1 | **Gestorias tradicionales no entienden el sector** | Gestorias generalistas | No saben que es Twitch, confunden ingresos de plataformas, eligen epigrafe IAE incorrecto, no tramitan alta en ROI, no presentan Modelo 349. Consecuencia: sanciones. |
| 2 | **OnlyTax es cara (70+ EUR/mes + IVA)** | OnlyTax | La unica gestoria especializada en creadores cobra desde 84,70 EUR/mes con IVA. Para creadores pequenos (<1.000 EUR/mes ingresos), es un coste proporcionalmente alto. |
| 3 | **No existe herramienta self-service para creadores** | Mercado | No hay ninguna app que permita a un creador gestionar su fiscalidad sin un gestor humano. Todo requiere asesoria presencial o telefonica. |
| 4 | **Confusion con operaciones intracomunitarias** | General | ROI, Modelo 349, inversion de sujeto pasivo, autoliquidacion de IVA... es un laberinto para alguien de 22 anos que hace videos en TikTok. |
| 5 | **Miedo a Hacienda sin saber que hacer** | General | La AEAT ha declarado que los influencers son "objetivo prioritario" en Plan Tributario 2026. Muchos creadores tienen ingresos sin declarar de anos anteriores y no saben como regularizar. |

### Quick Wins para Impuestify (Creadores)

1. **"Soy creador, que tengo que hacer?" — Wizard de alta** — Guia paso a paso: epigrafe IAE, alta SS, ROI, primer trimestre. Diferenciador enorme vs gestorias.
2. **Calculadora IVA por plataforma** — Input: plataforma + pais de la empresa. Output: aplica IVA si/no, necesitas Modelo 349 si/no, necesitas ROI si/no.
3. **Estimador fiscal para creadores** — "Cuanto ganas al mes en YouTube? Y en sponsors? Asi quedan tus impuestos."
4. **Guia DAC7 + regularizacion** — "Hacienda ya sabe cuanto ganas. Asi puedes ponerte al dia sin sancion maxima." Contenido que genera confianza y capta leads.
5. **Checklist fiscal del creador** — PDF descargable / interactivo con todos los pasos: alta, trimestres, renta, Modelo 349, DAC7.

---

## Analisis Transversal: Oportunidades Estrategicas

### Patrones comunes en los 3 segmentos

1. **Desconocimiento de deducciones** — Particulares no aplican autonomicas, autonomos no conocen el 7% de gastos de dificil justificacion, creadores no saben que pueden deducir equipo.
2. **Miedo a Hacienda + paralisis** — Los 3 segmentos tienen miedo a "hacerlo mal". Quieren una herramienta que les de seguridad y confianza.
3. **Frustracion con soporte humano** — Todas las herramientas fallan en atencion al cliente. Impuestify con IA 24/7 es un diferenciador real.
4. **Necesidad de simulacion pre-declaracion** — Todos quieren saber "cuanto me sale" ANTES de comprometerse.
5. **Lenguaje fiscal incomprensible** — Los 3 piden explicaciones en lenguaje llano, no jerga tributaria.

### Diferenciadores competitivos de Impuestify

| Diferenciador | TaxDown | Declarando | OnlyTax | Holded/Quipu | **Impuestify** |
|---------------|---------|------------|---------|--------------|----------------|
| Deducciones autonomicas (17 CCAA + forales) | Parcial | No | No | No | **600+ deducciones, todos los territorios** |
| Simulador IRPF sin registro | No (requiere registro) | No | No | No | **Si, gratuito** |
| IA fiscal 24/7 | No | No | No | No | **Si, RAG + multi-agente** |
| Creadores de contenido | No | No | Si (caro) | No | **Si (plan 49 EUR)** |
| Comparador conjunta/individual | Si | No | No | No | **Si, 4 escenarios** |
| Forales (Pais Vasco + Navarra) | Parcial | No | No | No | **Si, 4 territorios** |
| Precio | 35-65 EUR/declaracion | 60-120 EUR/mes | 70+ EUR/mes | 40-150 EUR/mes | **5-49 EUR/mes** |

### Funcionalidades Prioritarias (Impacto vs Esfuerzo)

```
                    ALTO IMPACTO
                        |
   Calculadora neto     |  Detector deducciones
   autonomo             |  autonomicas
                        |
   Wizard creadores     |  Comparador conjunta
                        |  (ya existe, mejorar UX)
                        |
   Estimador trimestral |  Checklist borrador
   Mod 130              |
 ----ALTO ESFUERZO------+------BAJO ESFUERZO----
                        |
   Dashboard fiscal     |  Alerta deduccion
   trimestral           |  alquiler
                        |
   Calculadora IVA      |  Guia DAC7
   por plataforma       |  (contenido)
                        |
                        |  Explicador casillas
                    BAJO IMPACTO
```

### Contenido SEO de Alto Volumen de Busqueda

Basado en los patrones de busqueda detectados:

1. "Estoy obligado a hacer la declaracion de la renta 2026" — **landing SEO dedicada**
2. "Deducciones alquiler [CCAA] 2026" — **17 landing pages territoriales** (ya tenemos infraestructura)
3. "Cuanto paga un autonomo de impuestos" — **calculadora + landing**
4. "Impuestos influencer Espana" — **guia completa + calculadora**
5. "Gastos deducibles autonomo 2026" — **guia interactiva**
6. "Simulador renta 2026 gratis" — **nuestra guia fiscal como funnel**
7. "Declaracion conjunta o individual que me conviene" — **comparador como landing**
8. "DAC7 Espana que es" — **contenido educativo para creadores**
9. "Modelo 130 como se calcula" — **calculadora trimestral**
10. "Errores borrador renta" — **checklist interactivo**

---

## Fuentes

### Prensa y blogs fiscales
- [El Espanol — Dudas frecuentes declaracion renta segun IA](https://www.elespanol.com/alicante/vivir/20260311/dudas-frecuentes-declaracion-renta-ia-hacienda-complicada-trt/1003744163860_0.html)
- [Infobae — Error de 9.000 millones EUR por no revisar borrador](https://www.infobae.com/espana/2025/05/02/una-abogada-explica-cual-es-el-error-que-los-espanoles-cometen-al-hacer-la-declaracion-de-la-renta-que-les-hace-perder-casi-9000-millones-de-euros/)
- [ElDiario — Errores mas comunes declaracion renta](https://www.eldiario.es/economia/tu-economia/son-errores-comunes-declaracion-renta-evitarlos_1_13061733.html)
- [Telecinco — 3 deducciones alquiler que la mayoria olvida](https://www.telecinco.es/noticias/economia/consumo/20260109/declaracion-renta-inquilinos-2025-2026-deducciones-olvidadas_18_017421049.html)
- [COPE — Inquilinos pierden >1.000 EUR de deduccion por alquiler](https://www.cope.es/actualidad/economia/noticias/jose-ramon-lopez-abogado-inquilinos-pierden-1-000-euros-deduccion-alquiler-creen-contrato-debe-anterior-2015-asi-aun-reclamar-2024-20251217_3272300.html)
- [El Confidencial Digital — Deduccion 2.000 EUR autonomos que pasan por alto](https://www.elconfidencialdigital.com/seguraria/articulo/declaracion-renta/deduccion-2000-euros-renta-que-muchos-autonomos-estan-pasando-alto/20260319071500002332.html)
- [Autonomos y Emprendedor — 200 horas/ano en burocracia](https://www.autonomosyemprendedor.es/articulo/info-ata/autonomos-han-invertido-200-horas-3000-euros-tramites-burocraticos-2025-ata/20251219150531047332.html)
- [ElDiario Madrid — Burocracia cuesta 10.000 millones a autonomos](https://www.eldiariodemadrid.es/articulo/emprendedores/autonomos-burocracia-200-horas-anuales-coste-10000-millones-ata/20251218105413116736.html)

### Foros y resenas
- [Rankia — Foro Declaracion de la Renta](https://www.rankia.com/foro/declaracion-de-la-renta)
- [Rankia — Errores mas frecuentes declaracion renta](https://www.rankia.com/blog/irpf-declaracion-renta/1198409-cuales-son-errores-mas-frecuentes-declaracion-renta-2021-como-evitarlos)
- [Rankia — Dudas mas frecuentes renta](https://www.rankia.com/blog/irpf-declaracion-renta/3882158-declaracion-renta-dudas-mas-frecuentes)
- [Trustpilot — TaxDown](https://www.trustpilot.com/review/taxdown.es)
- [Trustpilot — Declarando](https://www.trustpilot.com/review/declarando.es)
- [Trustpilot — Holded](https://www.trustpilot.com/review/holded.com)
- [Trustpilot — Quipu](https://www.trustpilot.com/review/getquipu.com)
- [OCU — Reclamaciones TaxDown](https://www.ocu.org/reclamar/empresas/taxdown/64863256-CC2487D8F)

### Fiscalidad creadores de contenido
- [Infoautonomos — Fiscalidad creadores de contenido digital](https://www.infoautonomos.com/blog/fiscalidad-creadores-contenido-digital/)
- [Iberley — Fiscalidad creadores contenido digital](https://www.iberley.es/revista/fiscalidad-creadores-contenido-digital-influencers-youtubers-streamers-552)
- [OnlyTax — Gestoria para creadores](https://onlytax.es/)
- [OnlyTax — DAC7 multa con Hacienda](https://onlytax.es/formulario-dac7-multa-con-hacienda/)
- [OnlyTax — Ingresos sin declarar plataformas digitales](https://onlytax.es/ingresos-sin-declarar-plataformas-digitales/)
- [Dani Herranz — Guia fiscal creadores contenido digital](https://daniherranz.com/guia-sobre-fiscalidad-de-creadores-de-contenido-digital-youtubers-instagramers-twitchers-y-tiktokers)
- [Taxencadenado — Fiscalidad influencers](https://taxencadenado.com/blog/fiscalidad-espana/fiscalidad-influencers-tributacion-impuestos)
- [Blind Creator — Guia fiscal creadores Espana](https://www.blindcreator.com/blog/guia-fiscal-creadores-contenido-espana-irpf-iva-empresas.html)
- [Autonomos y Emprendedor — Epigrafe IAE influencers](https://www.autonomosyemprendedor.es/articulo/hacienda/que-epigrafe-iae-deben-estar-dados-alta-influencers-tributar-trabajo/20240409225648035661.html)

### Fuentes oficiales y herramientas
- [AEAT — Campana Renta 2025](https://sede.agenciatributaria.gob.es/Sede/Renta.html)
- [AEAT — Deducciones autonomicas IRPF](https://sede.agenciatributaria.gob.es/Sede/vivienda-otros-inmuebles/irpf-deducciones-autonomicas.html)
- [AEAT — Simuladores](https://sede.agenciatributaria.gob.es/Sede/procedimientoini/ZZ08.shtml)
- [Infoautonomos — Gastos deducibles autonomos IRPF](https://www.infoautonomos.com/fiscalidad/gastos-deducibles-autonomos-irpf-estimacion-directa/)
- [Infoautonomos — Calendario fiscal 2026](https://www.infoautonomos.com/fiscalidad/calendario-fiscal-autonomo-pyme/)

### VeriFactu y factura electronica
- [PoliticaFiscal — Aclaracion VeriFactu 2026](https://www.politicafiscal.es/cartas-a-taxlandia/obligatoriedad-factura-electronica-verifactu-qr)
- [Infoautonomos — Hacienda retrasa VeriFactu](https://www.infoautonomos.com/blog/hacienda-retrasa-entrada-vigor-verifactu/)
- [Escoem — Guia VeriFactu 2026](https://www.escoem.com/es/noticias/sistema-verifactu-2026/)

---

## Conclusiones y Recomendaciones

### Para el Roadmap de Impuestify

**Prioridad 1 (Campana Renta abril-junio 2026):**
- Maximizar visibilidad del simulador IRPF gratuito (ya existe)
- Landing SEO "obligado a declarar 2026" + "deducciones alquiler [CCAA]"
- Checklist pre-confirmacion del borrador (nuevo contenido)
- Mejorar UX del comparador conjunta/individual (ya existe)

**Prioridad 2 (Post-campana, Q3 2026):**
- Calculadora sueldo neto autonomo
- Estimador trimestral Modelo 130
- Wizard de alta para creadores de contenido
- Guia interactiva de gastos deducibles

**Prioridad 3 (Q4 2026):**
- Dashboard fiscal trimestral para autonomos
- Calculadora IVA por plataforma para creadores
- Contenido DAC7 + regularizacion
- Preparacion VeriFactu

### Metricas de exito sugeridas
- Particulares: % de usuarios que descubren deducciones nuevas vs borrador AEAT
- Autonomos: tiempo ahorrado en gestion fiscal (vs 200h/ano baseline)
- Creadores: conversion de "no sabia que tenia que declara" a cliente activo
