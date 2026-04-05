"""
Contabilidad Service for TaxIA (Impuestify)

Generates double-entry journal entries (asientos contables) from classified
invoices and provides accounting book queries (libro diario, libro mayor,
balance de sumas y saldos, cuenta de PyG).

PGC (Plan General Contable) compliant.
"""
import uuid
import logging
from dataclasses import dataclass
from typing import Optional

from app.database.turso_client import get_db_client

logger = logging.getLogger(__name__)


@dataclass
class AsientoLine:
    """A single line in a double-entry journal entry."""
    cuenta_code: str
    cuenta_nombre: str
    debe: float
    haber: float
    concepto: str


class ContabilidadService:
    """
    Accounting service — journal entries and book queries.

    Supports:
    - Generating asiento lines from classified invoices (recibida / emitida)
    - Persisting asientos to the database
    - Querying libro diario, libro mayor, balance, and PyG
    """

    def __init__(self, db=None):
        self._db = db

    async def _get_db(self):
        if self._db is not None:
            return self._db
        return await get_db_client()

    # ------------------------------------------------------------------
    # Core: Generate journal entry lines
    # ------------------------------------------------------------------

    @staticmethod
    def generate_asiento_lines(
        tipo: str,
        cuenta_pgc_code: str,
        cuenta_pgc_nombre: str,
        base_imponible: float,
        cuota_iva: float,
        total: float,
        retencion_irpf: float,
        concepto: str,
    ) -> list[AsientoLine]:
        """
        Generate double-entry journal lines for an invoice.

        Args:
            tipo: 'recibida' (expense) or 'emitida' (income)
            cuenta_pgc_code: PGC account code for the expense/income
            cuenta_pgc_nombre: PGC account name
            base_imponible: Tax base amount
            cuota_iva: VAT amount
            total: Total invoice amount (base + IVA - IRPF for emitida)
            retencion_irpf: IRPF withholding amount (only for emitida)
            concepto: Description / concept

        Returns:
            List of AsientoLine ensuring sum(debe) == sum(haber)
        """
        lines: list[AsientoLine] = []

        if tipo == "recibida":
            # ----------------------------------------------------------
            # FACTURA RECIBIDA (gasto)
            # Debe: cuenta gasto (base_imponible)
            # Debe: 472 IVA soportado (cuota_iva) — if > 0
            # Haber: 400 Proveedores or 410 Acreedores (total)
            # ----------------------------------------------------------
            lines.append(AsientoLine(
                cuenta_code=cuenta_pgc_code,
                cuenta_nombre=cuenta_pgc_nombre,
                debe=base_imponible,
                haber=0.0,
                concepto=concepto,
            ))

            if cuota_iva > 0:
                lines.append(AsientoLine(
                    cuenta_code="472",
                    cuenta_nombre="HP IVA soportado",
                    debe=cuota_iva,
                    haber=0.0,
                    concepto=concepto,
                ))

            # 400 for compras (cuenta starts with "60"), 410 otherwise
            if cuenta_pgc_code.startswith("60"):
                contrapartida_code = "400"
                contrapartida_nombre = "Proveedores"
            else:
                contrapartida_code = "410"
                contrapartida_nombre = "Acreedores por prestaciones de servicios"

            lines.append(AsientoLine(
                cuenta_code=contrapartida_code,
                cuenta_nombre=contrapartida_nombre,
                debe=0.0,
                haber=total,
                concepto=concepto,
            ))

        elif tipo == "emitida":
            # ----------------------------------------------------------
            # FACTURA EMITIDA (ingreso)
            # Debe: 430 Clientes (total)
            # Debe: 473 HP retenciones (retencion_irpf) — if > 0
            # Haber: cuenta ingreso (base_imponible)
            # Haber: 477 IVA repercutido (cuota_iva) — if > 0
            # ----------------------------------------------------------
            lines.append(AsientoLine(
                cuenta_code="430",
                cuenta_nombre="Clientes",
                debe=total,
                haber=0.0,
                concepto=concepto,
            ))

            if retencion_irpf > 0:
                lines.append(AsientoLine(
                    cuenta_code="473",
                    cuenta_nombre="HP retenciones y pagos a cuenta",
                    debe=retencion_irpf,
                    haber=0.0,
                    concepto=concepto,
                ))

            lines.append(AsientoLine(
                cuenta_code=cuenta_pgc_code,
                cuenta_nombre=cuenta_pgc_nombre,
                debe=0.0,
                haber=base_imponible,
                concepto=concepto,
            ))

            if cuota_iva > 0:
                lines.append(AsientoLine(
                    cuenta_code="477",
                    cuenta_nombre="HP IVA repercutido",
                    debe=0.0,
                    haber=cuota_iva,
                    concepto=concepto,
                ))

        else:
            raise ValueError(f"Tipo de factura no soportado: {tipo}. Usar 'recibida' o 'emitida'.")

        return lines

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    async def save_asiento(
        self,
        user_id: str,
        libro_registro_id: Optional[str],
        fecha: str,
        lines: list[AsientoLine],
        year: int,
        trimestre: int,
    ) -> list[str]:
        """
        Persist journal entry lines to asientos_contables.

        Gets next numero_asiento (MAX+1) and inserts each line.

        Returns:
            List of created row IDs.
        """
        db = await self._get_db()

        # Get next asiento number for this user+year
        result = await db.execute(
            "SELECT MAX(numero_asiento) as max_num FROM asientos_contables WHERE user_id = ? AND year = ?",
            [user_id, year],
        )
        max_num = (result.rows[0]["max_num"] or 0) if result.rows else 0
        numero_asiento = max_num + 1

        created_ids: list[str] = []

        for line in lines:
            row_id = str(uuid.uuid4())
            await db.execute(
                """
                INSERT INTO asientos_contables
                    (id, user_id, libro_registro_id, fecha, numero_asiento,
                     cuenta_code, cuenta_nombre, debe, haber, concepto, year, trimestre)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    row_id,
                    user_id,
                    libro_registro_id,
                    fecha,
                    numero_asiento,
                    line.cuenta_code,
                    line.cuenta_nombre,
                    line.debe,
                    line.haber,
                    line.concepto,
                    year,
                    trimestre,
                ],
            )
            created_ids.append(row_id)

        logger.info(
            "Saved asiento #%d with %d lines for user %s (year=%d, T%d)",
            numero_asiento, len(lines), user_id, year, trimestre,
        )
        return created_ids

    # ------------------------------------------------------------------
    # Queries: Libro Diario
    # ------------------------------------------------------------------

    async def get_libro_diario(
        self,
        user_id: str,
        year: int,
        trimestre: Optional[int] = None,
    ) -> list[dict]:
        """
        Get journal entries (libro diario) for a user.

        Args:
            user_id: User ID
            year: Fiscal year
            trimestre: Optional quarter filter (1-4)

        Returns:
            List of entry dicts ordered by numero_asiento, cuenta_code.
        """
        db = await self._get_db()

        if trimestre is not None:
            sql = """
                SELECT id, fecha, numero_asiento, cuenta_code, cuenta_nombre,
                       debe, haber, concepto, trimestre
                FROM asientos_contables
                WHERE user_id = ? AND year = ? AND trimestre = ?
                ORDER BY numero_asiento, cuenta_code
            """
            params = [user_id, year, trimestre]
        else:
            sql = """
                SELECT id, fecha, numero_asiento, cuenta_code, cuenta_nombre,
                       debe, haber, concepto, trimestre
                FROM asientos_contables
                WHERE user_id = ? AND year = ?
                ORDER BY numero_asiento, cuenta_code
            """
            params = [user_id, year]

        result = await db.execute(sql, params)
        return list(result.rows) if result.rows else []

    # ------------------------------------------------------------------
    # Queries: Libro Mayor
    # ------------------------------------------------------------------

    async def get_libro_mayor(self, user_id: str, year: int) -> list[dict]:
        """
        Get general ledger (libro mayor) — grouped by account with totals.

        Returns:
            List of dicts with cuenta_code, cuenta_nombre, total_debe,
            total_haber, saldo. Ordered by cuenta_code.
        """
        db = await self._get_db()

        result = await db.execute(
            """
            SELECT cuenta_code, cuenta_nombre,
                   SUM(debe) as total_debe,
                   SUM(haber) as total_haber
            FROM asientos_contables
            WHERE user_id = ? AND year = ?
            GROUP BY cuenta_code, cuenta_nombre
            ORDER BY cuenta_code
            """,
            [user_id, year],
        )

        rows = list(result.rows) if result.rows else []
        for row in rows:
            row["saldo"] = row["total_debe"] - row["total_haber"]

        return rows

    # ------------------------------------------------------------------
    # Queries: Balance de Sumas y Saldos
    # ------------------------------------------------------------------

    async def get_balance_sumas_saldos(self, user_id: str, year: int) -> dict:
        """
        Get trial balance (balance de sumas y saldos).

        Returns:
            Dict with cuentas list, total_debe, total_haber, diferencia, year.
        """
        cuentas = await self.get_libro_mayor(user_id, year)

        total_debe = sum(c["total_debe"] for c in cuentas)
        total_haber = sum(c["total_haber"] for c in cuentas)

        return {
            "cuentas": cuentas,
            "total_debe": total_debe,
            "total_haber": total_haber,
            "diferencia": round(total_debe - total_haber, 2),
            "year": year,
        }

    # ------------------------------------------------------------------
    # Queries: Cuenta de Perdidas y Ganancias (PyG)
    # ------------------------------------------------------------------

    async def get_pyg(self, user_id: str, year: int) -> dict:
        """
        Get profit and loss statement (cuenta de PyG).

        Gastos = accounts starting with '6' (grupo 6 PGC).
        Ingresos = accounts starting with '7' (grupo 7 PGC).

        Returns:
            Dict with gastos, ingresos, total_gastos, total_ingresos,
            resultado, year, disclaimer.
        """
        cuentas = await self.get_libro_mayor(user_id, year)

        gastos = [c for c in cuentas if c["cuenta_code"].startswith("6")]
        ingresos = [c for c in cuentas if c["cuenta_code"].startswith("7")]

        # Gastos: saldo deudor (debe - haber)
        total_gastos = sum(c["total_debe"] - c["total_haber"] for c in gastos)
        # Ingresos: saldo acreedor (haber - debe)
        total_ingresos = sum(c["total_haber"] - c["total_debe"] for c in ingresos)

        resultado = total_ingresos - total_gastos

        return {
            "gastos": gastos,
            "ingresos": ingresos,
            "total_gastos": round(total_gastos, 2),
            "total_ingresos": round(total_ingresos, 2),
            "resultado": round(resultado, 2),
            "year": year,
            "disclaimer": (
                "Este resultado es una estimacion basada en los asientos registrados. "
                "No sustituye la contabilidad oficial ni el asesoramiento de un profesional. "
                "Consulte con su asesor fiscal para la declaracion definitiva."
            ),
        }
