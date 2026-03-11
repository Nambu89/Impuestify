"""
Calculadora FIFO de criptomonedas para IRPF espanol.

Implementa el metodo First-In-First-Out (FIFO) para calcular ganancias y perdidas
patrimoniales derivadas de la transmision de monedas virtuales, segun:
- Art. 37.1.Undecies LIRPF (metodo FIFO obligatorio para criptomonedas)
- Art. 33.5.f LIRPF (regla antiaplicacion: perdidas no computables si recompra
  dentro de 2 meses para valores cotizados / 1 ano para no cotizados)
- Casillas 1813 (perdidas) y 1814 (ganancias) del Modelo 100 IRPF
"""
from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from app.services.crypto_parser import CryptoTransaction, FIAT_CURRENCIES

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Tipos de operacion que generan transmision sujeta a IRPF
_TAXABLE_TX_TYPES: frozenset[str] = frozenset({"sell", "swap"})

# Tipos de adquisicion (crean lote en el pool)
_ACQUISITION_TX_TYPES: frozenset[str] = frozenset(
    {"buy", "staking_reward", "airdrop", "mining", "transfer"}
)

# Ventana antiaplicacion para valores cotizados: 2 meses
_ANTI_APLICACION_WINDOW_DAYS: int = 61  # ~2 meses calendario


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class CryptoGain:
    """Ganancia o perdida patrimonial individual por transmision FIFO."""

    asset: str
    """Ticker del activo transmitido (BTC, ETH...)."""

    tx_type: str
    """Tipo de operacion: sell o swap."""

    clave_contraprestacion: str
    """Clave AEAT (casilla 1803): F=fiat, N=cripto, O=otro activo virtual, B=bienes/servicios."""

    date_acquisition: str
    """Fecha de adquisicion del lote (ISO 8601)."""

    date_transmission: str
    """Fecha de transmision (ISO 8601)."""

    acquisition_value_eur: float
    """Valor de adquisicion proporcional (EUR)."""

    acquisition_fees_eur: float
    """Comisiones de adquisicion proporcionales (EUR)."""

    transmission_value_eur: float
    """Valor de transmision (EUR)."""

    transmission_fees_eur: float
    """Comisiones de transmision proporcionales (EUR)."""

    gain_loss_eur: float
    """Ganancia (positivo) o perdida (negativo) patrimonial en EUR."""

    anti_aplicacion: bool = False
    """True si la perdida no computa por la regla antiaplicacion (Art. 33.5.f LIRPF)."""

    source_tx_id: Optional[str] = None
    """ID de la transaccion origen (para trazabilidad)."""


@dataclass
class _Lot:
    """Lote de compra mantenido en el pool FIFO."""

    amount: float
    """Cantidad restante del activo en este lote."""

    cost_per_unit: float
    """Coste por unidad en EUR (incluyendo comision prorrateada)."""

    date: str
    """Fecha de adquisicion del lote (ISO 8601)."""


@dataclass
class FIFOResult:
    """Resultado completo del calculo FIFO."""

    gains: list[CryptoGain] = field(default_factory=list)
    """Lista de ganancias/perdidas individuales."""

    summary: dict = field(default_factory=dict)
    """Resumen con totales y casillas AEAT."""


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _parse_dt(date_str: str) -> datetime:
    """Convierte ISO 8601 a datetime. Tolerante a formatos sin hora."""
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha no reconocido: {date_str!r}")


def _determine_clave(tx: CryptoTransaction) -> str:
    """
    Determina la clave de contraprestacion AEAT (casilla 1803) segun el tipo de operacion:
    - F: moneda de curso legal (fiat)
    - N: otra moneda virtual (cripto a cripto)
    - O: otro activo virtual (NFT, token no fungible)
    - B: bienes o servicios
    """
    if tx.tx_type == "sell":
        # Venta a fiat
        return "F"
    if tx.tx_type == "swap":
        counterpart = (tx.counterpart_asset or "").upper()
        if not counterpart:
            # Sin informacion del contraparte -> asumir F
            return "F"
        if counterpart in FIAT_CURRENCIES:
            return "F"
        # Heuristica NFT: tokens con nombre que sugiere NFT o longitud > 6
        if "NFT" in counterpart or len(counterpart) > 6:
            return "O"
        return "N"
    # Fallback
    return "F"


def _apply_anti_aplicacion(
    gains: list[CryptoGain],
    transactions: list[CryptoTransaction],
) -> None:
    """
    Marca las perdidas no computables por la regla antiaplicacion (Art. 33.5.f LIRPF).

    Si dentro de los 2 meses anteriores O posteriores a la transmision con perdida
    se ha recomprado el mismo activo, la perdida queda diferida (anti_aplicacion=True).

    NOTA: La regla se aplica conservadoramente a todos los activos crypto (tratados
    como valores cotizados en mercado organizado a efectos de la norma).
    """
    # Construir indice de fechas de compra por activo
    buy_dates: dict[str, list[datetime]] = defaultdict(list)
    for tx in transactions:
        if tx.tx_type in ("buy",) and tx.date_utc:
            try:
                buy_dates[tx.asset].append(_parse_dt(tx.date_utc))
            except ValueError:
                pass

    window = timedelta(days=_ANTI_APLICACION_WINDOW_DAYS)

    for gain in gains:
        if gain.gain_loss_eur >= 0:
            continue  # Solo aplica a perdidas
        try:
            tx_dt = _parse_dt(gain.date_transmission)
        except ValueError:
            continue

        asset_buys = buy_dates.get(gain.asset, [])
        for buy_dt in asset_buys:
            # La regla antiaplicacion aplica solo a recompras POSTERIORES a la venta
            # (o el mismo dia) dentro de los 2 meses siguientes
            days_after = (buy_dt - tx_dt).days
            if 0 <= days_after <= _ANTI_APLICACION_WINDOW_DAYS:
                gain.anti_aplicacion = True
                logger.debug(
                    "anti_aplicacion activada: %s, perdida=%s EUR, recompra=%s (%d dias despues)",
                    gain.asset,
                    gain.gain_loss_eur,
                    buy_dt.isoformat(),
                    days_after,
                )
                break


# ---------------------------------------------------------------------------
# Main FIFO engine
# ---------------------------------------------------------------------------


def calculate_fifo_gains(
    transactions: list[CryptoTransaction],
    tax_year: Optional[int] = None,
) -> FIFOResult:
    """
    Calcula las ganancias y perdidas patrimoniales por criptomonedas usando FIFO.

    Implementa Art. 37.1.Undecies LIRPF: las transmisiones de monedas virtuales
    tributan como ganancia/perdida patrimonial usando el orden de adquisicion FIFO.

    Args:
        transactions: Lista de CryptoTransaction ordenadas por fecha (la funcion
                      las re-ordena internamente para garantizarlo).
        tax_year: Si se indica, solo devuelve ganancias del ejercicio fiscal.
                  Las adquisiciones de todos los anios se tienen en cuenta para
                  el pool FIFO.

    Returns:
        FIFOResult con la lista de ganancias/perdidas y el resumen por casillas AEAT.
    """
    if not transactions:
        return FIFOResult(gains=[], summary=_build_summary([], tax_year))

    # Ordenar por fecha (necesario para FIFO correcto)
    sorted_txs = sorted(
        transactions,
        key=lambda t: t.date_utc or "9999-99-99",
    )

    # Pool FIFO: {asset: deque[_Lot]}
    pool: dict[str, deque[_Lot]] = defaultdict(deque)

    all_gains: list[CryptoGain] = []

    for tx in sorted_txs:
        if not tx.date_utc or not tx.asset:
            continue

        try:
            tx_dt = _parse_dt(tx.date_utc)
        except ValueError:
            logger.warning("Fecha no reconocida en transaccion: %s", tx.date_utc)
            continue

        tx_year = tx_dt.year

        # ---------------------------------------------------------------
        # ADQUISICIONES: anadir lote al pool
        # ---------------------------------------------------------------
        if tx.tx_type in _ACQUISITION_TX_TYPES:
            amount = tx.amount
            if amount <= 0:
                continue

            # Coste total del lote
            if tx.total_eur is not None and tx.total_eur > 0:
                cost_total = tx.total_eur + tx.fee_eur
            elif tx.price_eur is not None and tx.price_eur > 0:
                cost_total = tx.price_eur * amount + tx.fee_eur
            else:
                # Staking/airdrop/mining sin precio conocido -> coste 0
                # (el valor de mercado deberia estar en price_eur si el parser lo capturo)
                cost_total = tx.fee_eur

            cost_per_unit = cost_total / amount if amount > 0 else 0.0

            pool[tx.asset].append(
                _Lot(
                    amount=amount,
                    cost_per_unit=cost_per_unit,
                    date=tx.date_utc,
                )
            )

        # ---------------------------------------------------------------
        # SWAP: el activo recibido entra al pool como nueva adquisicion
        # ---------------------------------------------------------------
        elif tx.tx_type == "swap" and tx.counterpart_asset and tx.counterpart_amount:
            counterpart = tx.counterpart_asset.upper()
            counterpart_amount = tx.counterpart_amount
            if counterpart_amount > 0 and counterpart not in FIAT_CURRENCIES:
                # El coste del activo recibido es el valor de transmision del entregado
                recv_total_eur = tx.total_eur or (
                    (tx.price_eur or 0) * tx.amount
                )
                recv_cost_per_unit = recv_total_eur / counterpart_amount if counterpart_amount > 0 else 0.0
                pool[counterpart].append(
                    _Lot(
                        amount=counterpart_amount,
                        cost_per_unit=recv_cost_per_unit,
                        date=tx.date_utc,
                    )
                )

        # ---------------------------------------------------------------
        # TRANSMISIONES: consumir lotes FIFO y calcular ganancia
        # ---------------------------------------------------------------
        if tx.tx_type in _TAXABLE_TX_TYPES:
            amount_to_sell = tx.amount
            if amount_to_sell <= 0:
                continue

            # Valor de transmision total
            if tx.total_eur is not None and tx.total_eur > 0:
                transmission_total = tx.total_eur
            elif tx.price_eur is not None and tx.price_eur > 0:
                transmission_total = tx.price_eur * tx.amount
            else:
                logger.warning(
                    "Transmision sin precio en EUR: %s %s %s",
                    tx.asset, tx.amount, tx.date_utc,
                )
                transmission_total = 0.0

            # Distribuir comision de venta proporcionalmente a los lotes consumidos
            transmission_fee_total = tx.fee_eur
            clave = _determine_clave(tx)

            asset_pool = pool[tx.asset]
            remaining_to_sell = amount_to_sell

            while remaining_to_sell > 1e-10 and asset_pool:
                lot = asset_pool[0]

                if lot.amount <= remaining_to_sell + 1e-10:
                    # Consumir lote entero
                    lot_amount = lot.amount
                    asset_pool.popleft()
                else:
                    # Consumo parcial del lote
                    lot_amount = remaining_to_sell
                    lot.amount -= lot_amount

                # Proporcion de esta venta que corresponde a este lote
                fraction = lot_amount / amount_to_sell

                acq_value = lot.cost_per_unit * lot_amount
                # Excluir comision del cost_per_unit que ya incluia la fee
                # La fee de adquisicion ya esta embebida en cost_per_unit
                acq_fee = 0.0  # ya incluida en acq_value via cost_per_unit

                trans_value = transmission_total * fraction
                trans_fee = transmission_fee_total * fraction

                gain_loss = trans_value - trans_fee - acq_value

                # Solo incluir en el resultado si pertenece al ano fiscal solicitado
                if tax_year is None or tx_year == tax_year:
                    all_gains.append(
                        CryptoGain(
                            asset=tx.asset,
                            tx_type=tx.tx_type,
                            clave_contraprestacion=clave,
                            date_acquisition=lot.date,
                            date_transmission=tx.date_utc,
                            acquisition_value_eur=round(acq_value, 4),
                            acquisition_fees_eur=round(acq_fee, 4),
                            transmission_value_eur=round(trans_value, 4),
                            transmission_fees_eur=round(trans_fee, 4),
                            gain_loss_eur=round(gain_loss, 4),
                            anti_aplicacion=False,
                        )
                    )

                remaining_to_sell -= lot_amount

            if remaining_to_sell > 1e-8:
                logger.warning(
                    "Pool FIFO insuficiente para %s: faltan %.8f unidades en %s",
                    tx.asset, remaining_to_sell, tx.date_utc,
                )

    # Aplicar regla antiaplicacion a las perdidas
    _apply_anti_aplicacion(all_gains, sorted_txs)

    summary = _build_summary(all_gains, tax_year)

    return FIFOResult(gains=all_gains, summary=summary)


def _build_summary(gains: list[CryptoGain], tax_year: Optional[int]) -> dict:
    """
    Construye el resumen fiscal con totales y casillas AEAT.

    Casillas Modelo 100:
    - 1813: suma de perdidas patrimoniales (valor positivo, representa la perdida)
    - 1814: suma de ganancias patrimoniales
    """
    total_gains = 0.0
    total_losses = 0.0
    computable_losses = 0.0  # Perdidas que computan (sin antiaplicacion)

    assets_seen: set[str] = set()

    for g in gains:
        assets_seen.add(g.asset)
        if g.gain_loss_eur >= 0:
            total_gains += g.gain_loss_eur
        else:
            total_losses += g.gain_loss_eur
            if not g.anti_aplicacion:
                computable_losses += g.gain_loss_eur

    net_result = total_gains + total_losses
    casilla_1814 = round(total_gains, 2)
    casilla_1813 = round(abs(computable_losses), 2)  # AEAT espera valor positivo

    return {
        "tax_year": tax_year,
        "total_operations": len(gains),
        "assets_involved": sorted(assets_seen),
        "total_gains_eur": round(total_gains, 2),
        "total_losses_eur": round(abs(total_losses), 2),
        "computable_losses_eur": round(abs(computable_losses), 2),
        "net_result_eur": round(net_result, 2),
        "casilla_1814": casilla_1814,  # Suma ganancias (casilla 1814)
        "casilla_1813": casilla_1813,  # Suma perdidas computables (casilla 1813)
        "anti_aplicacion_count": sum(1 for g in gains if g.anti_aplicacion),
    }
