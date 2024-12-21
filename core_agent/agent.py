from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from core.utils import load_credential


class BaseAgent:
    """
    Base class for an agent. This class should be inherited by the agent class.
    """
    def __init__(self):
        self.tools = self.add_tools()
        self.workflow = self.build_workflow()
        self.model =self.get_model()
        self.thread_id = None
        # check if there is tools to bind
        if self.tools:
            self.model = self.model.bind_tools(self.tools)
        checkpointer = MemorySaver()
        self.graph = self.workflow.compile(checkpointer=checkpointer)

    def invoke_agent(self, state):
        """
        Invokes the agent model with the messages in the state.
        """
        messages = state["messages"]
        response = self.model.invoke(messages)
        return {"messages": [response]}

    def add_tools(self):
        """
        Add tools to the agent model.
        Example:
        from langchain_community.tools.tavily_search import TavilySearchResults
        tools.append(TavilySearchResults(max_results=1))
        """
        tools = []
        return tools

    def build_workflow(self):
        workflow = StateGraph(MessagesState)
        workflow.add_node("invoke_agent", self.invoke_agent)
        workflow.add_edge(START, "invoke_agent")
        workflow = self.add_nodes_edges(workflow)
        return workflow

    def get_model(self):
        """
        Returns the model to be used for the agent
        """
        API_KEY = load_credential("OPENAI_API_KEY")
        model = ChatOpenAI(model_name="gpt-4o", api_key=API_KEY)
        return model

    def add_nodes_edges(self, workflow):
        workflow.add_edge("invoke_agent", END)
        return workflow

    def run(self, new_message: str, thread_id: str, config: dict=None):
        """
        Processes the chat message and returns the response.
        """
        self.thread_id = thread_id
        if config is None:
            config = {
                "configurable": {
                    "thread_id": thread_id
                }
            }
        final_state = self.graph.invoke(
            {"messages": [{"role": "user", "content": new_message}]},
            config=config
        )
        return final_state["messages"][-1].content