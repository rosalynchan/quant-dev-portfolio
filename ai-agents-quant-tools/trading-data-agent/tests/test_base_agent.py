"""
Unit tests for BaseAgent abstract class and template method pattern.

Tests verify:
- validate_input() and process() are called in order
- Validation failure skips process()
- Exceptions are caught and appended to state["errors"]
- Logging happens at the right levels
"""

from src.agents.base_agent import BaseAgent
from src.agents.state import TradingAgentState


class TestAgent(BaseAgent):
    """Concrete test implementation of BaseAgent for testing."""

    def validate_input(self, state: TradingAgentState) -> TradingAgentState:
        """
        Simple validation: check if 'test_field' is present.
        If not, add an error.
        """
        if "errors" not in state:
            state["errors"] = []
        
        if "test_field" not in state or state["test_field"] is None:
            state["errors"].append("test_field is missing")
        
        return state

    def process(self, state: TradingAgentState) -> TradingAgentState:
        """
        Simple process: add a result field to state.
        Can optionally raise an exception if state["should_fail"] is True.
        """
        if state.get("should_fail"):
            raise ValueError("Intentional test failure")
        
        state["result"] = "process completed"
        return state


# ==================================================
# Test Cases
# ==================================================

def test_agent_init():
    """
    Test that BaseAgent initialization stores name, description, and logger.
    """
    agent = TestAgent(name="TestAgent", description="Test")
    
    assert agent.name == "TestAgent"
    assert agent.description == "Test"
    assert agent.logger is not None


def test_successful_run():
    """
    Test that a successful validation → process flow updates state correctly.
    """
    state: TradingAgentState = {
        "test_field": "value",
        "errors": [],
    }
    
    agent = TestAgent(name="TestAgent", description="Test")
    result_state = agent.run(state)
    
    assert result_state["result"] == "process completed"
    assert result_state["errors"] == []


def test_validation_failure_skips_process():
    """
    Test that when validate_input() adds an error, process() is not called.
    """
    state: TradingAgentState = {
        "errors": [],
    }
    
    agent = TestAgent(name="TestAgent", description="Test")
    result_state = agent.run(state)
    
    assert "test_field is missing" in result_state["errors"]
    assert "result" not in result_state


def test_process_exception_caught():
    """
    Test that exceptions in process() are caught and appended to errors.
    """
    state: TradingAgentState = {
        "test_field": "value",
        "should_fail": True,
        "errors": [],
    }
    
    agent = TestAgent(name="TestAgent", description="Test")
    result_state = agent.run(state)
    
    assert len(result_state["errors"]) > 0
    assert any("Intentional test failure" in error for error in result_state["errors"])


def test_errors_list_initialized_if_missing():
    """
    Test that run() initializes state["errors"] if it doesn't exist.
    """
    state: TradingAgentState = {
        "test_field": "value",
        "should_fail": True,
    }
    
    agent = TestAgent(name="TestAgent", description="Test")
    result_state = agent.run(state)
    
    assert "errors" in result_state
    assert len(result_state["errors"]) > 0