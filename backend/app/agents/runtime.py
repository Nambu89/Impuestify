"""
Agent Runtime for TaxIA

Orchestrates multiple agents using Microsoft Agent Framework.
Supports sequential, concurrent, and group chat patterns.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# Microsoft Agent Framework imports
try:
    from agent_framework import Runtime, AgentGroup
    from agent_framework.patterns import Sequential, Concurrent, GroupChat
    RUNTIME_AVAILABLE = True
except Exception:
    RUNTIME_AVAILABLE = False
    Runtime = None
    AgentGroup = None

from app.agents.tax_agent import TaxAgent, AgentResponse, get_tax_agent

logger = logging.getLogger(__name__)


@dataclass
class RuntimeResponse:
    """Response from agent runtime"""
    final_response: AgentResponse
    agent_responses: List[AgentResponse]
    pattern: str
    total_agents: int


class AgentRuntime:
    """
    Runtime for orchestrating TaxIA agents.
    
    Currently supports single agent (TaxAgent) with architecture
    ready for multi-agent expansion:
    
    Future agents:
    - DocumentAgent: Specialized in document analysis
    - CalculationAgent: Tax calculations
    - ComplianceAgent: Deadline and compliance checks
    """
    
    def __init__(self):
        """Initialize the agent runtime."""
        self._runtime = None
        self._agents: Dict[str, TaxAgent] = {}
        self._pattern = "single"
        
        self._initialize()
    
    def _initialize(self):
        """Initialize runtime with available agents."""
        # Register primary TaxAgent
        self._agents["tax"] = get_tax_agent()
        
        if RUNTIME_AVAILABLE:
            try:
                self._runtime = Runtime()
                # Register agents with framework runtime
                for name, agent in self._agents.items():
                    if agent._agent:
                        self._runtime.register(agent._agent)
                
                logger.info("AgentRuntime initialized with Microsoft Agent Framework")
            except Exception as e:
                logger.warning(f"Runtime initialization failed: {e}")
                self._runtime = None
        else:
            logger.info("AgentRuntime initialized in single-agent mode")
    
    def register_agent(self, name: str, agent: TaxAgent):
        """
        Register a new agent with the runtime.
        
        Args:
            name: Unique agent identifier
            agent: TaxAgent instance
        """
        self._agents[name] = agent
        
        if self._runtime and agent._agent:
            self._runtime.register(agent._agent)
        
        logger.info(f"Registered agent: {name}")
    
    async def run(
        self,
        query: str,
        context: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        agent_name: Optional[str] = None,
        pattern: str = "single"
    ) -> RuntimeResponse:
        """
        Run query through the agent runtime.
        
        Args:
            query: User's question
            context: RAG context
            sources: Source documents
            agent_name: Specific agent to use (None for default)
            pattern: Orchestration pattern ('single', 'sequential', 'concurrent')
            
        Returns:
            RuntimeResponse with agent outputs
        """
        self._pattern = pattern
        agent_responses = []
        
        if pattern == "single" or len(self._agents) == 1:
            # Single agent execution
            agent = self._agents.get(agent_name, self._agents.get("tax"))
            if agent:
                response = await agent.run(query, context, sources)
                agent_responses.append(response)
        
        elif pattern == "sequential" and RUNTIME_AVAILABLE and self._runtime:
            # Sequential execution through multiple agents
            for name, agent in self._agents.items():
                response = await agent.run(query, context, sources)
                agent_responses.append(response)
                # Each agent can refine based on previous responses
                context = f"{context or ''}\n\nRespuesta de {name}: {response.content}"
        
        elif pattern == "concurrent" and RUNTIME_AVAILABLE and self._runtime:
            # Concurrent execution - all agents run simultaneously
            import asyncio
            tasks = [
                agent.run(query, context, sources)
                for agent in self._agents.values()
            ]
            agent_responses = await asyncio.gather(*tasks)
        
        else:
            # Fallback to single agent
            agent = self._agents.get("tax")
            if agent:
                response = await agent.run(query, context, sources)
                agent_responses.append(response)
        
        # Return the last/final response as the main response
        final_response = agent_responses[-1] if agent_responses else AgentResponse(
            content="No se pudo procesar la consulta.",
            sources=[],
            metadata={},
            agent_name="unknown"
        )
        
        return RuntimeResponse(
            final_response=final_response,
            agent_responses=agent_responses,
            pattern=pattern,
            total_agents=len(self._agents)
        )
    
    def run_sync(
        self,
        query: str,
        context: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        agent_name: Optional[str] = None,
        pattern: str = "single"
    ) -> RuntimeResponse:
        """Synchronous version of run()."""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.run(query, context, sources, agent_name, pattern)
        )
    
    @property
    def available_agents(self) -> List[str]:
        """Get list of registered agent names."""
        return list(self._agents.keys())
    
    @property
    def is_multi_agent_ready(self) -> bool:
        """Check if runtime supports multi-agent patterns."""
        return RUNTIME_AVAILABLE and self._runtime is not None


# Global runtime instance
_agent_runtime: Optional[AgentRuntime] = None


def get_agent_runtime() -> AgentRuntime:
    """
    Get the global AgentRuntime instance.
    
    Returns:
        AgentRuntime instance
    """
    global _agent_runtime
    
    if _agent_runtime is None:
        _agent_runtime = AgentRuntime()
    
    return _agent_runtime
