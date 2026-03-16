"""
Tools module for Impuestify agents.

Centralizes all available tools for function calling.
"""
from app.tools.irpf_calculator_tool import IRPF_CALCULATOR_TOOL, calculate_irpf_tool
from app.tools.irpf_simulator_tool import IRPF_SIMULATOR_TOOL, simulate_irpf_tool
from app.tools.autonomous_quota_tool import AUTONOMOUS_QUOTA_TOOL, calculate_autonomous_quota_tool
from app.tools.search_tool import SEARCH_TAX_REGULATIONS_TOOL, search_tax_regulations_tool
from app.tools.payslip_analysis_tool import PAYSLIP_ANALYSIS_TOOL, analyze_payslip_tool
from app.tools.modelo_303_tool import MODELO_303_TOOL, calculate_modelo_303_tool
from app.tools.modelo_130_tool import MODELO_130_TOOL, calculate_modelo_130_tool
from app.tools.deduction_discovery_tool import DISCOVER_DEDUCTIONS_TOOL, discover_deductions_tool
from app.tools.isd_calculator_tool import ISD_CALCULATOR_TOOL, calculate_isd
from app.tools.modelo_ipsi_tool import MODELO_IPSI_TOOL, calculate_modelo_ipsi_tool
from app.tools.casilla_lookup_tool import CASILLA_LOOKUP_TOOL, lookup_casilla_tool
from app.tools.fiscal_profile_tool import UPDATE_FISCAL_PROFILE_TOOL, update_fiscal_profile_tool
from app.tools.crypto_gains_tool import CRYPTO_GAINS_TOOL, calculate_crypto_gains_tool
from app.tools.crypto_csv_tool import CRYPTO_CSV_TOOL, parse_crypto_csv_tool
from app.tools.iae_lookup_tool import IAE_LOOKUP_TOOL, lookup_iae
from app.tools.joint_comparison_tool import JOINT_COMPARISON_TOOL, compare_joint_individual_executor

# Registry of all available tools
# NOTE: search_tax_regulations is NOT included by default (RAG-first strategy)
# NOTE: calculate_irpf kept for backward compat; simulate_irpf is the enhanced version
ALL_TOOLS = [
	IRPF_SIMULATOR_TOOL,
	IRPF_CALCULATOR_TOOL,
	AUTONOMOUS_QUOTA_TOOL,
	# SEARCH_TAX_REGULATIONS_TOOL,  # ← REMOVED - Only add when explicitly needed
	PAYSLIP_ANALYSIS_TOOL,
	MODELO_303_TOOL,
	MODELO_130_TOOL,
	DISCOVER_DEDUCTIONS_TOOL,
	ISD_CALCULATOR_TOOL,
	MODELO_IPSI_TOOL,
	CASILLA_LOOKUP_TOOL,
	UPDATE_FISCAL_PROFILE_TOOL,
	CRYPTO_GAINS_TOOL,
	CRYPTO_CSV_TOOL,
	IAE_LOOKUP_TOOL,
	JOINT_COMPARISON_TOOL,
]

# Registry of tool execution functions
TOOL_EXECUTORS = {
	"simulate_irpf": simulate_irpf_tool,
	"calculate_irpf": calculate_irpf_tool,
	"calculate_autonomous_quota": calculate_autonomous_quota_tool,
	"search_tax_regulations": search_tax_regulations_tool,
	"analyze_payslip": analyze_payslip_tool,
	"calculate_modelo_303": calculate_modelo_303_tool,
	"calculate_modelo_130": calculate_modelo_130_tool,
	"discover_deductions": discover_deductions_tool,
	"calculate_isd": calculate_isd,
	"calculate_modelo_ipsi": calculate_modelo_ipsi_tool,
	"lookup_casilla": lookup_casilla_tool,
	"update_fiscal_profile": update_fiscal_profile_tool,
	"calculate_crypto_gains": calculate_crypto_gains_tool,
	"parse_crypto_csv": parse_crypto_csv_tool,
	"lookup_iae": lookup_iae,
	"compare_joint_individual": compare_joint_individual_executor,
}

__all__ = [
	"ALL_TOOLS",
	"TOOL_EXECUTORS",
	"IRPF_SIMULATOR_TOOL",
	"IRPF_CALCULATOR_TOOL",
	"AUTONOMOUS_QUOTA_TOOL",
	"SEARCH_TAX_REGULATIONS_TOOL",
	"PAYSLIP_ANALYSIS_TOOL",
	"MODELO_303_TOOL",
	"MODELO_130_TOOL",
	"DISCOVER_DEDUCTIONS_TOOL",
	"ISD_CALCULATOR_TOOL",
	"simulate_irpf_tool",
	"calculate_irpf_tool",
	"calculate_autonomous_quota_tool",
	"search_tax_regulations_tool",
	"analyze_payslip_tool",
	"calculate_modelo_303_tool",
	"calculate_modelo_130_tool",
	"discover_deductions_tool",
	"calculate_isd",
	"MODELO_IPSI_TOOL",
	"calculate_modelo_ipsi_tool",
	"CASILLA_LOOKUP_TOOL",
	"lookup_casilla_tool",
	"UPDATE_FISCAL_PROFILE_TOOL",
	"update_fiscal_profile_tool",
	"CRYPTO_GAINS_TOOL",
	"calculate_crypto_gains_tool",
	"CRYPTO_CSV_TOOL",
	"parse_crypto_csv_tool",
	"IAE_LOOKUP_TOOL",
	"lookup_iae",
	"JOINT_COMPARISON_TOOL",
	"compare_joint_individual_executor",
]
