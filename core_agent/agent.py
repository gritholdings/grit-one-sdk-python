import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from django.apps import apps
from langchain_core.messages import SystemMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.callbacks.manager import get_openai_callback
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from core.utils import load_credential, set_environ_credential
from .chroma import ChromaService

if apps.is_installed("core_payments"):
    from core_payments.utils import record_usage
else:
    def record_usage(*args, **kwargs):
        pass

@dataclass
class AgentConfig:
    enable_web_search: bool = True
    record_usage_for_payment: bool = False

class BaseAgent(ABC):
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
        model = ChatOpenAI(model="gpt-4o", api_key=API_KEY)
        return model

    def add_nodes_edges(self, workflow):
        workflow.add_edge("invoke_agent", END)
        return workflow

    def run(self, new_message: str, thread_id: str):
        """
        Processes the chat message and returns the response.
        """
        self.thread_id = thread_id
        graph_config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        final_state = self.graph.invoke(
            {"messages": [{"role": "user", "content": new_message}]},
            config=graph_config
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
                chroma_service_config = self.get_chroma_service_config()
                chroma_service = ChromaService(config=chroma_service_config)
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
    
    @abstractmethod
    def get_agent_config(self):
        """Override this method to provide a custom agent configuration"""
        pass

    @abstractmethod
    def get_agent_prompt(self) -> str:
        """Override this method to provide a custom agent prompt"""
        pass
    
    @abstractmethod
    def get_chroma_service_config(self):
        """Override this method to provide a custom configuration for the agent"""
        pass

    def add_nodes_edges(self, workflow):
        super().add_nodes_edges(workflow)
        workflow.add_node("tools", ToolNode(tools=self.tools))
        workflow.add_conditional_edges(
            "invoke_agent",
            tools_condition
        )
        workflow.add_edge("tools", "invoke_agent")
        return workflow

    def process_chat(self, user, session_key: str, thread_id: str, new_message: str) -> str:
        """Process chat messages for a specific thread and return the response
        Record usage for payment if enabled in the agent configuration
        """
        user_id = user.id
        config = self.get_agent_config()
        if config.record_usage_for_payment:
            stripe_customer_id = user.stripecustomer.stripe_customer_id if user.stripecustomer else None
            # check if user has enough units
            if user.stripecustomer.units_remaining <= 0:
                return "You have run out of units. Please purchase more units to continue using the service."
            with get_openai_callback() as usage_tracker_cb:
                response = self.run(new_message, thread_id)
                # Record usage for payment
                total_cost = usage_tracker_cb.total_cost
                success = record_usage(user_id, stripe_customer_id, total_cost)
        else:
            response = self.run(new_message, thread_id)
        return response