"""
Tests para la calculadora FIFO de criptomonedas.

Cubre: FIFO basico, crypto-to-crypto, antiaplicacion,
multiples activos, perdidas, staking/airdrop, casos borde.
"""
from __future__ import annotations

import pytest
from app.services.crypto_parser import CryptoTransaction
from app.utils.calculators.crypto_fifo import (
    CryptoGain,
    FIFOResult,
    calculate_fifo_gains,
    _determine_clave,
    _build_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _buy(asset: str, amount: float, date: str, price_eur: float, fee: float = 0.0) -> CryptoTransaction:
    return CryptoTransaction(
        tx_type="buy",
        date_utc=date,
        asset=asset,
        amount=amount,
        price_eur=price_eur,
        total_eur=price_eur * amount,
        fee_eur=fee,
        exchange="test",
    )


def _sell(asset: str, amount: float, date: str, price_eur: float, fee: float = 0.0) -> CryptoTransaction:
    return CryptoTransaction(
        tx_type="sell",
        date_utc=date,
        asset=asset,
        amount=amount,
        price_eur=price_eur,
        total_eur=price_eur * amount,
        fee_eur=fee,
        exchange="test",
    )


def _swap(
    asset: str,
    amount: float,
    date: str,
    total_eur: float,
    counterpart_asset: str,
    counterpart_amount: float,
    fee: float = 0.0,
) -> CryptoTransaction:
    return CryptoTransaction(
        tx_type="swap",
        date_utc=date,
        asset=asset,
        amount=amount,
        total_eur=total_eur,
        fee_eur=fee,
        exchange="test",
        counterpart_asset=counterpart_asset,
        counterpart_amount=counterpart_amount,
    )


def _staking(asset: str, amount: float, date: str, price_eur: float | None = None) -> CryptoTransaction:
    return CryptoTransaction(
        tx_type="staking_reward",
        date_utc=date,
        asset=asset,
        amount=amount,
        price_eur=price_eur,
        total_eur=(price_eur * amount) if price_eur else 0.0,
        fee_eur=0.0,
        exchange="test",
    )


def _airdrop(asset: str, amount: float, date: str) -> CryptoTransaction:
    return CryptoTransaction(
        tx_type="airdrop",
        date_utc=date,
        asset=asset,
        amount=amount,
        price_eur=None,
        total_eur=None,
        fee_eur=0.0,
        exchange="test",
    )


# ---------------------------------------------------------------------------
# T1: FIFO basico — una compra, una venta
# ---------------------------------------------------------------------------

def test_fifo_basic_gain():
    """Compra 1 BTC a 10.000, vende a 15.000 -> ganancia 5.000."""
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _sell("BTC", 1.0, "2024-06-01T10:00:00", 15_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    g = result.gains[0]
    assert g.asset == "BTC"
    assert g.gain_loss_eur == pytest.approx(5_000.0, abs=0.01)
    assert g.acquisition_value_eur == pytest.approx(10_000.0, abs=0.01)
    assert g.transmission_value_eur == pytest.approx(15_000.0, abs=0.01)
    assert g.clave_contraprestacion == "F"


def test_fifo_basic_loss():
    """Compra 1 ETH a 2.000, vende a 1.500 -> perdida 500."""
    txs = [
        _buy("ETH", 1.0, "2024-01-01T10:00:00", 2_000.0),
        _sell("ETH", 1.0, "2024-06-01T10:00:00", 1_500.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    assert result.gains[0].gain_loss_eur == pytest.approx(-500.0, abs=0.01)


def test_fifo_gain_with_fee():
    """Compra 1 BTC a 10.000 con fee 50, vende a 15.000 con fee 75 -> ganancia 4.875."""
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0, fee=50.0),
        _sell("BTC", 1.0, "2024-06-01T10:00:00", 15_000.0, fee=75.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    g = result.gains[0]
    # acq_value = 10.000 + 50 = 10.050; trans_value = 15.000; trans_fee = 75
    # ganancia = 15.000 - 75 - 10.050 = 4.875
    assert g.gain_loss_eur == pytest.approx(4_875.0, abs=0.01)


def test_fifo_partial_sell():
    """Compra 2 BTC a 10.000/u, vende 1 a 12.000 -> ganancia 2.000."""
    txs = [
        _buy("BTC", 2.0, "2024-01-01T10:00:00", 10_000.0),
        _sell("BTC", 1.0, "2024-06-01T10:00:00", 12_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    assert result.gains[0].gain_loss_eur == pytest.approx(2_000.0, abs=0.01)


# ---------------------------------------------------------------------------
# T2: FIFO con multiples lotes
# ---------------------------------------------------------------------------

def test_fifo_two_lots_ordered():
    """
    Compra 1 BTC a 10.000 (lot1), luego 1 BTC a 20.000 (lot2).
    Vende 1 BTC a 25.000 -> debe consumir lot1 primero (FIFO).
    Ganancia = 25.000 - 10.000 = 15.000.
    """
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _buy("BTC", 1.0, "2024-03-01T10:00:00", 20_000.0),
        _sell("BTC", 1.0, "2024-06-01T10:00:00", 25_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    assert result.gains[0].acquisition_value_eur == pytest.approx(10_000.0, abs=0.01)
    assert result.gains[0].gain_loss_eur == pytest.approx(15_000.0, abs=0.01)


def test_fifo_sell_spans_two_lots():
    """
    Compra 1 BTC a 10.000 (lot1) y 1 BTC a 20.000 (lot2).
    Vende 2 BTC a 25.000/u -> 2 ganancias separadas.
    Lot1: 25.000 - 10.000 = 15.000
    Lot2: 25.000 - 20.000 = 5.000
    """
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _buy("BTC", 1.0, "2024-03-01T10:00:00", 20_000.0),
        _sell("BTC", 2.0, "2024-06-01T10:00:00", 25_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 2
    gains_sorted = sorted(result.gains, key=lambda g: g.acquisition_value_eur)
    assert gains_sorted[0].gain_loss_eur == pytest.approx(15_000.0, abs=0.01)
    assert gains_sorted[1].gain_loss_eur == pytest.approx(5_000.0, abs=0.01)


def test_fifo_cross_year():
    """
    Compra en 2023, vende en 2024. Con tax_year=2024, solo devuelve la ganancia del 2024.
    """
    txs = [
        _buy("BTC", 1.0, "2023-06-01T10:00:00", 15_000.0),
        _sell("BTC", 1.0, "2024-03-01T10:00:00", 20_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    assert result.gains[0].gain_loss_eur == pytest.approx(5_000.0, abs=0.01)
    # La fecha de adquisicion es de 2023
    assert result.gains[0].date_acquisition.startswith("2023")


def test_fifo_cross_year_no_filter():
    """Sin tax_year, devuelve todas las ganancias."""
    txs = [
        _buy("BTC", 1.0, "2023-01-01T10:00:00", 10_000.0),
        _sell("BTC", 0.5, "2023-06-01T10:00:00", 15_000.0),
        _sell("BTC", 0.5, "2024-03-01T10:00:00", 20_000.0),
    ]
    result = calculate_fifo_gains(txs)
    assert len(result.gains) == 2


# ---------------------------------------------------------------------------
# T3: Multiples activos independientes
# ---------------------------------------------------------------------------

def test_fifo_multiple_assets_independent():
    """
    BTC y ETH tienen pools independientes. No se mezclan.
    """
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _buy("ETH", 5.0, "2024-01-15T10:00:00", 2_000.0),
        _sell("BTC", 1.0, "2024-06-01T10:00:00", 12_000.0),
        _sell("ETH", 5.0, "2024-06-15T10:00:00", 1_500.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 2

    btc_gain = next(g for g in result.gains if g.asset == "BTC")
    eth_gain = next(g for g in result.gains if g.asset == "ETH")

    assert btc_gain.gain_loss_eur == pytest.approx(2_000.0, abs=0.01)
    assert eth_gain.gain_loss_eur == pytest.approx(-2_500.0, abs=0.01)


# ---------------------------------------------------------------------------
# T4: Swap (cripto a cripto)
# ---------------------------------------------------------------------------

def test_swap_clave_N():
    """Swap BTC -> ETH genera clave N (otra moneda virtual)."""
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _swap("BTC", 1.0, "2024-06-01T10:00:00",
              total_eur=15_000.0,
              counterpart_asset="ETH",
              counterpart_amount=8.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    g = result.gains[0]
    assert g.clave_contraprestacion == "N"
    assert g.gain_loss_eur == pytest.approx(5_000.0, abs=0.01)


def test_swap_received_asset_enters_pool():
    """
    Swap BTC -> ETH: el ETH recibido entra al pool a coste 15.000 EUR.
    Posterior venta de ETH calcula ganancia sobre ese coste base.
    """
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _swap("BTC", 1.0, "2024-06-01T10:00:00",
              total_eur=15_000.0,
              counterpart_asset="ETH",
              counterpart_amount=10.0),
        _sell("ETH", 10.0, "2024-12-01T10:00:00", 2_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    eth_gain = next(g for g in result.gains if g.asset == "ETH")
    # ETH entro al pool a 15.000/10 = 1.500/u; vende a 2.000/u
    # ganancia = 20.000 - 15.000 = 5.000
    assert eth_gain.gain_loss_eur == pytest.approx(5_000.0, abs=0.01)


def test_swap_clave_F_when_receiving_fiat():
    """Swap BTC -> USDT (fiat) genera clave F."""
    tx = CryptoTransaction(
        tx_type="swap",
        date_utc="2024-06-01T10:00:00",
        asset="BTC",
        amount=1.0,
        total_eur=15_000.0,
        fee_eur=0.0,
        exchange="test",
        counterpart_asset="USDT",
        counterpart_amount=15_000.0,
    )
    assert _determine_clave(tx) == "F"


# ---------------------------------------------------------------------------
# T5: Staking y airdrop
# ---------------------------------------------------------------------------

def test_staking_reward_enters_pool():
    """Staking reward de 0.1 ETH a precio 2.000 -> entra al pool a coste 200."""
    txs = [
        _staking("ETH", 0.1, "2024-01-01T10:00:00", price_eur=2_000.0),
        _sell("ETH", 0.1, "2024-06-01T10:00:00", price_eur=3_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    # acq = 0.1 * 2.000 = 200; trans = 0.1 * 3.000 = 300; ganancia = 100
    assert result.gains[0].gain_loss_eur == pytest.approx(100.0, abs=0.01)


def test_airdrop_zero_cost():
    """Airdrop sin precio conocido -> coste 0, toda la venta es ganancia."""
    txs = [
        _airdrop("SOL", 10.0, "2024-01-01T10:00:00"),
        _sell("SOL", 10.0, "2024-06-01T10:00:00", price_eur=100.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    # Coste 0 -> ganancia = 1.000
    assert result.gains[0].gain_loss_eur == pytest.approx(1_000.0, abs=0.01)


# ---------------------------------------------------------------------------
# T6: Regla antiaplicacion (Art. 33.5.f LIRPF)
# ---------------------------------------------------------------------------

def test_anti_aplicacion_triggered():
    """
    Venta con perdida seguida de recompra dentro de 2 meses -> anti_aplicacion=True.
    """
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _sell("BTC", 1.0, "2024-03-01T10:00:00", 8_000.0),   # perdida -2.000
        _buy("BTC", 1.0, "2024-03-15T10:00:00", 8_500.0),    # recompra 14 dias despues
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    # Debe haber una ganancia con perdida marcada como anti_aplicacion
    loss_gains = [g for g in result.gains if g.gain_loss_eur < 0]
    assert len(loss_gains) == 1
    assert loss_gains[0].anti_aplicacion is True


def test_anti_aplicacion_not_triggered_beyond_window():
    """
    Recompra 3 meses despues de la venta -> fuera de ventana, perdida computa.
    """
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _sell("BTC", 1.0, "2024-03-01T10:00:00", 8_000.0),
        _buy("BTC", 1.0, "2024-07-01T10:00:00", 9_000.0),  # 4 meses despues
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    loss_gains = [g for g in result.gains if g.gain_loss_eur < 0]
    assert len(loss_gains) == 1
    assert loss_gains[0].anti_aplicacion is False


def test_anti_aplicacion_only_affects_losses():
    """La regla antiaplicacion NO afecta a ganancias."""
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _sell("BTC", 1.0, "2024-03-01T10:00:00", 15_000.0),  # ganancia
        _buy("BTC", 1.0, "2024-03-15T10:00:00", 14_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    profit_gains = [g for g in result.gains if g.gain_loss_eur > 0]
    assert all(g.anti_aplicacion is False for g in profit_gains)


# ---------------------------------------------------------------------------
# T7: Summary y casillas AEAT
# ---------------------------------------------------------------------------

def test_summary_casillas():
    """El resumen contiene casillas 1813 y 1814 con valores correctos."""
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _sell("BTC", 0.5, "2024-06-01T10:00:00", 15_000.0),  # ganancia 2.500
        _buy("ETH", 5.0, "2024-01-01T10:00:00", 2_000.0),
        _sell("ETH", 5.0, "2024-07-01T10:00:00", 1_500.0),   # perdida -2.500
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    s = result.summary
    assert s["casilla_1814"] == pytest.approx(2_500.0, abs=0.01)
    assert s["casilla_1813"] == pytest.approx(2_500.0, abs=0.01)
    assert s["net_result_eur"] == pytest.approx(0.0, abs=0.01)


def test_summary_empty():
    """Sin transacciones, el resumen tiene ceros."""
    result = calculate_fifo_gains([], tax_year=2024)
    assert result.summary["casilla_1813"] == 0.0
    assert result.summary["casilla_1814"] == 0.0
    assert result.summary["total_operations"] == 0


def test_summary_assets_involved():
    """El resumen incluye la lista de activos involucrados."""
    txs = [
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),
        _sell("BTC", 1.0, "2024-06-01T10:00:00", 12_000.0),
        _buy("ETH", 2.0, "2024-01-01T10:00:00", 2_000.0),
        _sell("ETH", 2.0, "2024-06-01T10:00:00", 3_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert "BTC" in result.summary["assets_involved"]
    assert "ETH" in result.summary["assets_involved"]


# ---------------------------------------------------------------------------
# T8: Casos borde
# ---------------------------------------------------------------------------

def test_empty_transactions():
    """Lista vacia devuelve FIFOResult vacio."""
    result = calculate_fifo_gains([])
    assert isinstance(result, FIFOResult)
    assert result.gains == []


def test_sell_without_buy_warns_but_continues():
    """Venta sin compra previa (pool vacio) no lanza excepcion."""
    txs = [
        _sell("BTC", 1.0, "2024-06-01T10:00:00", 15_000.0),
    ]
    # No debe lanzar excepcion; puede generar 0 ganancias
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert isinstance(result, FIFOResult)


def test_very_small_amounts():
    """Cantidades muy pequenas (satoshis) no generan division por cero."""
    txs = [
        _buy("BTC", 0.00001, "2024-01-01T10:00:00", 30_000.0),
        _sell("BTC", 0.00001, "2024-06-01T10:00:00", 35_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    assert result.gains[0].gain_loss_eur == pytest.approx(0.05, abs=0.001)


def test_date_ordering_respected():
    """
    Incluso si las transacciones se pasan desordenadas, el FIFO opera en orden cronologico.
    """
    txs = [
        _sell("BTC", 1.0, "2024-06-01T10:00:00", 15_000.0),  # pasa primero
        _buy("BTC", 1.0, "2024-01-01T10:00:00", 10_000.0),    # pero es anterior
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert len(result.gains) == 1
    assert result.gains[0].gain_loss_eur == pytest.approx(5_000.0, abs=0.01)


def test_year_filter_excludes_other_years():
    """Con tax_year=2023, no se devuelven ganancias de 2024."""
    txs = [
        _buy("BTC", 1.0, "2023-01-01T10:00:00", 10_000.0),
        _sell("BTC", 0.5, "2023-06-01T10:00:00", 12_000.0),
        _sell("BTC", 0.5, "2024-01-15T10:00:00", 15_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2023)
    assert len(result.gains) == 1
    assert result.gains[0].date_transmission.startswith("2023")


def test_transfer_ignored_for_gains():
    """Las transferencias (depositos/retiros) no generan ganancias pero pueden entrar al pool."""
    txs = [
        CryptoTransaction(
            tx_type="transfer",
            date_utc="2024-01-01T10:00:00",
            asset="BTC",
            amount=1.0,
            price_eur=10_000.0,
            total_eur=10_000.0,
            fee_eur=0.0,
            exchange="test",
        ),
        _sell("BTC", 1.0, "2024-06-01T10:00:00", 12_000.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    # La transferencia entra al pool; la venta genera ganancia
    assert len(result.gains) == 1
    assert result.gains[0].gain_loss_eur == pytest.approx(2_000.0, abs=0.01)


def test_anti_aplicacion_summary_count():
    """El resumen cuenta correctamente las operaciones con antiaplicacion."""
    txs = [
        _buy("BTC", 2.0, "2024-01-01T10:00:00", 10_000.0),
        _sell("BTC", 1.0, "2024-03-01T10:00:00", 8_000.0),
        _buy("BTC", 1.0, "2024-03-10T10:00:00", 8_500.0),
    ]
    result = calculate_fifo_gains(txs, tax_year=2024)
    assert result.summary["anti_aplicacion_count"] >= 1
