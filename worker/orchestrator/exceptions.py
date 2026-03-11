"""Orchestrator exceptions."""


class OrchestratorError(Exception):
    """Base exception for orchestrator operations."""
    pass


class AgentExecutionError(OrchestratorError):
    """Agent execution failed."""
    pass


class ToolExecutionError(OrchestratorError):
    """Tool execution failed."""
    pass


class ModelError(OrchestratorError):
    """Model API call failed."""
    pass


class MaxIterationsError(OrchestratorError):
    """Agent exceeded maximum iterations."""
    pass
