"""
Calculators package — SOLID income calculators for IRPF simulation.

Each calculator handles a single type of income (Single Responsibility).
New income types can be added without modifying existing ones (Open/Closed).
All calculators follow the same interface (Liskov/Interface Segregation).
Calculators depend on TaxParameterRepository, not SQL (Dependency Inversion).
"""
from typing import Protocol, Dict, Any


class IncomeCalculator(Protocol):
    """Protocol for all income calculators."""

    async def calculate(self, **kwargs) -> Dict[str, Any]:
        """Calculate the net income for this income type."""
        ...


from app.utils.calculators.modelo_130 import Modelo130Calculator  # noqa: E402

__all__ = ["IncomeCalculator", "Modelo130Calculator"]
