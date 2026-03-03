"""
Competitor Analysis Tools for Impuestify

Provides structured competitive intelligence about the Spanish digital tax market.
Tools for comparing features, identifying gaps, and suggesting improvements.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Competitor Knowledge Base ─────────────────────────────────────────────

COMPETITORS = {
    "taxdown": {
        "name": "TaxDown",
        "founded": 2019,
        "users": "1,000,000+",
        "funding": "29.7M EUR",
        "team_size": "200+ tax experts",
        "aeat_status": "Colaborador Social (certified)",
        "trustpilot": "4.7/5 (6,500+ reviews)",
        "markets": ["Spain", "Mexico"],
        "pricing": {
            "gratis": {"price": 0, "features": ["Guided app", "Result calculation/optimization", "Fiscal knowledge base", "AsesorIA chatbot"]},
            "pro": {"price": 35, "features": ["Expert review", "AEAT submission", "Notification responses", "Year-round support", "24h email"]},
            "live": {"price": 45, "features": ["Everything in PRO", "Direct chat with advisor", "WhatsApp support", "Model 030"]},
            "full": {"price": 65, "features": ["Everything in LIVE", "Expert handles entire process", "Complex situations", "Beckham Law", "Non-residents"]},
        },
        "features": {
            "irpf_filing": True,
            "quarterly_filing": False,
            "aeat_data_import": True,
            "aeat_submission": True,
            "ai_chatbot": True,
            "rag_documentation": False,
            "irpf_calculator": True,
            "autonomos_quotas": False,
            "payslip_analysis": False,
            "notification_analysis": True,
            "invoicing": False,
            "expense_tracking": False,
            "open_banking": False,
            "human_advisors": True,
            "mobile_app": True,
            "b2b_enterprise": True,
            "gdpr_compliance": True,
            "ai_guardrails": False,
            "workspace_documents": False,
            "multi_agent_system": False,
            "semantic_cache": False,
            "deduction_optimizer": True,
        },
        "strengths": [
            "Massive user base (1M+) and brand recognition",
            "Free tier with real value (calculation + optimization)",
            "AEAT Colaborador Social status (can file declarations)",
            "Strong B2B channel (500+ enterprise partners: BBVA, Revolut, N26)",
            "Banking partnerships (25% discount for BBVA customers)",
            "AI investment (AsesorIA chatbot, Rita tax engine)",
            "Mobile-first approach (iOS/Android)",
            "Average user savings: 350-483 EUR per declaration",
            "Rita engine: analyzes 250+ state and regional deductions",
        ],
        "weaknesses": [
            "Primarily focused on IRPF/Renta - not full accounting",
            "No quarterly tax filing (303, 130) for autonomos",
            "AsesorIA chatbot is basic (lead generation, not deep analysis)",
            "No payslip analysis capability",
            "No invoicing or expense tracking platform",
            "No workspace for user documents",
            "No transparent AI safety/guardrails",
        ],
        "avg_savings": "350-483 EUR",
        "key_partnerships": ["BBVA", "Revolut", "N26", "eToro", "Mahou", "XTB"],
    },
    "declarando": {
        "name": "Declarando",
        "founded": 2015,
        "users": "70,000+",
        "funding": "Unknown",
        "team_size": "70+ specialists",
        "aeat_status": "Integrated",
        "markets": ["Spain"],
        "pricing": {
            "basic": {"price_monthly": 70, "features": ["Invoicing", "Quarterly filings", "Annual Renta"]},
            "advanced": {"price_monthly": 100, "features": ["Everything in Basic", "Dedicated advisor", "VeriFactu"]},
        },
        "features": {
            "irpf_filing": True,
            "quarterly_filing": True,
            "aeat_data_import": True,
            "aeat_submission": True,
            "ai_chatbot": False,
            "rag_documentation": False,
            "irpf_calculator": True,
            "autonomos_quotas": True,
            "payslip_analysis": False,
            "notification_analysis": False,
            "invoicing": True,
            "expense_tracking": True,
            "open_banking": False,
            "human_advisors": True,
            "mobile_app": True,
            "b2b_enterprise": False,
            "gdpr_compliance": True,
            "ai_guardrails": False,
            "workspace_documents": False,
            "multi_agent_system": False,
            "semantic_cache": False,
            "deduction_optimizer": True,
        },
        "strengths": [
            "Specialized exclusively for autonomos",
            "Full fiscal lifecycle (quarterly + annual)",
            "Invoicing + accounting built-in",
            "VeriFactu compliance",
            "Claims 4,000 EUR average annual savings",
            "Strong support: chat, email, phone, WhatsApp, video (<2 min response)",
        ],
        "weaknesses": [
            "Significantly more expensive (70-100 EUR/month)",
            "No free tier",
            "Not suitable for salaried employees",
            "Smaller brand awareness than TaxDown",
            "No AI chatbot or advanced technology differentiator",
        ],
        "avg_savings": "4,000 EUR/year (autonomos)",
    },
    "taxfix": {
        "name": "Taxfix (ex-TaxScouts)",
        "founded": 2016,
        "users": "Unknown (169K monthly visits)",
        "funding": "International (Taxfix group)",
        "team_size": "Unknown",
        "aeat_status": "Integrated",
        "markets": ["Spain", "Germany", "UK", "Italy"],
        "pricing": {
            "renta_individual": {"price": 69.90, "features": ["Personal IRPF filing", "Assigned advisor"]},
            "renta_matrimonio": {"price": 109.80, "features": ["Couple filing", "Both declarations"]},
            "autonomos_pro": {"price_monthly": 39.90, "features": ["Registration", "Quarterly/annual filings", "International invoicing"]},
            "autonomos_premium": {"price_monthly": 59.90, "features": ["Pro + phone calls", "Advisor-prepared accounting"]},
            "autonomos_total": {"price_monthly": 99.90, "features": ["Premium + payroll (up to 3 employees)"]},
        },
        "features": {
            "irpf_filing": True,
            "quarterly_filing": True,
            "aeat_data_import": True,
            "aeat_submission": True,
            "ai_chatbot": False,
            "rag_documentation": False,
            "irpf_calculator": True,
            "autonomos_quotas": True,
            "payslip_analysis": False,
            "notification_analysis": True,
            "invoicing": True,
            "expense_tracking": True,
            "open_banking": False,
            "human_advisors": True,
            "mobile_app": True,
            "b2b_enterprise": False,
            "gdpr_compliance": True,
            "ai_guardrails": False,
            "workspace_documents": False,
            "multi_agent_system": False,
            "semantic_cache": False,
            "deduction_optimizer": True,
        },
        "strengths": [
            "Personal assigned advisor for each case",
            "International backing (Taxfix group)",
            "Combined individual + autonomo plans",
            "Unlimited chat support",
            "Invoice creation with customizable design",
        ],
        "weaknesses": [
            "More expensive than TaxDown for Renta (69.90 vs 35 EUR)",
            "Rebranding confusion (TaxScouts to Taxfix)",
            "Less technologically differentiated",
            "No AI capabilities",
        ],
    },
    "xolo": {
        "name": "Xolo",
        "founded": 2017,
        "users": "Unknown",
        "funding": "EU fintech",
        "team_size": "Unknown",
        "aeat_status": "Integrated",
        "markets": ["Spain", "Estonia", "Finland", "Portugal"],
        "pricing": {
            "lite": {"price_monthly": 15, "features": ["Invoice generator", "Expense management"]},
            "starter": {"price_monthly": 49, "features": ["Free registration", "Spanish invoices", "Quarterly/annual filings"]},
            "global": {"price_monthly": 59, "features": ["Starter + international invoices", "Multi-currency"]},
            "premium": {"price_monthly": 99, "features": ["All features", "Priority 24h support", "Consulting hours"]},
        },
        "features": {
            "irpf_filing": True,
            "quarterly_filing": True,
            "aeat_data_import": True,
            "aeat_submission": True,
            "ai_chatbot": False,
            "rag_documentation": False,
            "irpf_calculator": True,
            "autonomos_quotas": True,
            "payslip_analysis": False,
            "notification_analysis": False,
            "invoicing": True,
            "expense_tracking": True,
            "open_banking": True,
            "human_advisors": True,
            "mobile_app": True,
            "b2b_enterprise": False,
            "gdpr_compliance": True,
            "ai_guardrails": False,
            "workspace_documents": False,
            "multi_agent_system": False,
            "semantic_cache": False,
            "deduction_optimizer": False,
        },
        "strengths": [
            "Best for international freelancers and digital nomads",
            "Open banking integration for real-time financial tracking",
            "Multi-currency and multi-language invoicing",
            "EU-wide presence",
            "Competitive pricing (starts at 15 EUR)",
        ],
        "weaknesses": [
            "Not a household name in Spain",
            "Less Spanish tax expertise than local competitors",
            "No IRPF/Renta-only offering at competitive prices",
            "No AI capabilities",
        ],
    },
}

IMPUESTIFY_FEATURES = {
    "irpf_filing": False,
    "quarterly_filing": False,
    "aeat_data_import": False,
    "aeat_submission": False,
    "ai_chatbot": True,
    "rag_documentation": True,
    "irpf_calculator": True,
    "autonomos_quotas": True,
    "payslip_analysis": True,
    "notification_analysis": True,
    "invoicing": False,
    "expense_tracking": False,
    "open_banking": False,
    "human_advisors": False,
    "mobile_app": False,
    "b2b_enterprise": False,
    "gdpr_compliance": True,
    "ai_guardrails": True,
    "workspace_documents": True,
    "multi_agent_system": True,
    "semantic_cache": True,
    "deduction_optimizer": False,
}

IMPUESTIFY_STRENGTHS = [
    "AI-native architecture: multi-agent system with RAG, Llama Guard, semantic caching",
    "Free unlimited AI tax advisory (deeper than TaxDown's AsesorIA)",
    "Automated payslip analysis with IRPF projection (unique in market)",
    "AEAT notification analysis with AI (competitors use humans)",
    "Defense-in-depth AI security (Llama Guard 4, prompt injection detection, PII filtering)",
    "User workspace for document management and analysis",
    "IRPF simulator with all 17 CCAA + territories forales",
    "Autonomo quota calculator with 2025 variable system",
    "Modelo 303 and Modelo 130 calculators",
    "Semantic cache for cost reduction (~30%)",
    "RAG on 394+ official fiscal PDFs (AEAT, BOE, CCAA)",
    "Conversational fiscal profile that learns from interactions",
    "Open architecture allowing rapid feature development",
]

IMPUESTIFY_WEAKNESSES = [
    "No AEAT submission capability (requires Colaborador Social status)",
    "No AEAT data import (no Cl@ve/certificate integration)",
    "No mobile app (web-only)",
    "No human experts (fully AI-based)",
    "No invoicing/accounting platform",
    "No B2B/enterprise channel",
    "No deduction optimization engine (250+ deductions like TaxDown's Rita)",
    "Small/no user base compared to TaxDown's 1M+",
    "No brand recognition in the market",
]

FEATURE_LABELS = {
    "irpf_filing": "Presentacion Declaracion Renta (IRPF)",
    "quarterly_filing": "Declaraciones Trimestrales (303/130)",
    "aeat_data_import": "Importacion Datos AEAT (Clave/Certificado)",
    "aeat_submission": "Presentacion Telematica a AEAT",
    "ai_chatbot": "Chatbot Fiscal con IA",
    "rag_documentation": "RAG sobre Documentacion Oficial",
    "irpf_calculator": "Calculadora IRPF",
    "autonomos_quotas": "Calculadora Cuotas Autonomos",
    "payslip_analysis": "Analisis de Nominas",
    "notification_analysis": "Analisis Notificaciones AEAT",
    "invoicing": "Plataforma de Facturacion",
    "expense_tracking": "Seguimiento de Gastos",
    "open_banking": "Open Banking (Conexion Bancaria)",
    "human_advisors": "Asesores Fiscales Humanos",
    "mobile_app": "App Movil (iOS/Android)",
    "b2b_enterprise": "Canal B2B / Empresas",
    "gdpr_compliance": "Cumplimiento GDPR",
    "ai_guardrails": "Guardrails de Seguridad IA",
    "workspace_documents": "Workspace de Documentos del Usuario",
    "multi_agent_system": "Sistema Multi-Agente IA",
    "semantic_cache": "Cache Semantico (Optimizacion Costes)",
    "deduction_optimizer": "Optimizador de Deducciones (Motor)",
}

AEAT_INTEGRATION_INFO = {
    "colaborador_social": {
        "description": "Estatus oficial de la AEAT que permite presentar declaraciones en nombre de terceros",
        "requirements": [
            "Firmar Convenio de Colaboracion Social con la AEAT",
            "Ser entidad juridica (empresa/asociacion/colegio profesional)",
            "Obtener certificado electronico de persona juridica o sello de entidad",
            "Implementar servicios web SOAP/XML (NO REST API)",
            "Pasar validacion tecnica en entorno de pre-produccion (preportal.aeat.es)",
        ],
        "contact": "comunicacion.sepri@correo.aeat.es",
        "developer_portal": "https://www.agenciatributaria.es/AEAT.desarrolladores/",
        "protocol": "SOAP/XML con certificados digitales (NO REST API moderna)",
        "who_has_it": ["TaxDown", "Declarando", "Taxfix", "Xolo", "Gestorias tradicionales"],
    },
    "clave_pin": {
        "description": "Sistema de autenticacion de la AEAT para ciudadanos",
        "usage": "Permite acceder a datos fiscales del contribuyente con su autorizacion",
        "alternatives": ["Certificado digital", "DNI electronico", "Numero de referencia"],
    },
    "third_party_apis": {
        "apimpuestos": {
            "url": "https://apimpuestos.es",
            "description": "API white-label para presentacion fiscal a AEAT y Registro Mercantil",
        },
        "aeat_web_services_oss": {
            "url": "https://github.com/initios/aeat-web-services",
            "description": "Libreria Python open-source para servicios web SOAP de AEAT",
        },
    },
}


# ─── Tool Definitions (OpenAI Function Calling schemas) ───────────────────

COMPARE_FEATURES_TOOL = {
    "type": "function",
    "function": {
        "name": "compare_features",
        "description": "Compara las funcionalidades de Impuestify con un competidor especifico del mercado fiscal espanol. Devuelve una tabla detallada de funcionalidades con ventajas y desventajas.",
        "parameters": {
            "type": "object",
            "properties": {
                "competitor": {
                    "type": "string",
                    "description": "Nombre del competidor a comparar (taxdown, declarando, taxfix, xolo)",
                    "enum": ["taxdown", "declarando", "taxfix", "xolo"],
                },
                "category": {
                    "type": "string",
                    "description": "Categoria especifica a comparar (optional). Si no se especifica, compara todas.",
                    "enum": ["ai_technology", "tax_features", "user_experience", "business_model", "all"],
                },
            },
            "required": ["competitor"],
        },
    },
}

ANALYZE_GAPS_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_gaps",
        "description": "Identifica los huecos funcionales de Impuestify respecto al mercado y los huecos que Impuestify llena que los competidores no cubren. Incluye prioridad y dificultad de implementacion.",
        "parameters": {
            "type": "object",
            "properties": {
                "focus": {
                    "type": "string",
                    "description": "Enfoque del analisis: 'our_gaps' (lo que nos falta), 'our_advantages' (lo que solo nosotros tenemos), 'all' (ambos)",
                    "enum": ["our_gaps", "our_advantages", "all"],
                },
            },
            "required": ["focus"],
        },
    },
}

SUGGEST_IMPROVEMENTS_TOOL = {
    "type": "function",
    "function": {
        "name": "suggest_improvements",
        "description": "Sugiere mejoras concretas para Impuestify con prioridad, impacto estimado, dificultad tecnica, y si el competidor lo tiene.",
        "parameters": {
            "type": "object",
            "properties": {
                "area": {
                    "type": "string",
                    "description": "Area de mejora a explorar",
                    "enum": ["ai_capabilities", "tax_features", "user_experience", "business_growth", "aeat_integration", "all"],
                },
                "max_suggestions": {
                    "type": "integer",
                    "description": "Numero maximo de sugerencias (default: 10)",
                },
            },
            "required": ["area"],
        },
    },
}

MARKET_POSITION_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_market_position",
        "description": "Analiza la posicion de Impuestify en el mercado fiscal espanol. Incluye analisis DAFO, posicionamiento, y estrategia recomendada.",
        "parameters": {
            "type": "object",
            "properties": {
                "analysis_type": {
                    "type": "string",
                    "description": "Tipo de analisis estrategico a realizar",
                    "enum": ["swot", "positioning", "pricing_strategy", "go_to_market", "all"],
                },
            },
            "required": ["analysis_type"],
        },
    },
}

AEAT_INTEGRATION_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_aeat_integration",
        "description": "Analiza las opciones de integracion con la AEAT: que es el estatus de Colaborador Social, como conseguirlo, alternativas tecnicas, y roadmap sugerido.",
        "parameters": {
            "type": "object",
            "properties": {
                "aspect": {
                    "type": "string",
                    "description": "Aspecto de la integracion AEAT a analizar",
                    "enum": ["colaborador_social", "technical_requirements", "alternatives", "roadmap", "all"],
                },
            },
            "required": ["aspect"],
        },
    },
}

# All competitor analysis tools
COMPETITOR_TOOLS = [
    COMPARE_FEATURES_TOOL,
    ANALYZE_GAPS_TOOL,
    SUGGEST_IMPROVEMENTS_TOOL,
    MARKET_POSITION_TOOL,
    AEAT_INTEGRATION_TOOL,
]


# ─── Tool Executor Functions ──────────────────────────────────────────────

async def compare_features_tool(competitor: str, category: str = "all") -> Dict[str, Any]:
    """Compare Impuestify features with a specific competitor."""
    comp_key = competitor.lower().replace(" ", "")
    if comp_key not in COMPETITORS:
        return {"success": False, "error": f"Competitor '{competitor}' not found. Available: {list(COMPETITORS.keys())}"}

    comp = COMPETITORS[comp_key]
    comp_features = comp["features"]

    # Build comparison
    categories = {
        "ai_technology": ["ai_chatbot", "rag_documentation", "multi_agent_system", "semantic_cache", "ai_guardrails"],
        "tax_features": ["irpf_filing", "quarterly_filing", "irpf_calculator", "autonomos_quotas", "payslip_analysis", "notification_analysis", "deduction_optimizer"],
        "user_experience": ["mobile_app", "workspace_documents", "invoicing", "expense_tracking", "open_banking", "human_advisors"],
        "business_model": ["b2b_enterprise", "gdpr_compliance", "aeat_data_import", "aeat_submission"],
    }

    if category != "all" and category in categories:
        selected_features = categories[category]
    else:
        selected_features = list(FEATURE_LABELS.keys())

    comparison = []
    impuestify_wins = 0
    competitor_wins = 0
    ties = 0

    for feat in selected_features:
        imp_has = IMPUESTIFY_FEATURES.get(feat, False)
        comp_has = comp_features.get(feat, False)
        label = FEATURE_LABELS.get(feat, feat)

        if imp_has and not comp_has:
            winner = "Impuestify"
            impuestify_wins += 1
        elif comp_has and not imp_has:
            winner = comp["name"]
            competitor_wins += 1
        elif imp_has and comp_has:
            winner = "Ambos"
            ties += 1
        else:
            winner = "Ninguno"

        comparison.append({
            "feature": label,
            "impuestify": imp_has,
            "competitor": comp_has,
            "winner": winner,
        })

    formatted = f"## Comparativa: Impuestify vs {comp['name']}\n\n"
    formatted += f"| Funcionalidad | Impuestify | {comp['name']} | Ventaja |\n"
    formatted += "|---|---|---|---|\n"

    for c in comparison:
        imp_icon = "Si" if c["impuestify"] else "No"
        comp_icon = "Si" if c["competitor"] else "No"
        formatted += f"| {c['feature']} | {imp_icon} | {comp_icon} | {c['winner']} |\n"

    formatted += f"\n**Resumen:** Impuestify gana en {impuestify_wins} features, "
    formatted += f"{comp['name']} gana en {competitor_wins}, empate en {ties}.\n\n"

    formatted += f"### Fortalezas de {comp['name']}:\n"
    for s in comp["strengths"]:
        formatted += f"- {s}\n"

    formatted += f"\n### Debilidades de {comp['name']}:\n"
    for w in comp["weaknesses"]:
        formatted += f"- {w}\n"

    formatted += f"\n### Datos clave de {comp['name']}:\n"
    formatted += f"- Fundado: {comp.get('founded', 'N/A')}\n"
    formatted += f"- Usuarios: {comp.get('users', 'N/A')}\n"
    formatted += f"- Financiacion: {comp.get('funding', 'N/A')}\n"
    formatted += f"- Estatus AEAT: {comp.get('aeat_status', 'N/A')}\n"

    if "pricing" in comp:
        formatted += f"\n### Precios de {comp['name']}:\n"
        for plan, details in comp["pricing"].items():
            price = details.get("price", details.get("price_monthly", "N/A"))
            period = "/mes" if "price_monthly" in details else " (pago unico)"
            formatted += f"- **{plan.title()}**: {price} EUR{period}\n"
            for f in details.get("features", []):
                formatted += f"  - {f}\n"

    return {
        "success": True,
        "formatted_response": formatted,
        "comparison": comparison,
        "score": {
            "impuestify_wins": impuestify_wins,
            "competitor_wins": competitor_wins,
            "ties": ties,
        },
        "competitor_info": {
            "name": comp["name"],
            "users": comp.get("users"),
            "funding": comp.get("funding"),
        },
    }


async def analyze_gaps_tool(focus: str = "all") -> Dict[str, Any]:
    """Analyze feature gaps and advantages."""
    our_gaps = []
    our_advantages = []

    # Features we DON'T have that at least one competitor does
    for feat, label in FEATURE_LABELS.items():
        imp_has = IMPUESTIFY_FEATURES.get(feat, False)
        competitors_with = []
        for comp_key, comp in COMPETITORS.items():
            if comp["features"].get(feat, False):
                competitors_with.append(comp["name"])

        if not imp_has and competitors_with:
            difficulty = _estimate_difficulty(feat)
            impact = _estimate_impact(feat)
            our_gaps.append({
                "feature": label,
                "key": feat,
                "competitors_with_it": competitors_with,
                "difficulty": difficulty,
                "impact": impact,
                "priority": _calculate_priority(impact, difficulty),
            })

        if imp_has and not competitors_with:
            our_advantages.append({
                "feature": label,
                "key": feat,
                "unique": True,
                "competitive_moat": _estimate_moat(feat),
            })
        elif imp_has and len(competitors_with) < len(COMPETITORS):
            missing_from = [c["name"] for k, c in COMPETITORS.items() if not c["features"].get(feat, False)]
            if missing_from:
                our_advantages.append({
                    "feature": label,
                    "key": feat,
                    "unique": False,
                    "missing_from": missing_from,
                    "competitive_moat": _estimate_moat(feat),
                })

    formatted = "## Analisis de Brechas Competitivas\n\n"

    if focus in ("our_gaps", "all"):
        # Sort gaps by priority
        our_gaps.sort(key=lambda x: {"critica": 0, "alta": 1, "media": 2, "baja": 3}.get(x["priority"], 4))

        formatted += "### Lo que nos FALTA (Gaps)\n\n"
        formatted += "| Funcionalidad | Quien lo tiene | Impacto | Dificultad | Prioridad |\n"
        formatted += "|---|---|---|---|---|\n"
        for gap in our_gaps:
            comps = ", ".join(gap["competitors_with_it"])
            formatted += f"| {gap['feature']} | {comps} | {gap['impact']} | {gap['difficulty']} | {gap['priority'].upper()} |\n"

    if focus in ("our_advantages", "all"):
        formatted += "\n### Lo que SOLO nosotros tenemos (Ventajas)\n\n"
        formatted += "| Funcionalidad | Exclusivo | Foso Competitivo | No lo tiene |\n"
        formatted += "|---|---|---|---|\n"
        for adv in our_advantages:
            exclusive = "UNICO" if adv["unique"] else "Parcial"
            missing = ", ".join(adv.get("missing_from", ["Ninguno"]))
            formatted += f"| {adv['feature']} | {exclusive} | {adv['competitive_moat']} | {missing} |\n"

    formatted += "\n### Resumen Estrategico\n\n"
    formatted += f"- **Gaps criticos/altos**: {sum(1 for g in our_gaps if g['priority'] in ('critica', 'alta'))}\n"
    formatted += f"- **Ventajas unicas**: {sum(1 for a in our_advantages if a['unique'])}\n"
    formatted += f"- **Ventajas parciales**: {sum(1 for a in our_advantages if not a['unique'])}\n"

    return {
        "success": True,
        "formatted_response": formatted,
        "gaps": our_gaps if focus in ("our_gaps", "all") else [],
        "advantages": our_advantages if focus in ("our_advantages", "all") else [],
    }


async def suggest_improvements_tool(area: str = "all", max_suggestions: int = 10) -> Dict[str, Any]:
    """Suggest specific improvements for Impuestify."""
    suggestions = _get_improvement_suggestions()

    area_mapping = {
        "ai_capabilities": ["ai_chatbot_upgrade", "deduction_engine", "predictive_tax", "multi_language"],
        "tax_features": ["quarterly_filing", "deduction_optimizer", "tax_calendar", "modelo_720"],
        "user_experience": ["mobile_app", "onboarding_wizard", "dashboard_analytics", "dark_mode"],
        "business_growth": ["b2b_api", "affiliate_program", "freemium_plus", "partnerships"],
        "aeat_integration": ["colaborador_social", "clave_import", "xml_submission", "veri_factu"],
    }

    if area != "all" and area in area_mapping:
        filtered = [s for s in suggestions if s["id"] in area_mapping[area]]
    else:
        filtered = suggestions

    filtered = filtered[:max_suggestions]

    formatted = f"## Sugerencias de Mejora para Impuestify\n\n"
    formatted += f"*Area: {area}*\n\n"

    for i, s in enumerate(filtered, 1):
        formatted += f"### {i}. {s['title']}\n"
        formatted += f"- **Descripcion**: {s['description']}\n"
        formatted += f"- **Impacto**: {s['impact']} | **Dificultad**: {s['difficulty']} | **Prioridad**: {s['priority'].upper()}\n"
        formatted += f"- **Tiempo estimado**: {s['estimated_time']}\n"
        formatted += f"- **Competidores que lo tienen**: {', '.join(s['competitors_with_it']) or 'Ninguno'}\n"
        if s.get("technical_notes"):
            formatted += f"- **Notas tecnicas**: {s['technical_notes']}\n"
        formatted += "\n"

    return {
        "success": True,
        "formatted_response": formatted,
        "suggestions": filtered,
        "total_available": len(suggestions),
    }


async def analyze_market_position_tool(analysis_type: str = "all") -> Dict[str, Any]:
    """Analyze Impuestify's market position."""
    result = {}
    formatted = "## Analisis de Posicion de Mercado - Impuestify\n\n"

    if analysis_type in ("swot", "all"):
        swot = {
            "strengths": IMPUESTIFY_STRENGTHS,
            "weaknesses": IMPUESTIFY_WEAKNESSES,
            "opportunities": [
                "Mercado de 22M declarantes IRPF en Espana (solo TaxDown tiene 1M)",
                "Creciente demanda de herramientas fiscales digitales post-COVID",
                "IA generativa aun no explotada a fondo por ningun competidor",
                "Autonomos (3.3M en Espana) mal servidos por TaxDown",
                "B2B: bancos y fintechs buscan soluciones de tax advisory embebidas",
                "AEAT modernizando sistemas (VeriFactu, factura electronica)",
                "Temporada de Renta (abril-junio) como ventana de adquisicion masiva",
                "Posibilidad de white-label AI fiscal para gestorias tradicionales",
            ],
            "threats": [
                "TaxDown con 29.7M de financiacion y 200+ empleados",
                "AEAT mejorando Renta WEB y su propio asistente virtual 'Informa'",
                "Barreras regulatorias para la presentacion telematica (Colaborador Social)",
                "Competidores establecidos con estatus AEAT y partnerships bancarios",
                "Riesgo reputacional si la IA comete errores fiscales",
                "Cambios regulatorios frecuentes requieren actualizacion constante",
                "OpenAI dependency (costes, latencia, disponibilidad)",
            ],
        }
        result["swot"] = swot

        formatted += "### Analisis DAFO\n\n"
        formatted += "#### Fortalezas\n"
        for s in swot["strengths"]:
            formatted += f"- {s}\n"
        formatted += "\n#### Debilidades\n"
        for w in swot["weaknesses"]:
            formatted += f"- {w}\n"
        formatted += "\n#### Oportunidades\n"
        for o in swot["opportunities"]:
            formatted += f"- {o}\n"
        formatted += "\n#### Amenazas\n"
        for t in swot["threats"]:
            formatted += f"- {t}\n"

    if analysis_type in ("positioning", "all"):
        positioning = {
            "current_position": "AI-first free tax advisor (niche player)",
            "target_position": "The intelligent tax companion for Spanish taxpayers",
            "differentiation_axes": [
                {"axis": "Tecnologia IA", "impuestify": "10/10", "taxdown": "4/10", "declarando": "1/10"},
                {"axis": "Cobertura Fiscal", "impuestify": "5/10", "taxdown": "8/10", "declarando": "9/10"},
                {"axis": "Precio/Valor", "impuestify": "9/10 (gratis)", "taxdown": "8/10", "declarando": "5/10"},
                {"axis": "Confianza/Marca", "impuestify": "2/10", "taxdown": "9/10", "declarando": "6/10"},
                {"axis": "AEAT Integration", "impuestify": "1/10", "taxdown": "9/10", "declarando": "8/10"},
            ],
            "recommended_tagline": "Tu asesor fiscal inteligente. Gratis. 24/7. Sin compromiso.",
        }
        result["positioning"] = positioning

        formatted += "\n### Posicionamiento Competitivo\n\n"
        formatted += f"- **Posicion actual**: {positioning['current_position']}\n"
        formatted += f"- **Posicion objetivo**: {positioning['target_position']}\n"
        formatted += f"- **Tagline recomendado**: *{positioning['recommended_tagline']}*\n\n"

        formatted += "| Eje | Impuestify | TaxDown | Declarando |\n"
        formatted += "|---|---|---|---|\n"
        for d in positioning["differentiation_axes"]:
            formatted += f"| {d['axis']} | {d['impuestify']} | {d['taxdown']} | {d['declarando']} |\n"

    if analysis_type in ("pricing_strategy", "all"):
        pricing = {
            "current": "Gratuito (sin modelo de monetizacion definido)",
            "recommended_tiers": [
                {"tier": "Free", "price": "0 EUR", "features": "Chat IA ilimitado, IRPF simulator, cuotas autonomos, perfil fiscal"},
                {"tier": "Pro", "price": "9.99 EUR/mes", "features": "Workspace documentos, analisis nominas, notificaciones AEAT, exportacion datos"},
                {"tier": "Autonomo", "price": "19.99 EUR/mes", "features": "Pro + Modelo 303/130, calendario fiscal, alertas trimestrales"},
                {"tier": "Enterprise", "price": "Custom", "features": "API white-label, integracion SSO, soporte dedicado"},
            ],
            "competitive_advantage": "Significativamente mas barato que Declarando (70-100 EUR/mes) y comparable a TaxDown Pro (35 EUR anuales) pero con IA superior",
        }
        result["pricing"] = pricing

        formatted += "\n### Estrategia de Precios Recomendada\n\n"
        formatted += f"**Actual**: {pricing['current']}\n\n"
        formatted += "| Tier | Precio | Features Clave |\n"
        formatted += "|---|---|---|\n"
        for t in pricing["recommended_tiers"]:
            formatted += f"| {t['tier']} | {t['price']} | {t['features']} |\n"
        formatted += f"\n*{pricing['competitive_advantage']}*\n"

    if analysis_type in ("go_to_market", "all"):
        gtm = {
            "phase_1_now": {
                "name": "AI Tax Advisor (Q1-Q2 2026)",
                "strategy": "Posicionarse como el mejor chatbot fiscal gratuito de Espana",
                "actions": [
                    "Lanzar landing page optimizada para SEO ('calculadora IRPF gratis', 'asesor fiscal IA')",
                    "Campana en redes durante temporada Renta (abril-junio)",
                    "Content marketing: blog con guias fiscales + herramientas gratuitas",
                    "Integracion con foros de autonomos (infoautonomos, autonomosyemprendedores)",
                ],
            },
            "phase_2_growth": {
                "name": "Platform Expansion (Q3-Q4 2026)",
                "strategy": "Anadir funcionalidades de pago y monetizar",
                "actions": [
                    "Lanzar tier Pro con workspace y analisis de nominas",
                    "App movil (React Native para iOS/Android)",
                    "Explorar partnership con neobancos (Revolut, N26) para embeber chatbot",
                    "Iniciar tramites de Colaborador Social con AEAT",
                ],
            },
            "phase_3_scale": {
                "name": "Market Leader (2027)",
                "strategy": "Competir directamente con TaxDown en funcionalidad",
                "actions": [
                    "Integracion AEAT completa (Colaborador Social)",
                    "Motor de optimizacion de deducciones (competir con Rita)",
                    "B2B API para gestorias y empresas",
                    "Expansion a otros mercados (Portugal, Latinoamerica)",
                ],
            },
        }
        result["go_to_market"] = gtm

        formatted += "\n### Estrategia Go-to-Market\n\n"
        for phase_key in ["phase_1_now", "phase_2_growth", "phase_3_scale"]:
            phase = gtm[phase_key]
            formatted += f"#### {phase['name']}\n"
            formatted += f"*{phase['strategy']}*\n"
            for a in phase["actions"]:
                formatted += f"- {a}\n"
            formatted += "\n"

    return {
        "success": True,
        "formatted_response": formatted,
        "analysis": result,
    }


async def analyze_aeat_integration_tool(aspect: str = "all") -> Dict[str, Any]:
    """Analyze AEAT integration options."""
    formatted = "## Analisis de Integracion con AEAT\n\n"
    result = {}

    info = AEAT_INTEGRATION_INFO

    if aspect in ("colaborador_social", "all"):
        cs = info["colaborador_social"]
        formatted += "### 1. Colaborador Social - Que es y como conseguirlo\n\n"
        formatted += f"**Descripcion**: {cs['description']}\n\n"
        formatted += "**Requisitos**:\n"
        for req in cs["requirements"]:
            formatted += f"1. {req}\n"
        formatted += f"\n**Contacto**: {cs['contact']}\n"
        formatted += f"**Portal de desarrolladores**: {cs['developer_portal']}\n"
        formatted += f"**Protocolo**: {cs['protocol']}\n"
        formatted += f"**Quien lo tiene**: {', '.join(cs['who_has_it'])}\n\n"
        formatted += "**IMPORTANTE**: NO es una API REST moderna. Es SOAP/XML con certificados digitales. "
        formatted += "El proceso de certificacion puede tardar varios meses.\n"
        result["colaborador_social"] = cs

    if aspect in ("technical_requirements", "all"):
        formatted += "\n### 2. Requisitos Tecnicos\n\n"
        formatted += "Para implementar la integracion con AEAT se necesita:\n\n"
        formatted += "1. **Certificado electronico** de persona juridica (FNMT o similar)\n"
        formatted += "2. **Implementar servicios web SOAP** con las especificaciones de AEAT:\n"
        formatted += "   - Esquemas XML para cada modelo tributario\n"
        formatted += "   - Firma digital XML (XMLDSig)\n"
        formatted += "   - Comunicacion HTTPS con certificado cliente\n"
        formatted += "3. **Entorno de pre-produccion**: preportal.aeat.es para tests\n"
        formatted += "4. **Validacion tecnica**: AEAT valida la implementacion antes de aprobar\n\n"
        formatted += "**Libreria Python disponible**: `aeat-web-services` (GitHub/initios) - "
        formatted += "implementacion open-source de los servicios SOAP de AEAT\n\n"
        formatted += "**Alternativa comercial**: APImpuestos (apimpuestos.es) - "
        formatted += "API white-label que abstrae la complejidad de AEAT\n"

    if aspect in ("alternatives", "all"):
        formatted += "\n### 3. Alternativas a Corto Plazo (sin Colaborador Social)\n\n"
        formatted += "| Alternativa | Viabilidad | Esfuerzo | Beneficio |\n"
        formatted += "|---|---|---|---|\n"
        formatted += "| APImpuestos (white-label) | Alta | Medio | Presentacion delegada sin ser Colaborador |\n"
        formatted += "| Export borrador pre-rellenado | Alta | Bajo | El usuario descarga y sube a Renta WEB |\n"
        formatted += "| Guia paso-a-paso con screenshots | Alta | Bajo | Tutorial interactivo para presentar en AEAT |\n"
        formatted += "| Partnership con gestoria digital | Media | Medio | Derivar presentacion a partner certificado |\n"
        formatted += "| aeat-web-services (OSS) | Media | Alto | Integracion directa pero requiere certificacion |\n"

    if aspect in ("roadmap", "all"):
        formatted += "\n### 4. Roadmap Sugerido de Integracion AEAT\n\n"
        formatted += "```\n"
        formatted += "FASE 1 (Ahora): Export borrador pre-rellenado\n"
        formatted += "  - Generar PDF/JSON con datos calculados por Impuestify\n"
        formatted += "  - El usuario copia datos a Renta WEB manualmente\n"
        formatted += "  - Esfuerzo: 2-4 semanas\n\n"
        formatted += "FASE 2 (Q2 2026): Guia interactiva de presentacion\n"
        formatted += "  - Tutorial paso-a-paso con screenshots de Renta WEB\n"
        formatted += "  - Pre-relleno de campos con datos del perfil fiscal\n"
        formatted += "  - Esfuerzo: 2-3 semanas\n\n"
        formatted += "FASE 3 (Q3 2026): Explorar APImpuestos\n"
        formatted += "  - Contactar apimpuestos.es para API comercial\n"
        formatted += "  - Evaluar costes y viabilidad tecnica\n"
        formatted += "  - Esfuerzo: 1-2 meses (incluye integracion)\n\n"
        formatted += "FASE 4 (Q4 2026-Q1 2027): Colaborador Social\n"
        formatted += "  - Iniciar tramites legales con AEAT\n"
        formatted += "  - Implementar SOAP/XML con aeat-web-services\n"
        formatted += "  - Validacion en pre-produccion\n"
        formatted += "  - Esfuerzo: 3-6 meses\n"
        formatted += "```\n"

    return {
        "success": True,
        "formatted_response": formatted,
        "aeat_info": result if result else info,
    }


# ─── Helper Functions ─────────────────────────────────────────────────────

def _estimate_difficulty(feature_key: str) -> str:
    """Estimate implementation difficulty for a feature."""
    difficulty_map = {
        "irpf_filing": "alta",
        "quarterly_filing": "alta",
        "aeat_data_import": "muy alta",
        "aeat_submission": "muy alta",
        "invoicing": "media",
        "expense_tracking": "media",
        "open_banking": "alta",
        "human_advisors": "alta (contratacion)",
        "mobile_app": "media-alta",
        "b2b_enterprise": "media",
        "deduction_optimizer": "alta",
    }
    return difficulty_map.get(feature_key, "media")


def _estimate_impact(feature_key: str) -> str:
    """Estimate business impact of implementing a feature."""
    impact_map = {
        "irpf_filing": "muy alto",
        "quarterly_filing": "alto",
        "aeat_data_import": "muy alto",
        "aeat_submission": "muy alto",
        "invoicing": "alto",
        "expense_tracking": "medio",
        "open_banking": "medio",
        "human_advisors": "alto",
        "mobile_app": "alto",
        "b2b_enterprise": "alto",
        "deduction_optimizer": "muy alto",
    }
    return impact_map.get(feature_key, "medio")


def _calculate_priority(impact: str, difficulty: str) -> str:
    """Calculate priority based on impact and difficulty."""
    impact_score = {"muy alto": 4, "alto": 3, "medio": 2, "bajo": 1}.get(impact, 2)
    diff_score = {"baja": 4, "media": 3, "media-alta": 2, "alta": 1, "muy alta": 0, "alta (contratacion)": 1}.get(difficulty, 2)
    total = impact_score + diff_score
    if total >= 7:
        return "critica"
    elif total >= 5:
        return "alta"
    elif total >= 3:
        return "media"
    return "baja"


def _estimate_moat(feature_key: str) -> str:
    """Estimate competitive moat strength."""
    moat_map = {
        "ai_chatbot": "Alto (requiere RAG + multi-agent + fine-tuning)",
        "rag_documentation": "Muy alto (394+ PDFs procesados, pipeline complejo)",
        "multi_agent_system": "Muy alto (arquitectura unica en el mercado)",
        "semantic_cache": "Medio (implementable por competidores con recursos)",
        "ai_guardrails": "Alto (Llama Guard + prompt injection + PII)",
        "payslip_analysis": "Medio-alto (extraction pipeline unico)",
        "notification_analysis": "Medio (replicable con LLMs)",
        "workspace_documents": "Medio (funcionalidad estandar)",
        "irpf_calculator": "Bajo (replicable)",
        "autonomos_quotas": "Bajo (replicable)",
        "gdpr_compliance": "Bajo (requerimiento legal)",
    }
    return moat_map.get(feature_key, "Medio")


def _get_improvement_suggestions():
    """Get prioritized improvement suggestions."""
    return [
        {
            "id": "deduction_engine",
            "title": "Motor de Optimizacion de Deducciones",
            "description": "Crear un motor que analice el perfil fiscal del usuario y sugiera las 250+ deducciones estatales y autonomicas aplicables. Similar al motor 'Rita' de TaxDown.",
            "impact": "muy alto",
            "difficulty": "alta",
            "priority": "critica",
            "estimated_time": "2-3 meses",
            "competitors_with_it": ["TaxDown (Rita)", "Declarando", "Taxfix"],
            "technical_notes": "Ya tenemos los PDFs de deducciones autonomicas. Requiere parser de requisitos y matching con perfil fiscal.",
        },
        {
            "id": "mobile_app",
            "title": "App Movil (React Native)",
            "description": "Crear app movil para iOS y Android. El frontend React existente facilita la migracion a React Native.",
            "impact": "alto",
            "difficulty": "media-alta",
            "priority": "alta",
            "estimated_time": "2-3 meses",
            "competitors_with_it": ["TaxDown", "Declarando", "Taxfix", "Xolo"],
            "technical_notes": "React Native reutiliza logica de hooks. SSE streaming requiere adaptacion nativa.",
        },
        {
            "id": "colaborador_social",
            "title": "Estatus Colaborador Social AEAT",
            "description": "Iniciar tramites para obtener el estatus de Colaborador Social, que permite presentar declaraciones en nombre de usuarios.",
            "impact": "muy alto",
            "difficulty": "muy alta",
            "priority": "alta",
            "estimated_time": "3-6 meses (tramites legales + implementacion tecnica)",
            "competitors_with_it": ["TaxDown", "Declarando", "Taxfix", "Xolo"],
            "technical_notes": "Requiere SOAP/XML, certificado electronico, y validacion en pre-produccion AEAT.",
        },
        {
            "id": "clave_import",
            "title": "Importacion de Datos via Cl@ve",
            "description": "Permitir a los usuarios importar sus datos fiscales directamente de AEAT usando Cl@ve PIN o certificado digital.",
            "impact": "muy alto",
            "difficulty": "muy alta",
            "priority": "alta",
            "estimated_time": "3-4 meses",
            "competitors_with_it": ["TaxDown", "Declarando", "Taxfix", "Xolo"],
            "technical_notes": "Requiere estatus Colaborador Social o partnership con empresa que lo tenga.",
        },
        {
            "id": "ai_chatbot_upgrade",
            "title": "Mejora del Chatbot: Proactividad y Seguimiento",
            "description": "Hacer que el chatbot sea proactivo: recuerde plazos del usuario, sugiera acciones fiscales segun epoca del ano, envie alertas de cambios normativos.",
            "impact": "alto",
            "difficulty": "media",
            "priority": "alta",
            "estimated_time": "3-4 semanas",
            "competitors_with_it": [],
            "technical_notes": "Aprovechar user_memory_service + calendario fiscal + notificaciones push.",
        },
        {
            "id": "b2b_api",
            "title": "API White-Label para B2B",
            "description": "Ofrecer el chatbot fiscal como API embebible para bancos, fintechs y gestorias. Similar a TaxDown Partners.",
            "impact": "alto",
            "difficulty": "media",
            "priority": "alta",
            "estimated_time": "1-2 meses",
            "competitors_with_it": ["TaxDown (Partners)"],
            "technical_notes": "El backend FastAPI ya es una API. Requiere multi-tenancy, API keys, y dashboard de uso.",
        },
        {
            "id": "quarterly_filing",
            "title": "Soporte Completo Declaraciones Trimestrales",
            "description": "Ampliar los calculadores 303/130 a un flujo completo: calculo + borrador + guia de presentacion.",
            "impact": "alto",
            "difficulty": "media",
            "priority": "alta",
            "estimated_time": "1-2 meses",
            "competitors_with_it": ["Declarando", "Taxfix", "Xolo"],
            "technical_notes": "Ya tenemos Modelo 303 y 130 tools. Falta flujo guiado y borrador pre-rellenado.",
        },
        {
            "id": "predictive_tax",
            "title": "Prediccion Fiscal Inteligente",
            "description": "Proyeccion de impuestos futuros basada en el patron de ingresos/gastos del usuario. 'En enero pagaras X de IVA si sigues asi'.",
            "impact": "alto",
            "difficulty": "media",
            "priority": "media",
            "estimated_time": "3-4 semanas",
            "competitors_with_it": [],
            "technical_notes": "Usar datos del workspace + perfil fiscal para proyecciones. Unico en el mercado.",
        },
        {
            "id": "onboarding_wizard",
            "title": "Asistente de Onboarding Fiscal",
            "description": "Wizard interactivo que en 5 minutos crea el perfil fiscal completo del usuario mediante preguntas guiadas.",
            "impact": "medio",
            "difficulty": "baja",
            "priority": "media",
            "estimated_time": "1-2 semanas",
            "competitors_with_it": ["TaxDown"],
            "technical_notes": "Formulario multi-paso en frontend que alimenta el perfil fiscal existente.",
        },
        {
            "id": "tax_calendar",
            "title": "Calendario Fiscal Personalizado",
            "description": "Calendario interactivo con fechas limite de declaraciones segun el perfil del usuario (asalariado vs autonomo).",
            "impact": "medio",
            "difficulty": "baja",
            "priority": "media",
            "estimated_time": "1-2 semanas",
            "competitors_with_it": ["Declarando"],
            "technical_notes": "Datos de calendario ya estan en workspace_agent. Falta componente frontend.",
        },
        {
            "id": "freemium_plus",
            "title": "Modelo Freemium Mejorado",
            "description": "Definir claramente el modelo freemium: chat gratuito ilimitado + features premium (workspace, nominas, notificaciones).",
            "impact": "alto",
            "difficulty": "baja",
            "priority": "alta",
            "estimated_time": "2-3 semanas",
            "competitors_with_it": ["TaxDown"],
            "technical_notes": "Implementar con sistema de suscripcion existente (Stripe) + middleware de acceso.",
        },
        {
            "id": "partnerships",
            "title": "Partnerships con Neobancos/Fintechs",
            "description": "Ofrecer Impuestify como beneficio embebido en apps de neobancos (Revolut, N26, Wise) como hace TaxDown con BBVA.",
            "impact": "muy alto",
            "difficulty": "alta",
            "priority": "alta",
            "estimated_time": "3-6 meses (comercial)",
            "competitors_with_it": ["TaxDown (BBVA, N26, Revolut)"],
            "technical_notes": "Requiere API white-label primero + equipo comercial.",
        },
        {
            "id": "veri_factu",
            "title": "Soporte VeriFactu (Factura Electronica)",
            "description": "Implementar el nuevo sistema VeriFactu de facturacion electronica obligatorio en Espana.",
            "impact": "alto",
            "difficulty": "alta",
            "priority": "media",
            "estimated_time": "2-3 meses",
            "competitors_with_it": ["Declarando"],
            "technical_notes": "Nuevo requerimiento legal. Primero requiere plataforma de facturacion.",
        },
    ]


# ─── Tool Executors Registry ──────────────────────────────────────────────

COMPETITOR_TOOL_EXECUTORS = {
    "compare_features": compare_features_tool,
    "analyze_gaps": analyze_gaps_tool,
    "suggest_improvements": suggest_improvements_tool,
    "analyze_market_position": analyze_market_position_tool,
    "analyze_aeat_integration": analyze_aeat_integration_tool,
}
