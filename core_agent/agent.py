import uuid
from langchain_core.messages import SystemMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from core.utils import load_credential, set_environ_credential
from .chroma import ChromaService, Config


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


class EnhancedAgent(BaseAgent):
    """
    A simple agent that can respond to user queries.
    It has access to a Tavily search tool to retrieve relevant information.
    """
    def create_new_thread(self, session_key: str) -> str:
        """Create a new thread and return its ID"""
        thread_id = str(uuid.uuid4())
        return thread_id

    def add_tools(self):
        tools = []
        set_environ_credential("TAVILY_API_KEY")
        tavily_tool = TavilySearchResults(max_results=3)
        tools.append(tavily_tool)
        return tools

    def invoke_agent(self, state):
        messages = state["messages"]
        thread_id = self.thread_id

        if thread_id:
            # Check if thread has existing vector store
            try:
                custom_config = self.get_custom_config()
                chroma_service = ChromaService(config=custom_config)
                if chroma_service.check_thread_exists(thread_id):
                    # Get existing vector store
                    vector_store = chroma_service.get_or_create_vector_store(thread_id)
                    retriever = vector_store.as_retriever()

                    # Search for relevant context
                    user_message = messages[-1].content
                    relevant_docs = retriever.invoke(user_message)

                    # Add context to messages
                    if relevant_docs:
                        context = "\n".join([doc.page_content for doc in relevant_docs])
                        messages = [SystemMessage(content=f"Here is relevant context from uploaded documents:\n\n{context}")] + messages
            except Exception as e:
                print(f"Error accessing vector store: {str(e)}")
        agent_prompt = self.get_agent_prompt()
        messages = [SystemMessage(content=agent_prompt)] + messages
        response = self.model.invoke(messages)
        return {"messages": [response]}
    
    def get_custom_config(self):
        """Override this method to provide a custom configuration for the agent"""
        return Config()
    
    def get_agent_prompt(self) -> str:
        """Override this method to provide a custom agent prompt"""
        return ""

    def add_nodes_edges(self, workflow):
        super().add_nodes_edges(workflow)
        workflow.add_node("tools", ToolNode(tools=self.tools))
        workflow.add_conditional_edges(
            "invoke_agent",
            tools_condition
        )
        workflow.add_edge("tools", "invoke_agent")
        return workflow

    def process_chat(self, session_key: str, thread_id: str, new_message: str, config: dict = None) -> str:
        """Process chat messages for a specific thread and return the response"""
        response = self.run(new_message, thread_id, config)
        return response