"""
Tax Parameter Repository — Data-driven access to fiscal parameters.

Reads all tax rates, thresholds, and amounts from the tax_parameters table.
Caches results in memory to avoid repeated DB queries within the same request.

Follows Dependency Inversion: calculators depend on this abstraction,
not on SQL queries directly.
"""
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TaxParameterRepository:
    """
    Read-only repository for tax parameters stored in the database.

    Parameters are organized by:
    - category: 'mpyf', 'trabajo', 'inmuebles', 'iva', etc.
    - param_key: specific parameter name within the category
    - year: fiscal year
    - jurisdiction: 'Estatal' or CCAA name (e.g., 'Comunitat Valenciana')
    """

    def __init__(self, db):
        self._db = db
        self._cache: Dict[str, Dict[str, float]] = {}

    async def get_params(
        self,
        category: str,
        year: int,
        jurisdiction: str = "Estatal",
    ) -> Dict[str, float]:
        """
        Get all parameters for a category/year/jurisdiction.

        Falls back to year-1 if no params exist for the requested year
        (tax params rarely change between consecutive years).

        Returns:
            Dict mapping param_key to value, e.g.:
            {'contribuyente': 5550, 'contribuyente_65': 6700, ...}
        """
        cache_key = f"{category}:{year}:{jurisdiction}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = await self._db.execute(
            "SELECT param_key, value FROM tax_parameters "
            "WHERE category = ? AND year = ? AND jurisdiction = ?",
            [category, year, jurisdiction],
        )
        params = {row["param_key"]: row["value"] for row in result.rows}

        # Fallback to previous year if no params found for requested year
        if not params and year > 2023:
            logger.info(
                "No tax_parameters for %s/%d/%s — falling back to %d",
                category, year, jurisdiction, year - 1,
            )
            result = await self._db.execute(
                "SELECT param_key, value FROM tax_parameters "
                "WHERE category = ? AND year = ? AND jurisdiction = ?",
                [category, year - 1, jurisdiction],
            )
            params = {row["param_key"]: row["value"] for row in result.rows}

        self._cache[cache_key] = params
        return params

    async def get_param(
        self,
        category: str,
        param_key: str,
        year: int,
        jurisdiction: str = "Estatal",
        default: Optional[float] = None,
    ) -> Optional[float]:
        """Get a single parameter value."""
        params = await self.get_params(category, year, jurisdiction)
        return params.get(param_key, default)

    async def get_with_fallback(
        self,
        category: str,
        year: int,
        jurisdiction: str,
    ) -> Dict[str, float]:
        """
        Get params for a specific jurisdiction, falling back to Estatal.

        This is the standard pattern for MPYF: if a CCAA has overrides,
        use them; otherwise, use the state-level defaults.
        """
        if jurisdiction != "Estatal":
            params = await self.get_params(category, year, jurisdiction)
            if params:
                return params
        return await self.get_params(category, year, "Estatal")

    def clear_cache(self):
        """Clear the in-memory cache (e.g., after a data update)."""
        self._cache.clear()
