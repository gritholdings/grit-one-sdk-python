"""
Deprecated. Synchronous agent implementation.
"""

import uuid
import logging
import json
from abc import ABC, abstractmethod
from typing import Generator, Optional, TypedDict
from datetime import date
from django.apps import apps
from langchain_core.messages import SystemMessage, AIMessageChunk, HumanMessage, ToolMessage, AIMessage
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.callbacks.manager import get_openai_callback
from langgraph.graph import END, START, StateGraph
from langchain_openai import ChatOpenAI
from grit.core.utils.env_config import load_credential, set_environ_credential
from ..store import MemoryStoreService
from ..utils import get_page_count, pdf_page_to_base64
from ..dataclasses import AgentConfig


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_record_usage_function():
    """
    Returns the appropriate record_usage function based on whether core_payments is installed.
    If not installed, returns a no-op function.
    """
    if apps.is_installed("core_payments"):
        from grit.payments.utils import record_usage
        return record_usage
    else:
        return lambda *args, **kwargs: None


class BaseState(TypedDict):
    messages: list[dict]


def route_tools(state: BaseState):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return "end"


class BaseToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        # Get the existing conversation history.
        messages = inputs.get("messages", [])
        if not messages:
            raise ValueError("No messages found in input")
        
        # The last message is expected to be the assistant message with tool_calls.
        last_message = messages[-1]
        outputs = []
        for tool_call in last_message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                ))
        return {"messages": messages + outputs}


class BaseConfigSchema(TypedDict):
    thread_id: str
    user_id: str


class BaseAgent(ABC):
    """
    Base class for an agent. This class should be inherited by the agent class.
    """
    def __init__(self):
        self.tools = self.add_tools()
        self.workflow = self.build_workflow()
        self.model = self.get_model()
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
        response = AIMessage(content=response.content, tool_calls=getattr(response, "tool_calls", None))
        state["messages"] = [response]
        return state

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
        workflow = StateGraph(BaseState, BaseConfigSchema)
        workflow.add_node("invoke_agent", self.invoke_agent)
        workflow.add_edge(START, "invoke_agent")
        workflow = self.add_nodes_edges(workflow)
        return workflow

    def get_model(self):
        """
        Returns the model to be used for the agent
        """
        API_KEY = load_credential("OPENAI_API_KEY")
        model = ChatOpenAI(model="gpt-4o", streaming=True, stream_usage=True, api_key=API_KEY,
                           max_retries=5, max_tokens=16000)
        return model

    def add_nodes_edges(self, workflow):
        workflow.add_edge("invoke_agent", END)
        return workflow

    def run(self, new_message: str, thread_id: str, user_id: str, data_type: str = "text"):
        """
        Processes the chat message and returns the response.
        """
        graph_state = {
            "messages": [{"role": "user", "content": new_message}],
        }
        graph_config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id
            }
        }
        if data_type == "text":
            gathered_chunks = []
            try:
                for message, metadata in self.graph.stream(
                    graph_state,
                    config=graph_config,
                    stream_mode="messages"
                ):
                    if (message.content
                            and (isinstance(message, (AIMessage, AIMessageChunk))
                            and not isinstance(message, (ToolMessage, HumanMessage)))):
                        yield message.content
                        gathered_chunks.append(message.content)
                    else:
                        continue
            except Exception as e:
                logger.exception("Error during streaming: %s", e)
                yield "An error occurred while processing your request."
            finally:
                final_answer = " ".join(gathered_chunks).strip()

                # After finished streaming, save the memory
                namespace_for_memory = ("memories", user_id)
                self.memory_store_service.upsert_memory(
                    namespace_for_memory, thread_id, 'conversation_history', f'user,{new_message}')
                self.memory_store_service.upsert_memory(
                    namespace_for_memory, thread_id, 'conversation_history', f'assistant,{final_answer}')
                self.memory_store_service.close()
        elif data_type == "image":
            namespace_for_memory = ("memories", user_id)
            # add each page of the PDF as a separate memory
            page_count = get_page_count(new_message)
            for page_index in range(page_count):
                base64_image, media_type = pdf_page_to_base64(pdf_path=new_message, page_number=page_index)
                self.memory_store_service.upsert_memory(
                    namespace_for_memory, thread_id, 'conversation_history', f'user_image,data:{media_type};base64,{base64_image}')
            self.memory_store_service.close()
        else:
            raise ValueError(f"Unsupported data type: {data_type}")


class EnhancedAgent(BaseAgent):
    """
    A simple agent that can respond to user queries.
    If config.enable_web_search, it uses Tavily for web-based searching.
    """
    def __init__(self, config:Optional[AgentConfig] = None):
        self.config = config or self.get_agent_config()
        super().__init__()
        if self.config.enable_knowledge_base:
            from ..store import KnowledgeBaseVectorStoreService
            self.kb_vectorstore_service = KnowledgeBaseVectorStoreService()

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

    def invoke_agent(self, state, config):
        messages = state['messages']
        thread_id = config['configurable']['thread_id']
        user_id = config['configurable']['user_id']

        agent_prompt = self.get_agent_prompt()
        # add knowledge base using RAG
        if self.config.enable_knowledge_base:
            latest_query = messages[-1]['content']

            knowledge_base_str = ''
            knowledge_bases = self.config.knowledge_bases
            if len(knowledge_bases) > 0:
                knowledge_base_str = '\n\n<retrieved_knowledge>\n'
            for knowledge_base in knowledge_bases:
                retrieval_results = self.kb_vectorstore_service.search_documents(
                    knowledge_base_id=str(knowledge_base['id']),
                    query=latest_query
                )
                if retrieval_results:
                    for i, result in enumerate(retrieval_results):
                        knowledge_base_str += f"<document id='{i+1}'>\n"
                        knowledge_base_str += f"{result['text']}\n"
                        knowledge_base_str += "</document>\n\n"
            if len(knowledge_bases) > 0:
                knowledge_base_str += '</retrieved_knowledge>\n\n'
                agent_prompt += knowledge_base_str

        namespace_for_memory = ("memories", user_id)
        memories = self.memory_store_service.get_memory(namespace_for_memory, thread_id)

        # read file images such as PDFs
        memories_list = []
        if memories and 'conversation_history' in memories.value:
            conversation_history = memories.value['conversation_history']
            for i, conversation_item in enumerate(conversation_history):
                role, text = conversation_item.split(',', 1)
                if role == 'user':
                    memories_list.append(HumanMessage(content=[{
                        "type": "text",
                        "text": text
                    }]))
                elif role == 'assistant':
                    memories_list.append(SystemMessage(content=text))
                elif role == 'user_image':
                    memories_list.append(HumanMessage(content=[{
                        "type": "image_url",
                        "image_url": {"url": text}
                    }]))

        messages = [SystemMessage(content=agent_prompt)] + memories_list + messages
        response = self.model.invoke(messages)
        state['messages'] = [response]
        return state
    
    @abstractmethod
    def get_agent_config(self):
        """Override this method to provide a custom agent configuration"""
        pass

    def get_agent_prompt(self) -> str:
        """Override this method to provide a custom agent prompt"""
        today_date = date.today().strftime('%Y-%m-%d')
        agent_prompt_result = self.config.prompt_template.format(
            today_date=today_date)
        return agent_prompt_result

    def add_nodes_edges(self, workflow):
        """
        If tools exist (i.e., enable_web_search is True),
        add a ToolNode and wire it correctly.
        Otherwise, just use the base agent flow.
        """
        workflow.add_edge("invoke_agent", END)
        if self.tools:
            workflow.add_node("tools", BaseToolNode(tools=self.tools))
            workflow.add_conditional_edges("invoke_agent", route_tools, {"tools": "tools", "end": END})
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
            record_usage = get_record_usage_function()
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