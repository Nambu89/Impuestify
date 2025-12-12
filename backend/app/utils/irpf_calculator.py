"""
IRPF Calculator using structured tax tables.

Calculates exact IRPF (Income Tax) using scales from SQL database.
"""
import asyncio
from typing import Dict, List, Optional
from app.database.turso_client import TursoClient


class IRPFCalculator:
    """
    Calculate IRPF using structured tax tables.
    
    Handles:
    - State (estatal) quota calculation
    - Autonomous community (CCAA) quota calculation
    - Combined total IRPF
    - Breakdown by tax brackets
    """
    
    def __init__(self):
        self.db = None
    
    async def connect(self):
        """Connect to database."""
        if self.db is None:
            self.db = TursoClient()
            await self.db.connect()
    
    async def disconnect(self):
        """Disconnect from database."""
        if self.db:
            await self.db.disconnect()
            self.db = None
    
    async def calculate_irpf(
        self,
        base_liquidable: float,
        jurisdiction: str,
        year: int = 2024,
        include_state: bool = True
    ) -> Dict:
        """
        Calculate IRPF for given base liquidable and jurisdiction.
        
        Args:
            base_liquidable: Taxable income (base liquidable general)
            jurisdiction: CCAA name (e.g., 'Aragón', 'Madrid')
            year: Tax year
            include_state: Whether to include state quota (default True)
        
        Returns:
            {
                'base_liquidable': float,
                'cuota_estatal': float,
                'cuota_autonomica': float,
                'cuota_total': float,
                'tipo_medio': float,  # Effective tax rate %
                'breakdown_estatal': List[Dict],
                'breakdown_autonomica': List[Dict]
            }
        """
        await self.connect()
        
        # Calculate state quota
        cuota_estatal = 0
        breakdown_estatal = []
        
        if include_state:
            try:
                state_scale = await self._get_scale('Estatal', year)
                cuota_estatal, breakdown_estatal = self._apply_scale(
                    base_liquidable, 
                    state_scale
                )
            except ValueError:
                # Estatal scale not found, skip it for now
                print("⚠️  Advertencia: Escala estatal no encontrada, solo calculando cuota autonómica")
        
        # Calculate CCAA quota
        ccaa_scale = await self._get_scale(jurisdiction, year)
        cuota_autonomica, breakdown_autonomica = self._apply_scale(
            base_liquidable,
            ccaa_scale
        )
        
        # Total
        cuota_total = cuota_estatal + cuota_autonomica
        tipo_medio = (cuota_total / base_liquidable * 100) if base_liquidable > 0 else 0
        
        return {
            'base_liquidable': base_liquidable,
            'jurisdiction': jurisdiction,
            'year': year,
            'cuota_estatal': round(cuota_estatal, 2),
            'cuota_autonomica': round(cuota_autonomica, 2),
            'cuota_total': round(cuota_total, 2),
            'tipo_medio': round(tipo_medio, 2),
            'breakdown_estatal': breakdown_estatal,
            'breakdown_autonomica': breakdown_autonomica
        }
    
    def calculate_with_custom_scale(
        self,
        base_liquidable: float,
        tramos_autonomicos: List[Dict],
        tramos_estatales: List[Dict] = None,
        year: int = 2024,
        jurisdiction: str = "Custom"
    ) -> Dict:
        """
        Calculate IRPF using custom scales (e.g., from web extraction).
        
        Args:
            base_liquidable: Taxable income
            tramos_autonomicos: Autonomous community scale (from web)
            tramos_estatales: Optional state scale (from web or DB)
            year: Tax year
            jurisdiction: CCAA name
            
        Returns:
            Same format as calculate_irpf()
        """
        # Calculate state quota
        cuota_estatal = 0
        breakdown_estatal = []
        
        if tramos_estatales:
            cuota_estatal, breakdown_estatal = self._apply_scale(
                base_liquidable,
                tramos_estatales
            )
        
        # Calculate CCAA quota with custom scale
        cuota_autonomica, breakdown_autonomica = self._apply_scale(
            base_liquidable,
            tramos_autonomicos
        )
        
        # Total
        cuota_total = cuota_estatal + cuota_autonomica
        tipo_medio = (cuota_total / base_liquidable * 100) if base_liquidable > 0 else 0
        
        return {
            'base_liquidable': base_liquidable,
            'jurisdiction': jurisdiction,
            'year': year,
            'cuota_estatal': round(cuota_estatal, 2),
            'cuota_autonomica': round(cuota_autonomica, 2),
            'cuota_total': round(cuota_total, 2),
            'tipo_medio': round(tipo_medio, 2),
            'breakdown_estatal': breakdown_estatal,
            'breakdown_autonomica': breakdown_autonomica,
            'source': 'web'  # Indicator that data came from web
        }
    
    async def _get_scale(self, jurisdiction: str, year: int) -> List[Dict]:
        """
        Get tax scale from database.
        
        Returns:
            List of scale rows ordered by tramo_num
        """
        result = await self.db.execute("""
            SELECT tramo_num, base_hasta, cuota_integra, resto_base, tipo_aplicable
            FROM irpf_scales
            WHERE jurisdiction = ? AND year = ? AND scale_type = 'general'
            ORDER BY tramo_num
        """, [jurisdiction, year])
        
        if not result.rows:
            raise ValueError(f"No scale found for {jurisdiction} {year}")
        
        return [dict(row) for row in result.rows]
    
    def _apply_scale(
        self,
        base_liquidable: float,
        scale: List[Dict]
    ) -> tuple[float, List[Dict]]:
        """
        Apply progressive tax scale to base liquidable.
        
        Spanish IRPF is progressive:
        - Each bracket has: base_hasta, cuota_integra, resto_base, tipo_aplicable
        - Formula for bracket i:
          - If base <= base_hasta: cuota = cuota_integra_prev + (base - base_hasta_prev) * tipo / 100
          - Else: Apply next bracket
        
        Returns:
            (total_cuota, breakdown_by_bracket)
        """
        cuota_total = 0
        breakdown = []
        
        for i, tramo in enumerate(scale):
            base_hasta = tramo['base_hasta']
            cuota_integra = tramo['cuota_integra']
            resto_base = tramo['resto_base']
            tipo_aplicable = tramo['tipo_aplicable']
            
            # Previous bracket's top
            base_desde = 0 if i == 0 else scale[i-1]['base_hasta']
            
            # Check if income falls in this bracket
            if base_liquidable <= base_hasta or base_hasta >= 999999:  # Last bracket
                # Income is in this bracket
                base_en_tramo = base_liquidable - base_desde
                cuota_en_tramo = base_en_tramo * (tipo_aplicable / 100)
                cuota_total = cuota_integra + cuota_en_tramo
                
                breakdown.append({
                    'tramo': i + 1,
                    'base_desde': round(base_desde, 2),
                    'base_hasta': round(base_hasta, 2) if base_hasta < 999999 else 'En adelante',
                    'base_gravada': round(base_en_tramo, 2),
                    'tipo': tipo_aplicable,
                    'cuota': round(cuota_en_tramo, 2)
                })
                
                break
            else:
                # Income exceeds this bracket, apply full bracket
                base_en_tramo = resto_base
                cuota_en_tramo = base_en_tramo * (tipo_aplicable / 100)
                
                breakdown.append({
                    'tramo': i + 1,
                    'base_desde': round(base_desde, 2),
                    'base_hasta': round(base_hasta, 2),
                    'base_gravada': round(base_en_tramo, 2),
                    'tipo': tipo_aplicable,
                    'cuota': round(cuota_en_tramo, 2)
                })
        
        return cuota_total, breakdown
    
    def format_result(self, result: Dict) -> str:
        """
        Format calculation result as user-friendly text.
        
        Returns:
            Human-readable explanation of IRPF calculation
        """
        lines = []
        lines.append(f"📊 Cálculo IRPF {result['year']} - {result['jurisdiction']}")
        lines.append("=" * 60)
        lines.append(f"Base liquidable: {result['base_liquidable']:,.2f} €")
        lines.append("")
        
        lines.append("💶 Cuota Estatal:")
        lines.append(f"   {result['cuota_estatal']:,.2f} €")
        if result['breakdown_estatal']:
            for tramo in result['breakdown_estatal'][-3:]:  # Show last 3 brackets
                lines.append(f"   • Tramo {tramo['tramo']}: {tramo['base_gravada']:,.2f} € × {tramo['tipo']}% = {tramo['cuota']:,.2f} €")
        lines.append("")
        
        lines.append(f"🏛️  Cuota Autonómica ({result['jurisdiction']}):")
        lines.append(f"   {result['cuota_autonomica']:,.2f} €")
        if result['breakdown_autonomica']:
            for tramo in result['breakdown_autonomica'][-3:]:  # Show last 3 brackets
                lines.append(f"   • Tramo {tramo['tramo']}: {tramo['base_gravada']:,.2f} € × {tramo['tipo']}% = {tramo['cuota']:,.2f} €")
        lines.append("")
        
        lines.append("✅ TOTAL:")
        lines.append(f"   Cuota íntegra: {result['cuota_total']:,.2f} €")
        lines.append(f"   Tipo medio efectivo: {result['tipo_medio']}%")
        lines.append("=" * 60)
        
        return "\n".join(lines)


async def test_calculator():
    """Test IRPF calculator with example."""
    calc = IRPFCalculator()
    
    try:
        # Test case: Zaragoza (Aragón), 35,000€
        print("\n🧪 TEST: Zaragoza, 35,000€ brutos\n")
        
        result = await calc.calculate_irpf(
            base_liquidable=35000,
            jurisdiction='Aragón',
            year=2024
        )
        
        print(calc.format_result(result))
        
    finally:
        await calc.disconnect()


if __name__ == "__main__":
    asyncio.run(test_calculator())
