"""
One-time UPDATE script for 21 deduction corrections found in the March 2026 AEAT audit.
Bugs 26-46 documented in memory/bugfixes-2026-03.md.

Usage:
    cd backend
    PYTHONUTF8=1 python scripts/update_deductions_audit_2026_03.py
    PYTHONUTF8=1 python scripts/update_deductions_audit_2026_03.py --dry-run
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


UPDATES = [
    # (code, percentage, max_amount, fixed_amount, legal_reference, description, clear_fields)
    # clear_fields: list of columns to set to NULL

    # Bug 26: AND-AYUDA-DOMESTICA 15->20%
    (
        "AND-AYUDA-DOMESTICA", 20.0, 500.0, None,
        "Arts. 19, 4 y DT 3a Ley 5/2021 Andalucia",
        "20% de las cotizaciones a la Seguridad Social del empleado/a del hogar, max. 500 EUR. "
        "Requisito: progenitor con hijos dependientes y ambos progenitores con rentas del trabajo/actividades, "
        "o contribuyente de 75+ anios.",
        [],
    ),
    # Bug 27: EXT-TRABAJO-DEPENDIENTE 200->75
    (
        "EXT-TRABAJO-DEPENDIENTE", None, None, 75.0,
        "Art. 2 DL 1/2018 Extremadura",
        "75 EUR para contribuyentes con rendimientos netos del trabajo <=12.000 EUR "
        "y otros rendimientos netos <=300 EUR (excluidos exentos).",
        ["percentage", "max_amount"],
    ),
    # Bug 28: EXT-VIV-JOVEN 8->3%
    (
        "EXT-VIV-JOVEN", 3.0, 9040.0, None,
        "Arts. 8, 12 bis y 13 DL 1/2018 Extremadura",
        "3% de las cantidades invertidas en adquisicion de vivienda habitual NUEVA "
        "(primera transmision), max base 9.040 EUR. En municipios <3.000 hab: 5%. "
        "Menores de 36 anios. BI <=19.000 EUR individual / 24.000 EUR conjunta "
        "(28.000/45.000 en municipios rurales).",
        ["fixed_amount"],
    ),
    # Bug 29: EXT-ARRENDAMIENTO-VIV 10/300->30/1000
    (
        "EXT-ARRENDAMIENTO-VIV", 30.0, 1000.0, None,
        "Arts. 9, 12 bis y 13 DL 1/2018 Extremadura",
        "30% del alquiler de vivienda habitual, max 1.000 EUR (1.500 EUR en municipios <3.000 hab). "
        "Para menores de 36, familias numerosas, monoparentales con 2+ hijos, discapacidad >=65%. "
        "BI <=28.000 EUR individual / 45.000 EUR conjunta.",
        [],
    ),
    # Bug 30: EXT-CUIDADO-DISCAPACIDAD
    (
        "EXT-CUIDADO-DISCAPACIDAD", None, None, 150.0,
        "Arts. 5, 12 bis y 13 DL 1/2018 Extremadura",
        "150 EUR por cada familiar ascendiente o colateral hasta tercer grado con "
        "discapacidad >=65% o incapacidad judicial, que conviva con el contribuyente "
        "y tenga rentas <=8.000 EUR. 220 EUR si dependencia reconocida. "
        "BI <=19.000 EUR individual / 24.000 EUR conjunta (28.000/45.000 rural).",
        [],
    ),
    # Bug 31: CYL-FAM-NUM 246->600
    (
        "CYL-FAM-NUM", None, None, 600.0,
        "Arts. 3 y 10 Decreto Leg. 1/2013 CyL",
        "600 EUR para familias numerosas generales (3 hijos); 1.500 EUR (4 hijos); "
        "2.500 EUR (5 hijos); +1.000 EUR por cada hijo a partir del 6o. "
        "+600 EUR si conyuge o hijo con discapacidad >=65%. Sin limite de renta.",
        [],
    ),
    # Bug 32: CYL-NACIMIENTO
    (
        "CYL-NACIMIENTO", None, None, 1010.0,
        "Arts. 4.1-3 y 10 Decreto Leg. 1/2013 CyL",
        "1.010 EUR por el primer hijo; 1.475 EUR por el segundo; 2.351 EUR por el tercero y "
        "siguientes. En municipios <=5.000 hab: 1.420/2.070/3.300 EUR. "
        "Importes duplicados si hijo con discapacidad >=33%.",
        [],
    ),
    # Bug 33: CYL-CUIDADO-HIJOS 312 fixed -> 30%/322
    (
        "CYL-CUIDADO-HIJOS", 30.0, 322.0, None,
        "Arts. 5.1 y 10 Decreto Leg. 1/2013 CyL",
        "30% de cotizaciones SS empleada hogar, max 322 EUR; o 100% guarderia/escuela infantil, "
        "max 1.320 EUR por hijo menor de 4 anios. Ambos progenitores deben trabajar. "
        "BI menor o igual a 18.900 EUR individual / 31.500 EUR conjunta.",
        ["fixed_amount"],
    ),
    # Bug 34: CYL-VIV-JOVEN 7.5->15%
    (
        "CYL-VIV-JOVEN", 15.0, 10000.0, None,
        "Arts. 7.1 y 10 Decreto Leg. 1/2013 CyL",
        "15% de las cantidades satisfechas por adquisicion o rehabilitacion de vivienda "
        "habitual en municipios rurales (<=10.000 hab) para menores de 36 anios. "
        "Base maxima 10.000 EUR/anio. Valor vivienda <150.000 EUR. "
        "BI menor o igual a 18.900 EUR individual / 31.500 EUR conjunta.",
        ["fixed_amount"],
    ),
    # Bug 35: CYL-ALQUILER-VIV 15->20%
    (
        "CYL-ALQUILER-VIV", 20.0, 459.0, None,
        "Arts. 7.4, 7.5 y 10 Decreto Leg. 1/2013 CyL",
        "20% de las cantidades satisfechas por arrendamiento de la vivienda habitual, "
        "max 459 EUR (918 EUR conjunta). En municipios <=10.000 hab: 25%, max 612 EUR. "
        "Requisito: menor de 36 anios. "
        "BI menor o igual a 18.900 EUR individual / 31.500 EUR conjunta.",
        [],
    ),
    # Bug 36: CLM-DISCAPACIDAD
    (
        "CLM-DISCAPACIDAD", None, None, 300.0,
        "Arts. 1 y 13 Ley 8/2013 CLM",
        "300 EUR para contribuyentes con discapacidad >=65%. "
        "Deduccion adicional: 300 EUR Grado I, 600 EUR Grado II, 900 EUR Grado III dependencia.",
        [],
    ),
    # Bug 37: CLM-ARRENDAMIENTO-VIV income limits
    (
        "CLM-ARRENDAMIENTO-VIV", 15.0, 450.0, None,
        "Arts. 9 y 13 Ley 8/2013 CLM",
        "15% de las cantidades satisfechas por arrendamiento de la vivienda habitual, "
        "max 450 EUR. En municipios rurales (<=2.500 hab o <=10.000 si >30km de ciudad 50.000+): "
        "20%, max 612 EUR. Requisito: menor de 36 anios. "
        "BI menor o igual a 12.500 EUR individual / 25.000 EUR conjunta.",
        [],
    ),
    # Bug 38: CLM-GASTOS-EDUCATIVOS
    (
        "CLM-GASTOS-EDUCATIVOS", 15.0, 300.0, None,
        "Arts. 3 y 13 Ley 8/2013 CLM",
        "100% libros de texto + 15% otros gastos educativos (idiomas, escolaridad). "
        "Max por tramos de BI: 50-200 EUR individual, 75-300 EUR conjunta segun nivel de renta. "
        "Limites especiales para familias numerosas (BI hasta 40.000 EUR).",
        [],
    ),
    # Bug 39: BAL-ARRENDAMIENTO-VIV 440->530
    (
        "BAL-ARRENDAMIENTO-VIV", 15.0, 530.0, None,
        "Art. 3 bis DL 1/2014 Baleares",
        "15% del alquiler de vivienda habitual, max 530 EUR. Para menores de 36 o mayores de 65 inactivos. "
        "Tier mejorado: 20%, max 650 EUR (menores de 30, discapacidad >=33%, familia numerosa/monoparental). "
        "BI <=33.000 EUR individual / 52.800 EUR conjunta (39.600/63.360 familia numerosa).",
        [],
    ),
    # Bug 40: MUR-VIV-JOVEN 3->5%
    (
        "MUR-VIV-JOVEN", 5.0, 300.0, None,
        "Art. 1 DL 1/2010 Murcia",
        "5% de las cantidades invertidas en adquisicion de vivienda habitual, max 300 EUR. "
        "Para contribuyentes de 40 anios o menos. "
        "BI general + ahorro <=40.000 EUR. BL ahorro <=1.800 EUR.",
        ["fixed_amount"],
    ),
    # Bug 41: MUR-GUARDERIA 15/330->20/1000
    (
        "MUR-GUARDERIA", 20.0, 1000.0, None,
        "Art. 1.Tres DL 1/2010 Murcia",
        "20% de los gastos de guarderia o centros de educacion infantil primer ciclo (0-3 anios), "
        "max 1.000 EUR por hijo (500 EUR si ambos padres aplican). "
        "BI <=30.000 EUR individual / 50.000 EUR conjunta.",
        [],
    ),
    # Bug 42: MUR-MEDIOAMBIENTE 10/300->50/7000
    (
        "MUR-MEDIOAMBIENTE", 50.0, 7000.0, None,
        "Art. 1.Seis DL 1/2010 Murcia",
        "50% de las inversiones en energias renovables (solar, eolica, biomasa) para vivienda habitual "
        "si BI <=33.007,20 EUR. 37,5% si BI <=53.007,20 EUR. 25% si BI <=80.000 EUR. "
        "Max 7.000 EUR. Incluye ahorro de agua domestica.",
        [],
    ),
    # Bug 43: MUR-ARRENDAMIENTO-VIV
    (
        "MUR-ARRENDAMIENTO-VIV", 10.0, 300.0, None,
        "Art. 1.Trece DL 1/2010 Murcia",
        "10% del alquiler pagado por la vivienda habitual, max 300 EUR. "
        "Para menores de 40 anios, familias numerosas o discapacidad >=65%. "
        "BI general + ahorro <=24.380 EUR (40.000 EUR para menores de 40). "
        "BL ahorro <=1.800 EUR.",
        [],
    ),
    # Bug 45: BAL-IDIOMAS 100->110
    (
        "BAL-IDIOMAS", 15.0, 110.0, None,
        "Art. 2 Ley 3/2022 Baleares",
        "15% de los gastos extraescolares de aprendizaje de idiomas extranjeros "
        "para hijos del contribuyente, max 110 EUR por hijo. "
        "BI <=33.000 EUR individual / 52.800 EUR conjunta.",
        [],
    ),
    # Bug 46: MUR-DONATIVOS 30->50%
    (
        "MUR-DONATIVOS", 50.0, None, None,
        "Art. 1.Siete DL 1/2010 Murcia (mod. Ley 4/2022)",
        "50% de los donativos puros dinerarios para proteccion del patrimonio cultural "
        "y actividades sociales de la Region de Murcia.",
        ["max_amount"],
    ),
]


async def run(dry_run: bool = False):
    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()

    updated = 0
    not_found = 0

    for code, pct, max_amt, fixed, legal, desc, clear_fields in UPDATES:
        sets = ["legal_reference = ?", "description = ?"]
        params = [legal, desc]

        if pct is not None:
            sets.append("percentage = ?")
            params.append(pct)
        if max_amt is not None:
            sets.append("max_amount = ?")
            params.append(max_amt)
        if fixed is not None:
            sets.append("fixed_amount = ?")
            params.append(fixed)

        for field in clear_fields:
            sets.append(f"{field} = NULL")

        params.append(code)
        sql = f"UPDATE deductions SET {', '.join(sets)} WHERE code = ?"

        if dry_run:
            print(f"  [DRY-RUN] {code}: {sql}")
            print(f"            params: {params}")
            updated += 1
        else:
            await db.execute(sql, params)
            check = await db.execute("SELECT id FROM deductions WHERE code = ?", [code])
            if check.rows:
                print(f"  {code}: UPDATED")
                updated += 1
            else:
                print(f"  {code}: NOT FOUND IN DB")
                not_found += 1

    # Also delete the duplicate ARG-DACION-PAGO (Bug 44)
    if dry_run:
        print("  [DRY-RUN] DELETE ARG-DACION-PAGO (duplicate of ARG-DACION-ALQUILER)")
    else:
        await db.execute("DELETE FROM deductions WHERE code = 'ARG-DACION-PAGO'")
        print("  ARG-DACION-PAGO: DELETED (duplicate)")

    await db.disconnect()

    print(f"\nDone: {updated} updated, {not_found} not found, 1 deleted")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(dry_run=args.dry_run))
