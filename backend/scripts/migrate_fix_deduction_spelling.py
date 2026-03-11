"""
Migration script: Fix spelling errors in deduction questions_json and description.

Updates existing records in the `deductions` table to fix:
- "anyo" / "ano" → "año"
- Missing accents (Cuanto → ¿Cuánto, maximo → máximo, etc.)
- Missing opening ¿ in questions
- Other systematic typos from the original seed scripts

Safe to run multiple times (idempotent — applies text replacements).

Usage:
    cd backend
    python scripts/migrate_fix_deduction_spelling.py
    python scripts/migrate_fix_deduction_spelling.py --dry-run
"""
import argparse
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app.database.turso_client import TursoClient  # noqa: E402


# Ordered replacement pairs (applied sequentially)
TEXT_REPLACEMENTS = [
    # Year misspellings
    ("anyo", "año"),
    ("ano ", "año "),
    ("ano?", "año?"),
    ("ano.", "año."),
    ("ano)", "año)"),
    ("anos", "años"),
    # Missing accents — questions
    ("Cuanto ", "¿Cuánto "),
    ("Cuantos ", "¿Cuántos "),
    ("Estan ", "¿Están "),
    # Missing accents — common words
    ("Basica", "Básica"),
    ("basica", "básica"),
    ("maximo", "máximo"),
    ("Maximo", "Máximo"),
    ("animo", "ánimo"),
    ("costo ", "costó "),
    ("Deduccion ", "Deducción "),
    ("deduccion ", "deducción "),
    ("adopcion", "adopción"),
    ("Adopcion", "Adopción"),
    ("educacion", "educación"),
    ("Educacion", "Educación"),
    ("reduccion", "reducción"),
    ("Reduccion", "Reducción"),
    ("Prevision", "Previsión"),
    ("prevision", "previsión"),
    ("pension ", "pensión "),
    ("Pension ", "Pensión "),
    ("guarderia", "guardería"),
    ("Guarderia", "Guardería"),
    ("regimen ", "régimen "),
    ("Regimen ", "Régimen "),
    ("comun", "común"),
    ("adquisicion", "adquisición"),
    ("Codigo", "Código"),
    ("poblacion", "población"),
    ("concesion", "concesión"),
    ("rehabilitacion", "rehabilitación"),
    ("conciliacion", "conciliación"),
    ("interes ", "interés "),
    ("Interes ", "Interés "),
    ("vehiculo", "vehículo"),
    ("Vehiculo", "Vehículo"),
    ("electrico", "eléctrico"),
    ("Electrico", "Eléctrico"),
]


def fix_text(text: str) -> str:
    """Apply all spelling fixes to a string."""
    if not text:
        return text
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    # Add ¿ to questions that end with ? but don't have ¿
    if text.endswith("?") and "¿" not in text:
        text = "¿" + text
    return text


def fix_questions_json(raw: str) -> str:
    """Parse questions_json, fix all text fields, and re-serialize."""
    if not raw:
        return raw
    try:
        questions = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return raw

    changed = False
    for q in questions:
        if "text" in q:
            fixed = fix_text(q["text"])
            if fixed != q["text"]:
                q["text"] = fixed
                changed = True
    return json.dumps(questions, ensure_ascii=False) if changed else raw


async def migrate(dry_run: bool = False) -> None:
    print("=" * 60)
    print("MIGRATION: Fix spelling in deductions questions_json + description")
    print("=" * 60)
    if dry_run:
        print("  (DRY RUN — no changes will be made)\n")

    db = TursoClient()
    await db.connect()

    result = await db.execute(
        "SELECT id, code, name, description, questions_json FROM deductions WHERE is_active = 1"
    )

    updated = 0
    for row in result.rows:
        row_id = row["id"]
        code = row["code"]
        old_name = row.get("name") or ""
        old_desc = row.get("description") or ""
        old_questions = row.get("questions_json") or ""

        new_name = fix_text(old_name)
        new_desc = fix_text(old_desc)
        new_questions = fix_questions_json(old_questions)

        if new_name != old_name or new_desc != old_desc or new_questions != old_questions:
            updated += 1
            print(f"  [FIX] {code}")
            if new_name != old_name:
                print(f"         name: {old_name!r} → {new_name!r}")
            if new_desc != old_desc:
                print(f"         desc changed")
            if new_questions != old_questions:
                print(f"         questions_json changed")

            if not dry_run:
                await db.execute(
                    "UPDATE deductions SET name = ?, description = ?, questions_json = ? WHERE id = ?",
                    [new_name, new_desc, new_questions, row_id],
                )

    print(f"\nTotal: {updated} deductions {'would be ' if dry_run else ''}updated out of {len(result.rows)}")

    await db.disconnect()
    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()
    asyncio.run(migrate(dry_run=args.dry_run))
