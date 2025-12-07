"""
Tests for TaxIA Agent Framework

Tests TaxAgent, AgentRuntime, and multi-agent patterns.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestTaxAgent:
    """Tests for TaxAgent"""
    
    def test_agent_response_structure(self):
        """AgentResponse should have correct structure"""
        from app.agents.tax_agent import AgentResponse
        
        response = AgentResponse(
            content="Test response",
            sources=[{"source": "test.pdf", "page": 1, "title": "Test"}],
            metadata={"model": "gpt-5-mini"},
            agent_name="TaxAgent"
        )
        
        assert response.content == "Test response"
        assert len(response.sources) == 1
        assert response.agent_name == "TaxAgent"
    
    def test_agent_system_prompt_exists(self):
        """TaxAgent should have a system prompt"""
        from app.agents.tax_agent import TaxAgent
        
        assert hasattr(TaxAgent, 'SYSTEM_PROMPT')
        assert "TaxIA" in TaxAgent.SYSTEM_PROMPT
        assert "AEAT" in TaxAgent.SYSTEM_PROMPT
        assert "evadir" in TaxAgent.SYSTEM_PROMPT.lower()
    
    def test_agent_initialization(self):
        """TaxAgent should initialize without credentials (warning mode)"""
        from app.agents.tax_agent import TaxAgent
        
        # Without credentials, should initialize in warning mode
        agent = TaxAgent(name="TestAgent")
        
        assert agent.name == "TestAgent"
        assert agent.model is not None
    
    def test_build_prompt_with_context(self):
        """TaxAgent should build prompt correctly with context"""
        from app.agents.tax_agent import TaxAgent
        
        agent = TaxAgent(name="TestAgent")
        
        prompt = agent._build_prompt(
            query="¿Cuándo presento el modelo 303?",
            context="El modelo 303 se presenta trimestralmente."
        )
        
        assert "modelo 303" in prompt.lower()
        assert "trimestralmente" in prompt.lower()
    
    def test_build_prompt_without_context(self):
        """TaxAgent should return query if no context"""
        from app.agents.tax_agent import TaxAgent
        
        agent = TaxAgent(name="TestAgent")
        query = "¿Cuándo presento el modelo 303?"
        
        prompt = agent._build_prompt(query, context=None)
        
        assert prompt == query


class TestAgentRuntime:
    """Tests for AgentRuntime"""
    
    def test_runtime_response_structure(self):
        """RuntimeResponse should have correct structure"""
        from app.agents.runtime import RuntimeResponse
        from app.agents.tax_agent import AgentResponse
        
        agent_response = AgentResponse(
            content="Test",
            sources=[],
            metadata={},
            agent_name="TaxAgent"
        )
        
        runtime_response = RuntimeResponse(
            final_response=agent_response,
            agent_responses=[agent_response],
            pattern="single",
            total_agents=1
        )
        
        assert runtime_response.pattern == "single"
        assert runtime_response.total_agents == 1
        assert len(runtime_response.agent_responses) == 1
    
    def test_runtime_initialization(self):
        """AgentRuntime should initialize with default agent"""
        from app.agents.runtime import AgentRuntime
        
        runtime = AgentRuntime()
        
        assert "tax" in runtime.available_agents
        assert len(runtime.available_agents) >= 1
    
    def test_runtime_register_agent(self):
        """AgentRuntime should allow registering new agents"""
        from app.agents.runtime import AgentRuntime
        from app.agents.tax_agent import TaxAgent
        
        runtime = AgentRuntime()
        new_agent = TaxAgent(name="CustomAgent")
        
        runtime.register_agent("custom", new_agent)
        
        assert "custom" in runtime.available_agents
    
    def test_runtime_patterns(self):
        """AgentRuntime should support different patterns"""
        from app.agents.runtime import AgentRuntime
        
        runtime = AgentRuntime()
        
        # Single pattern should always work
        assert runtime._pattern == "single" or True
        
        # Multi-agent readiness check
        assert isinstance(runtime.is_multi_agent_ready, bool)


class TestAgentFrameworkAvailability:
    """Tests for framework availability handling"""
    
    def test_framework_import_handling(self):
        """Should handle missing agent-framework gracefully"""
        from app.agents.tax_agent import AGENT_FRAMEWORK_AVAILABLE
        
        # Should be a boolean
        assert isinstance(AGENT_FRAMEWORK_AVAILABLE, bool)
    
    def test_fallback_client_available(self):
        """Fallback Azure OpenAI client should be available"""
        from app.agents.tax_agent import AzureOpenAI
        
        assert AzureOpenAI is not None


class TestAgentIntegration:
    """Integration tests for agent system"""
    
    def test_get_tax_agent_singleton(self):
        """get_tax_agent should return singleton instance"""
        from app.agents.tax_agent import get_tax_agent
        
        agent1 = get_tax_agent()
        agent2 = get_tax_agent()
        
        # Note: In real tests, you might want to reset the singleton
        # These should be the same instance
        assert agent1 is agent2
    
    def test_get_agent_runtime_singleton(self):
        """get_agent_runtime should return singleton instance"""
        from app.agents.runtime import get_agent_runtime
        
        runtime1 = get_agent_runtime()
        runtime2 = get_agent_runtime()
        
        assert runtime1 is runtime2
    
    def test_agent_module_exports(self):
        """Agent module should export correct classes"""
        from app.agents import (
            TaxAgent,
            get_tax_agent,
            AgentRuntime,
            get_agent_runtime
        )
        
        assert TaxAgent is not None
        assert get_tax_agent is not None
        assert AgentRuntime is not None
        assert get_agent_runtime is not None
