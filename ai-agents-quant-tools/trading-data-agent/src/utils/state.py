"""
LangGraph shared state schema for the Trading Data Agent pipeline.

TradingAgentState is the typed dictionary that flows between all
LangGraph nodes. Each agent reads the fields it needs and writes
its outputs back to the same state object.

Eg:
    from src.agents.state import TradingAgentState

    state: TradingAgentState = {
        "file_path": "data/sample_ticks.csv",
        "errors": [],
    }
"""

from __future__ import annotations
from typing import Optional
from typing_extensions import TypedDict
import pandas as pd


class TradingAgentState(TypedDict, total=False):
    """
    Shared state flowing through the LangGraph pipeline.

    All fields except 'errors' are Optional because state is built
    incrementally, each agent adds its piece.
    """
    file_path: Optional[str]
    raw_df: Optional[pd.DataFrame]
    clean_df: Optional[pd.DataFrame]
    metadata: Optional[dict]
    quality_report: Optional[dict]
    analysis_results: Optional[dict]
    report_path: Optional[str]
    errors: list[str]
    