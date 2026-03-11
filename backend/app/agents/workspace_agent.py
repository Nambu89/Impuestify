"""
WorkspaceAgent - Specialized Agent for User Workspace Context

Analyzes user's uploaded documents (payslips, invoices, tax declarations)
and provides personalized fiscal assistance based on their data.
Combines workspace documents with RAG knowledge base and all centralized tools.
CCAA-aware: adapts tools and system prompt to user's fiscal regime
(comun, foral_vasco, foral_navarra, ceuta_melilla, canarias).
"""
import logging
import json
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from openai import OpenAI, AsyncOpenAI

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

    Uses the SAME tools as TaxAgent (simulate_irpf, discover_deductions,
    calculate_isd, IPSI, crypto, casillas, etc.) plus workspace-specific
    tools (get_workspace_summary, calculate_vat_balance, project_annual_irpf).

    CCAA-aware: adapts tool availability and system prompt to the user's
    fiscal regime (foral territories, Ceuta/Melilla IPSI, Canarias IGIC).
    """

    def __init__(
        self,
        name: str = "WorkspaceAgent",
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        from app.config import settings
        self.name = name
        self.model = model or settings.OPENAI_MODEL
        self.api_key = api_key or settings.OPENAI_API_KEY

        self.current_date = datetime.now()
        self.current_year = self.current_date.year
        self.current_quarter = (self.current_date.month - 1) // 3 + 1

        self._client = None
        self._async_client = None
        self._initialize()

    def _initialize(self):
        """Initialize OpenAI clients (sync for tool calls, async for streaming)."""
        if self.api_key:
            self._client = OpenAI(api_key=self.api_key)
            self._async_client = AsyncOpenAI(api_key=self.api_key)
            logger.info(f"WorkspaceAgent '{self.name}' initialized (year: {self.current_year}, Q{self.current_quarter})")
        else:
            logger.error("WorkspaceAgent initialization failed - missing OPENAI_API_KEY")
            raise ValueError("OPENAI_API_KEY is required")

    # ── Fiscal profile formatting ──────────────────────────────────────

    def _format_fiscal_profile(self, fp: Dict[str, Any]) -> str:
        """Format fiscal profile dict into a readable string for the system prompt."""
        if not fp:
            return ""
        lines = []
        label_map = {
            "ccaa_residencia": "CCAA residencia",
            "situacion_laboral": "Situacion laboral",
            "epigrafe_iae": "Epigrafe IAE",
            "tipo_actividad": "Tipo actividad",
            "fecha_alta_autonomo": "Fecha alta autonomo",
            "metodo_estimacion_irpf": "Metodo estimacion IRPF",
            "regimen_iva": "Regimen IVA",
            "rendimientos_netos_mensuales": "Rendimientos netos mensuales",
            "base_cotizacion_reta": "Base cotizacion RETA",
            "territorio_foral": "Territorio foral",
            "territorio_historico": "Territorio historico",
            "tipo_retencion_facturas": "Tipo retencion facturas",
            "tarifa_plana": "Tarifa plana",
            "pluriactividad": "Pluriactividad",
            "ceuta_melilla": "Residente en Ceuta/Melilla",
            "planes_pensiones": "Aportaciones planes pensiones",
            "hipoteca_pre2013_base": "Hipoteca pre-2013 (base)",
            "maternidad_hijos": "Hijos menores de 3 anos",
            "familia_numerosa": "Familia numerosa",
            "donativos": "Donativos",
            "tributacion_conjunta": "Tributacion conjunta",
        }
        for key, label in label_map.items():
            val = fp.get(key)
            if val is not None and val != "":
                if isinstance(val, bool):
                    lines.append(f"- {label}: {'Si' if val else 'No'}")
                elif isinstance(val, float) and key == "tipo_retencion_facturas":
                    lines.append(f"- {label}: {val}%")
                elif isinstance(val, (int, float)) and ("netos" in key or "cotizacion" in key or "pensiones" in key or "hipoteca" in key or "donativos" in key):
                    lines.append(f"- {label}: {val:,.2f} EUR")
                else:
                    lines.append(f"- {label}: {val}")
        return "\n".join(lines)

    # ── CCAA-aware system prompt ───────────────────────────────────────

    def _get_regime_context(self, fiscal_profile: Optional[Dict[str, Any]] = None) -> str:
        """Generate CCAA-specific context for the system prompt."""
        if not fiscal_profile:
            return ""

        ccaa = fiscal_profile.get("ccaa_residencia", "")
        if not ccaa:
            return ""

        from app.utils.regime_classifier import classify_regime
        regime = classify_regime(ccaa)

        if regime == "foral_vasco":
            return f"""
🏛️ **REGIMEN FISCAL FORAL VASCO** ({ccaa}):
- El usuario tributa bajo la Hacienda Foral de {ccaa}, NO por la AEAT estatal.
- IRPF foral: escala propia (7 tramos, 23-49%), minimums como deduccion en cuota.
- IVA: se aplica el IVA estatal (Modelo 303) pero se declara en la Hacienda Foral.
- Deducciones: usa SOLO las deducciones forales de {ccaa} (NO las estatales ni de otras CCAA).
- EPSV (Entidades Prevision Social Voluntaria): limite deduccion 5.000 EUR/anio (en vez de planes pensiones estatales).
- Modelos trimestrales: Modelo 303 (IVA) + Modelo 130 (IRPF) ante la Hacienda Foral.
- Al simular IRPF, usa `simulate_irpf` que detecta automaticamente la escala foral.
- Al buscar deducciones, `discover_deductions` filtra por territorio "{ccaa}".
"""
        elif regime == "foral_navarra":
            return f"""
🏛️ **REGIMEN FISCAL FORAL NAVARRA**:
- El usuario tributa bajo la Hacienda Foral de Navarra, NO por la AEAT estatal.
- IRPF foral navarro: escala propia (11 tramos, 13-52%), deduccion en cuota por minimo contribuyente 1.084 EUR.
- IVA: se aplica el IVA estatal pero se declara en la Hacienda Foral de Navarra (Modelo F-69).
- Deducciones: usa SOLO las deducciones forales de Navarra (NO las estatales).
- Modelos trimestrales: Modelo F-69 (IVA) + Modelo 130 (IRPF) ante la Hacienda Foral.
- Al simular IRPF, usa `simulate_irpf` que detecta automaticamente la escala foral navarra.
- Al buscar deducciones, `discover_deductions` filtra por territorio "Navarra".
"""
        elif regime == "ceuta_melilla":
            return f"""
🏛️ **REGIMEN ESPECIAL CEUTA/MELILLA** ({ccaa}):
- Deduccion del 60% de la cuota integra del IRPF (Art. 68.4 LIRPF) — MUY favorable.
- NO hay IVA en {ccaa}. Se aplica el IPSI (Impuesto sobre la Produccion, los Servicios y la Importacion).
- IPSI tiene 6 tipos: 0.5%, 1%, 2%, 4%, 8%, 10% (Ley 8/1991 Ceuta, Ley 13/1996 Melilla).
- Usa `calculate_modelo_ipsi` para calcular el IPSI trimestral (NO Modelo 303).
- Modelo 130 si es autonomo para pago fraccionado IRPF.
- Al simular IRPF, `simulate_irpf` aplica automaticamente la bonificacion del 60%.
- Al buscar deducciones, `discover_deductions` incluye las especificas de {ccaa}.
"""
        elif regime == "canarias":
            return """
🏛️ **REGIMEN ESPECIAL CANARIAS**:
- NO hay IVA en Canarias. Se aplica el IGIC (Impuesto General Indirecto Canario).
- IGIC general: 7% (vs 21% IVA peninsular). Otros tipos: 0%, 3%, 9.5%, 15%.
- Modelo 420 (IGIC) en vez de Modelo 303 (IVA).
- IRPF: escala estatal + tramos autonomicos de Canarias.
- Modelo 130 si es autonomo para pago fraccionado IRPF.
- Al buscar deducciones, `discover_deductions` incluye las especificas de Canarias.
- Al simular IRPF, `simulate_irpf` usa los tramos autonomicos de Canarias.
"""
        else:
            # Regimen comun
            return f"""
📍 **CCAA: {ccaa}** (regimen comun):
- IRPF: escala estatal + tramos autonomicos de {ccaa}.
- IVA estatal: Modelo 303.
- Al buscar deducciones, `discover_deductions` filtra por "{ccaa}" (deducciones estatales + autonomicas).
- Al simular IRPF, `simulate_irpf` usa los tramos autonomicos de {ccaa}.
"""

    def _get_system_prompt(self, fiscal_profile: Optional[Dict[str, Any]] = None) -> str:
        """Generate system prompt with CCAA-aware context and workspace instructions."""
        fiscal_section = ""
        if fiscal_profile:
            formatted = self._format_fiscal_profile(fiscal_profile)
            if formatted:
                fiscal_section = f"""

👤 **PERFIL FISCAL DEL USUARIO** (usa estos datos para pre-rellenar calculos):
{formatted}

⚠️ Usa estos datos del perfil para rellenar automaticamente los parametros de las herramientas.
"""

        regime_section = self._get_regime_context(fiscal_profile)

        # Determine CCAA-specific model names for the prompt
        ccaa = (fiscal_profile or {}).get("ccaa_residencia", "")
        from app.utils.regime_classifier import classify_regime
        regime = classify_regime(ccaa) if ccaa else "comun"

        iva_model = "Modelo 303 (IVA)"
        if regime == "ceuta_melilla":
            iva_model = "IPSI (calculate_modelo_ipsi)"
        elif regime == "canarias":
            iva_model = "Modelo 420 (IGIC)"
        elif regime == "foral_navarra":
            iva_model = "Modelo F-69 (IVA Navarra)"

        return f"""Eres Impuestify en modo Workspace, un asesor fiscal experto que analiza los documentos personales del usuario.

📁 **TU ROL**:
El usuario ha adjuntado documentos (nominas, facturas, declaraciones, etc.) a su espacio de trabajo.
Analiza estos documentos Y combinalos con la normativa fiscal (legislacion AEAT, BOE, normativas forales, CCAA) para dar respuestas personalizadas y precisas.
{regime_section}
📅 **CONTEXTO TEMPORAL**:
- Fecha actual: {self.current_date.strftime('%d de %B de %Y')}
- Anio fiscal: {self.current_year} | Trimestre: Q{self.current_quarter}
{fiscal_section}
📊 **HERRAMIENTAS DISPONIBLES**:
*Workspace:*
- `get_workspace_summary`: Resumen de archivos del workspace
- `calculate_vat_balance`: Balance IVA de facturas del workspace
- `project_annual_irpf`: Proyeccion IRPF anual desde nominas
- `get_quarterly_deadlines`: Proximas fechas limite fiscales

*Calculo fiscal (identicas al chat individual):*
- `simulate_irpf`: Simulacion IRPF completa (detecta automaticamente regimen foral/comun/Ceuta-Melilla)
- `calculate_irpf`: Calculo rapido tramos IRPF
- `discover_deductions`: Busca deducciones aplicables por CCAA (estatales + autonomicas/forales)
- `calculate_autonomous_quota`: Cuota de autonomo
- `calculate_modelo_303`: Modelo 303 IVA trimestral
- `calculate_modelo_130`: Modelo 130 pago fraccionado IRPF
- `calculate_modelo_ipsi`: IPSI Ceuta/Melilla (6 tipos: 0.5%-10%)
- `calculate_isd`: Impuesto Sucesiones y Donaciones
- `lookup_casilla`: Buscar casillas IRPF Modelo 100
- `calculate_crypto_gains`: Ganancias cripto (FIFO + antiaplicacion)
- `update_fiscal_profile`: Actualizar perfil fiscal del usuario

📋 **FLUJOS DE CALCULO** (adapta segun CCAA):
- IVA trimestral → Lee facturas del workspace → {iva_model}
- Pago fraccionado → Lee ingresos/gastos acumulados → Modelo 130
- Simulacion IRPF → Usa datos del perfil + workspace → `simulate_irpf`
- Deducciones → `discover_deductions` con la CCAA del usuario

🎯 **TU ESTILO**:
- Cercano y profesional, como un asesor fiscal de confianza
- Usa tuteo y lenguaje claro
- Basa respuestas en los DATOS REALES del usuario combinados con normativa vigente
- Cita fuentes: "Segun tu nomina de enero..." / "Segun la normativa de {ccaa or 'tu CCAA'}..."
- Si faltan datos, pide que suban los documentos necesarios

🚫 **NUNCA hagas esto en tu respuesta** (el usuario lo veria directamente):
- NUNCA escribas tus pensamientos internos ("Llamo a la herramienta...", "Voy a usar...", "Primero calculo...")
- NUNCA incluyas JSON crudo en tu respuesta ({{"call":..., "args":...}})
- NUNCA describas que herramienta vas a usar — simplemente usala y muestra el resultado
- Tu respuesta debe ser SOLO la informacion util para el usuario, como si fueras un asesor humano

Responde siempre en espaniol, de forma clara y estructurada."""

    # ── Tools ──────────────────────────────────────────────────────────

    def _get_tools(self, restricted_mode: bool = False) -> List[Dict[str, Any]]:
        """Get ALL tools: workspace-specific + centralized (same as TaxAgent)."""
        # Workspace-specific tools
        workspace_tools = [
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
                                "description": "Anio fiscal. Si no se especifica, usa el anio actual."
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
                    "description": "Proyecta el IRPF anual basado en las nominas del workspace",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {
                                "type": "integer",
                                "description": "Anio para la proyeccion. Si no se especifica, usa el anio actual."
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
                    "description": "Obtiene las proximas fechas limite de declaraciones trimestrales",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "include_past": {
                                "type": "boolean",
                                "description": "Incluir fechas pasadas del anio actual. Por defecto false."
                            }
                        },
                        "required": []
                    }
                }
            }
        ]

        # Add ALL centralized tools (same as TaxAgent)
        try:
            from app.tools import ALL_TOOLS
            workspace_tools.extend(ALL_TOOLS)
        except ImportError:
            logger.warning("Could not import centralized tools")

        # In restricted mode (particular plan), remove autonomo-specific tools
        RESTRICTED_TOOL_NAMES = {
            "calculate_vat_balance", "calculate_modelo_303", "calculate_modelo_130",
            "calculate_autonomous_quota", "calculate_modelo_ipsi"
        }
        if restricted_mode:
            workspace_tools = [
                t for t in workspace_tools
                if t.get("function", {}).get("name") not in RESTRICTED_TOOL_NAMES
            ]

        return workspace_tools

    # ── Tool execution ─────────────────────────────────────────────────

    async def _execute_tool(
        self,
        function_name: str,
        function_args: Dict[str, Any],
        workspace_context: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a tool — workspace-specific or centralized."""

        # Workspace-specific tools (need workspace_context)
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

        # Tools that need special params (user_id, db_client)
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

        elif function_name == "discover_deductions":
            try:
                from app.tools import TOOL_EXECUTORS
                executor = TOOL_EXECUTORS[function_name]
                # Auto-inject user_id for profile-based answers
                return await executor(user_id=user_id, **function_args)
            except Exception as e:
                logger.error(f"Error executing discover_deductions: {e}")
                return {"success": False, "error": str(e)}

        else:
            # ALL other tools — delegate to centralized TOOL_EXECUTORS
            try:
                from app.tools import TOOL_EXECUTORS
                if function_name in TOOL_EXECUTORS:
                    executor = TOOL_EXECUTORS[function_name]
                    return await executor(**function_args)
                else:
                    return {"error": f"Unknown function: {function_name}"}
            except Exception as e:
                logger.error(f"Error executing {function_name}: {e}")
                return {"success": False, "error": str(e)}

    # ── Workspace-specific tool implementations ────────────────────────

    async def _tool_get_workspace_summary(self, context: str) -> Dict[str, Any]:
        """Get summary of workspace files."""
        files_info = []
        if "nomina" in context.lower() or "nomina" in context.lower():
            files_info.append("nominas")
        if "factura" in context.lower():
            files_info.append("facturas")
        if "declaracion" in context.lower() or "declaracion" in context.lower():
            files_info.append("declaraciones")

        summary = f"El workspace contiene documentos de tipo: {', '.join(files_info) if files_info else 'varios tipos'}"
        return {
            "success": True,
            "summary": summary,
            "document_types": files_info,
            "formatted_response": f"Resumen del Workspace\n\n{summary}\n\nPuedes preguntarme sobre cualquiera de estos documentos."
        }

    async def _tool_calculate_vat_balance(self, context: str, quarter: int, year: int) -> Dict[str, Any]:
        """Calculate VAT balance from invoices in context."""
        import re
        iva_soportado = 0.0
        iva_repercutido = 0.0

        iva_pattern = r'IVA[:\s]*(\d+[.,]?\d*)\s*[EUR%]?'
        matches = re.findall(iva_pattern, context, re.IGNORECASE)
        for match in matches:
            amount = float(match.replace(',', '.'))
            if amount > 0:
                iva_soportado += amount

        balance = iva_repercutido - iva_soportado
        return {
            "success": True,
            "quarter": quarter, "year": year,
            "iva_soportado": iva_soportado,
            "iva_repercutido": iva_repercutido,
            "balance": balance,
            "formatted_response": f"""Balance IVA Q{quarter}/{year}

| Concepto | Importe |
|----------|---------|
| IVA Repercutido | {iva_repercutido:,.2f} EUR |
| IVA Soportado | {iva_soportado:,.2f} EUR |
| **Balance** | **{balance:,.2f} EUR** |

{"Balance negativo: tienes IVA a compensar o devolver." if balance < 0 else "Balance positivo: tienes IVA a ingresar."}

*Basado en las facturas de tu workspace. Revisa los datos con tu asesor.*"""
        }

    async def _tool_project_annual_irpf(self, context: str, year: int) -> Dict[str, Any]:
        """Project annual IRPF from payslips."""
        import re
        bruto_mensual = 0.0
        irpf_retenido = 0.0
        meses_encontrados = 0

        bruto_pattern = r'bruto[:\s]*(\d+[.,]?\d*)'
        irpf_pattern = r'IRPF[:\s]*(\d+[.,]?\d*)[%EUR]?'

        bruto_matches = re.findall(bruto_pattern, context, re.IGNORECASE)
        irpf_matches = re.findall(irpf_pattern, context, re.IGNORECASE)

        if bruto_matches:
            bruto_mensual = float(bruto_matches[0].replace(',', '.'))
            meses_encontrados = len(bruto_matches)
        if irpf_matches:
            irpf_retenido = float(irpf_matches[0].replace(',', '.'))

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
            "formatted_response": f"""Proyeccion IRPF {year}

Basado en {meses_encontrados} nomina(s) encontrada(s):

| Concepto | Mensual | Anual (proyectado) |
|----------|---------|-------------------|
| Salario Bruto | {bruto_mensual:,.2f} EUR | {bruto_anual:,.2f} EUR |
| Retencion IRPF | {irpf_retenido:,.2f} EUR | {irpf_anual_estimado:,.2f} EUR |

**Tipo de retencion efectivo**: {(irpf_retenido/bruto_mensual*100) if bruto_mensual > 0 else 0:.2f}%

*Esta es una proyeccion basada en tus nominas actuales. Los importes finales pueden variar.*"""
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

        deadline_lines = []
        for d in deadlines:
            days_left = (d["date"] - today).days
            status = "Proximo!" if days_left <= 15 else ""
            deadline_lines.append(f"- Q{d['quarter']}: {d['deadline']} ({days_left} dias) {status}")

        return {
            "success": True,
            "deadlines": deadlines,
            "formatted_response": f"""Proximas Fechas Limite Fiscales

{chr(10).join(deadline_lines)}

**Modelos mas comunes:**
- Modelo 303: IVA trimestral
- Modelo 130: Pago fraccionado IRPF (autonomos)
- Modelo 111: Retenciones IRPF

*Las fechas pueden variar si caen en festivo. Consulta el calendario de la AEAT.*"""
        }

    # ── Main execution ─────────────────────────────────────────────────

    async def run(
        self,
        query: str,
        context: str = "",
        rag_context: str = "",
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
            rag_context: RAG context from knowledge base (normativa fiscal)
            sources: Source documents
            conversation_history: Previous messages
            user_id: User ID for audit
            workspace_id: Workspace being analyzed
            progress_callback: SSE callback for streaming
            restricted_mode: True if user is on plan Particular
            fiscal_profile: User's fiscal profile dict

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

        # Build user message with workspace docs + RAG context
        user_message = self._build_prompt(query, context, rag_context)
        messages.append({"role": "user", "content": user_message})

        try:
            # First call: OpenAI with tools (non-streaming, to check for tool_calls)
            response = await asyncio.wait_for(
                self._async_client.chat.completions.create(
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
            tool_used = False

            # Handle tool calls
            if message.tool_calls:
                tool_used = True
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

                # Add tool result and stream final response
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

                # Stream the final response (same as TaxAgent)
                content = await self._stream_response(messages, progress_callback)

                if not content:
                    content = tool_result.get("formatted_response", "")
            else:
                # No tool call — stream the direct response
                content = message.content or ""
                if content and progress_callback:
                    await self._emit_content_chunks(content, progress_callback)

            return AgentResponse(
                content=content,
                sources=sources or [],
                metadata={
                    "model": self.model,
                    "agent": self.name,
                    "workspace_id": workspace_id,
                    "tool_used": tool_used,
                    "current_quarter": self.current_quarter,
                    "current_year": self.current_year
                },
                agent_name=self.name
            )

        except asyncio.TimeoutError:
            logger.error("WorkspaceAgent timeout")
            return AgentResponse(
                content="El analisis esta tardando mas de lo esperado. Intenta con una pregunta mas especifica.",
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

    # ── Streaming ──────────────────────────────────────────────────────

    async def _stream_response(
        self,
        messages: List[Dict[str, Any]],
        progress_callback: Optional[Any] = None,
        timeout: float = 60.0,
        chunk_timeout: float = 30.0
    ) -> str:
        """
        Call OpenAI with stream=True and emit content_chunk events in real-time.
        Mirrors TaxAgent._stream_openai_response() for consistent UX.
        """
        accumulated = []

        try:
            stream = await asyncio.wait_for(
                self._async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=1,
                    max_completion_tokens=4000,
                    stream=True
                ),
                timeout=timeout
            )

            buffer = ""
            CHUNK_SIZE = 12
            stream_iter = stream.__aiter__()

            while True:
                try:
                    chunk = await asyncio.wait_for(
                        stream_iter.__anext__(),
                        timeout=chunk_timeout
                    )
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Stream stalled after {sum(len(c) for c in accumulated)} chars"
                    )
                    break

                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    buffer += delta.content
                    accumulated.append(delta.content)

                    if len(buffer) >= CHUNK_SIZE:
                        if progress_callback:
                            await progress_callback.content_chunk(buffer)
                        buffer = ""

            # Flush remaining buffer
            if buffer and progress_callback:
                await progress_callback.content_chunk(buffer)

        except asyncio.TimeoutError:
            logger.error("Streaming OpenAI call creation timed out")
            raise
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            if accumulated:
                logger.info(f"Returning partial content ({len(accumulated)} chunks)")
            else:
                raise

        return "".join(accumulated)

    async def _emit_content_chunks(self, content: str, progress_callback: Any) -> None:
        """Emit already-generated content as chunks for real-time display."""
        CHUNK_SIZE = 12
        for i in range(0, len(content), CHUNK_SIZE):
            chunk = content[i:i + CHUNK_SIZE]
            await progress_callback.content_chunk(chunk)
            await asyncio.sleep(0.01)

    # ── Prompt building ────────────────────────────────────────────────

    def _build_prompt(self, query: str, context: Optional[str] = None, rag_context: Optional[str] = None) -> str:
        """Build user prompt with workspace context + RAG knowledge base."""
        parts = []

        if context:
            parts.append(f"""DOCUMENTOS DEL WORKSPACE DEL USUARIO:

{context}""")

        if rag_context:
            parts.append(f"""NORMATIVA FISCAL (base de conocimiento):

{rag_context}""")

        if parts:
            combined = "\n\n---\n\n".join(parts)
            return f"""{combined}

---

**PREGUNTA DEL USUARIO:**
{query}

---

Responde combinando los documentos del usuario con la normativa fiscal. Si necesitas datos que no estan en los documentos, indicalo claramente."""
        else:
            return f"""{query}

No hay documentos en el workspace. Pide al usuario que suba sus archivos fiscales para poder ayudarle con datos personalizados."""


# Global instance
_workspace_agent: Optional[WorkspaceAgent] = None


def get_workspace_agent() -> WorkspaceAgent:
    """Get the global WorkspaceAgent instance."""
    global _workspace_agent

    if _workspace_agent is None:
        _workspace_agent = WorkspaceAgent()

    return _workspace_agent
