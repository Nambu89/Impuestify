"""
Tools module for Impuestify agents.

Centralizes all available tools for function calling.
"""
from app.tools.irpf_calculator_tool import IRPF_CALCULATOR_TOOL, calculate_irpf_tool
from app.tools.autonomous_quota_tool import AUTONOMOUS_QUOTA_TOOL, calculate_autonomous_quota_tool
from app.tools.search_tool import SEARCH_TAX_REGULATIONS_TOOL, search_tax_regulations_tool
from app.tools.payslip_analysis_tool import PAYSLIP_ANALYSIS_TOOL, analyze_payslip_tool

# Registry of all available tools
ALL_TOOLS = [
	IRPF_CALCULATOR_TOOL,
	AUTONOMOUS_QUOTA_TOOL,
	SEARCH_TAX_REGULATIONS_TOOL,
	PAYSLIP_ANALYSIS_TOOL,  # NUEVO
]

# Registry of tool execution functions
TOOL_EXECUTORS = {
	"calculate_irpf": calculate_irpf_tool,
	"calculate_autonomous_quota": calculate_autonomous_quota_tool,
	"search_tax_regulations": search_tax_regulations_tool,
	"analyze_payslip": analyze_payslip_tool,  # NUEVO
}

__all__ = [
	"ALL_TOOLS",
	"TOOL_EXECUTORS",
	"IRPF_CALCULATOR_TOOL",
	"AUTONOMOUS_QUOTA_TOOL",
	"SEARCH_TAX_REGULATIONS_TOOL",
	"PAYSLIP_ANALYSIS_TOOL",
	"calculate_irpf_tool",
	"calculate_autonomous_quota_tool",
	"search_tax_regulations_tool",
	"analyze_payslip_tool",
]