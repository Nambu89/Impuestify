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
