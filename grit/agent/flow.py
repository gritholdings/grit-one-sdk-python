class BaseFlow:
    def __init__(self):
        pass
    async def on_flow_output(self, state):
        pass
    async def invoke(self, state, config):
        yield self.on_flow_output(state)