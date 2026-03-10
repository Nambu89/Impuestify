"""
Generate Impuestify User Manual as professional Word document.
Separate sections for Particulares and Autónomos.
"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "plans")


def set_cell_shading(cell, color_hex):
    shading = cell._tc.get_or_add_tcPr()
    shading_elm = shading.makeelement(qn('w:shd'), {
        qn('w:val'): 'clear', qn('w:color'): 'auto', qn('w:fill'): color_hex,
    })
    shading.append(shading_elm)


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
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
    for r_idx, row_data in enumerate(rows):
        for c_idx, val in enumerate(row_data):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(9)
            if r_idx % 2 == 1:
                set_cell_shading(cell, 'f0f5ff')
    return table


def add_step(doc, number, title, description):
    p = doc.add_paragraph()
    run = p.add_run(f'Paso {number}: {title}')
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(26, 86, 219)
    doc.add_paragraph(description)


def build_manual():
    doc = Document()

    for section in doc.sections:
        section.top_margin = Cm(2)
        section.bottom_margin = Cm(2)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    style = doc.styles['Normal']
    style.font.name = 'Montserrat'
    style.font.size = Pt(11)

    for level in range(1, 4):
        hs = doc.styles[f'Heading {level}']
        hs.font.name = 'Montserrat'
        hs.font.color.rgb = RGBColor(26, 86, 219)

    for ls in ['List Bullet', 'List Number']:
        if ls in doc.styles:
            doc.styles[ls].font.name = 'Montserrat'
            doc.styles[ls].font.size = Pt(11)

    # =========================================================================
    # COVER
    # =========================================================================
    for _ in range(5):
        doc.add_paragraph()

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run('IMPUESTIFY')
    run.font.size = Pt(38)
    run.bold = True
    run.font.color.rgb = RGBColor(26, 86, 219)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run('Manual de Usuario')
    run.font.size = Pt(22)
    run.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_paragraph()

    desc = doc.add_paragraph()
    desc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = desc.add_run('Guía completa para Particulares y Autónomos')
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(26, 86, 219)

    doc.add_paragraph()
    ver = doc.add_paragraph()
    ver.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = ver.add_run('Versión 1.0 — Marzo 2026')
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(150, 150, 150)

    doc.add_page_break()

    # =========================================================================
    # TABLE OF CONTENTS
    # =========================================================================
    doc.add_heading('Índice', level=1)
    toc = [
        'PARTE I — Para todos los usuarios',
        '  1. Qué es Impuestify',
        '  2. Crear tu cuenta',
        '  3. Elegir tu plan',
        '  4. Tu primer chat con la IA',
        '  5. Perfil fiscal',
        '  6. Deducciones personalizadas',
        '  7. Informe IRPF en PDF',
        '  8. Guía Fiscal interactiva',
        '  8b. Calendario fiscal',
        '',
        'PARTE II — Plan Particular',
        '  9. Consultas IRPF por comunidad autónoma',
        '  10. Análisis de nóminas',
        '  11. Notificaciones de Hacienda',
        '',
        'PARTE III — Plan Autónomo',
        '  12. Cuota de autónomos (RETA)',
        '  13. IVA trimestral (Modelo 303)',
        '  14. Pago fraccionado IRPF (Modelo 130)',
        '  14b. IPSI (Ceuta y Melilla)',
        '  14c. ISD (Sucesiones y Donaciones)',
        '  15. Retenciones IRPF en facturas',
        '  16. Workspaces de documentos',
        '',
        'PARTE IV — Referencia',
        '  17. Territorios forales',
        '  18. Preguntas frecuentes',
        '  19. Soporte y contacto',
    ]
    for item in toc:
        if item == '':
            doc.add_paragraph()
            continue
        p = doc.add_paragraph(item)
        if item.startswith('PARTE'):
            p.runs[0].bold = True
            p.runs[0].font.color.rgb = RGBColor(26, 86, 219)
        p.paragraph_format.space_after = Pt(2)

    doc.add_page_break()

    # =========================================================================
    # PARTE I — PARA TODOS
    # =========================================================================
    p = doc.add_paragraph()
    run = p.add_run('PARTE I')
    run.font.size = Pt(28)
    run.bold = True
    run.font.color.rgb = RGBColor(26, 86, 219)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('Para todos los usuarios')
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_page_break()

    # --- 1. Qué es Impuestify ---
    doc.add_heading('1. Qué es Impuestify', level=1)
    doc.add_paragraph(
        'Impuestify es tu asistente fiscal con Inteligencia Artificial. Puedes hacerle cualquier '
        'pregunta sobre impuestos en España y te responderá en segundos, citando fuentes legales '
        'oficiales. Es como tener un asesor fiscal disponible 24 horas al día, 7 días a la semana.'
    )

    doc.add_heading('Qué puede hacer por ti', level=2)
    capabilities = [
        'Calcular tu IRPF en cualquier comunidad autónoma (incluyendo País Vasco y Navarra)',
        'Descubrir deducciones fiscales que te corresponden entre más de 550 opciones en 21 territorios',
        'Adjuntar documentos directamente en el chat para análisis instantáneo',
        'Calcular el Impuesto de Sucesiones y Donaciones (ISD)',
        'Consultar tu calendario fiscal personalizado con fechas límite',
        'Actualizar tu perfil fiscal automáticamente desde la conversación',
        'Analizar tus nóminas en PDF y detectar errores de retención',
        'Interpretar notificaciones de Hacienda y decirte qué hacer',
        'Generar un informe IRPF exportable en PDF',
        'Para autónomos: calcular IVA, cuota RETA, pagos fraccionados y retenciones',
    ]
    for c in capabilities:
        doc.add_paragraph(c, style='List Bullet')

    doc.add_heading('Qué NO puede hacer (todavía)', level=2)
    limitations = [
        'Presentar tu declaración de la renta directamente a Hacienda (en desarrollo)',
        'Importar datos automáticamente con Cl@ve PIN (en desarrollo)',
        'Sustituir a un asesor en situaciones muy complejas (inversiones internacionales, herencias)',
    ]
    for l in limitations:
        doc.add_paragraph(l, style='List Bullet')

    # --- 2. Crear cuenta ---
    doc.add_heading('2. Crear tu cuenta', level=1)
    add_step(doc, 1, 'Accede a impuestify.com', 'Abre tu navegador y ve a impuestify.com.')
    add_step(doc, 2, 'Pulsa "Empezar Ahora"', 'En la página principal, haz clic en el botón azul.')
    add_step(doc, 3, 'Rellena tus datos',
             'Introduce tu nombre, email y una contraseña segura. '
             'Tu email será tu identificador único.')
    add_step(doc, 4, 'Selecciona tu comunidad autónoma',
             'Durante el registro deberás indicar tu comunidad autónoma. Este dato es obligatorio '
             'y determina los tramos IRPF, las deducciones territoriales y el calendario fiscal '
             'que verás en la aplicación.')
    add_step(doc, 5, 'Completa el control de seguridad',
             'Verás un control de seguridad Cloudflare Turnstile (un clic o resolución automática). '
             'Este paso protege la plataforma contra registros automáticos.')
    add_step(doc, 6, 'Confirma tu cuenta',
             'Recibirás un email de confirmación. Haz clic en el enlace para activar tu cuenta.')

    # --- 3. Elegir plan ---
    doc.add_heading('3. Elegir tu plan', level=1)
    doc.add_paragraph('Impuestify ofrece dos planes adaptados a tu situación:')

    add_table(doc,
        ['Característica', 'Plan Particular (5 EUR/mes)', 'Plan Autónomo (39 EUR/mes)'],
        [
            ['Chat IA fiscal ilimitado', 'SI', 'SI'],
            ['Cálculo IRPF por CCAA', 'SI', 'SI'],
            ['554+ deducciones personalizadas', 'SI', 'SI'],
            ['Análisis de nóminas (PDF)', 'SI', 'SI'],
            ['Adjuntar documentos en chat', 'SI', 'SI'],
            ['Calendario fiscal personalizado', 'SI', 'SI'],
            ['Cálculo ISD (Sucesiones)', 'SI', 'SI'],
            ['Notificaciones AEAT', 'SI', 'SI'],
            ['Workspace documentos', 'SI', 'SI'],
            ['Informe IRPF en PDF', 'SI', 'SI'],
            ['Perfil fiscal adaptativo por CCAA', 'SI', 'SI'],
            ['Cuota autónomos (RETA)', 'NO', 'SI'],
            ['IVA trimestral (Mod. 303)', 'NO', 'SI'],
            ['Pago fraccionado (Mod. 130)', 'NO', 'SI'],
            ['IPSI Ceuta/Melilla', 'NO', 'SI'],
            ['Retenciones IRPF facturas', 'NO', 'SI'],
            ['Deducciones autónomos', 'NO', 'SI'],
            ['Cobertura foral completa', 'SI', 'SI'],
        ]
    )

    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run('Consejo: ')
    run.bold = True
    p.add_run(
        'Si eres trabajador por cuenta ajena, el Plan Particular es perfecto para ti. '
        'Si eres autónomo o profesional por cuenta propia, necesitas el Plan Autónomo '
        'para acceder a las calculadoras de IVA, RETA y pagos fraccionados.'
    )

    doc.add_page_break()

    # --- 4. Tu primer chat ---
    doc.add_heading('4. Tu primer chat con la IA', level=1)
    doc.add_paragraph(
        'Una vez dentro, verás el chat de Impuestify. Puedes escribir cualquier pregunta '
        'fiscal en lenguaje natural, como si hablaras con un asesor.'
    )

    doc.add_heading('Ejemplos de preguntas', level=2)
    examples = [
        '"Cuánto IRPF pago si gano 40.000 euros en Madrid?"',
        '"Que deducciones me corresponden si tengo hijos y vivo en Cataluña?"',
        '"He recibido una notificación de Hacienda, qué hago?"',
        '"Cuánto es mi cuota de autónomos si gano 2.000 euros al mes?"',
        '"Cómo calculo el IVA del trimestre?"',
    ]
    for e in examples:
        doc.add_paragraph(e, style='List Bullet')

    doc.add_heading('Cómo funciona la respuesta', level=2)
    doc.add_paragraph(
        'Cuando envías una pregunta, verás un timeline de pasos que muestra cómo piensa la IA:'
    )
    steps = [
        ('Pensando...', 'La IA analiza tu pregunta y decide qué herramientas necesita.'),
        ('Buscando normativa...', 'Consulta entre 439+ documentos oficiales.'),
        ('Calculando...', 'Ejecuta las calculadoras necesarias (IRPF, deducciones, etc.).'),
        ('Respuesta', 'Te muestra el resultado con explicación y fuentes citadas.'),
    ]
    for title, desc in steps:
        p = doc.add_paragraph()
        run = p.add_run(f'{title} ')
        run.bold = True
        run.font.color.rgb = RGBColor(26, 86, 219)
        p.add_run(desc)

    doc.add_heading('Adjuntar documentos', level=2)
    doc.add_paragraph(
        'Junto al campo de texto verás un icono de clip. Pulsa para adjuntar un documento '
        '(PDF, JPG, PNG). El sistema lo analiza automáticamente, extrae los datos relevantes '
        'y los usa como contexto para la conversación. Los documentos adjuntos son temporales: '
        'se eliminan al cerrar el navegador.'
    )
    p = doc.add_paragraph()
    run = p.add_run('Ejemplo: ')
    run.bold = True
    p.add_run('Adjunta tu nómina y pregunta: "¿Es correcta mi retención IRPF?"')

    # --- 5. Perfil fiscal ---
    doc.add_heading('5. Perfil fiscal', level=1)
    doc.add_paragraph(
        'Tu perfil fiscal permite a la IA personalizar las respuestas. '
        'Ve a Ajustes > Perfil Fiscal para configurarlo. '
        'El perfil se puede rellenar manualmente en Ajustes o automáticamente desde la Guía Fiscal.'
    )

    doc.add_paragraph(
        'Tu perfil fiscal se adapta dinámicamente según tu comunidad autónoma. '
        'Si vives en un territorio foral (Araba, Bizkaia, Gipuzkoa, Navarra) verás campos '
        'específicos como EPSV, cuenta vivienda foral, etc.'
    )

    doc.add_paragraph(
        'La IA puede actualizar tu perfil automáticamente. Sube una nómina y pide: '
        '"Guarda estos datos en mi perfil fiscal". La IA extraerá los datos y los guardará.'
    )

    doc.add_heading('Datos del perfil', level=2)
    profile_fields = [
        ('Comunidad autónoma', 'Donde resides. Determina los tramos IRPF y deducciones territoriales.'),
        ('Situación laboral', 'Particular (cuenta ajena) o Autónomo (cuenta propia).'),
        ('Deducciones y situación familiar',
         'Planes de pensiones, hipoteca pre-2013, maternidad, familia numerosa, donativos a ONGs, '
         'tributación conjunta, alquiler pre-2015, rentas imputadas por segundas viviendas.'),
        ('Discapacidad', 'Grado de discapacidad del contribuyente y de familiares a cargo.'),
        ('Vivienda', 'Tipo de situación: alquiler, propiedad, rehabilitación, zona rural.'),
        ('Sostenibilidad', 'Vehículo eléctrico, instalación de paneles solares, obras de eficiencia energética.'),
        ('Donaciones', 'Aportaciones a entidades autonómicas, investigación, patrimonio histórico.'),
        ('Para autónomos', 'Epígrafe IAE, base de cotización, tipo de IVA, retención IRPF, '
         'régimen SS, gastos deducibles, amortizaciones...'),
    ]
    for title, desc in profile_fields:
        p = doc.add_paragraph()
        run = p.add_run(f'{title}: ')
        run.bold = True
        p.add_run(desc)

    p = doc.add_paragraph()
    run = p.add_run('Importante: ')
    run.bold = True
    run.font.color.rgb = RGBColor(200, 50, 50)
    p.add_run('La IA recuerda tu perfil entre sesiones. Si cambias de comunidad '
              'autónoma o de situación laboral, actualízalo en Ajustes.')

    # --- 6. Deducciones ---
    doc.add_heading('6. Deducciones personalizadas', level=1)
    doc.add_paragraph(
        'Impuestify tiene un motor de 554+ deducciones fiscales en 21 territorios: '
        'estatales, autonómicas y forales. Cuando preguntas por deducciones, la IA:'
    )

    deduction_steps = [
        'Identifica tu comunidad autónoma (del perfil o preguntando)',
        'Filtra las deducciones aplicables a tu territorio',
        'Te hace preguntas de elegibilidad (hijos, alquiler, discapacidad, etc.)',
        'Calcula el ahorro estimado para cada deducción',
        'Muestra las deducciones en tarjetas visuales con el detalle legal',
    ]
    for s in deduction_steps:
        doc.add_paragraph(s, style='List Number')

    p = doc.add_paragraph()
    run = p.add_run('Ejemplo: ')
    run.bold = True
    p.add_run(
        'Un residente en Araba (País Vasco) con hijos puede acceder a deducciones forales '
        'como la deducción por descendientes de 734,80 EUR por hijo, la deducción por alquiler '
        'del 20% (max 1.600 EUR), o la deducción por compra de vivienda del 18%. '
        'Estas deducciones NO existen en el régimen común y ningún otro asistente digital las cubre.'
    )

    doc.add_paragraph(
        'Para residentes forales (Araba, Bizkaia, Gipuzkoa, Navarra) el sistema aplica '
        'automáticamente solo las deducciones forales, ya que tienen un IRPF completamente '
        'independiente del régimen estatal.'
    )

    # --- 7. Informe PDF ---
    doc.add_heading('7. Informe IRPF en PDF', level=1)
    doc.add_paragraph(
        'Después de una simulación IRPF, puedes exportar un informe completo en PDF con:'
    )
    pdf_contents = [
        'Resumen de ingresos y gastos deducibles',
        'Cálculo detallado por tramos IRPF (estatal + autonómico)',
        'Deducciones aplicables con importes',
        'Cuota resultante y tipo efectivo',
        'Referencias legales de cada cálculo',
    ]
    for c in pdf_contents:
        doc.add_paragraph(c, style='List Bullet')

    doc.add_paragraph(
        'Puedes descargar el PDF o enviarlo directamente por email a tu asesor '
        'desde el botón "Enviar a asesor" que aparece junto al informe.'
    )

    # --- 8. Guía Fiscal interactiva ---
    doc.add_heading('8. Guía Fiscal interactiva', level=1)
    doc.add_paragraph(
        'La Guía Fiscal es un asistente paso a paso que te ayuda a estimar tu declaración de la renta '
        'de forma visual e interactiva. Accede desde el menú principal > "Guía Fiscal".'
    )

    doc.add_heading('Los 7 pasos', level=2)
    add_step(doc, 1, 'Datos personales',
             'Indica tu comunidad autónoma, edad, y si tributas en régimen conjunto. '
             'Si vives en Ceuta o Melilla, se aplicará automáticamente la bonificación del 60%.')
    add_step(doc, 2, 'Trabajo',
             'Introduce tus ingresos brutos del trabajo, cotizaciones a la Seguridad Social '
             'y retenciones IRPF practicadas por tu empresa.')
    add_step(doc, 3, 'Ahorro e inversiones',
             'Indica intereses bancarios, dividendos, ganancias de fondos de inversión y sus retenciones.')
    add_step(doc, 4, 'Inmuebles',
             'Si tienes inmuebles en alquiler, indica ingresos y gastos. Si pagaste alquiler de vivienda '
             'habitual antes de 2015, puedes aplicar la deducción transitoria. También se calculan las '
             'rentas imputadas de segundas viviendas.')
    add_step(doc, 5, 'Familia',
             'Información sobre descendientes (hijos), ascendientes mayores de 65/75 años, '
             'discapacidad, maternidad y familia numerosa.')
    add_step(doc, 6, 'Deducciones',
             'Planes de pensiones, hipoteca anterior a 2013, donativos a ONGs... '
             'El sistema aplica automáticamente los límites legales.')
    add_step(doc, 7, 'Resultado',
             'Visualiza el resultado completo: cuota líquida, retenciones pagadas, resultado '
             '(a pagar o a devolver), tipo medio efectivo y desglose de todas las deducciones aplicadas.')

    doc.add_paragraph(
        'Mientras completas los pasos, una barra de estimación en tiempo real te muestra el resultado '
        'parcial. Verde si te sale a devolver, rojo si te sale a pagar, con el importe actualizado '
        'automáticamente.'
    )

    doc.add_paragraph(
        'Al terminar, puedes pedir a la IA que guarde los datos en tu perfil fiscal. '
        'Los campos se rellenan automáticamente con los datos que has introducido durante la guía.'
    )

    # --- 8b. Calendario fiscal ---
    doc.add_heading('8b. Calendario fiscal', level=1)
    doc.add_paragraph(
        'Impuestify incluye un calendario fiscal personalizado que te muestra tus próximas '
        'obligaciones tributarias. Accede desde el menú principal > "Calendario".'
    )

    doc.add_paragraph('El calendario se adapta a tu perfil:')
    calendar_items = [
        'Particular: plazos de declaración IRPF anual',
        'Autónomo: plazos trimestrales (Modelo 303 IVA, Modelo 130 IRPF, cuota RETA)',
        'Canarias: IGIC en lugar de IVA',
        'Ceuta/Melilla: IPSI en lugar de IVA',
    ]
    for item in calendar_items:
        doc.add_paragraph(item, style='List Bullet')

    doc.add_paragraph(
        'Cada fecha límite incluye una descripción del trámite y los días restantes para presentarlo.'
    )

    doc.add_page_break()

    # =========================================================================
    # PARTE II — PLAN PARTICULAR
    # =========================================================================
    p = doc.add_paragraph()
    run = p.add_run('PARTE II')
    run.font.size = Pt(28)
    run.bold = True
    run.font.color.rgb = RGBColor(26, 86, 219)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('Plan Particular')
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_page_break()

    # --- 9. IRPF por CCAA ---
    doc.add_heading('9. Consultas IRPF por comunidad autónoma', level=1)
    doc.add_paragraph(
        'Pregunta por tu IRPF indicando tus ingresos y comunidad autónoma. '
        'La IA aplicará los tramos correctos (estatal + autonómico) y te mostrará:'
    )
    irpf_results = [
        'Base imponible general y del ahorro',
        'Cálculo tramo a tramo con tipos aplicables',
        'Cuota íntegra estatal y autonómica',
        'Deducciones aplicables',
        'Cuota líquida y tipo efectivo resultante',
    ]
    for r in irpf_results:
        doc.add_paragraph(r, style='List Bullet')

    p = doc.add_paragraph()
    run = p.add_run('Ejemplo de pregunta: ')
    run.bold = True
    p.add_run('"Si gano 35.000 euros brutos al año en Valencia, cuánto IRPF pago?"')

    # --- 10. Nóminas ---
    doc.add_heading('10. Análisis de nóminas', level=1)
    doc.add_paragraph(
        'Adjunta tu nómina directamente en el chat con el botón de clip, o súbela a un workspace. '
        'La IA extraerá automáticamente:'
    )
    payslip_fields = [
        'Salario bruto y neto',
        'Retención IRPF (porcentaje y importe)',
        'Cotizaciones a la Seguridad Social',
        'Base de cotización SS',
        'Base IRPF',
        'Aportaciones de la empresa',
        'Grupo de cotización y categoría profesional',
        'Pagas extraordinarias',
        'Detalle de devengos (salario base, complementos, pluses)',
        'Proyección IRPF anual basada en la nómina',
    ]
    for f in payslip_fields:
        doc.add_paragraph(f, style='List Bullet')

    p = doc.add_paragraph()
    run = p.add_run('Consejo: ')
    run.bold = True
    p.add_run('Si detectamos que tu retención IRPF es incorrecta respecto a tus ingresos anuales, '
              'te avisaremos automáticamente.')

    doc.add_paragraph(
        'La IA puede guardar los datos extraídos en tu perfil fiscal para futuras consultas. '
        'Pide: "Guarda estos datos en mi perfil fiscal."'
    )

    # --- 11. Notificaciones ---
    doc.add_heading('11. Notificaciones de Hacienda', level=1)
    doc.add_paragraph(
        'Si recibes una notificación de la AEAT (Agencia Tributaria), adjunta el PDF directamente '
        'en el chat o súbelo a un workspace. La IA extraerá:'
    )
    notif_fields = [
        'Tipo de notificación (requerimiento, liquidación, sanción, etc.)',
        'Plazo de respuesta',
        'Importe (si aplica)',
        'Referencia y número de expediente',
        'Acción requerida y pasos a seguir',
    ]
    for f in notif_fields:
        doc.add_paragraph(f, style='List Bullet')

    p = doc.add_paragraph()
    run = p.add_run('Importante: ')
    run.bold = True
    run.font.color.rgb = RGBColor(200, 50, 50)
    p.add_run('Las notificaciones de Hacienda tienen plazos legales. '
              'Si la notificación requiere acción urgente, te lo indicaremos claramente.')

    doc.add_page_break()

    # =========================================================================
    # PARTE III — PLAN AUTÓNOMO
    # =========================================================================
    p = doc.add_paragraph()
    run = p.add_run('PARTE III')
    run.font.size = Pt(28)
    run.bold = True
    run.font.color.rgb = RGBColor(26, 86, 219)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('Plan Autónomo')
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_page_break()

    # --- 12. RETA ---
    doc.add_heading('12. Cuota de autónomos (RETA)', level=1)
    doc.add_paragraph(
        'Desde 2023, la cuota de autónomos se calcula en función de los rendimientos netos reales '
        '(sistema de tramos). Impuestify calcula tu cuota exacta preguntándote:'
    )
    reta_questions = [
        'Ingresos netos mensuales estimados',
        'Si estás en tarifa plana (primeros 12 meses: 80 EUR/mes)',
        'Tramo de cotización correspondiente',
    ]
    for q in reta_questions:
        doc.add_paragraph(q, style='List Bullet')

    p = doc.add_paragraph()
    run = p.add_run('Ejemplo: ')
    run.bold = True
    p.add_run('"Soy autónomo y facturo 3.000 euros netos al mes, cuánto pago de cuota?"')

    doc.add_heading('Tabla de tramos RETA 2025', level=2)
    add_table(doc,
        ['Rendimientos netos/mes', 'Base minima', 'Base maxima', 'Cuota minima aprox.'],
        [
            ['Hasta 670 EUR', '735,29 EUR', '816,98 EUR', '~225 EUR'],
            ['670 - 900 EUR', '816,99 EUR', '900 EUR', '~250 EUR'],
            ['900 - 1.166,70 EUR', '872,55 EUR', '1.166,70 EUR', '~267 EUR'],
            ['1.166,70 - 1.300 EUR', '950,98 EUR', '1.300 EUR', '~291 EUR'],
            ['1.300 - 1.500 EUR', '960,78 EUR', '1.500 EUR', '~294 EUR'],
            ['1.500 - 1.700 EUR', '960,78 EUR', '1.700 EUR', '~294 EUR'],
            ['Más de 1.700 EUR', '1.143,79 EUR', '4.720,50 EUR', '~350+ EUR'],
        ]
    )

    doc.add_page_break()

    # --- 13. IVA ---
    doc.add_heading('13. IVA trimestral (Modelo 303)', level=1)
    doc.add_paragraph(
        'El Modelo 303 es la declaración trimestral de IVA. Impuestify te ayuda a calcularlo:'
    )

    add_step(doc, 1, 'Indica tus datos del trimestre',
             '"He facturado 15.000 EUR con IVA del 21% y tengo gastos deducibles por 3.000 EUR con IVA."')
    add_step(doc, 2, 'La IA calcula',
             'IVA repercutido (cobrado a clientes) - IVA soportado (pagado en gastos) = IVA a ingresar.')
    add_step(doc, 3, 'Resultado',
             'Te muestra el importe a pagar (o a compensar si el soportado es mayor) y el plazo de presentación.')

    doc.add_heading('Plazos de presentación', level=2)
    add_table(doc,
        ['Trimestre', 'Periodo', 'Plazo de presentación'],
        [
            ['1T', 'Enero - Marzo', '1 al 20 de abril'],
            ['2T', 'Abril - Junio', '1 al 20 de julio'],
            ['3T', 'Julio - Septiembre', '1 al 20 de octubre'],
            ['4T', 'Octubre - Diciembre', '1 al 30 de enero (año siguiente)'],
        ]
    )

    # --- 14. Modelo 130 ---
    doc.add_heading('14. Pago fraccionado IRPF (Modelo 130)', level=1)
    doc.add_paragraph(
        'Si estás en estimación directa, debes presentar pagos fraccionados trimestrales '
        'del IRPF (Modelo 130). Es un anticipo del 20% sobre el beneficio acumulado.'
    )

    p = doc.add_paragraph()
    run = p.add_run('Fórmula: ')
    run.bold = True
    p.add_run('20% x (Ingresos acumulados - Gastos acumulados) - Pagos fraccionados anteriores')

    p = doc.add_paragraph()
    run = p.add_run('Ejemplo de pregunta: ')
    run.bold = True
    p.add_run('"He facturado 30.000 EUR en el primer semestre con gastos de 8.000 EUR. '
              'Cuánto debo pagar en el Modelo 130 del 2T?"')

    # --- 14b. IPSI Ceuta y Melilla ---
    doc.add_heading('14b. IPSI (Ceuta y Melilla)', level=1)
    doc.add_paragraph(
        'Si resides en Ceuta o Melilla, el IVA no aplica. En su lugar pagas el IPSI '
        '(Impuesto sobre la Producción, los Servicios y la Importación). '
        'Impuestify calcula el IPSI trimestral con los 6 tipos impositivos aplicables: '
        '0,5%, 1%, 2%, 4%, 8% y 10%.'
    )

    # --- 14c. ISD ---
    doc.add_heading('14c. ISD (Sucesiones y Donaciones)', level=1)
    doc.add_paragraph(
        'Si recibes una herencia o donación, Impuestify calcula el Impuesto de Sucesiones '
        'y Donaciones aplicando la tarifa estatal y las bonificaciones de tu comunidad autónoma. '
        'Más de 8 CCAA tienen bonificaciones del 95-99% para familiares directos.'
    )

    # --- 15. Retenciones ---
    doc.add_heading('15. Retenciones IRPF en facturas', level=1)
    doc.add_paragraph(
        'Si facturas a empresas o profesionales, debes aplicar retención de IRPF en tus facturas. '
        'Impuestify te ayuda a calcular el importe correcto.'
    )

    add_table(doc,
        ['Situación', 'Retención'],
        [
            ['Profesional (general)', '15%'],
            ['Nuevo autónomo (primeros 3 años)', '7%'],
            ['Actividades agricolas/ganaderas', '2%'],
            ['Actividades forestales', '2%'],
        ]
    )

    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run('Ejemplo: ')
    run.bold = True
    p.add_run('"Si facturo 1.000 EUR + IVA con retención del 15%, cuánto cobra mi cliente?"')

    doc.add_page_break()

    # --- 16. Workspaces ---
    doc.add_heading('16. Workspaces de documentos', level=1)
    doc.add_paragraph(
        'Los workspaces son carpetas inteligentes donde puedes subir tus documentos fiscales. '
        'La IA analiza cada workspace de forma aislada, manteniendo el contexto separado.'
    )

    doc.add_heading('Cómo usar los workspaces', level=2)
    add_step(doc, 1, 'Crea un workspace',
             'Ve a "Workspaces" en el menu lateral. Pulsa "Crear workspace" y dale un nombre '
             'descriptivo (ej: "IVA Q1 2026", "Facturas clientes", "Nóminas 2025").')
    add_step(doc, 2, 'Sube documentos',
             'Puedes subir archivos arrastrando y soltando sobre la zona de archivos, o '
             'pulsando el botón "Subir archivo". Formatos aceptados: PDF, Word, Excel, imagenes.')
    add_step(doc, 3, 'Selecciona el workspace en el chat',
             'En la parte superior del chat, selecciona el workspace activo con el desplegable. '
             'Verás un indicador que confirma cuántos documentos se están consultando.')
    add_step(doc, 4, 'Pregunta sobre tus documentos',
             'La IA tendra el contexto completo de los documentos del workspace seleccionado. '
             'Por ejemplo: "Analiza las facturas de este trimestre y calcula el IVA."')

    doc.add_heading('Ideas de organizacion', level=2)
    ideas = [
        '"IVA Q1 2026" — Facturas de compras y ventas del primer trimestre',
        '"Nóminas 2025" — Todas las nóminas del año para proyección IRPF',
        '"Notificaciones AEAT" — Notificaciones recibidas de Hacienda',
        '"Gastos deducibles" — Tickets y facturas de gastos profesionales',
    ]
    for idea in ideas:
        doc.add_paragraph(idea, style='List Bullet')

    doc.add_page_break()

    # =========================================================================
    # PARTE IV — REFERENCIA
    # =========================================================================
    p = doc.add_paragraph()
    run = p.add_run('PARTE IV')
    run.font.size = Pt(28)
    run.bold = True
    run.font.color.rgb = RGBColor(26, 86, 219)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('Referencia')
    run.font.size = Pt(16)
    run.font.color.rgb = RGBColor(100, 100, 100)

    doc.add_page_break()

    # --- 17. Forales ---
    doc.add_heading('17. Territorios forales', level=1)
    doc.add_paragraph(
        'Impuestify es el ÚNICO asistente fiscal digital que cubre los territorios forales. '
        'Estos territorios tienen un sistema IRPF completamente independiente del régimen común, '
        'con tramos, tipos y deducciones propias.'
    )

    add_table(doc,
        ['Territorio', 'Hacienda', 'Deducciones propias', 'Particularidad'],
        [
            ['Araba/Álava', 'Hacienda Foral de Álava', '15 deducciones',
             'Deducción vivienda vigente (eliminada en régimen común en 2013)'],
            ['Bizkaia', 'Hacienda Foral de Bizkaia', '11 deducciones',
             'Tipos IRPF propios, diferente al estatal'],
            ['Gipuzkoa', 'Hacienda Foral de Gipuzkoa', '11 deducciones',
             'Sistema TicketBAI obligatorio'],
            ['Navarra', 'Hacienda Foral de Navarra', '13 deducciones',
             'IRPF navarro completamente independiente'],
        ]
    )

    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run('Nota: ')
    run.bold = True
    p.add_run('Si resides en un territorio foral, las deducciones estatales NO te aplican. '
              'Impuestify lo gestiona automáticamente: cuando indicas que vives en Araba, Bizkaia, '
              'Gipuzkoa o Navarra, solo te muestra las deducciones forales correspondientes.')

    # --- 18. FAQ ---
    doc.add_heading('18. Preguntas frecuentes', level=1)

    faqs = [
        ('Es seguro compartir mis datos fiscales?',
         'Si. Impuestify cumple con el RGPD y la LSSI-CE. Tus datos se almacenan cifrados, '
         'no compartimos información con terceros, y tenemos filtros automáticos de PII '
         '(datos personales) para evitar que datos sensibles se envien a la IA.'),
        ('Puede la IA equivocarse?',
         'Como cualquier herramienta, la IA puede cometer errores. Por eso citamos siempre '
         'la fuente legal de cada respuesta para que puedas verificarla. Para situaciones '
         'complejas, recomendamos consultar con un asesor fiscal.'),
        ('Puedo cancelar mi suscripción?',
         'Si, en cualquier momento. Ve a Ajustes > Suscripción > "Gestionar suscripción". '
         'Se abre el portal de Stripe donde puedes cancelar sin penalización.'),
        ('Funciona en el móvil?',
         'Si. Impuestify funciona en cualquier dispositivo con navegador moderno: ordenador, '
         'tablet o móvil. Además, es una PWA (Progressive Web App): puedes instalarlo en tu '
         'móvil desde el navegador pulsando "Añadir a pantalla de inicio" y se comportará como '
         'una app nativa.'),
        ('Puedo adjuntar documentos en el chat?',
         'Si. Pulsa el icono de clip junto al campo de texto para adjuntar PDFs, imágenes o '
         'documentos. El sistema los analiza automáticamente, extrae los datos y anonimiza la '
         'información personal antes de procesarla.'),
        ('Cómo actualizo mi perfil fiscal desde el chat?',
         'Sube un documento (nómina, factura) y pide: "Guarda estos datos en mi perfil fiscal". '
         'La IA extraerá los datos relevantes y los guardará automáticamente.'),
        ('Qué pasa con mis datos si cancelo?',
         'Tus datos se conservan 30 días tras la cancelación. Puedes solicitar la eliminación '
         'completa en cualquier momento desde Ajustes > Privacidad.'),
        ('La IA puede presentar mi declaración?',
         'Todavía no. Estamos tramitando ser Colaborador Social de la AEAT para poder presentar '
         'declaraciones directamente. Mientras tanto, te preparamos toda la información para que '
         'la presentes tu en 5 minutos via Renta WEB.'),
    ]
    for q, a in faqs:
        p = doc.add_paragraph()
        run = p.add_run(q)
        run.bold = True
        run.font.color.rgb = RGBColor(26, 86, 219)
        doc.add_paragraph(a)

    # --- 19. Soporte ---
    doc.add_heading('19. Soporte y contacto', level=1)
    doc.add_paragraph('Si necesitas ayuda, tienes varias opciones:')
    support = [
        'Chat de la app — pregunta directamente a la IA, que también puede ayudarte con dudas sobre el funcionamiento',
        'Email — contacto@impuestify.com',
        'Web — impuestify.com/contacto',
    ]
    for s in support:
        doc.add_paragraph(s, style='List Bullet')

    doc.add_paragraph()
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('impuestify.com')
    run.font.size = Pt(16)
    run.bold = True
    run.font.color.rgb = RGBColor(26, 86, 219)

    # Save
    output_path = os.path.join(OUTPUT_DIR, "Impuestify_Manual_Usuario_2026.docx")
    doc.save(output_path)
    print(f"User Manual saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    build_manual()
