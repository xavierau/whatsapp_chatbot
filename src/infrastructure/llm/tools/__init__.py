"""Tools for the conversation agent.

This module provides tools that extend the agent's capabilities:
- compute: Solve complex computational problems (mathematical, statistical, financial, engineering)
- jot: Working memory for planning and multi-hop reasoning
- note_tools: Comprehensive note-taking with vector search (create, update, delete, get, list, search)
- expense_tools: Expense tracking with categories, tags, search, and analytics
"""

from src.infrastructure.llm.tools.expenses import expense_tools
from src.infrastructure.llm.tools.notes import note_tools
from src.infrastructure.llm.tools.program_of_thought import compute
from src.infrastructure.llm.tools.thinking import jot

__all__ = ["compute", "jot", "note_tools", "expense_tools"]
