import uuid
from abc import ABC, abstractmethod
from typing import Generator, Optional
from datetime import date
from django.apps import apps
from langchain_core.messages import SystemMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.callbacks.manager import get_openai_callback
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from core.utils import load_credential, set_environ_credential
from .memory import MemoryStoreService
from .utils import get_page_count, pdf_page_to_base64
from .dataclasses import AgentConfig


if apps.is_installed("core_payments"):
    from core_payments.utils import record_usage
else:
    def record_usage(*args, **kwargs):
        pass


class BaseAgent(ABC):
    """
    Base class for an agent. This class should be inherited by the agent class.
    """
    def __init__(self, config:Optional[AgentConfig] = None):
        self.config = config or self.get_agent_config()
        self.tools = self.add_tools()
        self.workflow = self.build_workflow()
        self.model = self.get_model()
        self.thread_id = None
        self.user_id = None
        self.memory_store_service = MemoryStoreService()
        # check if there is tools to bind
        if self.tools:
            self.model = self.model.bind_tools(self.tools)
        self.graph = self.workflow.compile()

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
        model = ChatOpenAI(model="gpt-4o", streaming=True, stream_usage=True, api_key=API_KEY)
        return model

    def add_nodes_edges(self, workflow):
        workflow.add_edge("invoke_agent", END)
        return workflow

    def run(self, new_message: str, thread_id: str, user_id: str, data_type: str = "text"):
        """
        Processes the chat message and returns the response.
        """
        self.thread_id = thread_id
        self.user_id = user_id
        graph_config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        if data_type == "text":
            first = True
            for msg, metadata in self.graph.stream(
                {"messages": [{"role": "user", "content": new_message}]},
                config=graph_config,
                stream_mode="messages"
            ):
                if (msg.content
                        and not isinstance(msg, HumanMessage)
                        and not isinstance(msg, ToolMessage)):
                    yield msg.content

                if isinstance(msg, AIMessageChunk):
                    if first:
                        gathered = msg
                        first = False
                    else:
                        gathered = gathered + msg

                    # if msg.tool_call_chunks:
                        # yield gathered.tool_calls
            # After finished streaming, save the memory
            namespace_for_memory = ("memories", user_id)
            self.memory_store_service.upsert_memory(
                namespace_for_memory, thread_id, 'conversation_history', f'user,{new_message}')
            self.memory_store_service.upsert_memory(
                namespace_for_memory, thread_id, 'conversation_history', f'assistant,{gathered.content}')
            self.memory_store_service.close()
        elif data_type == "image":
            namespace_for_memory = ("memories", user_id)
            # add each page of the PDF as a separate memory
            page_count = get_page_count(new_message)
            for page_index in range(page_count):
                base64_image = pdf_page_to_base64(pdf_path=new_message, page_number=page_index)
                self.memory_store_service.upsert_memory(
                    namespace_for_memory, thread_id, 'conversation_history', f'user_image,data:image/jpeg;base64,{base64_image}')
            self.memory_store_service.close()
        else:
            raise ValueError(f"Unsupported data type: {data_type}")


class EnhancedAgent(BaseAgent):
    """
    A simple agent that can respond to user queries.
    It can use Tavily for web-based searching if enabled in the config.
    """
    def create_new_thread(self, session_key: str) -> str:
        """Create a new thread and return its ID"""
        thread_id = str(uuid.uuid4())
        return thread_id

    def add_tools(self):
        """
        Add tools based on agent config.
        If enable_web_search is True, load the TavilySearch tool.
        Otherwise, return an empty list.
        """
        tools = []
        if self.config.enable_web_search:
            set_environ_credential("TAVILY_API_KEY")
            tavily_tool = TavilySearchResults(max_results=3)
            tools.append(tavily_tool)
        return tools

    def invoke_agent(self, state):
        messages = state["messages"]
        thread_id = self.thread_id
        user_id = self.user_id

        agent_prompt = self.get_agent_prompt()
        namespace_for_memory = ("memories", user_id)
        memories_str = ''
        memories = self.memory_store_service.get_memory(namespace_for_memory, thread_id)
        if memories and 'conversation_history' in memories.value:
            conversation_history = memories.value['conversation_history']
            memories_str += '<conversation_history>\n'
            for i, conversation_item in enumerate(conversation_history):
                role, text = conversation_item.split(',', 1)
                if role == 'user' or role == 'assistant':
                    memories_str += f'<{role} index="{i}">{text}</{role}>\n'
            memories_str += '</conversation_history>\n\n'
        memories_list = [SystemMessage(content=memories_str)] if memories_str else []

        # read file images such as PDFs
        image_list = []
        if memories and 'conversation_history' in memories.value:
            for i, conversation_item in enumerate(conversation_history):
                role, text = conversation_item.split(',', 1)
                if role == 'user_image':
                    image_list.append(HumanMessage(content=[{
                        "type": "image_url",
                        "image_url": {"url": text}
                    }]))

        messages = [SystemMessage(content=agent_prompt)] + memories_list + image_list + messages
        response = self.model.invoke(messages)
        return {"messages": [response]}
    
    @abstractmethod
    def get_agent_config(self):
        """Override this method to provide a custom agent configuration"""
        pass

    def get_agent_prompt(self) -> str:
        """Override this method to provide a custom agent prompt"""
        TODAY_DATE = date.today().strftime('%Y-%m-%d')
        agent_prompt_result = self.config.prompt_template.format(
            TODAY_DATE=TODAY_DATE)
        return agent_prompt_result

    def add_nodes_edges(self, workflow):
        """
        If tools exist (i.e., enable_web_search is True),
        add a ToolNode and wire it correctly.
        Otherwise, just use the base agent flow.
        """
        super().add_nodes_edges(workflow)
        if self.tools:
            workflow.add_node("tools", ToolNode(tools=self.tools))
            workflow.add_conditional_edges("invoke_agent", tools_condition)
            workflow.add_edge("tools", "invoke_agent")
        return workflow

    def process_chat(self, user, thread_id: str, new_message: str, data_type: str = "text") -> Generator[str, None, None]:
        """Process chat messages for a specific thread and return the response
        Record usage for payment if enabled in the agent configuration
        """
        user_id = str(user.id)
        if self.config.record_usage_for_payment:
            stripe_customer_id = user.stripecustomer.stripe_customer_id if user.stripecustomer else None
            # check if user has enough units
            if user.stripecustomer.units_remaining <= 0:
                yield "You have run out of units. Please purchase more units to continue using the service."
                return
            with get_openai_callback() as usage_tracker_cb:
                try:
                    for token in self.run(new_message, thread_id, user_id, data_type):
                        yield token
                finally:
                    # Record usage for payment
                    total_cost = usage_tracker_cb.total_cost
                    total_tokens = usage_tracker_cb.total_tokens
                    success = record_usage(
                        user_id=user_id, token_used=total_tokens, provider_cost=total_cost)
        else:
            for token in self.run(new_message, thread_id, user_id, data_type):
                yield token