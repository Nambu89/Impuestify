"""Test IRPF Calculator"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Setup
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load env
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.utils.irpf_calculator import IRPFCalculator


async def test():
    """Test IRPF calculator with Zaragoza example."""
    calc = IRPFCalculator()
    
    try:
        print("\n🧪 TEST: Zaragoza, 35,000€ brutos\n")
        
        result = await calc.calculate_irpf(
            base_liquidable=35000,
            jurisdiction='Aragón',
            year=2024
        )
        
        print(calc.format_result(result))
        
        # Also test with Madrid for comparison
        print("\n\n🧪 COMPARACIÓN: Madrid, 35,000€ brutos\n")
        
        result_madrid = await calc.calculate_irpf(
            base_liquidable=35000,
            jurisdiction='Comunidad de Madrid',
            year=2024
        )
        
        print(calc.format_result(result_madrid))
        
    finally:
        await calc.disconnect()


if __name__ == "__main__":
    asyncio.run(test())
