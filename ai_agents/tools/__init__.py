"""
AI Agent Tools Package

This package contains various tools that can be used by AI agents to extend their capabilities.
Each tool should implement the BaseTool interface and provide specific functionality.
"""

from .base_tool import BaseTool
from .datetime_tool import DateTimeTool
from .calculator_tool import CalculatorTool
from .search_pubmed_tool import SearchPubmedTool
from .search_arxiv_tool import SearchArxivTool
from .search_lii_tool import SearchLIITool
from .search_doaj_tool import SearchDOAJTool
from .search_clinical_trials_tool import SearchClinicalTrialsTool
from .tool_manager import ToolManager

__all__ = [
    'BaseTool',
    'DateTimeTool',
    'CalculatorTool',
    'SearchPubmedTool',
    'SearchArxivTool',
    'SearchLIITool',
    'SearchDOAJTool',
    'SearchClinicalTrialsTool',
    'ToolManager'
]