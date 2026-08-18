"""Agents package — lazy imports to avoid loading heavy ML libraries at startup."""


def __getattr__(name: str):
    if name == "DataAgent":
        from .data_agent import DataAgent
        return DataAgent
    if name == "AnalysisAgent":
        from .analysis_agent import AnalysisAgent
        return AnalysisAgent
    if name == "OrchestratorAgent":
        from .orchestrator import OrchestratorAgent
        return OrchestratorAgent
    raise AttributeError(f"module 'backend.agents' has no attribute {name!r}")


__all__ = [
    "DataAgent",
    "AnalysisAgent",
    "OrchestratorAgent",
]
