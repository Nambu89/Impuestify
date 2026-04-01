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
