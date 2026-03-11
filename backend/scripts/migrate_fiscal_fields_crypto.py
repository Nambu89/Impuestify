"""
Migración de campos de perfil fiscal: criptomonedas, apuestas y trading.

Renombra keys antiguas en datos_fiscales JSON de user_profiles según MIGRATION_MAP.
Idempotente: si la key nueva ya existe, no sobreescribe.

Ejecutar:
    python backend/scripts/migrate_fiscal_fields_crypto.py
    python backend/scripts/migrate_fiscal_fields_crypto.py --dry-run
"""
import argparse
import asyncio
import json
import logging
import os
import sys

# Asegurar que el path de backend está en sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapa de migración: key_vieja → key_nueva
# ---------------------------------------------------------------------------

MIGRATION_MAP: dict[str, str] = {
    "ganancias_brutas_apuestas": "premios_metalico_privados",
    "perdidas_apuestas": "perdidas_juegos_privados",
    "tiene_ganancias_apuestas": "tiene_ganancias_juegos_privados",
    "premios_loterias_estado": "premios_metalico_publicos",
    "ganancias_fondos_etf": "ganancias_reembolso_fondos",
    "perdidas_fondos_etf": "perdidas_reembolso_fondos",
    "ganancias_derivados_cfd": "ganancias_derivados",
    "perdidas_derivados_cfd": "perdidas_derivados",
}

# Keys a ELIMINAR sin sustituto (calculadas automáticamente o ya no necesarias)
KEYS_TO_DELETE: list[str] = [
    "tiene_premios_exentos",   # se calcula: exento si premios_metalico_publicos < 40.000
    "tiene_acciones_fondos",   # reemplazado por tiene_acciones + tiene_fondos_inversion + tiene_derivados
    "mineria_cripto",          # fusionado con tiene_staking_defi
    "tiene_nfts",              # cubierto por cripto_clave_contraprestacion = "O"
]


async def migrate(dry_run: bool = False) -> None:
    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()

    # Leer todos los perfiles
    result = await db.execute(
        "SELECT user_id, datos_fiscales FROM user_profiles WHERE datos_fiscales IS NOT NULL"
    )
    rows = result.rows or []

    logger.info("Perfiles encontrados: %d", len(rows))

    updated_count = 0
    skipped_count = 0

    for row in rows:
        user_id = row["user_id"]
        datos_raw = row.get("datos_fiscales")

        if not datos_raw:
            skipped_count += 1
            continue

        try:
            datos: dict = json.loads(datos_raw) if isinstance(datos_raw, str) else dict(datos_raw)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("user_id=%s — JSON inválido, saltando: %s", user_id, exc)
            skipped_count += 1
            continue

        changed = False

        # 1. Renombrar keys según MIGRATION_MAP (no sobreescribir si la nueva ya existe)
        for old_key, new_key in MIGRATION_MAP.items():
            if old_key in datos and new_key not in datos:
                datos[new_key] = datos.pop(old_key)
                logger.info(
                    "user_id=%s — %s → %s", user_id, old_key, new_key
                )
                changed = True
            elif old_key in datos and new_key in datos:
                # Nueva key ya existe: solo eliminar la vieja
                del datos[old_key]
                logger.info(
                    "user_id=%s — eliminando %s (nueva key %s ya existe)",
                    user_id, old_key, new_key,
                )
                changed = True

        # 2. Eliminar keys obsoletas
        for del_key in KEYS_TO_DELETE:
            if del_key in datos:
                del datos[del_key]
                logger.info("user_id=%s — eliminando obsoleta: %s", user_id, del_key)
                changed = True

        if not changed:
            skipped_count += 1
            continue

        updated_count += 1

        if dry_run:
            logger.info("DRY-RUN user_id=%s — cambios detectados (no guardados)", user_id)
            continue

        # Guardar JSON actualizado
        datos_json = json.dumps(datos, ensure_ascii=False)
        await db.execute(
            "UPDATE user_profiles SET datos_fiscales = ?, updated_at = datetime('now') WHERE user_id = ?",
            [datos_json, user_id],
        )
        logger.info("user_id=%s — actualizado correctamente", user_id)

    await db.disconnect()

    mode = "DRY-RUN" if dry_run else "REAL"
    logger.info(
        "[%s] Migracion completada — actualizados: %d | sin cambios: %d | total: %d",
        mode, updated_count, skipped_count, len(rows),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migración de campos de perfil fiscal crypto/apuestas/trading"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validar cambios sin modificar la base de datos",
    )
    args = parser.parse_args()

    asyncio.run(migrate(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
