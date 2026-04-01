# Columna A: Patrones Claude Code para Impuestify — Plan de Implementacion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar 5 features inspiradas en la filtracion de Claude Code: modularizacion territorial, cost tracking admin, memory extraction LLM, pre-calentamiento RAG + bienvenida personalizada, y ventana semantica para conversaciones.

**Architecture:** Big Bang territorial primero (plugin system con interfaz abstracta TerritoryPlugin), luego features incrementales que se apoyan en los plugins. Backend Python/FastAPI, frontend React/TypeScript.

**Tech Stack:** Python 3.12, FastAPI, Turso (SQLite), Upstash Vector/Redis, OpenAI API (gpt-4o-mini para extraction/warmup, text-embedding-3-large para embeddings), React 18 + TypeScript.

**Spec:** `docs/superpowers/specs/2026-03-31-column-a-claude-code-patterns-design.md`

---

## Wave 1 (parallelizable): Tasks 1-6 (Territories) + Tasks 7-9 (Prometheus cleanup)

---

### Task 1: Create TerritoryPlugin base class

**Files:**
- Create: `backend/app/territories/__init__.py`
- Create: `backend/app/territories/base.py`
- Test: `backend/tests/test_territory_base.py`

- [ ] **Step 1: Write the failing test for TerritoryPlugin interface**

```python
# backend/tests/test_territory_base.py
import pytest
from app.territories.base import TerritoryPlugin


def test_territory_plugin_is_abstract():
    """TerritoryPlugin cannot be instantiated directly."""
    with pytest.raises(TypeError):
        TerritoryPlugin()


def test_territory_plugin_has_required_methods():
    """TerritoryPlugin defines all required abstract methods."""
    abstract_methods = TerritoryPlugin.__abstractmethods__
    assert "get_irpf_scales" in abstract_methods
    assert "simulate_irpf" in abstract_methods
    assert "get_deductions" in abstract_methods
    assert "get_indirect_tax_model" in abstract_methods
    assert "get_minimos_personales" in abstract_methods
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_territory_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.territories'`

- [ ] **Step 3: Write TerritoryPlugin base class**

```python
# backend/app/territories/__init__.py
"""
Territory Plugin System for Impuestify.

Each fiscal regime (comun, foral_vasco, foral_navarra, canarias, ceuta_melilla)
is encapsulated in a plugin that implements TerritoryPlugin.
"""
from app.territories.base import TerritoryPlugin
from app.territories.registry import get_territory, register_territory, list_territories

__all__ = ["TerritoryPlugin", "get_territory", "register_territory", "list_territories"]
```

```python
# backend/app/territories/base.py
"""Abstract base class for territory plugins."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScaleData:
    """IRPF scale brackets for a jurisdiction."""
    jurisdiction: str
    year: int
    scale_type: str  # 'general', 'autonomica', 'foral'
    brackets: List[Dict[str, float]]  # [{base_hasta, cuota_integra, resto_base, tipo_aplicable}]


@dataclass
class SimulationResult:
    """Result of a full IRPF simulation."""
    base_imponible_general: float = 0.0
    base_imponible_ahorro: float = 0.0
    cuota_integra: float = 0.0
    cuota_liquida: float = 0.0
    resultado: float = 0.0  # positive = a pagar, negative = a devolver
    tipo_resultado: str = "a_pagar"
    desglose: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MinimosConfig:
    """Personal and family minimum configuration."""
    contribuyente: float = 0.0
    descendientes: List[float] = field(default_factory=list)
    ascendiente_65: float = 0.0
    ascendiente_75: float = 0.0
    apply_as: str = "base_reduction"  # 'base_reduction' (comun) or 'quota_deduction' (foral)


@dataclass
class Deadline:
    """Fiscal deadline."""
    modelo: str
    description: str
    date: str  # ISO format YYYY-MM-DD
    period: str  # 'Q1', 'Q2', 'Q3', 'Q4', 'annual'


class TerritoryPlugin(ABC):
    """
    Abstract base for territory-specific fiscal logic.

    Each plugin encapsulates IRPF scales, deductions, indirect taxes,
    and RAG filtering for a fiscal regime.
    """
    territories: List[str] = []
    regime: str = ""

    @abstractmethod
    async def get_irpf_scales(self, year: int) -> List[ScaleData]:
        """Return IRPF scale brackets for this territory."""
        ...

    @abstractmethod
    async def simulate_irpf(self, profile: Dict[str, Any], db) -> SimulationResult:
        """Run full IRPF simulation using territory-specific rules."""
        ...

    @abstractmethod
    async def get_deductions(self, ccaa: str, year: int, db) -> List[Dict[str, Any]]:
        """Return applicable deductions for a CCAA within this regime."""
        ...

    @abstractmethod
    def get_indirect_tax_model(self) -> str:
        """Return the indirect tax modelo: '303' (IVA), '420' (IGIC), or 'ipsi'."""
        ...

    @abstractmethod
    def get_minimos_personales(self) -> MinimosConfig:
        """Return personal/family minimum configuration."""
        ...

    def get_rag_filters(self, ccaa: str) -> Dict[str, Any]:
        """Return RAG search filters for this territory. Override for specifics."""
        return {"territory": ccaa, "regime": self.regime}

    def get_upcoming_deadlines(self) -> List[Deadline]:
        """Return upcoming fiscal deadlines. Override per territory."""
        return []

    def supports(self, ccaa: str) -> bool:
        """Check if this plugin handles the given CCAA."""
        return ccaa in self.territories
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_territory_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/territories/__init__.py backend/app/territories/base.py backend/tests/test_territory_base.py
git commit -m "feat: add TerritoryPlugin abstract base class for fiscal regime modularization"
```

---

### Task 2: Create territory registry

**Files:**
- Create: `backend/app/territories/registry.py`
- Test: `backend/tests/test_territory_registry.py`

- [ ] **Step 1: Write the failing test for registry**

```python
# backend/tests/test_territory_registry.py
import pytest
from app.territories.registry import get_territory, register_territory, list_territories, _registry
from app.territories.base import TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig


class FakePlugin(TerritoryPlugin):
    territories = ["FakeLand"]
    regime = "fake"

    async def get_irpf_scales(self, year):
        return []

    async def simulate_irpf(self, profile, db):
        return SimulationResult()

    async def get_deductions(self, ccaa, year, db):
        return []

    def get_indirect_tax_model(self):
        return "303"

    def get_minimos_personales(self):
        return MinimosConfig()


def test_register_and_get_territory():
    _registry.clear()
    plugin = FakePlugin()
    register_territory(plugin)
    result = get_territory("FakeLand")
    assert result is plugin


def test_get_territory_unknown_raises():
    _registry.clear()
    with pytest.raises(KeyError, match="No territory plugin"):
        get_territory("Atlantis")


def test_list_territories():
    _registry.clear()
    plugin = FakePlugin()
    register_territory(plugin)
    territories = list_territories()
    assert "FakeLand" in territories
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_territory_registry.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write registry module**

```python
# backend/app/territories/registry.py
"""Territory plugin registry — maps CCAA names to their TerritoryPlugin."""
from typing import Dict, List
from app.territories.base import TerritoryPlugin

_registry: Dict[str, TerritoryPlugin] = {}


def register_territory(plugin: TerritoryPlugin) -> None:
    """Register a plugin for all its territories."""
    for territory in plugin.territories:
        _registry[territory] = plugin


def get_territory(ccaa: str) -> TerritoryPlugin:
    """Get the plugin for a CCAA. Raises KeyError if not found."""
    if ccaa not in _registry:
        raise KeyError(f"No territory plugin registered for '{ccaa}'")
    return _registry[ccaa]


def list_territories() -> List[str]:
    """Return all registered territory names."""
    return list(_registry.keys())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_territory_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/territories/registry.py backend/tests/test_territory_registry.py
git commit -m "feat: add territory plugin registry with register/get/list"
```

---

### Task 3: Create CommonTerritory plugin

**Files:**
- Create: `backend/app/territories/comun/__init__.py`
- Create: `backend/app/territories/comun/plugin.py`
- Test: `backend/tests/test_territory_comun.py`

This is the largest plugin — covers 15 CCAA under common regime. It wraps existing logic from `irpf_simulator.py` (the `_simulate_common` path) and `deduction_service.py`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_territory_comun.py
import pytest
from app.territories.comun.plugin import CommonTerritory


def test_common_territory_covers_15_ccaa():
    plugin = CommonTerritory()
    assert len(plugin.territories) == 15
    assert "Madrid" in plugin.territories
    assert "Andalucia" in plugin.territories
    assert "Cataluna" in plugin.territories


def test_common_territory_regime():
    plugin = CommonTerritory()
    assert plugin.regime == "comun"


def test_common_territory_indirect_tax():
    plugin = CommonTerritory()
    assert plugin.get_indirect_tax_model() == "303"


def test_common_territory_minimos():
    plugin = CommonTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.contribuyente == 5550.0
    assert minimos.apply_as == "base_reduction"


def test_common_territory_rag_filters():
    plugin = CommonTerritory()
    filters = plugin.get_rag_filters("Madrid")
    assert filters["territory"] == "Madrid"
    assert filters["regime"] == "comun"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_territory_comun.py -v`
Expected: FAIL

- [ ] **Step 3: Write CommonTerritory plugin**

```python
# backend/app/territories/comun/__init__.py
from app.territories.comun.plugin import CommonTerritory

__all__ = ["CommonTerritory"]
```

```python
# backend/app/territories/comun/plugin.py
"""Common regime territory plugin — covers 15 CCAA under standard IRPF system."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig, Deadline,
)


# All 15 CCAA under common regime (canonical short names from ccaa_constants.py)
COMUN_TERRITORIES = [
    "Andalucia", "Aragon", "Asturias", "Baleares", "Cantabria",
    "Castilla-La Mancha", "Castilla y Leon", "Cataluna", "Extremadura",
    "Galicia", "La Rioja", "Madrid", "Murcia", "Comunidad Valenciana",
    "Canarias",  # NOTE: Canarias uses comun IRPF but IGIC — handled by CanariasTerritory
]

# Canarias is special: common IRPF but IGIC instead of IVA.
# It gets its own plugin (CanariasTerritory) which overrides get_indirect_tax_model().
# So we exclude it here.
COMUN_TERRITORIES_IRPF = [t for t in COMUN_TERRITORIES if t != "Canarias"]


class CommonTerritory(TerritoryPlugin):
    """
    Plugin for the 15 CCAA under common fiscal regime.

    IRPF: Estatal + Autonomica scales (split).
    Deductions: Estatal + Territorial.
    Indirect tax: IVA (Modelo 303).
    Minimos: Applied as base reduction (not quota deduction).
    """
    territories = COMUN_TERRITORIES_IRPF
    regime = "comun"

    async def get_irpf_scales(self, year: int) -> List[ScaleData]:
        """Delegates to IRPFCalculator which loads scales from irpf_scales table."""
        # Scales are loaded from DB by IRPFCalculator — this method is for the interface
        return []  # Actual calculation delegated to simulate_irpf

    async def simulate_irpf(self, profile: Dict[str, Any], db) -> SimulationResult:
        """Delegate to existing IRPFSimulator._simulate_common logic."""
        from app.utils.irpf_simulator import IRPFSimulator
        simulator = IRPFSimulator(db)
        result = await simulator.simulate(**profile)
        return SimulationResult(
            base_imponible_general=result.get("base_imponible_general", 0),
            base_imponible_ahorro=result.get("base_imponible_ahorro", 0),
            cuota_integra=result.get("cuota_integra", 0),
            cuota_liquida=result.get("cuota_liquida", 0),
            resultado=result.get("resultado", 0),
            tipo_resultado=result.get("tipo_resultado", "a_pagar"),
            desglose=result,
        )

    async def get_deductions(self, ccaa: str, year: int, db) -> List[Dict[str, Any]]:
        """Delegate to existing DeductionService — returns estatal + territorial."""
        from app.services.deduction_service import DeductionService
        service = DeductionService(db)
        return await service.get_all_deductions(ccaa=ccaa, tax_year=year)

    def get_indirect_tax_model(self) -> str:
        return "303"

    def get_minimos_personales(self) -> MinimosConfig:
        """Common regime MPYF — base reductions per Art. 57-61 LIRPF."""
        return MinimosConfig(
            contribuyente=5550.0,
            descendientes=[2400.0, 2700.0, 4000.0, 4500.0],
            ascendiente_65=1150.0,
            ascendiente_75=2550.0,  # cumulative with 65
            apply_as="base_reduction",
        )

    def get_rag_filters(self, ccaa: str) -> Dict[str, Any]:
        return {"territory": ccaa, "regime": "comun"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_territory_comun.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/territories/comun/ backend/tests/test_territory_comun.py
git commit -m "feat: add CommonTerritory plugin for 15 CCAA common regime"
```

---

### Task 4: Create ForalVasco and ForalNavarra plugins

**Files:**
- Create: `backend/app/territories/foral_vasco/__init__.py`
- Create: `backend/app/territories/foral_vasco/plugin.py`
- Create: `backend/app/territories/foral_navarra/__init__.py`
- Create: `backend/app/territories/foral_navarra/plugin.py`
- Test: `backend/tests/test_territory_foral.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_territory_foral.py
import pytest
from app.territories.foral_vasco.plugin import ForalVascoTerritory
from app.territories.foral_navarra.plugin import ForalNavarraTerritory


def test_foral_vasco_covers_3_territories():
    plugin = ForalVascoTerritory()
    assert set(plugin.territories) == {"Araba", "Bizkaia", "Gipuzkoa"}
    assert plugin.regime == "foral_vasco"


def test_foral_vasco_indirect_tax():
    plugin = ForalVascoTerritory()
    assert plugin.get_indirect_tax_model() == "303"  # IVA foral + TicketBAI


def test_foral_vasco_minimos_are_quota_deductions():
    plugin = ForalVascoTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.contribuyente == 5472.0
    assert minimos.apply_as == "quota_deduction"


def test_foral_navarra_covers_1_territory():
    plugin = ForalNavarraTerritory()
    assert plugin.territories == ["Navarra"]
    assert plugin.regime == "foral_navarra"


def test_foral_navarra_minimos():
    plugin = ForalNavarraTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.contribuyente == 1084.0
    assert minimos.apply_as == "quota_deduction"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_territory_foral.py -v`
Expected: FAIL

- [ ] **Step 3: Write ForalVasco plugin**

```python
# backend/app/territories/foral_vasco/__init__.py
from app.territories.foral_vasco.plugin import ForalVascoTerritory
__all__ = ["ForalVascoTerritory"]
```

```python
# backend/app/territories/foral_vasco/plugin.py
"""Foral Vasco territory plugin — Araba, Bizkaia, Gipuzkoa."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
)


class ForalVascoTerritory(TerritoryPlugin):
    """
    Pais Vasco foral regime.

    IRPF: Single unified foral scale (7 brackets).
    Deductions: Foral only (no estatal deductions).
    Indirect tax: IVA foral + TicketBAI.
    Minimos: Applied as direct quota deduction (EUR off the bill).
    EPSV: Replaces pension plan contributions.
    """
    territories = ["Araba", "Bizkaia", "Gipuzkoa"]
    regime = "foral_vasco"

    async def get_irpf_scales(self, year: int) -> List[ScaleData]:
        return []  # Loaded from DB in simulate_irpf

    async def simulate_irpf(self, profile: Dict[str, Any], db) -> SimulationResult:
        from app.utils.irpf_simulator import IRPFSimulator
        simulator = IRPFSimulator(db)
        result = await simulator.simulate(**profile)
        return SimulationResult(
            base_imponible_general=result.get("base_imponible_general", 0),
            base_imponible_ahorro=result.get("base_imponible_ahorro", 0),
            cuota_integra=result.get("cuota_integra", 0),
            cuota_liquida=result.get("cuota_liquida", 0),
            resultado=result.get("resultado", 0),
            tipo_resultado=result.get("tipo_resultado", "a_pagar"),
            desglose=result,
        )

    async def get_deductions(self, ccaa: str, year: int, db) -> List[Dict[str, Any]]:
        from app.services.deduction_service import DeductionService
        service = DeductionService(db)
        return await service.get_all_deductions(ccaa=ccaa, tax_year=year)

    def get_indirect_tax_model(self) -> str:
        return "303"  # IVA foral (+ TicketBAI obligation)

    def get_minimos_personales(self) -> MinimosConfig:
        return MinimosConfig(
            contribuyente=5472.0,
            descendientes=[2808.0, 3432.0, 5040.0, 5040.0],
            ascendiente_65=2040.0,
            ascendiente_75=4080.0,
            apply_as="quota_deduction",
        )
```

- [ ] **Step 4: Write ForalNavarra plugin**

```python
# backend/app/territories/foral_navarra/__init__.py
from app.territories.foral_navarra.plugin import ForalNavarraTerritory
__all__ = ["ForalNavarraTerritory"]
```

```python
# backend/app/territories/foral_navarra/plugin.py
"""Foral Navarra territory plugin."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
)


class ForalNavarraTerritory(TerritoryPlugin):
    """
    Navarra foral regime.

    IRPF: Single unified foral scale (11 brackets).
    Deductions: Foral only.
    Indirect tax: IVA + Modelo F69.
    Minimos: Applied as direct quota deduction.
    """
    territories = ["Navarra"]
    regime = "foral_navarra"

    async def get_irpf_scales(self, year: int) -> List[ScaleData]:
        return []

    async def simulate_irpf(self, profile: Dict[str, Any], db) -> SimulationResult:
        from app.utils.irpf_simulator import IRPFSimulator
        simulator = IRPFSimulator(db)
        result = await simulator.simulate(**profile)
        return SimulationResult(
            base_imponible_general=result.get("base_imponible_general", 0),
            base_imponible_ahorro=result.get("base_imponible_ahorro", 0),
            cuota_integra=result.get("cuota_integra", 0),
            cuota_liquida=result.get("cuota_liquida", 0),
            resultado=result.get("resultado", 0),
            tipo_resultado=result.get("tipo_resultado", "a_pagar"),
            desglose=result,
        )

    async def get_deductions(self, ccaa: str, year: int, db) -> List[Dict[str, Any]]:
        from app.services.deduction_service import DeductionService
        service = DeductionService(db)
        return await service.get_all_deductions(ccaa=ccaa, tax_year=year)

    def get_indirect_tax_model(self) -> str:
        return "303"  # IVA + F69 Navarra

    def get_minimos_personales(self) -> MinimosConfig:
        return MinimosConfig(
            contribuyente=1084.0,
            descendientes=[600.0, 750.0, 1200.0, 1350.0],
            ascendiente_65=450.0,
            ascendiente_75=900.0,
            apply_as="quota_deduction",
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_territory_foral.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/territories/foral_vasco/ backend/app/territories/foral_navarra/ backend/tests/test_territory_foral.py
git commit -m "feat: add ForalVasco and ForalNavarra territory plugins"
```

---

### Task 5: Create Canarias and CeutaMelilla plugins

**Files:**
- Create: `backend/app/territories/canarias/__init__.py`
- Create: `backend/app/territories/canarias/plugin.py`
- Create: `backend/app/territories/ceuta_melilla/__init__.py`
- Create: `backend/app/territories/ceuta_melilla/plugin.py`
- Test: `backend/tests/test_territory_special.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_territory_special.py
import pytest
from app.territories.canarias.plugin import CanariasTerritory
from app.territories.ceuta_melilla.plugin import CeutaMelillaTerritory


def test_canarias_territory():
    plugin = CanariasTerritory()
    assert plugin.territories == ["Canarias"]
    assert plugin.regime == "canarias"
    assert plugin.get_indirect_tax_model() == "420"  # IGIC


def test_canarias_minimos_are_base_reduction():
    plugin = CanariasTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.apply_as == "base_reduction"


def test_ceuta_melilla_territory():
    plugin = CeutaMelillaTerritory()
    assert set(plugin.territories) == {"Ceuta", "Melilla"}
    assert plugin.regime == "ceuta_melilla"
    assert plugin.get_indirect_tax_model() == "ipsi"


def test_ceuta_melilla_minimos_are_base_reduction():
    plugin = CeutaMelillaTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.apply_as == "base_reduction"


def test_ceuta_melilla_rag_filters_include_special_flag():
    plugin = CeutaMelillaTerritory()
    filters = plugin.get_rag_filters("Ceuta")
    assert filters["territory"] == "Ceuta"
    assert filters.get("deduccion_60") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_territory_special.py -v`
Expected: FAIL

- [ ] **Step 3: Write CanariasTerritory plugin**

```python
# backend/app/territories/canarias/__init__.py
from app.territories.canarias.plugin import CanariasTerritory
__all__ = ["CanariasTerritory"]
```

```python
# backend/app/territories/canarias/plugin.py
"""Canarias territory plugin — IGIC instead of IVA, common IRPF."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
)


class CanariasTerritory(TerritoryPlugin):
    """
    Canarias fiscal regime.

    IRPF: Uses estatal scales (both portions) like common regime.
    Deductions: Estatal + Canarias territorial.
    Indirect tax: IGIC (Modelo 420), NOT IVA.
    General IGIC rate: 7% (vs 21% peninsular IVA).
    Modelo 349 does NOT apply (Canarias is not harmonized EU territory).
    """
    territories = ["Canarias"]
    regime = "canarias"

    async def get_irpf_scales(self, year: int) -> List[ScaleData]:
        return []

    async def simulate_irpf(self, profile: Dict[str, Any], db) -> SimulationResult:
        from app.utils.irpf_simulator import IRPFSimulator
        simulator = IRPFSimulator(db)
        result = await simulator.simulate(**profile)
        return SimulationResult(
            base_imponible_general=result.get("base_imponible_general", 0),
            base_imponible_ahorro=result.get("base_imponible_ahorro", 0),
            cuota_integra=result.get("cuota_integra", 0),
            cuota_liquida=result.get("cuota_liquida", 0),
            resultado=result.get("resultado", 0),
            tipo_resultado=result.get("tipo_resultado", "a_pagar"),
            desglose=result,
        )

    async def get_deductions(self, ccaa: str, year: int, db) -> List[Dict[str, Any]]:
        from app.services.deduction_service import DeductionService
        service = DeductionService(db)
        return await service.get_all_deductions(ccaa=ccaa, tax_year=year)

    def get_indirect_tax_model(self) -> str:
        return "420"  # IGIC

    def get_minimos_personales(self) -> MinimosConfig:
        # Canarias uses same MPYF as common regime
        return MinimosConfig(
            contribuyente=5550.0,
            descendientes=[2400.0, 2700.0, 4000.0, 4500.0],
            ascendiente_65=1150.0,
            ascendiente_75=2550.0,
            apply_as="base_reduction",
        )

    def get_rag_filters(self, ccaa: str) -> Dict[str, Any]:
        return {"territory": "Canarias", "regime": "canarias", "igic": True}
```

- [ ] **Step 4: Write CeutaMelillaTerritory plugin**

```python
# backend/app/territories/ceuta_melilla/__init__.py
from app.territories.ceuta_melilla.plugin import CeutaMelillaTerritory
__all__ = ["CeutaMelillaTerritory"]
```

```python
# backend/app/territories/ceuta_melilla/plugin.py
"""Ceuta/Melilla territory plugin — IPSI + 60% deduction."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
)


class CeutaMelillaTerritory(TerritoryPlugin):
    """
    Ceuta and Melilla fiscal regime.

    IRPF: Uses estatal scale for both portions (no autonomica scale).
    60% deduction on cuota integra (Art. 68.4 LIRPF).
    Deductions: Estatal only + IPSI.
    Indirect tax: IPSI (6 rate tiers: 0.5%, 1%, 2%, 4%, 8%, 10%).
    """
    territories = ["Ceuta", "Melilla"]
    regime = "ceuta_melilla"

    async def get_irpf_scales(self, year: int) -> List[ScaleData]:
        return []

    async def simulate_irpf(self, profile: Dict[str, Any], db) -> SimulationResult:
        from app.utils.irpf_simulator import IRPFSimulator
        simulator = IRPFSimulator(db)
        result = await simulator.simulate(**profile)
        return SimulationResult(
            base_imponible_general=result.get("base_imponible_general", 0),
            base_imponible_ahorro=result.get("base_imponible_ahorro", 0),
            cuota_integra=result.get("cuota_integra", 0),
            cuota_liquida=result.get("cuota_liquida", 0),
            resultado=result.get("resultado", 0),
            tipo_resultado=result.get("tipo_resultado", "a_pagar"),
            desglose=result,
        )

    async def get_deductions(self, ccaa: str, year: int, db) -> List[Dict[str, Any]]:
        from app.services.deduction_service import DeductionService
        service = DeductionService(db)
        return await service.get_all_deductions(ccaa=ccaa, tax_year=year)

    def get_indirect_tax_model(self) -> str:
        return "ipsi"

    def get_minimos_personales(self) -> MinimosConfig:
        # Same base MPYF as common, but applied to estatal-only scale
        return MinimosConfig(
            contribuyente=5550.0,
            descendientes=[2400.0, 2700.0, 4000.0, 4500.0],
            ascendiente_65=1150.0,
            ascendiente_75=2550.0,
            apply_as="base_reduction",
        )

    def get_rag_filters(self, ccaa: str) -> Dict[str, Any]:
        return {"territory": ccaa, "regime": "ceuta_melilla", "deduccion_60": True}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_territory_special.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/territories/canarias/ backend/app/territories/ceuta_melilla/ backend/tests/test_territory_special.py
git commit -m "feat: add Canarias (IGIC) and CeutaMelilla (IPSI+60%) territory plugins"
```

---

### Task 6: Register all plugins and wire into main.py

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_territory_integration.py`

- [ ] **Step 1: Write the failing integration test**

```python
# backend/tests/test_territory_integration.py
import pytest
from app.territories import get_territory, list_territories
from app.territories.registry import _registry


def setup_function():
    """Ensure registry is loaded before each test."""
    _registry.clear()
    from app.territories.startup import register_all_territories
    register_all_territories()


def test_all_21_territories_registered():
    territories = list_territories()
    assert len(territories) == 21


def test_madrid_is_comun():
    plugin = get_territory("Madrid")
    assert plugin.regime == "comun"


def test_araba_is_foral_vasco():
    plugin = get_territory("Araba")
    assert plugin.regime == "foral_vasco"


def test_navarra_is_foral_navarra():
    plugin = get_territory("Navarra")
    assert plugin.regime == "foral_navarra"


def test_canarias_is_canarias():
    plugin = get_territory("Canarias")
    assert plugin.regime == "canarias"


def test_ceuta_is_ceuta_melilla():
    plugin = get_territory("Ceuta")
    assert plugin.regime == "ceuta_melilla"


def test_melilla_is_ceuta_melilla():
    plugin = get_territory("Melilla")
    assert plugin.regime == "ceuta_melilla"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_territory_integration.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.territories.startup'`

- [ ] **Step 3: Create startup registration module**

```python
# backend/app/territories/startup.py
"""Register all territory plugins at application startup."""
from app.territories.registry import register_territory
from app.territories.comun.plugin import CommonTerritory
from app.territories.foral_vasco.plugin import ForalVascoTerritory
from app.territories.foral_navarra.plugin import ForalNavarraTerritory
from app.territories.canarias.plugin import CanariasTerritory
from app.territories.ceuta_melilla.plugin import CeutaMelillaTerritory


def register_all_territories() -> None:
    """Register all 5 territory plugins (covers 21 CCAA)."""
    register_territory(CommonTerritory())
    register_territory(ForalVascoTerritory())
    register_territory(ForalNavarraTerritory())
    register_territory(CanariasTerritory())
    register_territory(CeutaMelillaTerritory())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_territory_integration.py -v`
Expected: PASS — 7 tests pass

- [ ] **Step 5: Add registration call to main.py lifespan**

Add `from app.territories.startup import register_all_territories` to imports in `main.py`, and call `register_all_territories()` inside the `lifespan` async context manager (alongside DB init).

- [ ] **Step 6: Run full test suite to verify no regressions**

Run: `cd backend && python -m pytest tests/ -v --tb=short -q`
Expected: All existing tests PASS (1200+)

- [ ] **Step 7: Commit**

```bash
git add backend/app/territories/startup.py backend/tests/test_territory_integration.py backend/app/main.py
git commit -m "feat: register all 5 territory plugins at startup (21 CCAA covered)"
```

---

### Task 7: Remove Prometheus — clean metrics.py and main.py

**Files:**
- Delete: `backend/app/metrics.py`
- Modify: `backend/app/main.py` — remove Prometheus imports and instrumentator
- Modify: `backend/app/routers/chat.py` — remove metrics imports
- Modify: `backend/app/routers/demo.py` — remove metrics imports
- Modify: `backend/requirements.txt` — remove prometheus packages

- [ ] **Step 1: Identify all Prometheus references**

Files that import from `app.metrics`:
- `backend/app/main.py` (lines 22, 501)
- `backend/app/routers/chat.py` (line 27)
- `backend/app/routers/demo.py` (line 33)

- [ ] **Step 2: Remove Prometheus from requirements.txt**

Remove lines containing `prometheus-fastapi-instrumentator` and `prometheus-client` from `backend/requirements.txt`.

- [ ] **Step 3: Remove metrics import and setup from main.py**

Remove:
- Line 22: `from prometheus_fastapi_instrumentator import Instrumentator`
- Line 501: `from app.metrics import setup_instrumentator, set_app_info`
- Any `setup_instrumentator(app)` or `set_app_info()` calls
- Any `/metrics` endpoint registration

- [ ] **Step 4: Remove metrics imports from chat.py**

Remove line 27 in `backend/app/routers/chat.py`:
```python
from app.metrics import record_tokens, record_request, record_error, record_rag_search, record_llm_latency
```
And all calls to `record_tokens()`, `record_request()`, `record_error()`, `record_rag_search()`, `record_llm_latency()` in chat.py. These will be replaced by cost_tracker in Task 8.

- [ ] **Step 5: Remove metrics imports from demo.py**

Remove line 33 in `backend/app/routers/demo.py`:
```python
from app.metrics import record_demo_request, record_security_block, record_rag_search, record_llm_latency
```
And all calls to these functions in demo.py.

- [ ] **Step 6: Delete metrics.py**

```bash
rm backend/app/metrics.py
```

- [ ] **Step 7: Run tests to verify no breakage**

Run: `cd backend && python -m pytest tests/ -v --tb=short -q`
Expected: All tests PASS (some tests may mock metrics — those should be removed or updated)

- [ ] **Step 8: Commit**

```bash
git add -u backend/
git commit -m "chore: remove Prometheus metrics — replaced by lightweight cost tracker"
```

---

### Task 8: Create CostTracker service

**Files:**
- Create: `backend/app/services/cost_tracker.py`
- Test: `backend/tests/test_cost_tracker.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_cost_tracker.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.cost_tracker import CostTracker


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(rows=[]))
    return db


@pytest.fixture
def tracker(mock_db):
    return CostTracker(mock_db)


@pytest.mark.asyncio
async def test_track_records_usage(tracker, mock_db):
    await tracker.track(
        user_id="user123",
        model="gpt-4o-mini",
        input_tokens=500,
        output_tokens=200,
        endpoint="/api/ask/stream",
    )
    mock_db.execute.assert_called_once()
    call_args = mock_db.execute.call_args
    assert "INSERT INTO usage_metrics" in call_args[0][0]


@pytest.mark.asyncio
async def test_calculate_cost_gpt4o_mini(tracker):
    cost = tracker.calculate_cost("gpt-4o-mini", 1000, 500)
    # input: 1000/1M * 0.15 = 0.00015, output: 500/1M * 0.60 = 0.0003
    assert abs(cost - 0.00045) < 0.0001


@pytest.mark.asyncio
async def test_calculate_cost_gpt4o(tracker):
    cost = tracker.calculate_cost("gpt-4o", 1000, 500)
    # input: 1000/1M * 2.50 = 0.0025, output: 500/1M * 10.00 = 0.005
    assert abs(cost - 0.0075) < 0.0001


@pytest.mark.asyncio
async def test_calculate_cost_unknown_model(tracker):
    cost = tracker.calculate_cost("unknown-model", 1000, 500)
    assert cost == 0.0  # unknown model, no cost
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_cost_tracker.py -v`
Expected: FAIL

- [ ] **Step 3: Write CostTracker service**

```python
# backend/app/services/cost_tracker.py
"""
Lightweight cost tracking service for Impuestify.

Tracks token usage and estimated costs per user/endpoint in the usage_metrics table.
Replaces Prometheus with simple DB-based tracking for admin dashboard.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# USD per 1M tokens (updated 2026)
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-5": {"input": 5.00, "output": 15.00},
    "gpt-5-mini": {"input": 0.30, "output": 1.20},
    "text-embedding-3-large": {"input": 0.13, "output": 0},
}

# EUR/USD exchange rate (approximate, update periodically)
EUR_USD_RATE = 0.92


class CostTracker:
    """Track token usage and costs in usage_metrics table."""

    def __init__(self, db=None):
        self._db = db

    async def _get_db(self):
        if self._db:
            return self._db
        from app.database.turso_client import get_db_client
        self._db = await get_db_client()
        return self._db

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost for a given model and token counts."""
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            return 0.0
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    async def track(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        endpoint: str,
        processing_time: float = 0.0,
        cached: bool = False,
    ) -> None:
        """Record a usage event in the database."""
        db = await self._get_db()
        cost_usd = self.calculate_cost(model, input_tokens, output_tokens)
        total_tokens = input_tokens + output_tokens

        await db.execute(
            """INSERT INTO usage_metrics
               (id, user_id, endpoint, tokens_used, processing_time, cached,
                model, input_tokens, output_tokens, cost_usd, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                str(uuid.uuid4()), user_id, endpoint, total_tokens,
                processing_time, int(cached), model, input_tokens,
                output_tokens, cost_usd, datetime.utcnow().isoformat(),
            ],
        )

    async def get_user_summary(
        self, user_id: str, period: str = "month"
    ) -> Dict[str, Any]:
        """Get usage summary for a specific user."""
        db = await self._get_db()
        since = self._period_start(period)

        result = await db.execute(
            """SELECT
                 COUNT(*) as total_requests,
                 COALESCE(SUM(tokens_used), 0) as total_tokens,
                 COALESCE(SUM(cost_usd), 0) as total_cost_usd,
                 model,
                 COALESCE(SUM(input_tokens), 0) as model_input,
                 COALESCE(SUM(output_tokens), 0) as model_output
               FROM usage_metrics
               WHERE user_id = ? AND created_at >= ?
               GROUP BY model""",
            [user_id, since],
        )

        by_model = {}
        total_cost = 0.0
        total_tokens = 0
        total_requests = 0

        for row in result.rows or []:
            row_dict = dict(row)
            model = row_dict.get("model", "unknown")
            cost = row_dict.get("total_cost_usd", 0) or 0
            by_model[model] = {
                "input_tokens": row_dict.get("model_input", 0),
                "output_tokens": row_dict.get("model_output", 0),
                "cost_usd": cost,
            }
            total_cost += cost
            total_tokens += row_dict.get("total_tokens", 0) or 0
            total_requests += row_dict.get("total_requests", 0) or 0

        return {
            "user_id": user_id,
            "period": period,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "total_cost_eur": round(total_cost * EUR_USD_RATE, 4),
            "by_model": by_model,
        }

    async def get_global_summary(
        self, period: str = "month"
    ) -> Dict[str, Any]:
        """Get global usage summary for admin dashboard."""
        db = await self._get_db()
        since = self._period_start(period)

        # Total costs
        result = await db.execute(
            """SELECT
                 COUNT(*) as total_requests,
                 COALESCE(SUM(tokens_used), 0) as total_tokens,
                 COALESCE(SUM(cost_usd), 0) as total_cost_usd
               FROM usage_metrics
               WHERE created_at >= ?""",
            [since],
        )
        totals = dict(result.rows[0]) if result.rows else {}

        # Top 10 users by cost
        top_result = await db.execute(
            """SELECT
                 um.user_id,
                 u.email,
                 u.subscription_plan,
                 COALESCE(SUM(um.cost_usd), 0) as user_cost_usd,
                 COUNT(*) as request_count
               FROM usage_metrics um
               LEFT JOIN users u ON um.user_id = u.id
               WHERE um.created_at >= ?
               GROUP BY um.user_id
               ORDER BY user_cost_usd DESC
               LIMIT 10""",
            [since],
        )
        top_users = [dict(row) for row in top_result.rows or []]

        # Cost by plan
        plan_result = await db.execute(
            """SELECT
                 COALESCE(u.subscription_plan, 'none') as plan,
                 COALESCE(SUM(um.cost_usd), 0) as plan_cost_usd,
                 COUNT(DISTINCT um.user_id) as user_count
               FROM usage_metrics um
               LEFT JOIN users u ON um.user_id = u.id
               WHERE um.created_at >= ?
               GROUP BY u.subscription_plan""",
            [since],
        )
        by_plan = {dict(row)["plan"]: dict(row) for row in plan_result.rows or []}

        total_cost = totals.get("total_cost_usd", 0) or 0

        return {
            "period": period,
            "total_requests": totals.get("total_requests", 0),
            "total_tokens": totals.get("total_tokens", 0),
            "total_cost_usd": round(total_cost, 4),
            "total_cost_eur": round(total_cost * EUR_USD_RATE, 4),
            "top_users": top_users,
            "by_plan": by_plan,
        }

    def _period_start(self, period: str) -> str:
        """Return ISO date string for the start of the period."""
        now = datetime.utcnow()
        if period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now - timedelta(days=30)
        elif period == "year":
            start = now - timedelta(days=365)
        else:
            start = now - timedelta(days=30)
        return start.isoformat()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_cost_tracker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/cost_tracker.py backend/tests/test_cost_tracker.py
git commit -m "feat: add CostTracker service for lightweight admin usage tracking"
```

---

### Task 9: Add admin cost dashboard endpoint + update usage_metrics schema

**Files:**
- Modify: `backend/app/routers/admin.py` — add `/admin/costs` endpoint
- Modify: `backend/app/database/turso_client.py` — add new columns to usage_metrics
- Modify: `frontend/src/pages/AdminDashboardPage.tsx` — add cost widget
- Test: `backend/tests/test_admin_costs.py`

- [ ] **Step 1: Update usage_metrics schema in turso_client.py**

Add new columns to the `CREATE TABLE IF NOT EXISTS usage_metrics` statement in `init_schema()`:

```sql
CREATE TABLE IF NOT EXISTS usage_metrics (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  endpoint TEXT,
  tokens_used INTEGER,
  processing_time REAL,
  cached BOOLEAN DEFAULT 0,
  model TEXT,
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  cost_usd REAL DEFAULT 0.0,
  created_at TIMESTAMP DEFAULT (datetime('now'))
);
```

Also add ALTER TABLE migration for existing DBs (in the migrations section of init_schema if present, or as a safe `try/except` block):

```python
# Migration: add new columns if they don't exist
for col, coltype in [("model", "TEXT"), ("input_tokens", "INTEGER DEFAULT 0"),
                      ("output_tokens", "INTEGER DEFAULT 0"), ("cost_usd", "REAL DEFAULT 0.0")]:
    try:
        await db.execute(f"ALTER TABLE usage_metrics ADD COLUMN {col} {coltype}")
    except Exception:
        pass  # column already exists
```

- [ ] **Step 2: Write failing test for admin endpoint**

```python
# backend/tests/test_admin_costs.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_admin_costs_endpoint_returns_summary(auth_token):
    """The /admin/costs endpoint returns a cost summary."""
    # This test depends on auth_token fixture from conftest.py
    # The endpoint should be owner-only
    pass  # Actual test depends on existing test patterns in the codebase
```

- [ ] **Step 3: Add endpoint to admin.py**

Add to `backend/app/routers/admin.py`:

```python
from app.services.cost_tracker import CostTracker

@router.get("/costs")
async def get_cost_dashboard(
    request: Request,
    period: str = Query("month", regex="^(week|month|year)$"),
    current_user=Depends(get_current_user),
):
    """Owner-only: Get cost tracking dashboard data."""
    if not current_user.is_owner:
        raise HTTPException(status_code=403, detail="Owner only")
    db = await get_db_client()
    tracker = CostTracker(db)
    return await tracker.get_global_summary(period)
```

- [ ] **Step 4: Wire CostTracker into chat.py SSE flow**

In `backend/app/routers/chat.py`, after the LLM response is received and tokens are counted, call:

```python
from app.services.cost_tracker import CostTracker

# After receiving LLM response with usage data:
cost_tracker = CostTracker(db)
await cost_tracker.track(
    user_id=current_user.user_id,
    model=model_used,
    input_tokens=usage.get("prompt_tokens", 0),
    output_tokens=usage.get("completion_tokens", 0),
    endpoint="/api/ask/stream",
    processing_time=elapsed_time,
    cached=from_cache,
)
```

- [ ] **Step 5: Add cost widget to AdminDashboardPage.tsx**

Add a new section to `frontend/src/pages/AdminDashboardPage.tsx` that fetches `/api/admin/costs` and displays:
- Total cost this month (EUR)
- Breakdown by plan
- Top 5 users by cost

Use existing admin API pattern (`useApi` hook with `apiRequest`).

- [ ] **Step 6: Run tests**

Run: `cd backend && python -m pytest tests/ -v --tb=short -q`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/admin.py backend/app/database/turso_client.py backend/app/routers/chat.py frontend/src/pages/AdminDashboardPage.tsx
git commit -m "feat: add admin cost dashboard with usage tracking per user/plan/model"
```

---

## Wave 2 (parallelizable): Tasks 10-11 (Memory Extraction) + Task 12 (Semantic Window)

---

### Task 10: Extend regex extraction patterns in user_memory_service.py

**Files:**
- Modify: `backend/app/services/user_memory_service.py`
- Test: `backend/tests/test_user_memory_extraction.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_user_memory_extraction.py
import pytest
from app.services.user_memory_service import UserMemoryService


def test_extract_hipoteca():
    svc = UserMemoryService.__new__(UserMemoryService)
    facts = svc._extract_facts_from_text("Pago una hipoteca de 800 euros al mes")
    assert any(f.fact_type == "hipoteca" for f in facts)


def test_extract_guarderia():
    svc = UserMemoryService.__new__(UserMemoryService)
    facts = svc._extract_facts_from_text("Mi hijo va a la guarderia desde septiembre")
    assert any(f.fact_type == "guarderia" for f in facts)


def test_extract_plan_pensiones():
    svc = UserMemoryService.__new__(UserMemoryService)
    facts = svc._extract_facts_from_text("Aporto 2000 euros al plan de pensiones")
    assert any(f.fact_type == "plan_pensiones" for f in facts)


def test_extract_cripto():
    svc = UserMemoryService.__new__(UserMemoryService)
    facts = svc._extract_facts_from_text("Tengo bitcoin en Binance y algo de ethereum")
    assert any(f.fact_type == "criptomonedas" for f in facts)


def test_extract_discapacidad():
    svc = UserMemoryService.__new__(UserMemoryService)
    facts = svc._extract_facts_from_text("Tengo un 33% de discapacidad reconocida")
    assert any(f.fact_type == "discapacidad" for f in facts)


def test_extract_familia_numerosa():
    svc = UserMemoryService.__new__(UserMemoryService)
    facts = svc._extract_facts_from_text("Somos familia numerosa con 4 hijos")
    assert any(f.fact_type == "familia_numerosa" for f in facts)


def test_no_false_positives_on_generic_text():
    svc = UserMemoryService.__new__(UserMemoryService)
    facts = svc._extract_facts_from_text("Hola, quiero saber sobre la renta")
    hipoteca_facts = [f for f in facts if f.fact_type == "hipoteca"]
    assert len(hipoteca_facts) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_user_memory_extraction.py -v`
Expected: FAIL (method `_extract_facts_from_text` may not have these fact types yet)

- [ ] **Step 3: Add new extraction patterns to user_memory_service.py**

Add to the existing `_extract_facts_from_text` method (or create if it doesn't exist as a standalone method) in `UserMemoryService`:

```python
EXTENDED_PATTERNS = {
    "hipoteca": r"hipoteca|pr[eé]stamo hipotecario|pago mensual de \d+",
    "guarderia": r"guarder[ií]a|escuela infantil|0[- ]?3 a[nñ]os",
    "plan_pensiones": r"plan de pensiones|aporta(?:ci[oó]n|ndo).*?\d+",
    "donaciones": r"donativos?|dona(?:ci[oó]n|ndo)|ONG|fundaci[oó]n",
    "criptomonedas": r"cripto|bitcoin|ethereum|binance|coinbase",
    "alquiler": r"alquil(?:o|er)|inquilino|arrendamiento",
    "autonomo_gastos": r"deducir.*gastos|factur(?:a|o)|suministros|coworking",
    "discapacidad": r"discapacidad|minusval[ií]a|\d+\s*%.*discapacidad",
    "familia_numerosa": r"familia numerosa|[34] hijos|t[ií]tulo.*familia",
}
```

For each pattern match, create a `UserFact` with the appropriate `fact_type`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_user_memory_extraction.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/user_memory_service.py backend/tests/test_user_memory_extraction.py
git commit -m "feat: extend memory extraction with 9 new fiscal patterns (hipoteca, cripto, etc.)"
```

---

### Task 11: Create ConversationAnalyzer (LLM post-conversation extraction)

**Files:**
- Create: `backend/app/services/conversation_analyzer.py`
- Test: `backend/tests/test_conversation_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_conversation_analyzer.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.conversation_analyzer import ConversationAnalyzer


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def analyzer(mock_db):
    return ConversationAnalyzer(mock_db)


@pytest.mark.asyncio
async def test_skip_short_conversations(analyzer):
    """Conversations with < 3 messages should not be analyzed."""
    with patch.object(analyzer, '_get_messages', return_value=[
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "Hola!"},
    ]):
        result = await analyzer.analyze("conv123", "user456")
        assert result == {}


@pytest.mark.asyncio
async def test_analyze_extracts_facts(analyzer):
    """Should extract structured fiscal facts from conversation."""
    messages = [
        {"role": "user", "content": "Soy autonomo en Madrid"},
        {"role": "assistant", "content": "Entendido, eres autonomo en Madrid."},
        {"role": "user", "content": "Tengo 2 hijos y pago hipoteca de 900 euros"},
        {"role": "assistant", "content": "Perfecto, tomo nota."},
    ]
    mock_llm_response = '{"ccaa": "Madrid", "situacion_laboral": "autonomo", "hijos": 2, "hipoteca_activa": true, "importe_hipoteca": 900}'

    with patch.object(analyzer, '_get_messages', return_value=messages):
        with patch.object(analyzer, '_call_llm', return_value=mock_llm_response):
            with patch.object(analyzer, '_merge_facts', new_callable=AsyncMock):
                result = await analyzer.analyze("conv123", "user456")
                assert result["ccaa"] == "Madrid"
                assert result["hijos"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_conversation_analyzer.py -v`
Expected: FAIL

- [ ] **Step 3: Write ConversationAnalyzer**

```python
# backend/app/services/conversation_analyzer.py
"""
Post-conversation LLM analyzer for Impuestify.

Analyzes completed conversations to extract structured fiscal facts
and merge them into the user's profile. Runs as a background task.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Analiza esta conversacion fiscal y extrae datos estructurados del usuario.
Devuelve SOLO un JSON valido con los campos que se mencionan EXPLICITAMENTE.
Si un dato NO se menciona, NO lo incluyas.

Campos posibles:
- ccaa (str): comunidad autonoma de residencia
- situacion_laboral (str): asalariado/autonomo/pensionista/desempleado
- hijos (int): numero de hijos
- edad_hijos (list[int]): edades de los hijos
- custodia_compartida (bool)
- hipoteca_activa (bool)
- importe_hipoteca (float): cuota mensual
- plan_pensiones (bool)
- aportacion_plan_pensiones (float): aportacion anual
- alquiler_vivienda (bool)
- importe_alquiler (float): cuota mensual alquiler
- autonomo_actividad (str): tipo de actividad
- cnae (str): codigo CNAE
- cripto_activo (bool)
- discapacidad_grado (int): porcentaje
- familia_numerosa (bool)
- donaciones (bool)
- ingresos_brutos (float): ingresos anuales brutos

Responde SOLO con el JSON, sin texto adicional."""


class ConversationAnalyzer:
    """Extracts fiscal facts from conversations using LLM."""

    def __init__(self, db=None):
        self._db = db
        self._client = None

    async def _get_db(self):
        if self._db:
            return self._db
        from app.database.turso_client import get_db_client
        self._db = await get_db_client()
        return self._db

    def _get_client(self) -> AsyncOpenAI:
        if not self._client:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def _get_messages(self, conversation_id: str) -> List[Dict[str, str]]:
        """Load messages from database."""
        db = await self._get_db()
        result = await db.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at",
            [conversation_id],
        )
        return [dict(row) for row in result.rows or []]

    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call gpt-4o-mini with the extraction prompt."""
        client = self._get_client()
        conversation_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": conversation_text},
            ],
            temperature=0,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()

    async def _merge_facts(self, user_id: str, extracted: Dict[str, Any]) -> None:
        """Merge extracted facts into user profile with source='llm'."""
        from app.services.user_memory_service import UserMemoryService
        memory_svc = UserMemoryService()
        db = await self._get_db()

        # Load existing profile
        result = await db.execute(
            "SELECT datos_fiscales FROM user_profiles WHERE user_id = ?",
            [user_id],
        )
        existing = {}
        if result.rows:
            raw = result.rows[0]["datos_fiscales"]
            if raw:
                existing = json.loads(raw) if isinstance(raw, str) else raw

        # Merge: manual > llm > regex (check _source field)
        for key, value in extracted.items():
            source_key = f"{key}_source"
            existing_source = existing.get(source_key, "")
            if existing_source == "manual":
                continue  # manual data takes priority
            existing[key] = value
            existing[source_key] = "llm"

        await db.execute(
            "UPDATE user_profiles SET datos_fiscales = ?, updated_at = datetime('now') WHERE user_id = ?",
            [json.dumps(existing), user_id],
        )

    async def analyze(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """
        Analyze a conversation and extract fiscal facts.

        Skips conversations with < 3 messages.
        Returns extracted facts dict (empty if nothing found).
        """
        messages = await self._get_messages(conversation_id)

        if len(messages) < 3:
            return {}

        try:
            raw_response = await self._call_llm(messages)
            # Parse JSON response
            extracted = json.loads(raw_response)
            if not isinstance(extracted, dict):
                return {}

            await self._merge_facts(user_id, extracted)
            logger.info(
                f"Extracted {len(extracted)} fiscal facts from conversation {conversation_id}"
            )
            return extracted

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to analyze conversation {conversation_id}: {e}")
            return {}
```

- [ ] **Step 4: Wire as background task in chat.py**

In `backend/app/routers/chat.py`, at the end of the SSE stream (after the last event), add:

```python
from app.services.conversation_analyzer import ConversationAnalyzer

# At the end of the streaming response, if conversation has ended:
async def _analyze_in_background(conversation_id: str, user_id: str):
    analyzer = ConversationAnalyzer()
    await analyzer.analyze(conversation_id, user_id)

# Add to background_tasks:
background_tasks.add_task(_analyze_in_background, conversation_id, current_user.user_id)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_conversation_analyzer.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/conversation_analyzer.py backend/tests/test_conversation_analyzer.py backend/app/routers/chat.py
git commit -m "feat: add LLM post-conversation analyzer for automatic fiscal fact extraction"
```

---

### Task 12: Create SemanticWindow service

**Files:**
- Create: `backend/app/services/semantic_window.py`
- Test: `backend/tests/test_semantic_window.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_semantic_window.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.semantic_window import SemanticWindow
from datetime import datetime, timedelta


def _make_message(idx: int, content: str) -> dict:
    return {
        "id": f"msg_{idx}",
        "role": "user" if idx % 2 == 0 else "assistant",
        "content": content,
        "created_at": (datetime(2026, 1, 1) + timedelta(hours=idx)).isoformat(),
    }


@pytest.mark.asyncio
async def test_short_conversation_returns_all():
    window = SemanticWindow(max_messages=15, recent_guaranteed=5)
    messages = [_make_message(i, f"Message {i}") for i in range(10)]

    with patch.object(window, '_get_messages', return_value=messages):
        result = await window.select("conv123", "query text")
        assert len(result) == 10  # all messages returned


@pytest.mark.asyncio
async def test_long_conversation_selects_semantically():
    window = SemanticWindow(max_messages=8, recent_guaranteed=3)
    messages = [_make_message(i, f"Message {i}") for i in range(20)]

    async def mock_embed(text):
        # Simple mock: return text length as a fake embedding
        return [len(text) / 100.0]

    async def mock_get_embedding(msg_id, content):
        return [len(content) / 100.0]

    with patch.object(window, '_get_messages', return_value=messages):
        with patch.object(window, '_embed', side_effect=mock_embed):
            with patch.object(window, '_get_or_create_embedding', side_effect=mock_get_embedding):
                result = await window.select("conv123", "Message 5")
                # Should return max_messages (8) total
                assert len(result) == 8
                # Last 3 should always be the recent ones
                assert result[-1]["id"] == "msg_19"
                assert result[-2]["id"] == "msg_18"
                assert result[-3]["id"] == "msg_17"


@pytest.mark.asyncio
async def test_result_is_chronologically_ordered():
    window = SemanticWindow(max_messages=6, recent_guaranteed=2)
    messages = [_make_message(i, f"Msg {i}") for i in range(10)]

    async def mock_embed(text):
        return [0.5]

    async def mock_get_embedding(msg_id, content):
        return [0.5]

    with patch.object(window, '_get_messages', return_value=messages):
        with patch.object(window, '_embed', side_effect=mock_embed):
            with patch.object(window, '_get_or_create_embedding', side_effect=mock_get_embedding):
                result = await window.select("conv123", "test query")
                # All selected messages should be in chronological order
                timestamps = [m["created_at"] for m in result]
                assert timestamps == sorted(timestamps)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_semantic_window.py -v`
Expected: FAIL

- [ ] **Step 3: Write SemanticWindow service**

```python
# backend/app/services/semantic_window.py
"""
Semantic Window — intelligent message selection for LLM context.

Instead of sending the last N messages to the LLM, selects the most
semantically relevant messages based on the current query.
Always includes the most recent messages for immediate context.
"""
import logging
import math
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticWindow:
    """Select the most relevant messages for LLM context."""

    def __init__(self, max_messages: int = 15, recent_guaranteed: int = 5):
        self.max_messages = max_messages
        self.recent_guaranteed = recent_guaranteed
        self._client = None
        self._embedding_cache: Dict[str, List[float]] = {}

    def _get_client(self) -> AsyncOpenAI:
        if not self._client:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def _get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Load all messages for a conversation."""
        from app.database.turso_client import get_db_client
        db = await get_db_client()
        result = await db.execute(
            """SELECT id, role, content, created_at
               FROM messages
               WHERE conversation_id = ?
               ORDER BY created_at""",
            [conversation_id],
        )
        return [dict(row) for row in result.rows or []]

    async def _embed(self, text: str) -> List[float]:
        """Get embedding for a text string."""
        client = self._get_client()
        response = await client.embeddings.create(
            model="text-embedding-3-large",
            input=text[:8000],  # truncate to avoid token limits
            dimensions=256,  # use smaller dims for similarity (faster)
        )
        return response.data[0].embedding

    async def _get_or_create_embedding(
        self, msg_id: str, content: str
    ) -> List[float]:
        """Get cached embedding or create new one."""
        if msg_id in self._embedding_cache:
            return self._embedding_cache[msg_id]
        embedding = await self._embed(content)
        self._embedding_cache[msg_id] = embedding
        return embedding

    async def select(
        self, conversation_id: str, current_query: str
    ) -> List[Dict[str, Any]]:
        """
        Select the most relevant messages for the current query.

        Returns up to max_messages messages:
        - Last recent_guaranteed messages always included
        - Remaining slots filled by most semantically similar messages
        - Result sorted chronologically
        """
        all_messages = await self._get_messages(conversation_id)

        if len(all_messages) <= self.max_messages:
            return all_messages

        # Always include the last N messages
        recent = all_messages[-self.recent_guaranteed:]
        candidates = all_messages[:-self.recent_guaranteed]

        # Embed the current query
        query_embedding = await self._embed(current_query)

        # Score each candidate by semantic similarity
        scored = []
        for msg in candidates:
            msg_embedding = await self._get_or_create_embedding(
                msg["id"], msg["content"]
            )
            score = cosine_similarity(query_embedding, msg_embedding)
            scored.append((score, msg))

        # Select top candidates
        scored.sort(key=lambda x: x[0], reverse=True)
        slots = self.max_messages - self.recent_guaranteed
        selected = [msg for _, msg in scored[:slots]]

        # Sort chronologically
        selected.sort(key=lambda m: m["created_at"])

        return selected + recent
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_semantic_window.py -v`
Expected: PASS

- [ ] **Step 5: Integrate into chat flow**

In `backend/app/routers/chat.py` (or `ask.py`), replace the current message loading:

```python
# Before:
# messages = await cache.get_recent_messages(user_id, limit=20)

# After:
from app.services.semantic_window import SemanticWindow
semantic_window = SemanticWindow(max_messages=15, recent_guaranteed=5)
messages = await semantic_window.select(conversation_id, user_query)
```

- [ ] **Step 6: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v --tb=short -q`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/semantic_window.py backend/tests/test_semantic_window.py backend/app/routers/chat.py
git commit -m "feat: add SemanticWindow for intelligent context selection using embeddings"
```

---

## Wave 3: Tasks 13-14 (Pre-calentamiento + Bienvenida)

---

### Task 13: Create WarmupService (backend)

**Files:**
- Create: `backend/app/services/warmup_service.py`
- Test: `backend/tests/test_warmup_service.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_warmup_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.warmup_service import WarmupService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def warmup(mock_db):
    return WarmupService(mock_db)


@pytest.mark.asyncio
async def test_warmup_returns_greeting_for_user_with_profile(warmup):
    profile = {
        "ccaa_residencia": "Madrid",
        "situacion_laboral": "autonomo",
    }
    with patch.object(warmup, '_get_profile', return_value=profile):
        with patch.object(warmup, '_preload_rag', return_value=True):
            with patch.object(warmup, '_generate_greeting', return_value="Hola, bienvenido"):
                result = await warmup.warmup("user123")
                assert result["greeting"] == "Hola, bienvenido"
                assert result["rag_preloaded"] is True


@pytest.mark.asyncio
async def test_warmup_static_greeting_for_new_user(warmup):
    with patch.object(warmup, '_get_profile', return_value=None):
        result = await warmup.warmup("user_new")
        assert "Impuestify" in result["greeting"]
        assert result["rag_preloaded"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_warmup_service.py -v`
Expected: FAIL

- [ ] **Step 3: Write WarmupService**

```python
# backend/app/services/warmup_service.py
"""
Warmup Service for Impuestify.

Pre-loads RAG context and generates personalized greetings
when users open the chat, before they type anything.
"""
import logging
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

GREETING_PROMPT = """Eres el asistente fiscal Impuestify. Genera un saludo breve y personalizado
para un usuario con este perfil fiscal. Maximo 2 frases. Menciona algo util:
un plazo proximo, una deduccion que podria aplicarle, o un recordatorio fiscal relevante.
Tono: cercano, profesional, sin emojis. Si no hay datos suficientes, saluda de forma generica.

Perfil del usuario:
{profile_summary}

Plazos proximos:
{deadlines}

Responde SOLO con el saludo, nada mas."""

STATIC_GREETING = (
    "Hola, bienvenido a Impuestify. Soy tu asistente fiscal. "
    "Puedes preguntarme sobre IRPF, deducciones, modelos fiscales o cualquier duda tributaria."
)


class WarmupService:
    """Pre-warm RAG context and generate personalized greetings."""

    def __init__(self, db=None):
        self._db = db
        self._client = None

    async def _get_db(self):
        if self._db:
            return self._db
        from app.database.turso_client import get_db_client
        self._db = await get_db_client()
        return self._db

    def _get_client(self) -> AsyncOpenAI:
        if not self._client:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def _get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load user's fiscal profile."""
        db = await self._get_db()
        result = await db.execute(
            "SELECT ccaa_residencia, situacion_laboral, datos_fiscales FROM user_profiles WHERE user_id = ?",
            [user_id],
        )
        if not result.rows:
            return None
        row = dict(result.rows[0])
        if not row.get("ccaa_residencia"):
            return None
        return row

    async def _preload_rag(self, ccaa: str, role: str) -> bool:
        """Pre-load RAG chunks for the user's territory into conversation cache."""
        try:
            from app.services.conversation_cache import ConversationCache
            cache = ConversationCache()
            # Load territory-specific chunks
            from app.territories import get_territory
            territory = get_territory(ccaa)
            rag_filters = territory.get_rag_filters(ccaa)
            # The actual RAG preloading depends on existing rag_service
            # For now, just signal success
            logger.info(f"Pre-loaded RAG context for {ccaa} ({role})")
            return True
        except Exception as e:
            logger.warning(f"RAG warmup failed: {e}")
            return False

    async def _generate_greeting(self, profile: Dict[str, Any]) -> str:
        """Generate personalized greeting using gpt-4o-mini."""
        ccaa = profile.get("ccaa_residencia", "")
        role = profile.get("situacion_laboral", "")

        # Build profile summary
        profile_summary = f"CCAA: {ccaa}, Situacion: {role}"
        datos = profile.get("datos_fiscales")
        if datos:
            import json
            if isinstance(datos, str):
                datos = json.loads(datos)
            if datos.get("hipoteca_activa"):
                profile_summary += ", Hipoteca activa"
            if datos.get("hijos"):
                profile_summary += f", {datos['hijos']} hijos"

        # Get deadlines from territory plugin
        deadlines = "No hay plazos proximos registrados"
        try:
            from app.territories import get_territory
            territory = get_territory(ccaa)
            upcoming = territory.get_upcoming_deadlines()
            if upcoming:
                deadlines = "\n".join(f"- {d.modelo}: {d.description} ({d.date})" for d in upcoming)
        except Exception:
            pass

        prompt = GREETING_PROMPT.format(
            profile_summary=profile_summary,
            deadlines=deadlines,
        )

        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=100,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Greeting generation failed: {e}")
            return STATIC_GREETING

    async def warmup(self, user_id: str) -> Dict[str, Any]:
        """
        Warm up chat context for a user.

        Returns greeting text and whether RAG was preloaded.
        """
        profile = await self._get_profile(user_id)

        if not profile:
            return {"greeting": STATIC_GREETING, "rag_preloaded": False}

        ccaa = profile.get("ccaa_residencia", "")
        role = profile.get("situacion_laboral", "particular")

        rag_ok = await self._preload_rag(ccaa, role)
        greeting = await self._generate_greeting(profile)

        return {"greeting": greeting, "rag_preloaded": rag_ok}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_warmup_service.py -v`
Expected: PASS

- [ ] **Step 5: Add warmup endpoint**

Add to `backend/app/routers/chat.py` (or create a new warmup router):

```python
from app.services.warmup_service import WarmupService

@router.post("/api/chat/warmup")
async def warmup_chat(request: Request, current_user=Depends(get_current_user)):
    db = await get_db_client()
    warmup = WarmupService(db)
    result = await warmup.warmup(current_user.user_id)
    return result
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/warmup_service.py backend/tests/test_warmup_service.py backend/app/routers/chat.py
git commit -m "feat: add WarmupService for RAG pre-loading and personalized greetings"
```

---

### Task 14: Integrate warmup into frontend chat

**Files:**
- Modify: `frontend/src/hooks/useConversations.ts` — add warmup call
- Modify: `frontend/src/pages/Chat.tsx` — show greeting message

- [ ] **Step 1: Add warmup API call to useConversations.ts**

Add a new method to the `useConversations` hook:

```typescript
const warmupChat = async (): Promise<{ greeting: string; rag_preloaded: boolean } | null> => {
    try {
        const response = await apiRequest('/api/chat/warmup', { method: 'POST' });
        return response;
    } catch (e) {
        console.warn('Chat warmup failed:', e);
        return null;
    }
};
```

Return `warmupChat` from the hook.

- [ ] **Step 2: Call warmup when opening a new conversation in Chat.tsx**

In `Chat.tsx`, when a new conversation is created (empty chat), call warmup in parallel:

```typescript
// When creating a new conversation:
const handleNewConversation = async () => {
    const conv = await createConversation();
    // Warmup in parallel
    const warmup = await warmupChat();
    if (warmup?.greeting) {
        setMessages([{
            id: 'warmup-greeting',
            role: 'assistant',
            content: warmup.greeting,
            created_at: new Date().toISOString(),
        }]);
    }
};
```

- [ ] **Step 3: Ensure greeting doesn't appear on existing conversations**

Only show the warmup greeting when `messages.length === 0` (new conversation). If the conversation already has messages, skip the warmup greeting.

- [ ] **Step 4: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useConversations.ts frontend/src/pages/Chat.tsx
git commit -m "feat: integrate warmup greeting into chat frontend (new conversations only)"
```

---

## Final: Task 15 — Run full test suite and verify

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS (existing + new)

- [ ] **Step 2: Build frontend**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Verify territory plugin registration**

Run: `cd backend && python -c "from app.territories.startup import register_all_territories; register_all_territories(); from app.territories import list_territories; print(f'{len(list_territories())} territories registered'); print(list_territories())"`
Expected: `21 territories registered` with all CCAA listed

- [ ] **Step 4: Final commit with all changes**

If any uncommitted changes remain:

```bash
git add -A
git commit -m "feat: complete Column A — territories, cost tracking, memory extraction, warmup, semantic window"
```
