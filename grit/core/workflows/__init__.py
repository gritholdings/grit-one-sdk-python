"""
Grit Workflow Automation System.

A simple workflow engine for defining and executing automated processes.

Usage:
    from grit.core.workflows.engine import WorkflowEngine

    # Get workflow config from settings
    workflow_config = settings.APP_METADATA_SETTINGS['WORKFLOWS']['workflow_1']

    # Execute the workflow
    engine = WorkflowEngine(workflow_id='workflow_1', config=workflow_config)
    result = engine.run()

    if result['success']:
        print("Workflow completed!")
        print(result['wf'])  # Workflow context
        print(result['nodes'])  # Node contexts
    else:
        print(f"Workflow failed: {result['error']}")
"""
from grit.core.workflows.engine import WorkflowEngine
from grit.core.workflows.context import WorkflowContext, NodeContext

__all__ = ['WorkflowEngine', 'WorkflowContext', 'NodeContext']
