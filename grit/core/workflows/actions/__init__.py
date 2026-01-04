"""
Workflow actions.

Actions are processing nodes that perform work within a workflow.
"""
from grit.core.workflows.actions.base import BaseAction
from grit.core.workflows.actions.code import CodeAction

__all__ = ['BaseAction', 'CodeAction']
