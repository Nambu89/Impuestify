"""
Generate Impuestify Business Plan as professional Word document.
"""
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "plans")

def set_cell_shading(cell, color_hex):
    """Set cell background color."""
    shading = cell._tc.get_or_add_tcPr()
    shading_elm = shading.makeelement(qn('w:shd'), {
        qn('w:val'): 'clear',
        qn('w:color'): 'auto',
        qn('w:fill'): color_hex,
    })
    shading.append(shading_elm)

def add_styled_table(doc, headers, rows, col_widths=None, highlight_col=None):
    """Add a styled table with header row."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'

    # Header row
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_shading(cell, '1a56db')

    # Data rows
    for r_idx, row_data in enumerate(rows):
        for c_idx, val in enumerate(row_data):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
                    if highlight_col is not None and c_idx == highlight_col:
                        run.bold = True
                        run.font.color.rgb = RGBColor(26, 86, 219)
            if r_idx % 2 == 1:
                set_cell_shading(cell, 'f0f5ff')

    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    return table

def build_document():
    doc = Document()

    # === Page margins ===
    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    style = doc.styles['Normal']
    style.font.name = 'Montserrat'
    style.font.size = Pt(11)
    style.font.color.rgb = RGBColor(30, 30, 30)

    for level in range(1, 4):
        hs = doc.styles[f'Heading {level}']
        hs.font.name = 'Montserrat'
        hs.font.color.rgb = RGBColor(26, 86, 219)

    for ls in ['List Bullet', 'List Number']:
        if ls in doc.styles:
            doc.styles[ls].font.name = 'Montserrat'
            doc.styles[ls].font.size = Pt(11)

    # === COVER PAGE ===
    for _ in range(6):
        doc.add_paragraph()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run('IMPUESTIFY')
    run.font.size = Pt(42)
    run.bold = True
    run.font.color.rgb = RGBColor(26, 86, 219)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run('Tu Asistente Fiscal Inteligente')
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_paragraph()

    tagline = doc.add_paragraph()
    tagline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = tagline.add_run('Business Plan — Marzo 2026')
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(26, 86, 219)

    doc.add_paragraph()
    doc.add_paragraph()

    conf = doc.add_paragraph()
    conf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = conf.add_run('CONFIDENCIAL')
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(180, 180, 180)
    run.italic = True

    doc.add_page_break()

    # === TABLE OF CONTENTS ===
    doc.add_heading('Índice', level=1)
    toc_items = [
        '1. Resumen Ejecutivo',
        '2. El Problema',
        '3. La Solución: Impuestify',
        '4. Producto y Tecnología',
        '5. Mercado Objetivo',
        '6. Análisis Competitivo',
        '7. Modelo de Negocio',
        '8. Tracción y Métricas',
        '9. Roadmap',
        '10. Equipo',
        '11. Financiación y Uso de Fondos',
    ]
    for item in toc_items:
        p = doc.add_paragraph(item)
        p.paragraph_format.space_after = Pt(4)
        p.runs[0].font.size = Pt(11)

    doc.add_page_break()

    # === 1. RESUMEN EJECUTIVO ===
    doc.add_heading('1. Resumen Ejecutivo', level=1)

    doc.add_paragraph(
        'Impuestify es el primer asistente fiscal con Inteligencia Artificial multi-agente '
        'que cubre todos los territorios de España, incluyendo los cuatro territorios forales '
        '(País Vasco y Navarra) que ningún competidor atiende.'
    )

    doc.add_paragraph(
        'En España, 21,8 millones de personas presentan la declaración de la renta cada año. '
        'De ellos, 1,6 millones residen en territorios forales y están completamente desatendidos '
        'por las plataformas digitales existentes. Impuestify es la única solución tecnológica '
        'que les ofrece asistencia fiscal avanzada con IA.'
    )

    doc.add_heading('Cifras clave', level=2)
    add_styled_table(doc,
        ['Métrica', 'Valor'],
        [
            ['Deducciones fiscales cubiertas', '554+ (16 estatales + 192 territoriales + 339 oficiales AEAT + 50 forales en 21 territorios)'],
            ['Territorios cubiertos', '21 (17 CCAA + 4 forales + Ceuta/Melilla)'],
            ['Documentos oficiales en RAG', '439+ (PDFs + Excel + especificaciones AEAT)'],
            ['Agentes IA especializados', '5 agentes especializados + 1 Coordinator'],
            ['Tests automatizados', '858 (100% passing)'],
            ['Stack tecnológico', 'FastAPI + React + OpenAI GPT + RAG avanzado'],
            ['Simulador IRPF completo', 'Completo: trabajo, ahorro, inmuebles, familia, deducciones, retenciones, forales, Ceuta/Melilla'],
            ['Casillas IRPF Modelo 100', '2.064 casillas oficiales indexadas'],
            ['Calculadoras especializadas', '12+ (IRPF, IVA, RETA, ISD, IPSI, deducciones, Mod.303, Mod.130, casillas, perfil fiscal)'],
            ['Guía Fiscal interactiva', 'Wizard 7 pasos con estimación IRPF en tiempo real y perfil fiscal adaptativo'],
            ['Plan Particular', '5 EUR/mes'],
            ['Plan Autónomo', '39 EUR/mes (IVA incluido)'],
        ],
        highlight_col=1
    )

    doc.add_page_break()

    # === 2. EL PROBLEMA ===
    doc.add_heading('2. El Problema', level=1)

    doc.add_heading('2.1 Complejidad fiscal en España', level=2)
    doc.add_paragraph(
        'España tiene uno de los sistemas fiscales más complejos de Europa. Con 17 comunidades '
        'autónomas con competencias fiscales propias, 4 territorios forales con sistemas IRPF '
        'completamente independientes (Araba, Bizkaia, Gipuzkoa y Navarra), y las particularidades '
        'de Ceuta y Melilla, el ciudadano medio se enfrenta a un laberinto normativo.'
    )

    problems = [
        ('El 72% de los españoles', 'no conoce todas las deducciones a las que tiene derecho (INE 2024).'),
        ('1,6 millones de declarantes forales', 'no tienen ninguna herramienta digital avanzada. '
         'TaxDown, líder del mercado, los rechaza explícitamente.'),
        ('3,4 millones de autónomos', 'gestionan trimestrales (IVA, IRPF) con asesores humanos a 50-150 EUR/mes, '
         'con tiempos de respuesta de 24-48 horas.'),
        ('Las notificaciones de Hacienda', 'generan ansiedad y confusión. No hay herramientas que las analicen '
         'automáticamente con IA.'),
    ]
    for title, desc in problems:
        p = doc.add_paragraph()
        run = p.add_run(title + ': ')
        run.bold = True
        p.add_run(desc)

    doc.add_heading('2.2 Las soluciones actuales son insuficientes', level=2)
    doc.add_paragraph(
        'TaxDown (líder con 1M+ usuarios y 29,7M EUR recaudados) es un fórmulario guiado con '
        'revisión humana. Su IA (AsesorIA) es un chatbot básico sobre ChatGPT sin documentos '
        'fiscales reales. No cubre forales, no analiza nóminas automáticamente, y su modelo '
        'depende de 200+ asesores humanos con costes crecientes.'
    )

    doc.add_page_break()

    # === 3. LA SOLUCIÓN ===
    doc.add_heading('3. La Solución: Impuestify', level=1)

    doc.add_paragraph(
        'Impuestify reemplaza al asesor fiscal humano con un sistema multi-agente de IA que:'
    )

    features = [
        'Responde consultas fiscales en segundos (no en 24-48 horas)',
        'Cubre TODOS los territorios de España, incluyendo forales',
        'Analiza nóminas en PDF automáticamente y proyecta IRPF anual',
        'Interpreta notificaciones de Hacienda con extracción estructurada',
        'Descubre deducciones personalizadas entre 554+ opciones en 21 territorios',
        'Adjunta documentos directamente en el chat para análisis instantáneo',
        'Calcula el Impuesto de Sucesiones y Donaciones (ISD) con bonificaciones por CCAA',
        'Calcula IPSI trimestral para residentes en Ceuta y Melilla',
        'Calendario fiscal personalizado con notificaciones de plazos',
        'Actualiza tu perfil fiscal automáticamente desde el chat',
        'Calcula IRPF, IVA (Modelo 303), pagos fraccionados (Modelo 130), cuota RETA, ISD e IPSI',
        'Cita fuentes legales en cada respuesta (439+ archivos fiscales oficiales)',
        'Funciona 24/7 sin coste marginal por consulta',
    ]
    for f in features:
        doc.add_paragraph(f, style='List Bullet')

    doc.add_heading('Propuesta de valor única', level=2)
    p = doc.add_paragraph()
    run = p.add_run(
        '"El único asistente fiscal con IA que cubre País Vasco y Navarra. '
        'Porque si vives en territorio foral, mereces las mismas ventajas que el resto."'
    )
    run.italic = True
    run.font.color.rgb = RGBColor(26, 86, 219)

    doc.add_page_break()

    # === 4. PRODUCTO Y TECNOLOGIA ===
    doc.add_heading('4. Producto y Tecnología', level=1)

    doc.add_heading('4.1 Arquitectura Multi-Agente', level=2)
    doc.add_paragraph(
        'Impuestify utiliza una arquitectura de agentes especializados que colaboran para resolver '
        'consultas complejas. Cada agente es experto en su dominio y tiene acceso a herramientas específicas.'
    )

    add_styled_table(doc,
        ['Agente', 'Función', 'Herramientas'],
        [
            ['Coordinador', 'Router inteligente, clasifica consultas', 'Routing automático a agente especializado'],
            ['Agente Fiscal', 'Consultas fiscales generales, IRPF, IVA, deducciones, ISD, IPSI',
             'calculate_irpf, discover_deductions, simulate_irpf, calculate_modelo_303, calculate_isd, calculate_modelo_ipsi, lookup_casilla, update_fiscal_profile'],
            ['Agente de Nóminas', 'Análisis de nóminas en PDF',
             'Extracción de 35 campos, proyección anual, detección errores retención'],
            ['Agente de Notificaciones', 'Interpretación notificaciones AEAT',
             'Extracción tipo, plazo, importe, acción requerida'],
            ['Agente Documental', 'Análisis de documentos del usuario',
             'Contexto aislado por workspace, embeddings por documento'],
            ['Agente de Sesión', 'Gestión de documentos efímeros en el chat',
             'Upload, extracción, clasificación automática, anonimización PII'],
        ]
    )

    doc.add_heading('4.2 RAG (Retrieval-Augmented Generation)', level=2)
    doc.add_paragraph(
        'Cada respuesta se genera a partir de 439+ archivos fiscales oficiales indexados: '
        'normativa AEAT, BOE, leyes de CCAA, Normas Forales de cada Diputacion, y '
        'manuales prácticos. El sistema realiza búsqueda híbrida (semántica + BM25 + FTS5) '
        'para recuperar los fragmentos más relevantes y cita la fuente en cada respuesta.'
    )

    doc.add_heading('4.3 Seguridad y Guardrails IA', level=2)
    security = [
        'Llama Guard 4 — moderación de contenido en 14 categorías',
        'Prompt Guard 2 — detección de inyección de prompts',
        'Filtro PII — detección de DNI, teléfono, email, cuentas bancarias',
        'Anonimización automática de datos personales en documentos adjuntos',
        'Clasificación inteligente de documentos por contenido',
        'Validador SQL — prevención de inyección SQL',
        'Rate limiting — protección contra abuso con cache en memoria',
        'Cache semántico — reducción de costes ~30%',
        'JWT + refresh tokens — autenticación segura',
        'RGPD compliant — cookies LSSI-CE, política de retención, AI Act Art. 52 compliance (transparencia IA)',
    ]
    for s in security:
        doc.add_paragraph(s, style='List Bullet')

    doc.add_heading('4.4 Stack Tecnológico', level=2)
    add_styled_table(doc,
        ['Capa', 'Tecnología'],
        [
            ['Backend', 'Python 3.12, FastAPI, framework multi-agente propietario'],
            ['Frontend', 'React 18, TypeScript, Vite 5, PWA'],
            ['IA', 'OpenAI GPT (últimas generaciones), embeddings de alta dimensión'],
            ['Base de datos', 'Base de datos distribuida, edge-first'],
            ['Cache', 'Cache en memoria + cache semántico vectorial'],
            ['Pagos', 'Stripe (suscripciones + portal gestión)'],
            ['PDF Export', 'Generación de informes IRPF en PDF'],
            ['Email', 'Resend (envío informes a asesor)'],
            ['Despliegue', 'Railway (backend + frontend)'],
            ['Seguridad IA', 'Moderación IA multicapa (Llama Guard 4 + Prompt Guard 2)'],
        ]
    )

    doc.add_heading('4.5 Simulador IRPF Completo', level=2)
    doc.add_paragraph(
        'Impuestify incluye un motor de cálculo IRPF que cubre todos los tramos '
        'estatales y autonómicos de los 21 territorios soportados. El simulador se '
        'organiza en dos fases y extiende el régimen común con soporte foral completo:'
    )
    phase_items = [
        'Fase 1: Rendimientos del trabajo, del ahorro y de inmuebles. '
        'Reducciones por planes de pensiones. Deducciones: hipoteca pre-2013, '
        'maternidad, familia numerosa, donativos.',
        'Fase 2: Tributación conjunta, alquiler habitual pre-2015, rentas imputadas '
        'por inmuebles a disposición.',
        'Motor IRPF foral completo: escalas propias de Araba, Bizkaia, Gipuzkoa y Navarra '
        'con mínimos como deducción de cuota.',
        'Deducción 60% cuota íntegra para residentes en Ceuta y Melilla (Art. 68.4 LIRPF).',
        'Perfil fiscal adaptativo: formulario dinámico con campos específicos por CCAA y régimen fiscal.',
        'REST endpoint /api/irpf/estimate con debounce y AbortController para '
        'estimación en tiempo real sin saturar el servidor.',
        'Guía Fiscal: wizard interactivo de 7 pasos con LiveEstimatorBar que muestra '
        'la estimación IRPF actualizada en cada paso del proceso.',
    ]
    for item in phase_items:
        doc.add_paragraph(item, style='List Bullet')

    doc.add_page_break()

    # === 5. MERCADO OBJETIVO ===
    doc.add_heading('5. Mercado Objetivo', level=1)

    doc.add_heading('5.1 TAM / SAM / SOM', level=2)
    add_styled_table(doc,
        ['Segmento', 'Tamaño', 'Descripción'],
        [
            ['TAM', '21,8M declarantes IRPF', 'Total de declaraciones de renta anuales en España'],
            ['SAM', '5,0M declarantes digitales', 'Usuarios que usan herramientas digitales para su fiscalidad'],
            ['SOM Fase 1', '1,6M declarantes forales', 'Desatendidos por TaxDown y competencia — mercado abierto'],
            ['SOM Fase 2', '3,4M autónomos', 'Autónomos que pagan 50-150 EUR/mes a gestores humanos'],
        ],
        highlight_col=1
    )

    doc.add_heading('5.2 Segmentos prioritarios', level=2)

    segments = [
        ('Residentes forales (País Vasco + Navarra)',
         '1,6M declarantes que TaxDown rechaza explícitamente. Ningún competidor digital los atiende. '
         'Impuestify es la ÚNICA opción con IA. Captación estimada: 5% = 80.000 usuarios potenciales.'),
        ('Autónomos con complejidad media',
         '3,4M autónomos que gestionan IVA trimestral, IRPF fraccionado y cuota RETA. '
         'Hoy pagan 50-150 EUR/mes a gestores humanos con respuestas en 24-48h. '
         'Impuestify ofrece respuestas en segundos a 39 EUR/mes.'),
        ('Particulares tecnológicos',
         'Trabajadores por cuenta ajena habituados a IA (ChatGPT, Gemini) que quieren un asistente '
         'fiscal inteligente, no un fórmulario. Plan Particular a 5 EUR/mes.'),
    ]
    for title, desc in segments:
        p = doc.add_paragraph()
        run = p.add_run(title + ': ')
        run.bold = True
        p.add_run(desc)

    doc.add_page_break()

    # === 6. ANÁLISIS COMPETITIVO ===
    doc.add_heading('6. Análisis Competitivo', level=1)

    doc.add_heading('6.1 Mapa de competidores', level=2)
    add_styled_table(doc,
        ['Plataforma', 'Tipo', 'Precio/mes', 'IA Real', 'Presenta AEAT', 'Forales'],
        [
            ['TaxDown', 'Asistente + asesor', '0-72 EUR', 'Básico', 'SI', 'NO'],
            ['Declarando', 'Asesor digital', '30-60 EUR', 'No', 'SI', 'NO'],
            ['Taxfix', 'Asesor humano', '~48 EUR', 'No', 'SI', 'NO'],
            ['Abaq', 'Gestoría digital', '39 EUR', 'No', 'SI', 'NO'],
            ['Fiscaliza', 'Asesor digital', '31-74 EUR', 'No', 'SI', 'NO'],
            ['Gestor presencial', 'Humano', '80-150 EUR', 'No', 'SI', 'Depende'],
            ['IMPUESTIFY', 'Asistente IA', '5-39 EUR', 'SI (multi-agente avanzado + 12 tools)', 'No (por ahora)', 'SI (ÚNICO)'],
        ],
        highlight_col=0
    )

    doc.add_heading('6.2 Ventajas competitivas de Impuestify', level=2)
    add_styled_table(doc,
        ['Ventaja', 'Detalle', 'Impacto'],
        [
            ['Cobertura foral completa', 'Único en cubrir PV + Navarra con IA', 'DIFERENCIADOR CRÍTICO'],
            ['Sistema multi-agente', '5 agentes especializados vs chatbot genérico', 'Calidad superior'],
            ['RAG sobre 439+ archivos oficiales', 'Respuestas con citas legales verificables', 'Confianza'],
            ['Análisis automático nóminas', 'Extracción PDF + proyección IRPF con extracción de 35 campos', 'Exclusivo'],
            ['Análisis notificaciones AEAT', 'IA en segundos vs humanos en 24h', 'Exclusivo'],
            ['554+ deducciones', '21 territorios cubiertos', 'Amplitud'],
            ['ISD + IPSI calculadoras', 'Sucesiones, donaciones y impuesto Ceuta/Melilla', 'Exclusivo'],
            ['Calendario fiscal personalizado', 'Plazos trimestrales por perfil con notificaciones', 'Diferenciador'],
            ['Adjuntar docs en chat', 'Upload directo sin workspace, anonimización PII', 'UX superior'],
            ['Guardrails seguridad IA', 'Sistema de seguridad multicapa, anti-PII, anti-injection', 'Confianza regulatoria'],
            ['Coste marginal casi cero', 'Sin asesores humanos, escalable', 'Margen superior'],
            ['Disponibilidad 24/7/365', 'No estacional como TaxDown', 'Engagement continuo'],
        ]
    )

    doc.add_heading('6.3 Gaps a cubrir (roadmap)', level=2)
    add_styled_table(doc,
        ['Gap', 'Competencia tiene', 'Plan Impuestify', 'Plazo'],
        [
            ['Presentación AEAT', 'TaxDown, Declarando', 'Colaborador Social AEAT', '6-12 meses'],
            ['Importación Clave', 'TaxDown, Declarando', 'Requiere Colab. Social', '6-12 meses'],
            ['App móvil nativa', 'TaxDown, Declarando', 'React Native / PWA avanzada', '3-6 meses'],
            ['Motor 250+ deducciones', 'TaxDown (Rita)', 'Expansión progresiva', '3-6 meses'],
        ]
    )

    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run(
        'Nota: TaxDown tiene debilidades documentadas en Trustpilot (4.3/5, 6.539 reviews): '
        'discrepancias de cálculo de hasta 850 EUR, cobros duplicados, rotación de asesores, '
        'servicio lento, y prácticas de reviews cuestionadas por Trustpilot.'
    )
    run.italic = True
    run.font.size = Pt(9)

    doc.add_page_break()

    # === 7. MODELO DE NEGOCIO ===
    doc.add_heading('7. Modelo de Negocio', level=1)

    doc.add_heading('7.1 Planes de suscripción', level=2)
    add_styled_table(doc,
        ['Plan', 'Precio', 'Público', 'Incluye'],
        [
            ['Particular', '5 EUR/mes', 'Trabajadores cuenta ajena',
             'Chat IA ilimitado, IRPF por CCAA, 554+ deducciones, análisis nóminas, '
             'notificaciones AEAT, workspace docs, export PDF, fuentes citadas, '
             'calendario fiscal, adjuntar documentos en chat, ISD'],
            ['Autónomo', '39 EUR/mes (IVA incl.)', 'Autónomos y profesionales',
             'Todo lo de Particular + IVA Mod.303, IRPF Mod.130, cuota RETA, '
             'retenciones IRPF, deducciones autónomos, workspaces aislados, cobertura foral completa, '
             'IPSI Ceuta/Melilla, calendario fiscal personalizado'],
        ],
        highlight_col=1
    )

    doc.add_heading('7.2 Proyección de ingresos (escenario conservador)', level=2)
    add_styled_table(doc,
        ['Métrica', 'Mes 6', 'Mes 12', 'Mes 24'],
        [
            ['Usuarios Particular', '500', '2.000', '8.000'],
            ['Usuarios Autónomo', '100', '500', '2.000'],
            ['MRR Particular', '2.500 EUR', '10.000 EUR', '40.000 EUR'],
            ['MRR Autónomo', '3.900 EUR', '19.500 EUR', '78.000 EUR'],
            ['MRR Total', '6.400 EUR', '29.500 EUR', '118.000 EUR'],
            ['ARR', '76.800 EUR', '354.000 EUR', '1.416.000 EUR'],
        ],
        highlight_col=3
    )

    doc.add_heading('7.3 Estructura de costes', level=2)
    add_styled_table(doc,
        ['Concepto', 'Coste mensual estimado', 'Notas'],
        [
            ['OpenAI API (GPT + embeddings)', '200-2.000 EUR', 'Escala con usuarios, cache semántico -30%'],
            ['Infraestructura (Railway + BD + cache)', '50-200 EUR', 'Serverless, escala automática'],
            ['Seguridad IA (moderación)', '0 EUR', 'Tier gratuito: 14.400 req/dia'],
            ['Stripe (comisiones)', '2,9% + 0,25 EUR/tx', 'Estandar Stripe'],
            ['Dominio + email', '~15 EUR', 'Fijo'],
        ]
    )

    p = doc.add_paragraph()
    run = p.add_run(
        'Ventaja estructural: sin asesores humanos, el coste marginal por usuario tiende a cero. '
        'El modelo es inherentemente escalable frente a competidores como TaxDown (200+ asesores) '
        'o Declarando (equipos humanos por cliente).'
    )
    run.bold = True

    doc.add_page_break()

    # === 8. TRACCION Y METRICAS ===
    doc.add_heading('8. Tracción y Métricas', level=1)

    doc.add_heading('8.1 Estado actual del producto', level=2)
    metrics = [
        ('Producto', 'MVP completo, en producción en impuestify.com'),
        ('Usuarios registrados', '13 (fase alpha privada)'),
        ('Tests automatizados', '858 tests, 100% passing'),
        ('Documentos RAG indexados', '439+ archivos fiscales oficiales'),
        ('Deducciones fiscales', '554+ activas en 21 territorios'),
        ('Agentes IA operativos', '5 agentes especializados + 1 Coordinator'),
        ('Herramientas IA', '12+ (IRPF, IVA, RETA, ISD, IPSI, deducciones, Mod.303/130, casillas, perfil fiscal, nóminas, notificaciones)'),
        ('Casillas IRPF', '2.064 casillas Modelo 100 indexadas'),
        ('Simulador IRPF', 'Completo: 21 territorios, forales, Ceuta/Melilla, tributación conjunta'),
        ('Guía Fiscal', 'Wizard 7 pasos con estimación IRPF en tiempo real y perfil fiscal adaptativo'),
        ('Documentos adjuntos', 'Upload en chat con clasificación automática y anonimización'),
        ('Seguridad', '12 capas de seguridad activas (rate limit, JWT, guardrails IA, PII, etc.)'),
        ('PWA', 'Instalable en móvil, offline-first para assets'),
        ('Pagos', 'Stripe integrado con 2 planes operativos'),
    ]
    for title, value in metrics:
        p = doc.add_paragraph()
        run = p.add_run(title + ': ')
        run.bold = True
        p.add_run(value)

    doc.add_heading('8.2 QA verificado en producción', level=2)
    doc.add_paragraph(
        '858 tests automatizados (backend) + E2E Playwright contra producción. '
        '15/17 sesiones QA aprobadas. Todas las funcionalidades principales operativas.'
    )

    doc.add_page_break()

    # === 9. ROADMAP ===
    doc.add_heading('9. Roadmap', level=1)

    add_styled_table(doc,
        ['Fase', 'Plazo', 'Objetivos', 'Impacto en precio'],
        [
            ['Fase 1: Captación forales',
             '0-3 meses',
             'SEO foral, landing territoriales, showcase nóminas, motor 64 deducciones activas expandiendo a 150+, '
             'Simulador IRPF completo (IMPLEMENTADO), Guía Fiscal interactiva (IMPLEMENTADO), app móvil PWA+',
             'Sin cambio (5/39 EUR)'],
            ['Fase 2: Colaborador Social AEAT',
             '3-6 meses',
             'Trámites AEAT, presentación telemática, importación Clave, app React Native',
             'Subir a 59-69 EUR/mes autónomo'],
            ['Fase 3: Expansión',
             '6-12 meses',
             '250+ deducciones, B2B/HR Tech (nóminas empresas forales), guía interactiva Renta Web, plan Pro',
             'Plan Pro 99-149 EUR/mes'],
            ['Fase 4: Escala',
             '12-24 meses',
             'Instant refund, expansión LATAM, API para integradores, seguro errores cálculo',
             'Plan Enterprise a medida'],
        ]
    )

    doc.add_page_break()

    # === 10. EQUIPO ===
    doc.add_heading('10. Equipo', level=1)

    doc.add_paragraph(
        'Impuestify ha sido desarrollado íntegramente por un equipo lean con enfoque en IA '
        'y automatización. La arquitectura multi-agente y el RAG sobre documentación fiscal '
        'oficial representan más de 6 meses de desarrollo especializado.'
    )

    doc.add_heading('Perfiles a incorporar (con financiación)', level=2)
    roles = [
        ('CTO / Lead Developer', 'Arquitectura backend, escalabilidad, seguridad'),
        ('Growth / Marketing', 'Captación en nicho foral, SEO, partnerships'),
        ('Compliance / Legal', 'Trámites Colaborador Social AEAT, RGPD, licencias'),
        ('Customer Success', 'Onboarding autónomos, feedback, churn prevention'),
    ]
    for title, desc in roles:
        p = doc.add_paragraph()
        run = p.add_run(title + ': ')
        run.bold = True
        p.add_run(desc)

    doc.add_page_break()

    # === 11. FINANCIACION ===
    doc.add_heading('11. Financiación y Uso de Fondos', level=1)

    doc.add_heading('11.1 Ronda objetivo', level=2)
    p = doc.add_paragraph()
    run = p.add_run('Pre-Seed: 150.000 - 300.000 EUR')
    run.font.size = Pt(16)
    run.bold = True
    run.font.color.rgb = RGBColor(26, 86, 219)

    doc.add_heading('11.2 Uso de fondos', level=2)
    add_styled_table(doc,
        ['Concepto', 'Porcentaje', 'Importe (sobre 200K)', 'Detalle'],
        [
            ['Equipo tecnico', '40%', '80.000 EUR', 'CTO + developer senior (6 meses)'],
            ['Marketing y captación', '25%', '50.000 EUR', 'SEO foral, paid acquisition, partnerships'],
            ['Compliance y legal', '15%', '30.000 EUR', 'Colaborador Social AEAT, certificados, RGPD'],
            ['Infraestructura y ops', '10%', '20.000 EUR', 'Servidores, APIs IA, herramientas'],
            ['Buffer operativo', '10%', '20.000 EUR', 'Reserva 3 meses'],
        ],
        highlight_col=2
    )

    doc.add_heading('11.3 Hitos con la financiación', level=2)
    milestones = [
        'Mes 3: 500 usuarios activos, SEO posicionado en forales',
        'Mes 6: 1.000 usuarios, presentación AEAT en trámite',
        'Mes 9: App móvil, 150+ deducciones, primeros autónomos de pago',
        'Mes 12: Colaborador Social operativo, 2.500 usuarios, ARR ~350K EUR',
    ]
    for m in milestones:
        doc.add_paragraph(m, style='List Bullet')

    doc.add_paragraph()
    doc.add_paragraph()

    # Final CTA
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('impuestify.com')
    run.font.size = Pt(16)
    run.bold = True
    run.font.color.rgb = RGBColor(26, 86, 219)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('Contacto: fernando.prada@proton.me')
    run.font.size = Pt(11)

    # Save
    output_path = os.path.join(OUTPUT_DIR, "Impuestify_Business_Plan_2026.docx")
    doc.save(output_path)
    print(f"Business Plan saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    build_document()
