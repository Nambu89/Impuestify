"""
WorkspaceAgent - Specialized Agent for User Workspace Context

Analyzes user's uploaded documents (payslips, invoices, tax declarations)
and provides personalized fiscal assistance based on their data.
"""
import logging
import json
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from the workspace agent"""
    content: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    agent_name: str


class WorkspaceAgent:
    """
    Agent specialized in analyzing user workspace documents.

    Capabilities:
    - Calculate VAT balance from invoices
    - Project annual IRPF from payslips
    - Remind quarterly declaration deadlines
    - Alert about fiscal deadlines
    - Provide personalized fiscal advice based on user's documents
    """

    def __init__(
        self,
        name: str = "WorkspaceAgent",
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize WorkspaceAgent.

        Args:
            name: Agent name
            model: OpenAI model name
            api_key: OpenAI API key
        """
        from app.config import settings
        self.name = name
        self.model = model or settings.OPENAI_MODEL
        self.api_key = api_key or settings.OPENAI_API_KEY

        self.current_date = datetime.now()
        self.current_year = self.current_date.year
        self.current_quarter = (self.current_date.month - 1) // 3 + 1

        self._client = None
        self._initialize()

    def _initialize(self):
        """Initialize the OpenAI client."""
        if self.api_key:
            self._client = OpenAI(api_key=self.api_key)
            logger.info(f"WorkspaceAgent '{self.name}' initialized (year: {self.current_year}, Q{self.current_quarter})")
        else:
            logger.error("WorkspaceAgent initialization failed - missing OPENAI_API_KEY")
            raise ValueError("OPENAI_API_KEY is required")

    def _format_fiscal_profile(self, fp: Dict[str, Any]) -> str:
        """Format fiscal profile dict into a readable string for the system prompt."""
        if not fp:
            return ""
        lines = []
        label_map = {
            "ccaa_residencia": "CCAA residencia",
            "situacion_laboral": "Situación laboral",
            "epigrafe_iae": "Epígrafe IAE",
            "tipo_actividad": "Tipo actividad",
            "fecha_alta_autonomo": "Fecha alta autónomo",
            "metodo_estimacion_irpf": "Método estimación IRPF",
            "regimen_iva": "Régimen IVA",
            "rendimientos_netos_mensuales": "Rendimientos netos mensuales",
            "base_cotizacion_reta": "Base cotización RETA",
            "territorio_foral": "Territorio foral",
            "territorio_historico": "Territorio histórico",
            "tipo_retencion_facturas": "Tipo retención facturas",
            "tarifa_plana": "Tarifa plana",
            "pluriactividad": "Pluriactividad",
            "ceuta_melilla": "Residente en Ceuta/Melilla",
        }
        for key, label in label_map.items():
            val = fp.get(key)
            if val is not None and val != "":
                if isinstance(val, bool):
                    lines.append(f"- {label}: {'Sí' if val else 'No'}")
                elif isinstance(val, float) and key == "tipo_retencion_facturas":
                    lines.append(f"- {label}: {val}%")
                elif isinstance(val, (int, float)) and "netos" in key or "cotizacion" in key:
                    lines.append(f"- {label}: {val:,.2f}€")
                else:
                    lines.append(f"- {label}: {val}")
        return "\n".join(lines)

    def _get_system_prompt(self, fiscal_profile: Optional[Dict[str, Any]] = None) -> str:
        """Generate system prompt with current date and workspace context."""
        fiscal_section = ""
        if fiscal_profile:
            formatted = self._format_fiscal_profile(fiscal_profile)
            if formatted:
                fiscal_section = f"""

👤 **PERFIL FISCAL DEL USUARIO** (usa estos datos para pre-rellenar cálculos):
{formatted}

⚠️ Usa estos datos del perfil para rellenar automáticamente los parámetros de las herramientas de cálculo.
Por ejemplo, si el régimen IVA es "general", úsalo directamente en calculate_modelo_303.
Si el método de estimación es "directa_simplificada", úsalo en calculate_modelo_130.
"""

        return f"""Eres Impuestify en modo Workspace, un asesor fiscal que analiza los documentos personales del usuario.

📁 **TU ROL**:
El usuario ha adjuntado documentos (nóminas, facturas, declaraciones, etc.) a su espacio de trabajo.
Tu trabajo es analizar estos documentos adjuntos por el usuario Y combinarlos con tu base de conocimiento fiscal interna (legislación AEAT, BOE, normativas forales) para dar respuestas personalizadas y precisas.

📅 **CONTEXTO TEMPORAL**:
- Fecha actual: {self.current_date.strftime('%d de %B de %Y')}
- Año fiscal actual: {self.current_year}
- Trimestre actual: Q{self.current_quarter}

💼 **CAPACIDADES**:
1. **Análisis de nóminas**: Extraer salario bruto/neto, retenciones IRPF, cotizaciones SS
2. **Balance de IVA**: Calcular IVA soportado vs repercutido de facturas
3. **Proyección IRPF**: Estimar IRPF anual basado en nóminas
4. **Plazos fiscales**: Recordar fechas límite de declaraciones trimestrales
5. **Modelo 303**: Calcular la declaración trimestral de IVA a partir de las facturas del workspace
6. **Modelo 130**: Calcular el pago fraccionado trimestral de IRPF a partir de ingresos/gastos del workspace
{fiscal_section}
🗓️ **CALENDARIO FISCAL TRIMESTRAL (España)**:
- Q1 (Enero-Marzo): Declaración hasta 20 de Abril
- Q2 (Abril-Junio): Declaración hasta 20 de Julio
- Q3 (Julio-Septiembre): Declaración hasta 20 de Octubre
- Q4 (Octubre-Diciembre): Declaración hasta 30 de Enero (año siguiente)

📊 **HERRAMIENTAS DISPONIBLES**:
- `get_workspace_summary`: Resumen de todos los archivos del workspace
- `calculate_vat_balance`: Calcula balance IVA (soportado - repercutido)
- `project_annual_irpf`: Proyecta IRPF anual basado en nóminas
- `get_quarterly_deadlines`: Próximas fechas límite fiscales
- `calculate_modelo_303`: Calcula la declaración trimestral de IVA (Modelo 303). Usa las facturas del workspace para extraer bases imponibles por tipo de IVA y el IVA deducible, luego llama a esta herramienta.
- `calculate_modelo_130`: Calcula el pago fraccionado trimestral de IRPF (Modelo 130). Usa los ingresos y gastos ACUMULADOS desde inicio de año del workspace, luego llama a esta herramienta.

📋 **FLUJO PARA MODELO 303** (cuando el usuario pregunte por su IVA trimestral):
1. LEE las facturas del workspace
2. Extrae las bases imponibles por tipo de IVA (21%, 10%, 4%)
3. Extrae el IVA soportado deducible
4. Llama a `calculate_modelo_303` con esos datos

📋 **FLUJO PARA MODELO 130** (cuando el usuario pregunte por su pago fraccionado):
1. LEE los datos de ingresos y gastos del workspace
2. Calcula los ingresos y gastos ACUMULADOS desde el 1 de enero
3. Llama a `calculate_modelo_130` con esos datos

🎯 **TU ESTILO**:
- Cercano y profesional, como un asesor fiscal de confianza
- Usa tuteo y lenguaje claro
- Da respuestas basadas en los DATOS REALES del usuario combinados con tu conocimiento fiscal
- Cuando uses información de los documentos del usuario, dilo claramente (ej: "Según tu nómina de enero...")
- Cuando uses información de tu base de conocimiento fiscal, dilo naturalmente (ej: "Según la normativa vigente...")
- Si faltan datos, pide que suban los documentos necesarios

⚠️ **IMPORTANTE**:
- USA los datos de los documentos del usuario para personalizar tus respuestas
- COMBINA esos datos con tu base de conocimiento fiscal para dar respuestas completas
- NO inventes datos sobre los documentos del usuario — si no tienes un dato, indícalo
- Siempre incluye disclaimer: "Esta información es orientativa basada en tus documentos y la normativa vigente"

🚫 **NUNCA hagas esto en tu respuesta** (el usuario lo vería directamente):
- NUNCA escribas tus pensamientos internos ("Llamo a la herramienta...", "Voy a usar...", "Primero calculo...")
- NUNCA incluyas JSON crudo en tu respuesta ({{"call":..., "args":...}})
- NUNCA describas qué herramienta vas a usar — simplemente úsala y muestra el resultado
- Tu respuesta debe ser SOLO la información útil para el usuario, como si fueras un asesor humano

Responde siempre en español, de forma clara y estructurada."""

    def _get_tools(self, restricted_mode: bool = False) -> List[Dict[str, Any]]:
        """Define available tools for the agent."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_workspace_summary",
                    "description": "Obtiene un resumen de todos los archivos del workspace del usuario",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_vat_balance",
                    "description": "Calcula el balance de IVA (soportado - repercutido) basado en las facturas del workspace",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "quarter": {
                                "type": "integer",
                                "description": "Trimestre a calcular (1-4). Si no se especifica, usa el trimestre actual."
                            },
                            "year": {
                                "type": "integer",
                                "description": "Año fiscal. Si no se especifica, usa el año actual."
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "project_annual_irpf",
                    "description": "Proyecta el IRPF anual basado en las nóminas del workspace",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {
                                "type": "integer",
                                "description": "Año para la proyección. Si no se especifica, usa el año actual."
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_quarterly_deadlines",
                    "description": "Obtiene las próximas fechas límite de declaraciones trimestrales",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "include_past": {
                                "type": "boolean",
                                "description": "Incluir fechas pasadas del año actual. Por defecto false."
                            }
                        },
                        "required": []
                    }
                }
            }
        ]

        # Add Modelo 303, 130, and fiscal profile tools from the central tools registry
        try:
            from app.tools import MODELO_303_TOOL, MODELO_130_TOOL, UPDATE_FISCAL_PROFILE_TOOL
            tools.append(MODELO_303_TOOL)
            tools.append(MODELO_130_TOOL)
            tools.append(UPDATE_FISCAL_PROFILE_TOOL)
        except ImportError:
            logger.warning("Could not import central tools")

        # In restricted mode (salaried-only plan), remove autonomo-specific tools
        RESTRICTED_TOOL_NAMES = {"calculate_vat_balance", "calculate_modelo_303", "calculate_modelo_130"}
        if restricted_mode:
            tools = [t for t in tools if t["function"]["name"] not in RESTRICTED_TOOL_NAMES]

        return tools

    async def _execute_tool(
        self,
        function_name: str,
        function_args: Dict[str, Any],
        workspace_context: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a tool and return results."""

        if function_name == "get_workspace_summary":
            return await self._tool_get_workspace_summary(workspace_context)

        elif function_name == "calculate_vat_balance":
            quarter = function_args.get("quarter", self.current_quarter)
            year = function_args.get("year", self.current_year)
            return await self._tool_calculate_vat_balance(workspace_context, quarter, year)

        elif function_name == "project_annual_irpf":
            year = function_args.get("year", self.current_year)
            return await self._tool_project_annual_irpf(workspace_context, year)

        elif function_name == "get_quarterly_deadlines":
            include_past = function_args.get("include_past", False)
            return await self._tool_get_quarterly_deadlines(include_past)

        elif function_name == "update_fiscal_profile":
            try:
                from app.tools import TOOL_EXECUTORS
                executor = TOOL_EXECUTORS[function_name]
                from app.database.turso_client import get_db_client
                db = await get_db_client()
                return await executor(user_id=user_id, db_client=db, **function_args)
            except Exception as e:
                logger.error(f"Error executing update_fiscal_profile: {e}")
                return {"success": False, "error": str(e)}

        elif function_name in ("calculate_modelo_303", "calculate_modelo_130"):
            # Delegate to centralized tool executors
            try:
                from app.tools import TOOL_EXECUTORS
                executor = TOOL_EXECUTORS[function_name]
                return await executor(**function_args)
            except Exception as e:
                logger.error(f"Error executing {function_name}: {e}")
                return {"success": False, "error": str(e)}

        else:
            # Try centralized tool executors as fallback
            try:
                from app.tools import TOOL_EXECUTORS
                if function_name in TOOL_EXECUTORS:
                    executor = TOOL_EXECUTORS[function_name]
                    return await executor(**function_args)
            except Exception as e:
                logger.error(f"Error executing {function_name}: {e}")
            return {"error": f"Unknown function: {function_name}"}

    async def _tool_get_workspace_summary(self, context: str) -> Dict[str, Any]:
        """Get summary of workspace files."""
        # Parse context to extract file info
        files_info = []

        if "nomina" in context.lower() or "nómina" in context.lower():
            files_info.append("nóminas")
        if "factura" in context.lower():
            files_info.append("facturas")
        if "declaracion" in context.lower() or "declaración" in context.lower():
            files_info.append("declaraciones")

        summary = f"El workspace contiene documentos de tipo: {', '.join(files_info) if files_info else 'varios tipos'}"

        return {
            "success": True,
            "summary": summary,
            "document_types": files_info,
            "formatted_response": f"📁 **Resumen del Workspace**\n\n{summary}\n\nPuedes preguntarme sobre cualquiera de estos documentos."
        }

    async def _tool_calculate_vat_balance(
        self,
        context: str,
        quarter: int,
        year: int
    ) -> Dict[str, Any]:
        """Calculate VAT balance from invoices in context."""
        import re

        # Try to extract VAT amounts from context
        # This is a simplified extraction - real implementation would be more sophisticated
        iva_soportado = 0.0
        iva_repercutido = 0.0

        # Look for IVA patterns in context
        iva_pattern = r'IVA[:\s]*(\d+[.,]?\d*)\s*[€%]?'
        matches = re.findall(iva_pattern, context, re.IGNORECASE)

        # Simple heuristic: invoices received = soportado, invoices emitted = repercutido
        for match in matches:
            amount = float(match.replace(',', '.'))
            if amount > 0:
                iva_soportado += amount  # Simplified

        balance = iva_repercutido - iva_soportado

        return {
            "success": True,
            "quarter": quarter,
            "year": year,
            "iva_soportado": iva_soportado,
            "iva_repercutido": iva_repercutido,
            "balance": balance,
            "formatted_response": f"""📊 **Balance IVA Q{quarter}/{year}**

| Concepto | Importe |
|----------|---------|
| IVA Repercutido | {iva_repercutido:,.2f}€ |
| IVA Soportado | {iva_soportado:,.2f}€ |
| **Balance** | **{balance:,.2f}€** |

{"⚠️ Balance negativo: tienes IVA a compensar o devolver." if balance < 0 else "✅ Balance positivo: tienes IVA a ingresar."}

*Basado en las facturas de tu workspace. Revisa los datos con tu asesor.*"""
        }

    async def _tool_project_annual_irpf(
        self,
        context: str,
        year: int
    ) -> Dict[str, Any]:
        """Project annual IRPF from payslips."""
        import re

        # Try to extract salary and IRPF data from context
        bruto_mensual = 0.0
        irpf_retenido = 0.0
        meses_encontrados = 0

        # Look for salary patterns
        bruto_pattern = r'bruto[:\s]*(\d+[.,]?\d*)'
        irpf_pattern = r'IRPF[:\s]*(\d+[.,]?\d*)[%€]?'

        bruto_matches = re.findall(bruto_pattern, context, re.IGNORECASE)
        irpf_matches = re.findall(irpf_pattern, context, re.IGNORECASE)

        if bruto_matches:
            bruto_mensual = float(bruto_matches[0].replace(',', '.'))
            meses_encontrados = len(bruto_matches)

        if irpf_matches:
            irpf_retenido = float(irpf_matches[0].replace(',', '.'))

        # Project annual
        bruto_anual = bruto_mensual * 12 if bruto_mensual > 0 else 0
        irpf_anual_estimado = irpf_retenido * 12 if irpf_retenido > 0 else 0

        return {
            "success": True,
            "year": year,
            "bruto_mensual_promedio": bruto_mensual,
            "bruto_anual_proyectado": bruto_anual,
            "irpf_mensual_promedio": irpf_retenido,
            "irpf_anual_proyectado": irpf_anual_estimado,
            "meses_analizados": meses_encontrados,
            "formatted_response": f"""📈 **Proyección IRPF {year}**

Basado en {meses_encontrados} nómina(s) encontrada(s):

| Concepto | Mensual | Anual (proyectado) |
|----------|---------|-------------------|
| Salario Bruto | {bruto_mensual:,.2f}€ | {bruto_anual:,.2f}€ |
| Retención IRPF | {irpf_retenido:,.2f}€ | {irpf_anual_estimado:,.2f}€ |

**Tipo de retención efectivo**: {(irpf_retenido/bruto_mensual*100) if bruto_mensual > 0 else 0:.2f}%

⚠️ *Esta es una proyección basada en tus nóminas actuales. Los importes finales pueden variar.*"""
        }

    async def _tool_get_quarterly_deadlines(self, include_past: bool = False) -> Dict[str, Any]:
        """Get upcoming quarterly tax deadlines."""
        from datetime import date

        deadlines = [
            {"quarter": 1, "deadline": f"20 de Abril {self.current_year}", "date": date(self.current_year, 4, 20)},
            {"quarter": 2, "deadline": f"20 de Julio {self.current_year}", "date": date(self.current_year, 7, 20)},
            {"quarter": 3, "deadline": f"20 de Octubre {self.current_year}", "date": date(self.current_year, 10, 20)},
            {"quarter": 4, "deadline": f"30 de Enero {self.current_year + 1}", "date": date(self.current_year + 1, 1, 30)},
        ]

        today = date.today()

        if not include_past:
            deadlines = [d for d in deadlines if d["date"] >= today]

        # Format response
        deadline_lines = []
        for d in deadlines:
            days_left = (d["date"] - today).days
            status = "⏰ ¡Próximo!" if days_left <= 15 else "📅"
            deadline_lines.append(f"- Q{d['quarter']}: {d['deadline']} ({days_left} días) {status}")

        return {
            "success": True,
            "deadlines": deadlines,
            "formatted_response": f"""🗓️ **Próximas Fechas Límite Fiscales**

{chr(10).join(deadline_lines)}

**Modelos más comunes:**
- Modelo 303: IVA trimestral
- Modelo 130: Pago fraccionado IRPF (autónomos)
- Modelo 111: Retenciones IRPF

*Las fechas pueden variar si caen en festivo. Consulta el calendario de la AEAT.*"""
        }

    async def run(
        self,
        query: str,
        context: str = "",
        sources: List[dict] = None,
        conversation_history: List[dict] = None,
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        progress_callback: Optional[Any] = None,
        restricted_mode: bool = False,
        fiscal_profile: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Run the workspace agent.

        Args:
            query: User's question
            context: Aggregated text from workspace files
            sources: Source documents
            conversation_history: Previous messages
            user_id: User ID for audit
            workspace_id: Workspace being analyzed
            progress_callback: SSE callback for streaming

        Returns:
            AgentResponse with answer and metadata
        """
        if progress_callback:
            await progress_callback.thinking("Analizando tus documentos...")

        # Build messages
        messages = [
            {"role": "system", "content": self._get_system_prompt(fiscal_profile=fiscal_profile)}
        ]

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content")
                })

        # Build user message with context
        user_message = self._build_prompt(query, context)
        messages.append({"role": "user", "content": user_message})

        try:
            # Call OpenAI with tools
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    tools=self._get_tools(restricted_mode=restricted_mode),
                    tool_choice="auto",
                    temperature=1,
                    max_completion_tokens=4000
                ),
                timeout=60.0
            )

            message = response.choices[0].message

            # Handle tool calls
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                logger.info(f"WorkspaceAgent tool call: {function_name}")

                if progress_callback:
                    await progress_callback.tool_call(function_name, function_args)

                # Execute tool
                tool_result = await self._execute_tool(function_name, function_args, context, user_id=user_id)

                if progress_callback:
                    await progress_callback.tool_result(function_name, tool_result.get("success", False))

                # Add tool result and get final response
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call.model_dump()]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result.get("formatted_response", json.dumps(tool_result))
                })

                final_response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._client.chat.completions.create,
                        model=self.model,
                        messages=messages,
                        temperature=1,
                        max_completion_tokens=4000
                    ),
                    timeout=60.0
                )

                content = final_response.choices[0].message.content or tool_result.get("formatted_response", "")
            else:
                content = message.content or ""

            return AgentResponse(
                content=content,
                sources=sources or [],
                metadata={
                    "model": self.model,
                    "agent": self.name,
                    "workspace_id": workspace_id,
                    "tool_used": bool(message.tool_calls),
                    "current_quarter": self.current_quarter,
                    "current_year": self.current_year
                },
                agent_name=self.name
            )

        except asyncio.TimeoutError:
            logger.error("WorkspaceAgent timeout")
            return AgentResponse(
                content="⏱️ El análisis está tardando más de lo esperado. Intenta con una pregunta más específica.",
                sources=[],
                metadata={"error": "timeout"},
                agent_name=self.name
            )
        except Exception as e:
            logger.error(f"WorkspaceAgent error: {e}", exc_info=True)
            return AgentResponse(
                content=f"Error al analizar los documentos: {str(e)}",
                sources=[],
                metadata={"error": str(e)},
                agent_name=self.name
            )

    def _build_prompt(self, query: str, context: Optional[str] = None) -> str:
        """Build user prompt with workspace context."""
        if context:
            return f"""📁 **DOCUMENTOS DEL WORKSPACE DEL USUARIO:**

{context}

---

**PREGUNTA DEL USUARIO:**
{query}

---

Responde basándote ÚNICAMENTE en los documentos proporcionados. Si necesitas datos que no están en los documentos, indícalo claramente."""
        else:
            return f"""{query}

⚠️ No hay documentos en el workspace. Pide al usuario que suba sus archivos fiscales para poder ayudarle con datos personalizados."""


# Global instance
_workspace_agent: Optional[WorkspaceAgent] = None


def get_workspace_agent() -> WorkspaceAgent:
    """Get the global WorkspaceAgent instance."""
    global _workspace_agent

    if _workspace_agent is None:
        _workspace_agent = WorkspaceAgent()

    return _workspace_agent
