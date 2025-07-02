from langchain_core.language_models import BaseLLM
from typing import Any, Dict


class BaseAgent:
    """
    Abstract base class for all agents in the multi-agent system.
    All agents must implement the run(inputs: dict) -> dict method.
    """

    def __init__(self, llm: BaseLLM):
        self.llm = llm

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Each agent must implement the run method.")
