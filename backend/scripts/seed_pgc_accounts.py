"""
Seed Plan General Contable (PGC) accounts.
~250 accounts covering 95%+ of real-world invoice classification
for Spanish autonomos and PYMEs (groups 1-7).
Idempotent: deletes existing and re-inserts.

Usage:
    cd backend
    PYTHONUTF8=1 python scripts/seed_pgc_accounts.py
"""
import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

PGC_ACCOUNTS = [
    # =============================================
    # GRUPO 1 — FINANCIACION BASICA (type: "balance")
    # =============================================
    {"code": "100", "name": "Capital social", "group_code": "10", "group_name": "Capital", "type": "balance"},
    {"code": "102", "name": "Capital empresario individual", "group_code": "10", "group_name": "Capital", "type": "balance",
     "common_for": ["autonomo"]},
    {"code": "110", "name": "Prima de emision o asuncion", "group_code": "11", "group_name": "Reservas y otros instrumentos de patrimonio", "type": "balance"},
    {"code": "112", "name": "Reserva legal", "group_code": "11", "group_name": "Reservas y otros instrumentos de patrimonio", "type": "balance",
     "common_for": ["sociedad"]},
    {"code": "113", "name": "Reservas voluntarias", "group_code": "11", "group_name": "Reservas y otros instrumentos de patrimonio", "type": "balance",
     "common_for": ["sociedad"]},
    {"code": "118", "name": "Aportaciones de socios o propietarios", "group_code": "11", "group_name": "Reservas y otros instrumentos de patrimonio", "type": "balance"},
    {"code": "120", "name": "Remanente", "group_code": "12", "group_name": "Resultados pendientes de aplicacion", "type": "balance"},
    {"code": "121", "name": "Resultados negativos de ejercicios anteriores", "group_code": "12", "group_name": "Resultados pendientes de aplicacion", "type": "balance"},
    {"code": "129", "name": "Resultado del ejercicio", "group_code": "12", "group_name": "Resultados pendientes de aplicacion", "type": "balance"},
    {"code": "130", "name": "Subvenciones oficiales de capital", "group_code": "13", "group_name": "Subvenciones donaciones y ajustes por cambios de valor", "type": "balance"},
    {"code": "131", "name": "Donaciones y legados de capital", "group_code": "13", "group_name": "Subvenciones donaciones y ajustes por cambios de valor", "type": "balance"},
    {"code": "141", "name": "Provision para impuestos", "group_code": "14", "group_name": "Provisiones", "type": "balance"},
    {"code": "142", "name": "Provision para otras responsabilidades", "group_code": "14", "group_name": "Provisiones", "type": "balance"},
    {"code": "170", "name": "Deudas a largo plazo con entidades de credito", "group_code": "17", "group_name": "Deudas a largo plazo por prestamos recibidos y otros conceptos", "type": "balance"},
    {"code": "171", "name": "Deudas a largo plazo", "group_code": "17", "group_name": "Deudas a largo plazo por prestamos recibidos y otros conceptos", "type": "balance"},
    {"code": "173", "name": "Proveedores de inmovilizado a largo plazo", "group_code": "17", "group_name": "Deudas a largo plazo por prestamos recibidos y otros conceptos", "type": "balance"},
    {"code": "174", "name": "Acreedores por arrendamiento financiero a largo plazo", "group_code": "17", "group_name": "Deudas a largo plazo por prestamos recibidos y otros conceptos", "type": "balance"},
    {"code": "175", "name": "Efectos a pagar a largo plazo", "group_code": "17", "group_name": "Deudas a largo plazo por prestamos recibidos y otros conceptos", "type": "balance"},
    {"code": "180", "name": "Fianzas recibidas a largo plazo", "group_code": "18", "group_name": "Pasivos por fianzas garantias y otros conceptos a largo plazo", "type": "balance"},

    # =============================================
    # GRUPO 2 — ACTIVO NO CORRIENTE (type: "balance")
    # =============================================
    {"code": "200", "name": "Investigacion", "group_code": "20", "group_name": "Inmovilizaciones intangibles", "type": "balance"},
    {"code": "201", "name": "Desarrollo", "group_code": "20", "group_name": "Inmovilizaciones intangibles", "type": "balance"},
    {"code": "202", "name": "Concesiones administrativas", "group_code": "20", "group_name": "Inmovilizaciones intangibles", "type": "balance"},
    {"code": "203", "name": "Propiedad industrial", "group_code": "20", "group_name": "Inmovilizaciones intangibles", "type": "balance"},
    {"code": "205", "name": "Derechos de traspaso", "group_code": "20", "group_name": "Inmovilizaciones intangibles", "type": "balance"},
    {"code": "206", "name": "Aplicaciones informaticas", "group_code": "20", "group_name": "Inmovilizaciones intangibles", "type": "balance",
     "keywords": ["software", "licencia", "programa", "app", "erp"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "209", "name": "Anticipos para inmovilizaciones intangibles", "group_code": "20", "group_name": "Inmovilizaciones intangibles", "type": "balance"},
    {"code": "210", "name": "Terrenos y bienes naturales", "group_code": "21", "group_name": "Inmovilizaciones materiales", "type": "balance"},
    {"code": "211", "name": "Construcciones", "group_code": "21", "group_name": "Inmovilizaciones materiales", "type": "balance"},
    {"code": "212", "name": "Instalaciones tecnicas", "group_code": "21", "group_name": "Inmovilizaciones materiales", "type": "balance"},
    {"code": "213", "name": "Maquinaria", "group_code": "21", "group_name": "Inmovilizaciones materiales", "type": "balance"},
    {"code": "214", "name": "Utillaje", "group_code": "21", "group_name": "Inmovilizaciones materiales", "type": "balance"},
    {"code": "215", "name": "Otras instalaciones", "group_code": "21", "group_name": "Inmovilizaciones materiales", "type": "balance"},
    {"code": "216", "name": "Mobiliario", "group_code": "21", "group_name": "Inmovilizaciones materiales", "type": "balance",
     "keywords": ["mueble", "estanteria", "mesa", "silla", "mobiliario"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "217", "name": "Equipos para procesos de informacion", "group_code": "21", "group_name": "Inmovilizaciones materiales", "type": "balance",
     "keywords": ["ordenador", "portatil", "servidor", "impresora", "monitor", "tablet"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "218", "name": "Elementos de transporte", "group_code": "21", "group_name": "Inmovilizaciones materiales", "type": "balance",
     "keywords": ["vehiculo", "coche", "furgoneta", "moto", "transporte"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "219", "name": "Otro inmovilizado material", "group_code": "21", "group_name": "Inmovilizaciones materiales", "type": "balance"},
    {"code": "220", "name": "Inversiones en terrenos y bienes naturales", "group_code": "22", "group_name": "Inversiones inmobiliarias", "type": "balance"},
    {"code": "221", "name": "Inversiones en construcciones", "group_code": "22", "group_name": "Inversiones inmobiliarias", "type": "balance"},
    {"code": "239", "name": "Anticipos para inmovilizaciones materiales", "group_code": "23", "group_name": "Inmovilizaciones materiales en curso", "type": "balance"},
    {"code": "240", "name": "Participaciones a largo plazo en partes vinculadas", "group_code": "24", "group_name": "Inversiones financieras a largo plazo en partes vinculadas", "type": "balance"},
    {"code": "250", "name": "Inversiones financieras a largo plazo en instrumentos de patrimonio", "group_code": "25", "group_name": "Otras inversiones financieras a largo plazo", "type": "balance"},
    {"code": "252", "name": "Creditos a largo plazo", "group_code": "25", "group_name": "Otras inversiones financieras a largo plazo", "type": "balance"},
    {"code": "258", "name": "Imposiciones a largo plazo", "group_code": "25", "group_name": "Otras inversiones financieras a largo plazo", "type": "balance"},
    {"code": "260", "name": "Fianzas constituidas a largo plazo", "group_code": "26", "group_name": "Fianzas y depositos constituidos a largo plazo", "type": "balance"},
    {"code": "265", "name": "Depositos constituidos a largo plazo", "group_code": "26", "group_name": "Fianzas y depositos constituidos a largo plazo", "type": "balance"},
    {"code": "280", "name": "Amortizacion acumulada del inmovilizado intangible", "group_code": "28", "group_name": "Amortizacion acumulada del inmovilizado", "type": "balance"},
    {"code": "281", "name": "Amortizacion acumulada del inmovilizado material", "group_code": "28", "group_name": "Amortizacion acumulada del inmovilizado", "type": "balance"},
    {"code": "282", "name": "Amortizacion acumulada de las inversiones inmobiliarias", "group_code": "28", "group_name": "Amortizacion acumulada del inmovilizado", "type": "balance"},
    {"code": "290", "name": "Deterioro de valor del inmovilizado intangible", "group_code": "29", "group_name": "Deterioro de valor de activos no corrientes", "type": "balance"},
    {"code": "291", "name": "Deterioro de valor del inmovilizado material", "group_code": "29", "group_name": "Deterioro de valor de activos no corrientes", "type": "balance"},

    # =============================================
    # GRUPO 3 — EXISTENCIAS (type: "balance")
    # =============================================
    {"code": "300", "name": "Mercaderias", "group_code": "30", "group_name": "Comerciales", "type": "balance",
     "keywords": ["mercaderia", "stock", "inventario", "almacen"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "310", "name": "Materias primas", "group_code": "31", "group_name": "Materias primas", "type": "balance"},
    {"code": "320", "name": "Elementos y conjuntos incorporables", "group_code": "32", "group_name": "Otros aprovisionamientos", "type": "balance"},
    {"code": "321", "name": "Combustibles", "group_code": "32", "group_name": "Otros aprovisionamientos", "type": "balance",
     "keywords": ["gasolina", "diesel", "combustible", "gasoil"]},
    {"code": "322", "name": "Repuestos", "group_code": "32", "group_name": "Otros aprovisionamientos", "type": "balance"},
    {"code": "325", "name": "Materiales diversos", "group_code": "32", "group_name": "Otros aprovisionamientos", "type": "balance"},
    {"code": "326", "name": "Embalajes", "group_code": "32", "group_name": "Otros aprovisionamientos", "type": "balance"},
    {"code": "327", "name": "Envases", "group_code": "32", "group_name": "Otros aprovisionamientos", "type": "balance"},
    {"code": "328", "name": "Material de oficina", "group_code": "32", "group_name": "Otros aprovisionamientos", "type": "balance",
     "keywords": ["papel", "toner", "material oficina", "papeleria"]},
    {"code": "350", "name": "Productos terminados", "group_code": "35", "group_name": "Productos terminados", "type": "balance"},
    {"code": "390", "name": "Deterioro de valor de las mercaderias", "group_code": "39", "group_name": "Deterioro de valor de las existencias", "type": "balance"},
    {"code": "391", "name": "Deterioro de valor de las materias primas", "group_code": "39", "group_name": "Deterioro de valor de las existencias", "type": "balance"},

    # =============================================
    # GRUPO 4 — ACREEDORES Y DEUDORES (type: "balance")
    # =============================================
    {"code": "400", "name": "Proveedores", "group_code": "40", "group_name": "Proveedores", "type": "balance",
     "keywords": ["proveedor", "compra", "suministro", "mercaderia", "factura recibida"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "4009", "name": "Proveedores facturas pendientes de recibir", "group_code": "40", "group_name": "Proveedores", "type": "balance"},
    {"code": "401", "name": "Proveedores efectos comerciales a pagar", "group_code": "40", "group_name": "Proveedores", "type": "balance",
     "keywords": ["letra", "pagare", "efecto comercial"]},
    {"code": "403", "name": "Proveedores empresas del grupo", "group_code": "40", "group_name": "Proveedores", "type": "balance",
     "common_for": ["sociedad"]},
    {"code": "406", "name": "Envases y embalajes a devolver a proveedores", "group_code": "40", "group_name": "Proveedores", "type": "balance"},
    {"code": "407", "name": "Anticipos a proveedores", "group_code": "40", "group_name": "Proveedores", "type": "balance",
     "keywords": ["anticipo", "pago anticipado", "provision fondos"]},
    {"code": "410", "name": "Acreedores por prestaciones de servicios", "group_code": "41", "group_name": "Acreedores varios", "type": "balance",
     "keywords": ["servicio", "asesoria", "consultoria", "profesional", "factura servicio"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "4109", "name": "Acreedores facturas pendientes de recibir", "group_code": "41", "group_name": "Acreedores varios", "type": "balance"},
    {"code": "411", "name": "Acreedores efectos comerciales a pagar", "group_code": "41", "group_name": "Acreedores varios", "type": "balance"},
    {"code": "430", "name": "Clientes", "group_code": "43", "group_name": "Clientes", "type": "balance",
     "keywords": ["cliente", "venta", "factura emitida", "cobro"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "4309", "name": "Clientes facturas pendientes de formalizar", "group_code": "43", "group_name": "Clientes", "type": "balance"},
    {"code": "431", "name": "Clientes efectos comerciales a cobrar", "group_code": "43", "group_name": "Clientes", "type": "balance",
     "keywords": ["letra cobrar", "pagare cobrar", "efecto cobrar"]},
    {"code": "432", "name": "Clientes operaciones de factoring", "group_code": "43", "group_name": "Clientes", "type": "balance",
     "keywords": ["factoring", "cesion creditos"]},
    {"code": "433", "name": "Clientes empresas del grupo", "group_code": "43", "group_name": "Clientes", "type": "balance",
     "common_for": ["sociedad"]},
    {"code": "436", "name": "Clientes de dudoso cobro", "group_code": "43", "group_name": "Clientes", "type": "balance",
     "keywords": ["impagado", "moroso", "dudoso cobro", "incobrable"]},
    {"code": "438", "name": "Anticipos de clientes", "group_code": "43", "group_name": "Clientes", "type": "balance",
     "keywords": ["anticipo cliente", "cobro anticipado", "senal"]},
    {"code": "440", "name": "Deudores", "group_code": "44", "group_name": "Deudores varios", "type": "balance",
     "keywords": ["deudor", "cobro pendiente"]},
    {"code": "446", "name": "Deudores de dudoso cobro", "group_code": "44", "group_name": "Deudores varios", "type": "balance"},
    {"code": "460", "name": "Anticipos de remuneraciones", "group_code": "46", "group_name": "Personal", "type": "balance",
     "keywords": ["anticipo nomina", "adelanto empleado"],
     "common_for": ["sociedad"]},
    {"code": "465", "name": "Remuneraciones pendientes de pago", "group_code": "46", "group_name": "Personal", "type": "balance",
     "keywords": ["nomina pendiente", "paga extra", "liquidacion"],
     "common_for": ["sociedad"]},
    {"code": "470", "name": "Hacienda Publica deudora por diversos conceptos", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance"},
    {"code": "4700", "name": "Hacienda Publica deudora por IVA", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance",
     "keywords": ["iva a compensar", "iva negativo", "devolucion iva"]},
    {"code": "4708", "name": "Hacienda Publica deudora por subvenciones concedidas", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance"},
    {"code": "4709", "name": "Hacienda Publica deudora por devolucion de impuestos", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance",
     "keywords": ["devolucion", "renta devolver"]},
    {"code": "471", "name": "Organismos de la Seguridad Social deudores", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance"},
    {"code": "472", "name": "Hacienda Publica IVA soportado", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance",
     "keywords": ["iva", "soportado", "deducible", "iva compras"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "473", "name": "Hacienda Publica retenciones y pagos a cuenta", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance",
     "keywords": ["retencion", "pago cuenta", "irpf retenido", "modelo 130"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "475", "name": "Hacienda Publica acreedora por conceptos fiscales", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance",
     "keywords": ["impuesto pagar", "liquidacion fiscal"]},
    {"code": "4750", "name": "Hacienda Publica acreedora por IVA", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance",
     "keywords": ["iva a pagar", "iva positivo", "liquidacion iva"]},
    {"code": "4751", "name": "Hacienda Publica acreedora por retenciones practicadas", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance",
     "keywords": ["retencion practicada", "irpf practicada", "modelo 111"]},
    {"code": "4752", "name": "Hacienda Publica acreedora por impuesto sobre sociedades", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance",
     "keywords": ["impuesto sociedades", "modelo 200", "is"],
     "common_for": ["sociedad"]},
    {"code": "476", "name": "Organismos de la Seguridad Social acreedores", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance",
     "keywords": ["seguridad social", "cotizacion", "cuota autonomo", "reta", "tc1"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "477", "name": "Hacienda Publica IVA repercutido", "group_code": "47", "group_name": "Administraciones Publicas", "type": "balance",
     "keywords": ["iva", "repercutido", "cobrado", "iva ventas"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "480", "name": "Gastos anticipados", "group_code": "48", "group_name": "Ajustes por periodificacion", "type": "balance",
     "keywords": ["gasto anticipado", "prepago", "seguro anticipado"]},
    {"code": "485", "name": "Ingresos anticipados", "group_code": "48", "group_name": "Ajustes por periodificacion", "type": "balance",
     "keywords": ["ingreso anticipado", "cobro anticipado"]},
    {"code": "490", "name": "Deterioro de valor de creditos por operaciones comerciales", "group_code": "49", "group_name": "Deterioro de valor de creditos comerciales y provisiones a corto plazo", "type": "balance"},
    {"code": "499", "name": "Provisiones por operaciones comerciales", "group_code": "49", "group_name": "Deterioro de valor de creditos comerciales y provisiones a corto plazo", "type": "balance"},

    # =============================================
    # GRUPO 5 — CUENTAS FINANCIERAS (type: "balance")
    # =============================================
    {"code": "520", "name": "Deudas a corto plazo con entidades de credito", "group_code": "52", "group_name": "Deudas a corto plazo por prestamos recibidos y otros conceptos", "type": "balance",
     "keywords": ["prestamo corto", "poliza credito", "linea credito"]},
    {"code": "521", "name": "Deudas a corto plazo", "group_code": "52", "group_name": "Deudas a corto plazo por prestamos recibidos y otros conceptos", "type": "balance"},
    {"code": "523", "name": "Proveedores de inmovilizado a corto plazo", "group_code": "52", "group_name": "Deudas a corto plazo por prestamos recibidos y otros conceptos", "type": "balance"},
    {"code": "524", "name": "Acreedores por arrendamiento financiero a corto plazo", "group_code": "52", "group_name": "Deudas a corto plazo por prestamos recibidos y otros conceptos", "type": "balance",
     "keywords": ["leasing corto", "renting corto"]},
    {"code": "525", "name": "Efectos a pagar a corto plazo", "group_code": "52", "group_name": "Deudas a corto plazo por prestamos recibidos y otros conceptos", "type": "balance"},
    {"code": "526", "name": "Dividendo activo a pagar", "group_code": "52", "group_name": "Deudas a corto plazo por prestamos recibidos y otros conceptos", "type": "balance",
     "common_for": ["sociedad"]},
    {"code": "540", "name": "Inversiones financieras a corto plazo en instrumentos de patrimonio", "group_code": "54", "group_name": "Otras inversiones financieras a corto plazo", "type": "balance"},
    {"code": "542", "name": "Creditos a corto plazo", "group_code": "54", "group_name": "Otras inversiones financieras a corto plazo", "type": "balance"},
    {"code": "544", "name": "Creditos a corto plazo al personal", "group_code": "54", "group_name": "Otras inversiones financieras a corto plazo", "type": "balance"},
    {"code": "548", "name": "Imposiciones a corto plazo", "group_code": "54", "group_name": "Otras inversiones financieras a corto plazo", "type": "balance"},
    {"code": "550", "name": "Titular de la explotacion", "group_code": "55", "group_name": "Otras cuentas no bancarias", "type": "balance",
     "keywords": ["titular", "empresario individual", "cuenta personal"],
     "common_for": ["autonomo"]},
    {"code": "551", "name": "Cuenta corriente con socios y administradores", "group_code": "55", "group_name": "Otras cuentas no bancarias", "type": "balance",
     "common_for": ["sociedad"]},
    {"code": "555", "name": "Partidas pendientes de aplicacion", "group_code": "55", "group_name": "Otras cuentas no bancarias", "type": "balance"},
    {"code": "565", "name": "Fianzas constituidas a corto plazo", "group_code": "56", "group_name": "Fianzas y depositos recibidos y constituidos a corto plazo", "type": "balance",
     "keywords": ["fianza", "deposito", "garantia alquiler"]},
    {"code": "570", "name": "Caja euros", "group_code": "57", "group_name": "Tesoreria", "type": "balance",
     "keywords": ["efectivo", "caja", "metalico", "caja registradora"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "572", "name": "Bancos e instituciones de credito c/c vista euros", "group_code": "57", "group_name": "Tesoreria", "type": "balance",
     "keywords": ["banco", "transferencia", "cuenta corriente", "ingreso banco", "bizum"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "574", "name": "Bancos e instituciones de credito cuentas de ahorro euros", "group_code": "57", "group_name": "Tesoreria", "type": "balance",
     "keywords": ["ahorro", "cuenta ahorro", "deposito"]},

    # =============================================
    # GRUPO 6 — COMPRAS Y GASTOS (type: "gasto")
    # =============================================
    {"code": "600", "name": "Compras de mercaderias", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["compra", "mercaderia", "producto", "material", "stock", "genero"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "601", "name": "Compras de materias primas", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["materia prima", "componente", "ingrediente"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "602", "name": "Compras de otros aprovisionamientos", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["consumible", "envase", "embalaje", "material oficina", "fungible"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "606", "name": "Descuentos sobre compras por pronto pago", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["descuento pronto pago", "dto financiero"]},
    {"code": "607", "name": "Trabajos realizados por otras empresas", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["subcontrata", "outsourcing", "trabajo externo", "maquila", "subcontratista"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "608", "name": "Devoluciones de compras y operaciones similares", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["devolucion compra", "abono proveedor"]},
    {"code": "609", "name": "Rappels por compras", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["rappel", "descuento volumen", "bonificacion"]},
    {"code": "610", "name": "Variacion de existencias de mercaderias", "group_code": "61", "group_name": "Variacion de existencias", "type": "gasto"},
    {"code": "611", "name": "Variacion de existencias de materias primas", "group_code": "61", "group_name": "Variacion de existencias", "type": "gasto"},
    {"code": "612", "name": "Variacion de existencias de otros aprovisionamientos", "group_code": "61", "group_name": "Variacion de existencias", "type": "gasto"},
    {"code": "613", "name": "Variacion de existencias de productos en curso", "group_code": "61", "group_name": "Variacion de existencias", "type": "gasto"},
    {"code": "615", "name": "Variacion de existencias de productos terminados", "group_code": "61", "group_name": "Variacion de existencias", "type": "gasto"},
    {"code": "620", "name": "Gastos en investigacion y desarrollo del ejercicio", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["i+d", "investigacion", "desarrollo", "innovacion"]},
    {"code": "621", "name": "Arrendamientos y canones", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["alquiler", "arrendamiento", "local", "oficina", "canon", "leasing", "renting", "coworking"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "622", "name": "Reparaciones y conservacion", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["reparacion", "mantenimiento", "conservacion", "arreglo", "reforma", "averia"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "623", "name": "Servicios de profesionales independientes", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["asesoria", "abogado", "gestor", "consultoria", "auditor", "notario", "profesional", "perito", "traductor"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "624", "name": "Transportes", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["transporte", "mensajeria", "envio", "logistica", "correos", "paqueteria", "flete"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "625", "name": "Primas de seguros", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["seguro", "poliza", "rc profesional", "responsabilidad civil", "seguro local", "seguro vehiculo"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "626", "name": "Servicios bancarios y similares", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["banco", "comision bancaria", "transferencia", "tpv", "pasarela pago", "comision tarjeta"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "627", "name": "Publicidad propaganda y relaciones publicas", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["publicidad", "marketing", "anuncio", "propaganda", "google ads", "meta ads", "instagram", "redes sociales", "folleto"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "628", "name": "Suministros", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["luz", "agua", "gas", "electricidad", "telefono", "internet", "fibra", "movil", "energia"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "629", "name": "Otros servicios", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["servicio", "limpieza", "formacion", "suscripcion", "software", "hosting", "cloud", "saas", "dominio", "viaje", "dieta", "parking"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "630", "name": "Impuesto sobre beneficios", "group_code": "63", "group_name": "Tributos", "type": "gasto",
     "keywords": ["impuesto sociedades", "is", "modelo 200"],
     "common_for": ["sociedad"]},
    {"code": "631", "name": "Otros tributos", "group_code": "63", "group_name": "Tributos", "type": "gasto",
     "keywords": ["ibi", "iae", "impuesto", "tasa", "tributo", "basura", "ivtm", "plusvalia", "tasa municipal"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "634", "name": "Ajustes negativos en la imposicion indirecta", "group_code": "63", "group_name": "Tributos", "type": "gasto",
     "keywords": ["ajuste iva", "regularizacion iva", "prorrata"]},
    {"code": "640", "name": "Sueldos y salarios", "group_code": "64", "group_name": "Gastos de personal", "type": "gasto",
     "keywords": ["nomina", "salario", "sueldo", "empleado", "trabajador", "paga extra", "finiquito"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "641", "name": "Indemnizaciones", "group_code": "64", "group_name": "Gastos de personal", "type": "gasto",
     "keywords": ["indemnizacion", "despido", "compensacion"],
     "common_for": ["sociedad"]},
    {"code": "642", "name": "Seguridad Social a cargo de la empresa", "group_code": "64", "group_name": "Gastos de personal", "type": "gasto",
     "keywords": ["seguridad social", "cotizacion empresa", "ss empresa", "tc1", "cuota patronal"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "649", "name": "Otros gastos sociales", "group_code": "64", "group_name": "Gastos de personal", "type": "gasto",
     "keywords": ["formacion empleados", "comedor", "guarderia", "ticket restaurante"],
     "common_for": ["sociedad"]},
    {"code": "650", "name": "Perdidas de creditos comerciales incobrables", "group_code": "65", "group_name": "Otros gastos de gestion", "type": "gasto",
     "keywords": ["incobrable", "impagado", "fallido", "insolvencia"]},
    {"code": "659", "name": "Otras perdidas en gestion corriente", "group_code": "65", "group_name": "Otros gastos de gestion", "type": "gasto"},
    {"code": "660", "name": "Gastos financieros por actualizacion de provisiones", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto"},
    {"code": "662", "name": "Intereses de deudas", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto",
     "keywords": ["interes", "prestamo", "hipoteca", "financiacion", "interes bancario"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "663", "name": "Intereses de deudas con empresas del grupo", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto",
     "common_for": ["sociedad"]},
    {"code": "665", "name": "Intereses por descuento de efectos y operaciones de factoring", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto",
     "keywords": ["descuento efectos", "factoring", "anticipo facturas"]},
    {"code": "666", "name": "Perdidas en participaciones y valores representativos de deuda", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto"},
    {"code": "667", "name": "Perdidas de creditos no comerciales", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto"},
    {"code": "668", "name": "Diferencias negativas de cambio", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto",
     "keywords": ["tipo cambio", "divisa", "diferencia cambio negativa"]},
    {"code": "669", "name": "Otros gastos financieros", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto",
     "keywords": ["comision aval", "gasto financiero", "descubierto"]},
    {"code": "670", "name": "Perdidas procedentes del inmovilizado intangible", "group_code": "67", "group_name": "Perdidas procedentes de activos no corrientes y gastos excepcionales", "type": "gasto"},
    {"code": "671", "name": "Perdidas procedentes del inmovilizado material", "group_code": "67", "group_name": "Perdidas procedentes de activos no corrientes y gastos excepcionales", "type": "gasto",
     "keywords": ["perdida venta activo", "baja inmovilizado"]},
    {"code": "672", "name": "Perdidas procedentes de las inversiones inmobiliarias", "group_code": "67", "group_name": "Perdidas procedentes de activos no corrientes y gastos excepcionales", "type": "gasto"},
    {"code": "678", "name": "Gastos excepcionales", "group_code": "67", "group_name": "Perdidas procedentes de activos no corrientes y gastos excepcionales", "type": "gasto",
     "keywords": ["gasto excepcional", "siniestro", "catastrofe", "multa", "sancion"]},
    {"code": "680", "name": "Amortizacion del inmovilizado intangible", "group_code": "68", "group_name": "Dotaciones para amortizaciones", "type": "gasto",
     "keywords": ["amortizacion software", "amortizacion intangible"]},
    {"code": "681", "name": "Amortizacion del inmovilizado material", "group_code": "68", "group_name": "Dotaciones para amortizaciones", "type": "gasto",
     "keywords": ["amortizacion", "depreciacion", "amortizacion vehiculo", "amortizacion equipo", "amortizacion mobiliario"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "682", "name": "Amortizacion de las inversiones inmobiliarias", "group_code": "68", "group_name": "Dotaciones para amortizaciones", "type": "gasto"},
    {"code": "690", "name": "Perdidas por deterioro del inmovilizado intangible", "group_code": "69", "group_name": "Perdidas por deterioro y otras dotaciones", "type": "gasto"},
    {"code": "691", "name": "Perdidas por deterioro del inmovilizado material", "group_code": "69", "group_name": "Perdidas por deterioro y otras dotaciones", "type": "gasto"},
    {"code": "693", "name": "Perdidas por deterioro de existencias", "group_code": "69", "group_name": "Perdidas por deterioro y otras dotaciones", "type": "gasto",
     "keywords": ["deterioro stock", "obsolescencia", "caducidad"],
     "common_for": ["farmacia"]},
    {"code": "694", "name": "Perdidas por deterioro de creditos por operaciones comerciales", "group_code": "69", "group_name": "Perdidas por deterioro y otras dotaciones", "type": "gasto",
     "keywords": ["provision impagados", "deterioro clientes"]},
    {"code": "695", "name": "Dotacion a la provision por operaciones comerciales", "group_code": "69", "group_name": "Perdidas por deterioro y otras dotaciones", "type": "gasto"},

    # =============================================
    # GRUPO 7 — VENTAS E INGRESOS (type: "ingreso")
    # =============================================
    {"code": "700", "name": "Ventas de mercaderias", "group_code": "70", "group_name": "Ventas de mercaderias de produccion propia servicios etc", "type": "ingreso",
     "keywords": ["venta", "mercaderia", "producto", "factura emitida"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "701", "name": "Ventas de productos terminados", "group_code": "70", "group_name": "Ventas de mercaderias de produccion propia servicios etc", "type": "ingreso",
     "keywords": ["venta producto", "fabricacion"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "702", "name": "Ventas de productos semiterminados", "group_code": "70", "group_name": "Ventas de mercaderias de produccion propia servicios etc", "type": "ingreso"},
    {"code": "703", "name": "Ventas de subproductos y residuos", "group_code": "70", "group_name": "Ventas de mercaderias de produccion propia servicios etc", "type": "ingreso",
     "keywords": ["residuo", "subproducto", "chatarra", "reciclaje"]},
    {"code": "704", "name": "Ventas de envases y embalajes", "group_code": "70", "group_name": "Ventas de mercaderias de produccion propia servicios etc", "type": "ingreso"},
    {"code": "705", "name": "Prestaciones de servicios", "group_code": "70", "group_name": "Ventas de mercaderias de produccion propia servicios etc", "type": "ingreso",
     "keywords": ["servicio", "honorarios", "factura emitida", "prestacion", "consultoria", "asesoria"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "706", "name": "Descuentos sobre ventas por pronto pago", "group_code": "70", "group_name": "Ventas de mercaderias de produccion propia servicios etc", "type": "ingreso",
     "keywords": ["descuento pronto pago ventas"]},
    {"code": "708", "name": "Devoluciones de ventas y operaciones similares", "group_code": "70", "group_name": "Ventas de mercaderias de produccion propia servicios etc", "type": "ingreso",
     "keywords": ["devolucion venta", "abono cliente", "rectificativa"]},
    {"code": "709", "name": "Rappels sobre ventas", "group_code": "70", "group_name": "Ventas de mercaderias de produccion propia servicios etc", "type": "ingreso",
     "keywords": ["rappel ventas", "descuento volumen ventas"]},
    {"code": "710", "name": "Variacion de existencias de productos en curso", "group_code": "71", "group_name": "Variacion de existencias", "type": "ingreso"},
    {"code": "712", "name": "Variacion de existencias de productos terminados", "group_code": "71", "group_name": "Variacion de existencias", "type": "ingreso"},
    {"code": "730", "name": "Trabajos realizados para el inmovilizado intangible", "group_code": "73", "group_name": "Trabajos realizados para la empresa", "type": "ingreso"},
    {"code": "731", "name": "Trabajos realizados para el inmovilizado material", "group_code": "73", "group_name": "Trabajos realizados para la empresa", "type": "ingreso"},
    {"code": "740", "name": "Subvenciones donaciones y legados a la explotacion", "group_code": "74", "group_name": "Subvenciones donaciones y legados", "type": "ingreso",
     "keywords": ["subvencion", "ayuda", "kit digital", "donacion", "legado", "bono empleo"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "746", "name": "Subvenciones donaciones y legados de capital transferidos al resultado", "group_code": "74", "group_name": "Subvenciones donaciones y legados", "type": "ingreso"},
    {"code": "752", "name": "Ingresos por arrendamientos", "group_code": "75", "group_name": "Otros ingresos de gestion", "type": "ingreso",
     "keywords": ["alquiler cobrado", "arrendamiento ingreso", "renta local"]},
    {"code": "753", "name": "Ingresos de propiedad industrial cedida en explotacion", "group_code": "75", "group_name": "Otros ingresos de gestion", "type": "ingreso",
     "keywords": ["royalty", "licencia", "patente"]},
    {"code": "754", "name": "Ingresos por comisiones", "group_code": "75", "group_name": "Otros ingresos de gestion", "type": "ingreso",
     "keywords": ["comision", "mediacion", "intermediacion"]},
    {"code": "755", "name": "Ingresos por servicios al personal", "group_code": "75", "group_name": "Otros ingresos de gestion", "type": "ingreso"},
    {"code": "759", "name": "Ingresos por servicios diversos", "group_code": "75", "group_name": "Otros ingresos de gestion", "type": "ingreso",
     "keywords": ["ingreso diverso", "servicio accesorio"]},
    {"code": "760", "name": "Ingresos de participaciones en instrumentos de patrimonio", "group_code": "76", "group_name": "Ingresos financieros", "type": "ingreso",
     "keywords": ["dividendo", "participacion beneficios"]},
    {"code": "762", "name": "Ingresos de creditos", "group_code": "76", "group_name": "Ingresos financieros", "type": "ingreso",
     "keywords": ["interes cobrado", "rendimiento deposito"]},
    {"code": "766", "name": "Beneficios en participaciones y valores representativos de deuda", "group_code": "76", "group_name": "Ingresos financieros", "type": "ingreso"},
    {"code": "768", "name": "Diferencias positivas de cambio", "group_code": "76", "group_name": "Ingresos financieros", "type": "ingreso",
     "keywords": ["tipo cambio positivo", "ganancia divisa"]},
    {"code": "769", "name": "Otros ingresos financieros", "group_code": "76", "group_name": "Ingresos financieros", "type": "ingreso",
     "keywords": ["ingreso financiero", "interes cobrado", "rendimiento"]},
    {"code": "770", "name": "Beneficios procedentes del inmovilizado intangible", "group_code": "77", "group_name": "Beneficios procedentes de activos no corrientes e ingresos excepcionales", "type": "ingreso"},
    {"code": "771", "name": "Beneficios procedentes del inmovilizado material", "group_code": "77", "group_name": "Beneficios procedentes de activos no corrientes e ingresos excepcionales", "type": "ingreso",
     "keywords": ["venta activo", "beneficio venta vehiculo", "plusvalia inmovilizado"]},
    {"code": "772", "name": "Beneficios procedentes de las inversiones inmobiliarias", "group_code": "77", "group_name": "Beneficios procedentes de activos no corrientes e ingresos excepcionales", "type": "ingreso"},
    {"code": "778", "name": "Ingresos excepcionales", "group_code": "77", "group_name": "Beneficios procedentes de activos no corrientes e ingresos excepcionales", "type": "ingreso",
     "keywords": ["ingreso excepcional", "indemnizacion cobrada", "seguro cobrado"]},
    {"code": "790", "name": "Reversion del deterioro del inmovilizado intangible", "group_code": "79", "group_name": "Excesos y aplicaciones de provisiones y de perdidas por deterioro", "type": "ingreso"},
    {"code": "791", "name": "Reversion del deterioro del inmovilizado material", "group_code": "79", "group_name": "Excesos y aplicaciones de provisiones y de perdidas por deterioro", "type": "ingreso"},
    {"code": "793", "name": "Reversion del deterioro de existencias", "group_code": "79", "group_name": "Excesos y aplicaciones de provisiones y de perdidas por deterioro", "type": "ingreso"},
    {"code": "794", "name": "Reversion del deterioro de creditos por operaciones comerciales", "group_code": "79", "group_name": "Excesos y aplicaciones de provisiones y de perdidas por deterioro", "type": "ingreso"},
    {"code": "795", "name": "Exceso de provisiones", "group_code": "79", "group_name": "Excesos y aplicaciones de provisiones y de perdidas por deterioro", "type": "ingreso"},
]


async def seed_pgc_accounts():
    """Delete existing PGC accounts and re-insert all."""
    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()

    # Ensure schema exists
    print("Initializing schema...")
    await db.init_schema()
    print("Schema ready.")

    # Delete existing accounts
    await db.execute("DELETE FROM pgc_accounts")
    print("Cleared existing pgc_accounts.")

    inserted = 0
    for account in PGC_ACCOUNTS:
        account_id = str(uuid.uuid4())
        try:
            await db.execute(
                """INSERT INTO pgc_accounts
                   (id, code, name, group_code, group_name, type, description, keywords, common_for, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                [
                    account_id,
                    account["code"],
                    account["name"],
                    account["group_code"],
                    account["group_name"],
                    account["type"],
                    account.get("description"),
                    json.dumps(account.get("keywords")) if account.get("keywords") else None,
                    json.dumps(account.get("common_for")) if account.get("common_for") else None,
                ],
            )
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {account['code']}: {e}")

    await db.disconnect()
    print(f"\nSeed complete: {inserted} PGC accounts inserted")
    print(f"Total accounts in seed data: {len(PGC_ACCOUNTS)}")


if __name__ == "__main__":
    asyncio.run(seed_pgc_accounts())
