"""
Flow is a structured class for managing and orchestrating how an agent processes
information and generates responses.

- state is a dictionary that contains the current state of the flow, including
  the input message and any other relevant data.
- config is a dictionary that contains configuration settings for the flow,
  such as the agent class and any other parameters needed for processing.
"""

class BaseFlow:
    def __init__(self):
        pass

    async def on_flow_output(self, state):
        pass

    async def invoke(self, state, config):
        """
        This method is called to invoke the flow with the given state and config.
        """
        yield self.on_flow_output(state)