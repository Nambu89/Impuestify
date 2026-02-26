"""
Tools module for Impuestify agents.

Centralizes all available tools for function calling.
"""
from app.tools.irpf_calculator_tool import IRPF_CALCULATOR_TOOL, calculate_irpf_tool
from app.tools.irpf_simulator_tool import IRPF_SIMULATOR_TOOL, simulate_irpf_tool
from app.tools.autonomous_quota_tool import AUTONOMOUS_QUOTA_TOOL, calculate_autonomous_quota_tool
from app.tools.search_tool import SEARCH_TAX_REGULATIONS_TOOL, search_tax_regulations_tool
from app.tools.payslip_analysis_tool import PAYSLIP_ANALYSIS_TOOL, analyze_payslip_tool

# Registry of all available tools
# NOTE: search_tax_regulations is NOT included by default (RAG-first strategy)
# NOTE: calculate_irpf kept for backward compat; simulate_irpf is the enhanced version
ALL_TOOLS = [
	IRPF_SIMULATOR_TOOL,
	IRPF_CALCULATOR_TOOL,
	AUTONOMOUS_QUOTA_TOOL,
	# SEARCH_TAX_REGULATIONS_TOOL,  # ← REMOVED - Only add when explicitly needed
	PAYSLIP_ANALYSIS_TOOL,
]

# Registry of tool execution functions
TOOL_EXECUTORS = {
	"simulate_irpf": simulate_irpf_tool,
	"calculate_irpf": calculate_irpf_tool,
	"calculate_autonomous_quota": calculate_autonomous_quota_tool,
	"search_tax_regulations": search_tax_regulations_tool,
	"analyze_payslip": analyze_payslip_tool,
}

__all__ = [
	"ALL_TOOLS",
	"TOOL_EXECUTORS",
	"IRPF_SIMULATOR_TOOL",
	"IRPF_CALCULATOR_TOOL",
	"AUTONOMOUS_QUOTA_TOOL",
	"SEARCH_TAX_REGULATIONS_TOOL",
	"PAYSLIP_ANALYSIS_TOOL",
	"simulate_irpf_tool",
	"calculate_irpf_tool",
	"calculate_autonomous_quota_tool",
	"search_tax_regulations_tool",
	"analyze_payslip_tool",
]
