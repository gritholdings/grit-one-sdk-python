"""
Workflow triggers.

Triggers are entry points that start workflow execution.
"""
from grit.core.workflows.triggers.base import BaseTrigger
from grit.core.workflows.triggers.manual import ManualTrigger

__all__ = ['BaseTrigger', 'ManualTrigger']
