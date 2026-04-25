"""
Abstract base class for all agents in the Trading Data Agent pipeline.

Every agent subclasses BaseAgent and implements validate_input()
and process(). The run() method handles the execution flow and
error capture — subclasses should not override it.

Usage:
    class IngestionAgent(BaseAgent):
        def validate_input(self, state):
            ...
        def process(self, state):
            ...

    agent = IngestionAgent("IngestionAgent", "Loads data files")
    state = agent.run(state)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from src.agents.state import TradingAgentState
from src.utils.logger import get_agent_logger


class BaseAgent(ABC):
    """
    Abstract base class defining the interface for all pipeline agents.

    Subclasses must implement validate_input() and process().
    The run() method orchestrates the call sequence with error handling.
    """

    def __init__(self, name: str, description: str) -> None:
        """
        Initialise the agent.

        :param: name: Agent identifier (e.g. "IngestionAgent").
        :param: description: Brief description of what this agent does.
        """
        self.name = name
        self.description = description
        self.logger = get_agent_logger(name)

    @abstractmethod
    def validate_input(self, state: TradingAgentState) -> TradingAgentState:
        """
        Check preconditions before processing.

        :Param: state: Current pipeline state.

        :Returns: The state dict (possibly with errors appended).

        Subclasses implement this to check that required fields exist.
        For example, CleaningAgent would verify state["raw_df"] is not None.
        """
        ...

    @abstractmethod
    def process(self, state: TradingAgentState) -> TradingAgentState:
        """
        Execute the agent's core logic.

        :Param: state: Current pipeline state (after validation).

        :Returns: The state dict with this agent's outputs added.
        """
        ...

    def run(self, state: TradingAgentState) -> TradingAgentState:
        """
        Execute the full agent pipeline: validate → process.

        This is the public API and should not override in subclasses.

        :Param: state: Current pipeline state.

        :Returns: Updated state dict.
        """
        try:
            self.logger.info(f"{self.name} starting")
            
            # Snapshot error count before validation
            error_count_before = len(state.get("errors", []))
            
            # Validate input
            state = self.validate_input(state)
            
            # Check if validation added errors
            error_count_after = len(state.get("errors", []))
            if error_count_after > error_count_before:
                self.logger.warning(f"{self.name} validation failed, skipping process")
                return state
            
            # Process
            state = self.process(state)
            
            self.logger.info(f"{self.name} completed")
            return state
            
        except Exception as e:
            error_msg = f"{self.name} failed with error: {str(e)}"
            self.logger.error(error_msg)
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(error_msg)
            return state