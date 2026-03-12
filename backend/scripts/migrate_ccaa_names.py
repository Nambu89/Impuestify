"""
Migration script: Unify CCAA names across all database tables.

Converts old naming conventions to canonical short names with correct accents:
  "Comunidad de Madrid" → "Madrid"
  "Comunitat Valenciana" → "Valencia"
  "Illes Balears" → "Baleares"
  "Región de Murcia" → "Murcia"
  "Aragon" → "Aragón"
  "Andalucia" → "Andalucía"
  "Cataluna" → "Cataluña"
  "Castilla y Leon" → "Castilla y León"
  "Comunidad Valenciana" → "Valencia"

Safe to run multiple times (idempotent).
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.utils.ccaa_constants import DB_MIGRATION_MAP


TABLES_AND_COLUMNS = [
    ("irpf_scales", "jurisdiction"),
    ("tax_parameters", "jurisdiction"),
    ("deductions", "territory"),
    ("user_profiles", "ccaa_residencia"),
    ("fiscal_deadlines", "territory"),
]


async def migrate():
    from app.database.turso_client import get_db_client
    db = await get_db_client()

    print("=" * 60)
    print("CCAA Name Migration — Unifying to canonical short names")
    print("=" * 60)

    total_updated = 0

    for table, column in TABLES_AND_COLUMNS:
        print(f"\n--- {table}.{column} ---")
        table_updated = 0

        for old_name, new_name in DB_MIGRATION_MAP.items():
            # Count existing rows with old name
            result = await db.execute(
                f"SELECT COUNT(*) as cnt FROM {table} WHERE {column} = ?",
                [old_name],
            )
            count = result.rows[0]["cnt"] if result.rows else 0

            if count > 0:
                if table == "deductions":
                    # Deductions have UNIQUE(code, tax_year, territory).
                    # If the new name already exists for the same code+year,
                    # delete the old-name duplicates instead of updating.
                    dupes = await db.execute(
                        """SELECT d1.id FROM deductions d1
                           INNER JOIN deductions d2
                           ON d1.code = d2.code AND d1.tax_year = d2.tax_year
                           WHERE d1.territory = ? AND d2.territory = ?""",
                        [old_name, new_name],
                    )
                    dupe_ids = [row["id"] for row in dupes.rows]
                    if dupe_ids:
                        for did in dupe_ids:
                            await db.execute("DELETE FROM deductions WHERE id = ?", [did])
                        print(f"  '{old_name}': {len(dupe_ids)} duplicate rows deleted (already exist as '{new_name}')")
                        # Update remaining (non-duplicate) rows
                        remaining = await db.execute(
                            f"SELECT COUNT(*) as cnt FROM {table} WHERE {column} = ?",
                            [old_name],
                        )
                        remaining_count = remaining.rows[0]["cnt"] if remaining.rows else 0
                        if remaining_count > 0:
                            await db.execute(
                                f"UPDATE {table} SET {column} = ? WHERE {column} = ?",
                                [new_name, old_name],
                            )
                            print(f"  '{old_name}' → '{new_name}': {remaining_count} rows updated")
                            table_updated += remaining_count
                        table_updated += len(dupe_ids)
                    else:
                        await db.execute(
                            f"UPDATE {table} SET {column} = ? WHERE {column} = ?",
                            [new_name, old_name],
                        )
                        print(f"  '{old_name}' → '{new_name}': {count} rows updated")
                        table_updated += count
                else:
                    await db.execute(
                        f"UPDATE {table} SET {column} = ? WHERE {column} = ?",
                        [new_name, old_name],
                    )
                    print(f"  '{old_name}' → '{new_name}': {count} rows updated")
                    table_updated += count
            # else: no rows to migrate, skip silently

        if table_updated == 0:
            print("  (no changes needed)")
        total_updated += table_updated

    # Verify final state
    print(f"\n{'=' * 60}")
    print(f"Total rows updated: {total_updated}")
    print(f"\nVerification — distinct values per table:")

    for table, column in TABLES_AND_COLUMNS:
        result = await db.execute(
            f"SELECT DISTINCT {column} FROM {table} ORDER BY {column}"
        )
        values = [row[column] for row in result.rows if row[column]]
        print(f"  {table}.{column}: {len(values)} distinct values")
        # Flag any remaining old-convention names
        for v in values:
            if v in DB_MIGRATION_MAP:
                print(f"    ⚠️  Still has old name: '{v}'")

    print(f"\n✅ Migration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())
