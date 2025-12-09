"""
Tools module for TaxIA agents.

Centralizes all available tools for function calling.
"""
from app.tools.irpf_calculator_tool import IRPF_CALCULATOR_TOOL, calculate_irpf_tool
from app.tools.autonomous_quota_tool import AUTONOMOUS_QUOTA_TOOL, calculate_autonomous_quota_tool

# Registry of all available tools
ALL_TOOLS = [
    IRPF_CALCULATOR_TOOL,
    AUTONOMOUS_QUOTA_TOOL,
]

# Registry of tool execution functions
TOOL_EXECUTORS = {
    "calculate_irpf": calculate_irpf_tool,
    "calculate_autonomous_quota": calculate_autonomous_quota_tool,
}

__all__ = [
    "ALL_TOOLS",
    "TOOL_EXECUTORS",
    "IRPF_CALCULATOR_TOOL",
    "AUTONOMOUS_QUOTA_TOOL",
    "calculate_irpf_tool",
    "calculate_autonomous_quota_tool",
]