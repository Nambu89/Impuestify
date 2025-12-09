"""
Autonomous Quota Calculator Tool for TaxIA

Provides function calling capability for the LLM to calculate
exact autonomous worker quotas based on income and region.
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Tool definition for OpenAI function calling
AUTONOMOUS_QUOTA_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_autonomous_quota",
        "description": "Calcula la cuota mensual de autónomos en España según ingresos netos mensuales y región. Devuelve la cuota exacta, el tramo correspondiente y la bonificación aplicable (si hay).",
        "parameters": {
            "type": "object",
            "properties": {
                "ingresos_netos_mensuales": {
                    "type": "number",
                    "description": "Ingresos netos mensuales del autónomo en euros (después de gastos y deducción del 7%)"
                },
                "region": {
                    "type": "string",
                    "enum": ["general", "ceuta", "melilla"],
                    "description": "Región del autónomo. 'general' para toda España excepto Ceuta/Melilla. Ceuta y Melilla tienen bonificación del 50%."
                },
                "year": {
                    "type": "integer",
                    "description": "Año de cotización (por defecto 2025)"
                }
            },
            "required": ["ingresos_netos_mensuales"]
        }
    }
}


async def calculate_autonomous_quota_tool(
    ingresos_netos_mensuales: float,
    region: str = "general",
    year: int = 2025
) -> Dict[str, Any]:
    """
    Calculate the autonomous worker quota based on net monthly income.
    
    Args:
        ingresos_netos_mensuales: Net monthly income in euros
        region: Region (general, ceuta, melilla)
        year: Year for calculation (default 2025)
        
    Returns:
        Dict with quota information and formatted response
    """
    try:
        from app.database.turso_client import TursoClient
        import os
        
        # Connect to database
        db = TursoClient(
            url=os.environ.get("TURSO_DATABASE_URL"),
            auth_token=os.environ.get("TURSO_AUTH_TOKEN")
        )
        await db.connect()
        
        # Query the autonomous_quotas table
        sql = """
        SELECT 
            tramo_number,
            rendimientos_netos_min,
            rendimientos_netos_max,
            base_cotizacion_min,
            base_cotizacion_max,
            cuota_min,
            cuota_max,
            bonificacion_percent,
            cuota_min_bonificada,
            cuota_max_bonificada
        FROM autonomous_quotas
        WHERE year = ?
        AND region = ?
        AND rendimientos_netos_min <= ?
        AND (rendimientos_netos_max >= ? OR rendimientos_netos_max IS NULL)
        LIMIT 1
        """
        
        result = await db.execute(sql, [year, region, ingresos_netos_mensuales, ingresos_netos_mensuales])
        
        await db.disconnect()
        
        if not result.rows:
            return {
                "success": False,
                "error": f"No se encontró un tramo de cotización para {ingresos_netos_mensuales}€ en {year}",
                "formatted_response": f"❌ No encontré información de cotización para ingresos de {ingresos_netos_mensuales}€ en {year}. Verifica que el importe sea correcto."
            }
        
        row = result.rows[0]
        
        # Extract data
        tramo = row['tramo_number']
        cuota_min = row['cuota_min']
        cuota_max = row['cuota_max']
        bonificacion = row['bonificacion_percent'] or 0
        cuota_min_bonificada = row['cuota_min_bonificada']
        cuota_max_bonificada = row['cuota_max_bonificada']
        base_min = row['base_cotizacion_min']
        base_max = row['base_cotizacion_max']
        
        # Format response
        region_name = {
            "general": "España (territorio común)",
            "ceuta": "Ceuta",
            "melilla": "Melilla"
        }.get(region, region)
        
        formatted_response = f"""✅ **Cuota de Autónomos {year} - {region_name}**

📊 **Tus ingresos**: {ingresos_netos_mensuales}€/mes
📍 **Tramo**: {tramo} de 15

💰 **Cuota mensual**:
- Mínima: {cuota_min:.2f}€
- Máxima: {cuota_max:.2f}€
"""
        
        if bonificacion > 0:
            formatted_response += f"""
🎁 **Bonificación {region_name}**: {bonificacion}% de descuento
- Cuota mínima bonificada: {cuota_min_bonificada:.2f}€
- Cuota máxima bonificada: {cuota_max_bonificada:.2f}€
"""
        
        formatted_response += f"""
📋 **Base de cotización**:
- Mínima: {base_min:.2f}€
- Máxima: {base_max:.2f}€

💡 **¿Qué significa esto?**
- Si cotizas por la **base mínima** ({base_min:.2f}€), pagarás **{cuota_min_bonificada or cuota_min:.2f}€/mes**.
- Puedes elegir cotizar por una base superior (hasta {base_max:.2f}€) para mejorar tus prestaciones futuras.
- Puedes cambiar tu base de cotización hasta **6 veces al año**.

⚠️ **Recuerda**: Esta cuota se calcula sobre tus **rendimientos netos** (ingresos - gastos - 7% de deducción).
"""
        
        return {
            "success": True,
            "tramo": tramo,
            "cuota_minima": cuota_min_bonificada or cuota_min,
            "cuota_maxima": cuota_max_bonificada or cuota_max,
            "bonificacion_percent": bonificacion,
            "region": region,
            "year": year,
            "formatted_response": formatted_response
        }
        
    except Exception as e:
        logger.error(f"Error calculating autonomous quota: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"❌ Error al calcular la cuota: {str(e)}"
        }
