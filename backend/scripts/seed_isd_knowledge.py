"""
Seed script: RAG knowledge base — Impuesto sobre Sucesiones y Donaciones (ISD).

Inserts structured knowledge chunks covering:
- Normativa estatal (Ley 29/1987)
- Tarifa estatal y tramos (Art. 21)
- Reducciones estatales por parentesco (Art. 20)
- Coeficientes multiplicadores por patrimonio (Art. 22)
- Reducciones especiales: discapacidad, vivienda habitual, empresa familiar
- Bonificaciones por CCAA: Madrid, Andalucia, Valencia, Aragon, Cataluna,
  Pais Vasco (Araba/Bizkaia/Gipuzkoa), Navarra, Canarias, Ceuta/Melilla
- Plazos de presentacion
- Diferencias sucesion vs donacion

These chunks are used by the search_tax_regulations tool (FTS5) and the
RAG pipeline to give context to ISD queries in the TaxAgent.

Idempotent: uses INSERT OR IGNORE on document hash; chunks also use
INSERT OR IGNORE on (document_id, chunk_index).

Usage:
    cd backend
    python scripts/seed_isd_knowledge.py
    python scripts/seed_isd_knowledge.py --dry-run
"""
import argparse
import asyncio
import hashlib
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# ---------------------------------------------------------------------------
# Document metadata
# ---------------------------------------------------------------------------

ISD_DOCUMENT = {
    "filename": "isd_normativa_espana_2025.txt",
    "filepath": "knowledge/isd",
    "title": "Impuesto sobre Sucesiones y Donaciones — Normativa estatal y autonomica 2025",
    "document_type": "normativa_fiscal",
    "year": 2025,
    "source": "Ley 29/1987 + normativas CCAA",
}


# ---------------------------------------------------------------------------
# Knowledge chunks
# Each chunk: {title, content, metadata dict}
# ---------------------------------------------------------------------------

ISD_CHUNKS = [

    # ------------------------------------------------------------------
    # 1. Introduccion y ambito de aplicacion
    # ------------------------------------------------------------------
    {
        "title": "ISD — Introduccion y ambito de aplicacion",
        "content": (
            "El Impuesto sobre Sucesiones y Donaciones (ISD) es un tributo estatal cedido a las "
            "Comunidades Autonomas, regulado por la Ley 29/1987, de 18 de diciembre, y su Reglamento "
            "(RD 1629/1991). Grava tres hechos imponibles: (1) adquisiciones mortis causa (herencias y "
            "legados), (2) adquisiciones inter-vivos a titulo gratuito (donaciones), y (3) percepcion "
            "de cantidades por beneficiarios de seguros de vida cuando el contratante es persona "
            "distinta del beneficiario. "
            "El sujeto pasivo es el adquirente (heredero, legatario, donatario o beneficiario del seguro). "
            "La base imponible es el valor neto de los bienes y derechos adquiridos. "
            "Las Comunidades Autonomas de regimen comun tienen competencia normativa sobre reducciones, "
            "tarifa, cuantias y coeficientes del patrimonio preexistente, deducciones y bonificaciones. "
            "Los territorios forales (Araba/Alava, Bizkaia, Gipuzkoa y Navarra) tienen su propio "
            "sistema ISD mediante Normas Forales o Leyes Forales, con tipos mucho mas reducidos."
        ),
        "metadata": {
            "territory": "estatal",
            "tax_type": "isd",
            "subtopic": "introduccion",
            "source": "Ley 29/1987",
        },
    },

    # ------------------------------------------------------------------
    # 2. Tarifa estatal — Art. 21 Ley 29/1987
    # ------------------------------------------------------------------
    {
        "title": "ISD — Tarifa estatal (Art. 21 Ley 29/1987)",
        "content": (
            "La tarifa del ISD estatal (Art. 21 Ley 29/1987) es progresiva. Se aplica sobre la "
            "base liquidable para obtener la cuota integra previa, que luego se corrige con el "
            "coeficiente multiplicador segun patrimonio preexistente y grupo de parentesco. "
            "Tramos principales de la tarifa estatal 2025:\n"
            "- Hasta 7.993,46 EUR: 7,65%\n"
            "- De 7.993,46 a 15.980,91 EUR: cuota previa 611,50 + 8,50% sobre exceso\n"
            "- De 15.980,91 a 23.968,36 EUR: cuota previa 1.290,43 + 9,35% sobre exceso\n"
            "- De 23.968,36 a 31.955,81 EUR: cuota previa 2.037,26 + 10,20% sobre exceso\n"
            "- De 31.955,81 a 39.943,26 EUR: cuota previa 2.851,98 + 11,05% sobre exceso\n"
            "- De 39.943,26 a 47.930,72 EUR: cuota previa 3.734,59 + 11,90% sobre exceso\n"
            "- De 47.930,72 a 55.918,17 EUR: cuota previa 4.685,10 + 12,75% sobre exceso\n"
            "- De 55.918,17 a 63.905,62 EUR: cuota previa 5.703,50 + 13,60% sobre exceso\n"
            "- De 63.905,62 a 71.893,07 EUR: cuota previa 6.789,79 + 14,45% sobre exceso\n"
            "- De 71.893,07 a 79.880,52 EUR: cuota previa 7.943,98 + 15,30% sobre exceso\n"
            "- De 79.880,52 a 119.757,67 EUR: cuota previa 9.166,06 + 16,15% sobre exceso\n"
            "- De 119.757,67 a 159.634,83 EUR: cuota previa 15.606,22 + 18,70% sobre exceso\n"
            "- De 159.634,83 a 239.389,13 EUR: cuota previa 23.063,25 + 21,25% sobre exceso\n"
            "- De 239.389,13 a 398.777,54 EUR: cuota previa 40.011,04 + 25,50% sobre exceso\n"
            "- De 398.777,54 a 797.555,08 EUR: cuota previa 80.655,08 + 29,75% sobre exceso\n"
            "- Mas de 797.555,08 EUR: cuota previa 199.291,40 + 34,00% sobre exceso\n"
            "Esta tarifa se aplica como base cuando la CCAA no ha aprobado su propia tarifa "
            "(todos los territorios de regimen comun salvo los que la han modificado expresamente)."
        ),
        "metadata": {
            "territory": "estatal",
            "tax_type": "isd",
            "subtopic": "tarifa",
            "source": "Art. 21 Ley 29/1987",
        },
    },

    # ------------------------------------------------------------------
    # 3. Reducciones estatales por parentesco — Art. 20.2.a) Ley 29/1987
    # ------------------------------------------------------------------
    {
        "title": "ISD — Reducciones por parentesco, grupos I a IV (Art. 20 Ley 29/1987)",
        "content": (
            "Las reducciones de la base imponible por parentesco (Art. 20.2.a) Ley 29/1987) "
            "se aplican antes de calcular la cuota. Los cuatro grupos son:\n\n"
            "GRUPO I — Descendientes y adoptados menores de 21 anos:\n"
            "  Reduccion base: 15.956,87 EUR\n"
            "  Incremento por ano menor de 21: + 3.990,72 EUR por cada ano por debajo de 21\n"
            "  Limite maximo: 47.858,59 EUR\n"
            "  Ejemplo: heredero de 18 anos => 15.956,87 + 3 x 3.990,72 = 27.928,03 EUR\n\n"
            "GRUPO II — Descendientes y adoptados de 21 o mas anos, conyuges, ascendientes "
            "y adoptantes:\n"
            "  Reduccion fija: 15.956,87 EUR\n\n"
            "GRUPO III — Colaterales de segundo y tercer grado (hermanos, tios, sobrinos), "
            "ascendientes y descendientes por afinidad:\n"
            "  Reduccion fija: 7.993,46 EUR\n\n"
            "GRUPO IV — Colaterales de cuarto grado, grados mas distantes y extraños:\n"
            "  Sin reduccion por parentesco (0 EUR)\n\n"
            "Estas son las reducciones estatales minimas. Las CCAA pueden mejorarlas "
            "(ampliar importes o ampliar los grupos beneficiados)."
        ),
        "metadata": {
            "territory": "estatal",
            "tax_type": "isd",
            "subtopic": "reducciones_parentesco",
            "source": "Art. 20.2.a) Ley 29/1987",
        },
    },

    # ------------------------------------------------------------------
    # 4. Coeficientes multiplicadores — Art. 22 Ley 29/1987
    # ------------------------------------------------------------------
    {
        "title": "ISD — Coeficientes multiplicadores por patrimonio preexistente (Art. 22)",
        "content": (
            "El coeficiente multiplicador (Art. 22 Ley 29/1987) corrige la cuota integra segun "
            "el patrimonio preexistente del receptor y el grupo de parentesco. Un mayor patrimonio "
            "previo eleva la cuota a pagar. Tabla de coeficientes:\n\n"
            "Patrimonio preexistente hasta 402.678,11 EUR:\n"
            "  Grupos I y II: 1,0000 | Grupo III: 1,5882 | Grupo IV: 2,0000\n\n"
            "Patrimonio de 402.678,11 a 2.007.380,43 EUR:\n"
            "  Grupos I y II: 1,0500 | Grupo III: 1,6676 | Grupo IV: 2,1000\n\n"
            "Patrimonio de 2.007.380,43 a 4.020.770,98 EUR:\n"
            "  Grupos I y II: 1,1000 | Grupo III: 1,7471 | Grupo IV: 2,2000\n\n"
            "Patrimonio superior a 4.020.770,98 EUR:\n"
            "  Grupos I y II: 1,2000 | Grupo III: 1,9059 | Grupo IV: 2,4000\n\n"
            "Si el receptor no tiene patrimonio previo relevante, se aplica el coeficiente "
            "mas bajo (1,0 para Grupos I/II). Las CCAA pueden establecer sus propios "
            "coeficientes o eliminarlos."
        ),
        "metadata": {
            "territory": "estatal",
            "tax_type": "isd",
            "subtopic": "coeficientes_multiplicadores",
            "source": "Art. 22 Ley 29/1987",
        },
    },

    # ------------------------------------------------------------------
    # 5. Reducciones especiales: discapacidad
    # ------------------------------------------------------------------
    {
        "title": "ISD — Reduccion por discapacidad (Art. 20.2.a) Ley 29/1987)",
        "content": (
            "Ademas de la reduccion por parentesco, si el receptor tiene discapacidad reconocida "
            "se aplica una reduccion adicional sobre la base imponible:\n\n"
            "- Discapacidad >= 33% y < 65%: reduccion de 15.956,87 EUR\n"
            "- Discapacidad >= 65%: reduccion de 47.858,59 EUR\n\n"
            "Esta reduccion es acumulable a la reduccion por parentesco. Por ejemplo, un hijo "
            "mayor de 21 anos con discapacidad del 67% puede aplicar:\n"
            "  15.956,87 (Grupo II) + 47.858,59 (discapacidad >= 65%) = 63.815,46 EUR de reduccion.\n\n"
            "Las CCAA pueden mejorar estos importes. Muchas CCAA han ampliado la reduccion "
            "por discapacidad hasta 300.000 EUR o incluso la exencion total."
        ),
        "metadata": {
            "territory": "estatal",
            "tax_type": "isd",
            "subtopic": "reduccion_discapacidad",
            "source": "Art. 20.2.a) Ley 29/1987",
        },
    },

    # ------------------------------------------------------------------
    # 6. Reduccion vivienda habitual y empresa familiar
    # ------------------------------------------------------------------
    {
        "title": "ISD — Reduccion vivienda habitual y empresa familiar (Art. 20.2.c)",
        "content": (
            "Reducciones especiales en la base imponible del ISD (Art. 20.2.c) Ley 29/1987):\n\n"
            "VIVIENDA HABITUAL DEL CAUSANTE (solo sucesiones):\n"
            "  Reduccion del 95% del valor de la vivienda habitual, con limite de 122.606,47 EUR "
            "  por cada heredero. Solo aplicable a Grupos I, II y III (colaterales de 2.o-3.er grado). "
            "  El adquirente debe mantener la vivienda durante 10 anos (salvo fallecimiento previo).\n\n"
            "EMPRESA O NEGOCIO FAMILIAR (sucesiones y donaciones):\n"
            "  Reduccion del 95% del valor de la empresa individual, negocio profesional o "
            "  participaciones en entidades. Aplicable a conyuges, descendientes o adoptados; "
            "  en su defecto, ascendientes o colaterales hasta tercer grado. "
            "  Requisitos: empresa exenta en IP (actividad economica real, no patrimonial), "
            "  mantenimiento 10 anos.\n\n"
            "EXPLOTACION AGRARIA:\n"
            "  Reduccion del 90% al 100% segun normativa (Ley 19/1995 de modernizacion de "
            "  explotaciones agrarias).\n\n"
            "Las CCAA pueden ampliar estos porcentajes o reducir los periodos de mantenimiento."
        ),
        "metadata": {
            "territory": "estatal",
            "tax_type": "isd",
            "subtopic": "reducciones_especiales",
            "source": "Art. 20.2.c) Ley 29/1987",
        },
    },

    # ------------------------------------------------------------------
    # 7. Plazos de presentacion
    # ------------------------------------------------------------------
    {
        "title": "ISD — Plazos de presentacion y autoliquidacion",
        "content": (
            "Los plazos para presentar el ISD son distintos segun el tipo de operacion:\n\n"
            "SUCESIONES (mortis causa — herencias y legados):\n"
            "  Plazo general: 6 meses desde el fallecimiento del causante (Arts. 67 y 68 RISD).\n"
            "  Prorroga: prorrogable otros 6 meses adicionales si se solicita antes de que venza "
            "  el plazo inicial. La prorroga conlleva devengo de intereses de demora desde el "
            "  sexto mes. Total maximo: 12 meses desde el fallecimiento.\n\n"
            "DONACIONES (inter-vivos):\n"
            "  Plazo: 30 dias habiles desde la fecha del documento publico de donacion (Art. 67 RISD).\n"
            "  En donaciones de bienes inmuebles, la competencia corresponde a la CCAA donde "
            "  radican los inmuebles.\n"
            "  En donaciones de bienes muebles o dinero, la competencia corresponde a la CCAA "
            "  de residencia del donatario (receptor).\n\n"
            "SEGUROS DE VIDA:\n"
            "  Plazo: mismo que sucesiones si es mortis causa (6 meses desde el fallecimiento); "
            "  30 dias habiles si se percibe en vida del asegurado.\n\n"
            "La presentacion fuera de plazo conlleva recargo por presentacion extemporanea "
            "(del 1% al 20% segun el retraso, Art. 27 LGT) o sancion si hay requerimiento previo."
        ),
        "metadata": {
            "territory": "estatal",
            "tax_type": "isd",
            "subtopic": "plazos",
            "source": "Arts. 67-68 RISD (RD 1629/1991)",
        },
    },

    # ------------------------------------------------------------------
    # 8. CCAA Madrid
    # ------------------------------------------------------------------
    {
        "title": "ISD — Bonificacion Madrid (99%) — Grupos I y II",
        "content": (
            "La Comunidad de Madrid aplica una bonificacion del 99% en la cuota tributaria del ISD "
            "para los Grupos I y II de parentesco, tanto en sucesiones como en donaciones. "
            "Normativa: Art. 22 del Decreto Legislativo 1/2010, de 21 de octubre, por el que se "
            "aprueba el Texto Refundido de las Disposiciones Legales de la Comunidad de Madrid "
            "en materia de tributos cedidos.\n\n"
            "Efecto practico: hijos, conyuges y padres que hereden o reciban donaciones en Madrid "
            "pagan solo el 1% del impuesto calculado, lo que en la practica equivale a casi nada. "
            "Ejemplo: herencia de 200.000 EUR entre padre e hijo en Madrid resulta en una cuota "
            "efectiva de decenas de euros frente a varios miles en CCAA sin bonificacion.\n\n"
            "Grupos NO bonificados en Madrid: Grupo III (hermanos, tios, sobrinos) y Grupo IV "
            "(colaterales lejanos y extraños) tributan por la tarifa estatal sin bonificacion "
            "autonomica relevante.\n\n"
            "Madrid es una de las CCAA con mayor bonificacion ISD de Espana, junto con "
            "Andalucia y Aragon."
        ),
        "metadata": {
            "territory": "Madrid",
            "tax_type": "isd",
            "subtopic": "bonificacion_ccaa",
            "source": "Art. 22 DL 1/2010 Madrid",
        },
    },

    # ------------------------------------------------------------------
    # 9. CCAA Andalucia
    # ------------------------------------------------------------------
    {
        "title": "ISD — Bonificacion Andalucia (99%) — Grupos I y II hasta 1.000.000 EUR",
        "content": (
            "Andalucia aplica una bonificacion del 99% en la cuota tributaria del ISD para "
            "los Grupos I y II de parentesco, tanto en sucesiones como en donaciones, siempre "
            "que la base liquidable sea inferior a 1.000.000 EUR. "
            "Normativa: Art. 22 quinquies del Decreto Legislativo 1/2018, de 19 de junio.\n\n"
            "Si la base liquidable supera 1.000.000 EUR, la bonificacion no se aplica y se "
            "tributa por la tarifa estatal completa con coeficientes multiplicadores.\n\n"
            "Efecto practico: la gran mayoria de herencias entre padres e hijos o entre conyuges "
            "en Andalucia estan practicamente exentas. Solo las grandes herencias (>1M EUR) "
            "tributan de forma significativa.\n\n"
            "Historia: Andalucia elimino el ISD en 2019 para Grupos I/II, igualandose a Madrid "
            "en competitividad fiscal. Fue una de las reformas fiscales mas relevantes de "
            "una CCAA en la ultima decada."
        ),
        "metadata": {
            "territory": "Andalucia",
            "tax_type": "isd",
            "subtopic": "bonificacion_ccaa",
            "source": "Art. 22 quinquies DL 1/2018 Andalucia",
        },
    },

    # ------------------------------------------------------------------
    # 10. CCAA Valencia
    # ------------------------------------------------------------------
    {
        "title": "ISD — Bonificacion Valencia (75%) — sucesiones y donaciones Grupos I/II",
        "content": (
            "La Comunitat Valenciana aplica una bonificacion del 75% sobre la cuota tributaria "
            "del ISD en los siguientes supuestos:\n\n"
            "SUCESIONES: bonificacion del 75% para Grupos I (descendientes < 21 anos) y "
            "Grupo II (descendientes >= 21, conyuges, ascendientes).\n\n"
            "DONACIONES: bonificacion del 75% solo para Grupo I (descendientes menores de 21 anos). "
            "Las donaciones a hijos mayores de 21 anos o al conyuge no tienen bonificacion "
            "equivalente en donaciones.\n\n"
            "Normativa: Ley 13/1997, de 23 de diciembre, de la Generalitat Valenciana, "
            "modificada por la Ley 8/2022.\n\n"
            "Valencia sigue siendo una CCAA con carga fiscal ISD moderada para herencias "
            "directas, pero mas elevada que Madrid o Andalucia (75% vs 99% de bonificacion). "
            "Grupos III y IV tributan sin bonificacion especial."
        ),
        "metadata": {
            "territory": "Valencia",
            "tax_type": "isd",
            "subtopic": "bonificacion_ccaa",
            "source": "Ley 13/1997 Valencia, mod. Ley 8/2022",
        },
    },

    # ------------------------------------------------------------------
    # 11. CCAA Aragon
    # ------------------------------------------------------------------
    {
        "title": "ISD — Bonificacion Aragon (99%) — sucesiones hasta 500.000 EUR",
        "content": (
            "Aragon aplica una bonificacion del 99% en la cuota tributaria del ISD en sucesiones "
            "para los Grupos I y II, siempre que la base imponible total no supere 500.000 EUR. "
            "Normativa: Decreto Legislativo 1/2005, de 26 de septiembre, modificado por "
            "la Ley 10/2021 de Aragon.\n\n"
            "Importante: la bonificacion se aplica a SUCESIONES pero no necesariamente a "
            "donaciones, donde el tratamiento es diferente. Para donaciones en Aragon, "
            "se aplica la tarifa estatal sin bonificacion del 99%.\n\n"
            "Si la herencia supera 500.000 EUR, la bonificacion del 99% no se aplica y "
            "el heredero tributa por la tarifa estatal completa (tramos del 7,65% al 34%).\n\n"
            "Aragon es una de las tres CCAA con mayor bonificacion ISD (junto con Madrid "
            "y Andalucia) para herencias moderadas entre familiares directos."
        ),
        "metadata": {
            "territory": "Aragon",
            "tax_type": "isd",
            "subtopic": "bonificacion_ccaa",
            "source": "DL 1/2005 Aragon, mod. Ley 10/2021",
        },
    },

    # ------------------------------------------------------------------
    # 12. CCAA Cataluna
    # ------------------------------------------------------------------
    {
        "title": "ISD — Cataluna: sistema de coeficientes reductores progresivos",
        "content": (
            "Cataluna aplica un sistema propio de coeficientes reductores sobre la cuota tributaria "
            "del ISD, regulado por la Ley 19/2010, de 7 de junio, del ISD en Cataluna. "
            "El descuento disminuye a medida que aumenta la base liquidable:\n\n"
            "Para Grupos I y II de parentesco (Grupos I y II de la normativa estatal):\n"
            "  - Base liquidable hasta 100.000 EUR: bonificacion del 99% (cuota efectiva: 1%)\n"
            "  - Base liquidable de 100.000 a 500.000 EUR: bonificacion del 50% (cuota efectiva: 50%)\n"
            "  - Base liquidable superior a 500.000 EUR: bonificacion del 20% (cuota efectiva: 80%)\n\n"
            "Efecto practico: Cataluna es intermedia en bonificacion ISD — protege herencias "
            "pequenas (hasta 100k) casi como Madrid, pero para herencias medianas o grandes "
            "la carga fiscal es significativamente mayor. \n\n"
            "Nota: Cataluna tiene su propio sistema de grupos de parentesco (I al IV) que "
            "no coincide exactamente con los grupos de la ley estatal. La normativa catalana "
            "es especialmente relevante para residentes en Barcelona y alrededores.\n\n"
            "Para donaciones en Cataluna, el tratamiento puede diferir; conviene consultar "
            "la normativa vigente cada ejercicio fiscal."
        ),
        "metadata": {
            "territory": "Cataluna",
            "tax_type": "isd",
            "subtopic": "bonificacion_ccaa",
            "source": "Ley 19/2010 Cataluna",
        },
    },

    # ------------------------------------------------------------------
    # 13. Territorios Forales: Araba, Bizkaia, Gipuzkoa
    # ------------------------------------------------------------------
    {
        "title": "ISD — Pais Vasco (Araba, Bizkaia, Gipuzkoa): exencion para Grupos I y II",
        "content": (
            "Los tres Territorios Historicos del Pais Vasco tienen competencia fiscal plena "
            "sobre el ISD mediante sus propias Normas Forales:\n\n"
            "  - Araba/Alava: Norma Foral 11/2005 de las Juntas Generales de Alava\n"
            "  - Bizkaia: Norma Foral 4/2015 de las Juntas Generales de Bizkaia\n"
            "  - Gipuzkoa: Norma Foral 3/1990 de las Juntas Generales de Gipuzkoa\n\n"
            "Para los Grupos I y II (descendientes, conyuges, ascendientes), las Normas Forales "
            "establecen una exencion practicamente total en sucesiones y donaciones. En la "
            "practica, heredar de padres o donar a hijos en el Pais Vasco NO genera impuesto "
            "a pagar.\n\n"
            "Para el Grupo III (hermanos, tios, sobrinos), la normativa foral aplica "
            "reducciones parciales de aproximadamente el 50%, aunque los tipos de la tarifa "
            "foral son muy inferiores a la tarifa estatal.\n\n"
            "El Pais Vasco es, junto con Navarra, el territorio con menor carga fiscal en ISD "
            "de toda Espana. Esto se debe a su regimen de Concierto Economico (Concierto "
            "Economico con el Estado, Ley 12/2002)."
        ),
        "metadata": {
            "territory": "Pais Vasco",
            "tax_type": "isd",
            "subtopic": "bonificacion_ccaa",
            "source": "NF 11/2005 Araba / NF 4/2015 Bizkaia / NF 3/1990 Gipuzkoa",
        },
    },

    # ------------------------------------------------------------------
    # 14. Navarra
    # ------------------------------------------------------------------
    {
        "title": "ISD — Navarra: exencion sucesiones y tarifa propia donaciones",
        "content": (
            "Navarra tiene competencia fiscal propia sobre el ISD mediante la Ley Foral "
            "11/2022, de 23 de diciembre (y sus antecedentes), en virtud del Convenio "
            "Economico con el Estado.\n\n"
            "SUCESIONES:\n"
            "  Conyuge y descendientes directos (linea directa Grupos I y II): exencion total "
            "  en sucesiones. No se paga ISD por heredar de padres o entre conyuges.\n\n"
            "DONACIONES:\n"
            "  Navarra aplica su propia tarifa de donaciones, considerablemente inferior a "
            "  la tarifa estatal. Para Grupos I y II, la reduccion efectiva es de aprox. 50% "
            "  respecto a lo que se pagaria por la tarifa estatal, aunque el calculo exacto "
            "  depende del importe donado.\n\n"
            "Navarra, junto con el Pais Vasco, es el territorio mas favorable en Espana para "
            "transmisiones patrimoniales gratuitas entre familiares directos. La diferencia "
            "entre tributar en Navarra y en Madrid (ya de por si con 99% de bonificacion) "
            "es minima para herencias moderadas."
        ),
        "metadata": {
            "territory": "Navarra",
            "tax_type": "isd",
            "subtopic": "bonificacion_ccaa",
            "source": "Ley Foral 11/2022 Navarra",
        },
    },

    # ------------------------------------------------------------------
    # 15. Canarias
    # ------------------------------------------------------------------
    {
        "title": "ISD — Canarias: bonificacion del 99,9% para Grupos I y II",
        "content": (
            "Las Islas Canarias aplican una de las bonificaciones mas generosas del territorio "
            "comun: un 99,9% de descuento sobre la cuota tributaria del ISD para los Grupos I "
            "y II de parentesco (descendientes, ascendientes y conyuges), tanto en sucesiones "
            "como en donaciones.\n\n"
            "Normativa: Decreto Legislativo 1/2009, de 21 de abril, por el que se aprueba el "
            "Texto Refundido de las disposiciones legales vigentes en materia de tributos cedidos "
            "del Gobierno de Canarias, con las modificaciones posteriores.\n\n"
            "Efecto practico: heredar de padres o entre conyuges en Canarias resulta en una cuota "
            "efectiva del 0,1% del impuesto calculado, que en la mayoria de los casos es una "
            "cantidad simbolica de pocos euros.\n\n"
            "Canarias es comparable en bonificacion ISD a Madrid y Andalucia para familias "
            "directas. La ventaja de Canarias es su aplicacion tambien a donaciones, a diferencia "
            "de Aragon (solo sucesiones hasta 500k)."
        ),
        "metadata": {
            "territory": "Canarias",
            "tax_type": "isd",
            "subtopic": "bonificacion_ccaa",
            "source": "DL 1/2009 Canarias",
        },
    },

    # ------------------------------------------------------------------
    # 16. Ceuta y Melilla
    # ------------------------------------------------------------------
    {
        "title": "ISD — Ceuta y Melilla: bonificacion del 50%",
        "content": (
            "Las Ciudades Autonomas de Ceuta y Melilla aplican una bonificacion del 50% sobre "
            "la cuota del ISD para adquisiciones mortis causa (sucesiones) y donaciones "
            "cuando el causante o donante y el receptor tengan su residencia habitual en "
            "estas ciudades.\n\n"
            "A diferencia de comunidades como Madrid (99%) o Canarias (99,9%), la bonificacion "
            "de Ceuta y Melilla es mas moderada. Un heredero que reciba 200.000 EUR en Ceuta "
            "pagaria aproximadamente la mitad de lo que pagaria en una CCAA sin bonificacion "
            "(como Castilla-La Mancha o Extremadura en algunos supuestos).\n\n"
            "Normativa: Ley 50/1998, de 30 de diciembre, de Medidas Fiscales, Administrativas "
            "y del Orden Social (disposicion adicional decimocuarta para Ceuta y Melilla), "
            "con modificaciones posteriores.\n\n"
            "Adicionalmente, los residentes en Ceuta y Melilla ya disfrutan de la deduccion "
            "del 60% en IRPF (Art. 68.4 LIRPF), lo que hace que la carga fiscal global "
            "sea significativamente inferior a la media espanola."
        ),
        "metadata": {
            "territory": "Ceuta y Melilla",
            "tax_type": "isd",
            "subtopic": "bonificacion_ccaa",
            "source": "DA 14.a Ley 50/1998",
        },
    },

    # ------------------------------------------------------------------
    # 17. CCAA sin bonificacion relevante o con cargas altas
    # ------------------------------------------------------------------
    {
        "title": "ISD — CCAA sin bonificaciones destacadas: Castilla-La Mancha, Extremadura, "
                 "Murcia, La Rioja, Cantabria, Asturias",
        "content": (
            "Varias Comunidades Autonomas no han aprobado bonificaciones equivalentes a las de "
            "Madrid, Andalucia o Canarias. En estas CCAA, las herencias y donaciones entre "
            "familiares directos pueden generar cuotas significativas:\n\n"
            "CASTILLA-LA MANCHA: mejoras sobre la tarifa estatal y algunas reducciones, pero "
            "sin bonificacion general del 95%+ para Grupos I/II. Herencias medianas tributan "
            "efectivamente.\n\n"
            "EXTREMADURA: reducciones mejoradas para Grupos I/II pero la bonificacion es "
            "inferior a la de Madrid o Andalucia. Herencias de importe medio generan cuota "
            "relevante.\n\n"
            "ASTURIAS: dispone de mejoras en reducciones pero la bonificacion total no alcanza "
            "el nivel de Madrid. Se aplica la tarifa estatal con modificaciones moderadas.\n\n"
            "CANTABRIA: similar a Asturias, con bonificaciones parciales.\n\n"
            "LA RIOJA: reducciones mejoradas para descendientes y conyuges, pero la bonificacion "
            "no es del 99%. Tipos efectivos por encima de Madrid o Andalucia.\n\n"
            "MURCIA: mejoras progresivas en los ultimos anos pero sin llegar al nivel de "
            "las CCAA con mayor bonificacion.\n\n"
            "Recomendacion: para herencias en estas CCAA, es especialmente importante calcular "
            "la cuota exacta con la herramienta ISD del sistema, ya que puede ser considerable."
        ),
        "metadata": {
            "territory": "estatal",
            "tax_type": "isd",
            "subtopic": "ccaa_sin_bonificacion_alta",
            "source": "Normativas autonomicas vigentes 2025",
        },
    },

    # ------------------------------------------------------------------
    # 18. Diferencias clave: sucesion vs donacion
    # ------------------------------------------------------------------
    {
        "title": "ISD — Diferencias clave entre sucesion y donacion",
        "content": (
            "Aunque ambas son transmisiones gratuitas, sucesion y donacion tienen tratamientos "
            "fiscales distintos en el ISD:\n\n"
            "SUCESION (mortis causa — herencia):\n"
            "  - Se produce por fallecimiento del causante.\n"
            "  - Plazo de liquidacion: 6 meses desde el fallecimiento (prorrogable 6 meses mas).\n"
            "  - Competencia: CCAA de residencia habitual del causante (fallecido).\n"
            "  - Reducciones mas amplias: vivienda habitual, empresa familiar, reduccion "
            "    por parentesco plena.\n"
            "  - Muchas CCAA con bonificaciones del 99% en sucesiones.\n\n"
            "DONACION (inter-vivos):\n"
            "  - Se produce en vida del donante.\n"
            "  - Plazo de liquidacion: 30 dias habiles desde la fecha de la escritura publica.\n"
            "  - Competencia: CCAA donde esten los bienes inmuebles (para inmuebles) o "
            "    CCAA de residencia del donatario (para bienes muebles y dinero).\n"
            "  - La reduccion por parentesco se aplica igual que en sucesiones.\n"
            "  - Ojo: algunas CCAA con alta bonificacion en sucesiones (Aragon, Valencia) "
            "    tienen menor bonificacion en donaciones.\n"
            "  - Para donaciones en efectivo (dinero), se recomienda hacerlo mediante "
            "    transferencia documentada y con escritura notarial para facilitar la "
            "    justificacion ante Hacienda.\n\n"
            "SEGUROS DE VIDA:\n"
            "  - Cuarto hecho imponible del ISD.\n"
            "  - El beneficiario tributa por la cantidad recibida menos la reduccion estatutaria.\n"
            "  - Si el contratante y el asegurado son la misma persona, no hay hecho imponible "
            "    de ISD (pero si puede haberlo de IRPF)."
        ),
        "metadata": {
            "territory": "estatal",
            "tax_type": "isd",
            "subtopic": "sucesion_vs_donacion",
            "source": "Ley 29/1987 Arts. 3, 5, 24, 67 RISD",
        },
    },

    # ------------------------------------------------------------------
    # 19. Preguntas frecuentes y casos practicos
    # ------------------------------------------------------------------
    {
        "title": "ISD — Preguntas frecuentes: cuanto se paga por heredar, donar dinero, casa",
        "content": (
            "Preguntas frecuentes sobre ISD en Espana:\n\n"
            "P: Si mis padres me dan 50.000 EUR en donacion, cuanto pago?\n"
            "R: Depende de la CCAA de residencia del receptor (para dinero). En Madrid o "
            "Andalucia: casi nada (bonificacion 99%). En Cataluna: base liquidable 50.000 - "
            "15.956,87 = 34.043 EUR => cuota ~2.600 EUR, bonificacion 99% = ~26 EUR. "
            "En CCAA sin bonificacion alta: cuota de ~2.600 EUR sin reduccion.\n\n"
            "P: Mi madre ha fallecido y me deja 200.000 EUR. Cuanto pago de ISD en Madrid?\n"
            "R: Base imponible 200.000 - 15.956,87 (reduccion Grupo II) = 184.043 EUR. "
            "Cuota tarifa estatal ~35.000 EUR. Bonificacion Madrid 99%: cuota a pagar ~350 EUR.\n\n"
            "P: Tengo que pagar ISD si heredo en el Pais Vasco?\n"
            "R: Si eres hijo/a o conyuge del fallecido (Grupos I y II), en el Pais Vasco "
            "la cuota es practicamente cero. La normativa foral establece exencion casi total.\n\n"
            "P: Cuando prescribe el ISD?\n"
            "R: El derecho de la Administracion para liquidar el ISD prescribe a los 4 anos "
            "desde que vence el plazo de presentacion (Art. 66 LGT). Si no se presenta "
            "la declaracion, el plazo de prescripcion puede ser mayor al no haberse "
            "iniciado el computo.\n\n"
            "P: Hay que declarar el ISD aunque no salga a pagar?\n"
            "R: Si, es obligatorio presentar la autoliquidacion aunque la cuota sea cero "
            "(por aplicacion de reducciones o bonificaciones). No presentar puede generar "
            "sancion por infraccion tributaria formal."
        ),
        "metadata": {
            "territory": "estatal",
            "tax_type": "isd",
            "subtopic": "faq",
            "source": "Ley 29/1987 + normativas CCAA",
        },
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _doc_hash(title: str) -> str:
    return hashlib.sha256(title.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

async def seed_isd_knowledge(dry_run: bool = False) -> None:
    """Insert ISD knowledge document and chunks into the RAG database."""
    print(f"ISD Knowledge Seed — {'DRY RUN' if dry_run else 'PRODUCTION'}")
    print(f"Document: {ISD_DOCUMENT['title']}")
    print(f"Chunks to insert: {len(ISD_CHUNKS)}\n")

    if dry_run:
        for i, chunk in enumerate(ISD_CHUNKS):
            print(f"  [{i:02d}] {chunk['title']}")
            print(f"       territory={chunk['metadata']['territory']}, "
                  f"subtopic={chunk['metadata']['subtopic']}")
        print(f"\nTotal: {len(ISD_CHUNKS)} chunks | Dry run complete. Nothing written.")
        return

    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()
    await db.init_schema()

    # -- Insert document (idempotent by hash) --
    doc_hash = _doc_hash(ISD_DOCUMENT["title"])
    doc_id = str(uuid.uuid4())

    existing_doc = await db.execute(
        "SELECT id FROM documents WHERE hash = ?", [doc_hash]
    )
    if existing_doc.rows:
        doc_id = existing_doc.rows[0]["id"]
        print(f"Document already exists (id={doc_id}), reusing it.")
    else:
        await db.execute(
            """INSERT INTO documents
               (id, filename, filepath, title, document_type, year, source,
                processed, processing_status, hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                doc_id,
                ISD_DOCUMENT["filename"],
                ISD_DOCUMENT["filepath"],
                ISD_DOCUMENT["title"],
                ISD_DOCUMENT["document_type"],
                ISD_DOCUMENT["year"],
                ISD_DOCUMENT["source"],
                1,           # processed = true (no PDF, direct text)
                "complete",
                doc_hash,
            ],
        )
        print(f"Document inserted (id={doc_id}).")

    # -- Insert chunks --
    inserted = 0
    skipped = 0

    for chunk_index, chunk in enumerate(ISD_CHUNKS):
        chunk_id = str(uuid.uuid4())
        content = chunk["content"]
        metadata_json = json.dumps(chunk["metadata"], ensure_ascii=False)
        c_hash = _content_hash(content)

        try:
            # Check if chunk already exists for this document + index
            existing = await db.execute(
                "SELECT id FROM document_chunks WHERE document_id = ? AND chunk_index = ?",
                [doc_id, chunk_index],
            )
            if existing.rows:
                skipped += 1
                continue

            await db.execute(
                """INSERT INTO document_chunks
                   (id, document_id, chunk_index, content, content_hash, metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [chunk_id, doc_id, chunk_index, content, c_hash, metadata_json],
            )
            inserted += 1
        except Exception as exc:
            print(f"  Error inserting chunk {chunk_index} ({chunk['title'][:40]}): {exc}")
            skipped += 1

    await db.disconnect()

    print(f"\nSeed complete:")
    print(f"  Chunks inserted : {inserted}")
    print(f"  Chunks skipped  : {skipped} (already existed)")
    print(f"  Total chunks    : {len(ISD_CHUNKS)}")
    print(f"\nThe ISD knowledge base is now available for RAG queries.")
    print(f"Topics covered: tarifa estatal, reducciones parentesco, coeficientes,")
    print(f"  discapacidad, vivienda habitual, empresa familiar, plazos,")
    print(f"  Madrid, Andalucia, Valencia, Aragon, Cataluna, Pais Vasco,")
    print(f"  Navarra, Canarias, Ceuta/Melilla, FAQ.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed ISD knowledge base into RAG document_chunks table"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be inserted without writing to the database",
    )
    args = parser.parse_args()
    asyncio.run(seed_isd_knowledge(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
