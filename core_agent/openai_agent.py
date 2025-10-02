"""
Asynchronous Agent implementation using openai-agents.
"""

import uuid
import logging
import json
from datetime import date
from typing import AsyncGenerator, Optional
from asgiref.sync import sync_to_async
from django.apps import apps
from agents import Runner, WebSearchTool, ModelSettings
from agents import Agent as OpenAIAgent
from openai.types.responses import ResponseTextDeltaEvent
from core_agent.dataclasses import AgentConfig
from core_agent.models import Agent
from core_agent.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX, prompt_with_handoff_instructions
from .store import MemoryStoreService
from .utils import get_page_count, pdf_page_to_base64


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Cost in USD per 1 million tokens
MODEL_CONFIG = {
    "gpt-4o": {
        "price_per_1m_tokens_input": 2.5,
        "price_per_1m_tokens_output": 10,
    },
    "gpt-4.1": {
        "price_per_1m_tokens_input": 2,
        "price_per_1m_tokens_output": 8,
    },
    "gpt-4.1-mini": {
        "price_per_1m_tokens_input": 0.4,
        "price_per_1m_tokens_output": 1.6,
    },
    "gpt-4.5": {
        "price_per_1m_tokens_input": 75,
        "price_per_1m_tokens_output": 150,
    },
    "o1": {
        "price_per_1m_tokens_input": 15,
        "price_per_1m_tokens_output": 60,
    },
    "o3": {
        "price_per_1m_tokens_input": 2,
        "price_per_1m_tokens_output": 8,
    },
    "gpt-5": {
        "price_per_1m_tokens_input": 1.25,
        "price_per_1m_tokens_output": 10.00,
    }
}

DEFAULT_MODEL_NAME = "gpt-4o"


def get_record_usage_function():
    """
    Returns the appropriate record_usage function based on whether core_payments is installed.
    If not installed, returns a no-op function.
    """
    if apps.is_installed("core_payments"):
        from core_payments.utils import record_usage
        return record_usage
    else:
        return lambda *args, **kwargs: None


class BaseOpenAIAgent:
    def __init__(self, config: Optional[AgentConfig] = None, handoff_context: Optional[dict] = None):
        """Regular synchronous __init__ method"""
        self._config = config
        self._initialized = False
        # Don't initialize async components here
        self.memory_store_service = None
        self.kb_vectorstore_service = None
        self.config = None  # Will be properly set in initialize()
        self.current_agent = None  # Placeholder for current agent instance
        self.agent_instance = None  # The Django Agent model instance
        self.handoff_context = handoff_context  # Store handoff context if provided
    
    async def initialize(self):
        """
        Async initialization method to be called after __init__
        Do not create agent yet, just set up the configuration and services.
        """
        if self._initialized:
            return
            
        # Get the configuration
        self.config = self._config if self._config is not None else await sync_to_async(self.get_agent_config)()
        
        if self.config is None:
            raise ValueError("Config cannot be None")
        
        self.memory_store_service = MemoryStoreService()
        if self.config is not None and self.config.enable_knowledge_base:
            from core_agent.store import KnowledgeBaseVectorStoreService
            self.kb_vectorstore_service = KnowledgeBaseVectorStoreService()
        
        self._initialized = True
    
    @classmethod
    async def create(cls, config: Optional[AgentConfig] = None, **kwargs) -> 'BaseOpenAIAgent':
        """Factory method for creating and initializing an agent"""
        instance = cls(config=config, **kwargs)
        await instance.initialize()
        return instance

    def get_agent_config(self):
        """Override this method to provide a custom agent config.
        If config is passed from the constructor, that will be used instead."""
        return None

    def create_new_thread(self, session_key: str) -> str:
        """Create a new thread and return its ID"""
        thread_id = str(uuid.uuid4())
        return thread_id

    def get_agent_instructions(self) -> str:
        """Override this method to provide a custom agent prompt
        """
        return Agent.objects.get_formatted_prompt_template(self.config.id)

    def create_agent(self):
        instructions = self.get_agent_instructions()
        tools = []
        if self.config.enable_web_search:
            tools.append(WebSearchTool())
        
        # Get sub-agents configuration from the agent's metadata if available
        sub_agents = Agent.objects.get_sub_agents(self.config.id)
        
        # Create handoff agents for the SDK
        handoff_agents = []
        for sub_agent in sub_agents:
            # Create OpenAI Agent instances for each sub-agent
            sub_agent_config = Agent.objects.get_agent_config(sub_agent.id)
            sub_agent_instance = None
            sub_agent_instance = OpenAIAgent(
                name=sub_agent_config.label, 
                instructions=Agent.objects.get_formatted_prompt_template(sub_agent.id),
                model=sub_agent_config.model_name,
                # tools=tools, assuming sub-agents do not have their own tools for now
                # handoffs=handoff_agents,  # Assume there are no sub agents for sub-agents for now
                model_settings=ModelSettings(max_tokens=16000)
            )
            handoff_agents.append(sub_agent_instance)
        
        # Store the agent instance reference
        self.agent_instance = Agent.objects.get(id=self.config.id)
            
        model_name = self.config.model_name or DEFAULT_MODEL_NAME
        created_agent = OpenAIAgent(
            name=self.config.label, 
            instructions=instructions,
            model=model_name, 
            tools=tools,
            handoffs=handoff_agents,  # Add handoffs parameter
            model_settings=ModelSettings(max_tokens=16000)
        )
        return created_agent
    
    def build_messages(self, user_id: str, thread_id: str, new_message: str):
        # if thread_id is None, raise error
        if user_id is None or thread_id is None or new_message is None:
            raise ValueError("user_id, thread_id and new_message cannot be None")

        # add knowledge base using RAG
        knowledge_base_list = []
        if self.config.enable_knowledge_base:
            knowledge_base_str = ''
            knowledge_bases = self.config.knowledge_bases
            if len(knowledge_bases) > 0:
                knowledge_base_str = '\n\n<retrieved_knowledge>\n'
            for knowledge_base in knowledge_bases:
                retrieval_results = self.kb_vectorstore_service.search_documents(
                    knowledge_base_id=str(knowledge_base['id']),
                    query=new_message
                )
                if retrieval_results:
                    for i, result in enumerate(retrieval_results):
                        knowledge_base_str += f"<document id='{i+1}'>\n"
                        knowledge_base_str += f"{result['text']}\n"
                        knowledge_base_str += "</document>\n\n"
            if len(knowledge_bases) > 0:
                knowledge_base_str += '</retrieved_knowledge>\n\n'
                knowledge_base_list.append({
                    "role": "assistant",
                    "content": knowledge_base_str
                })

        namespace_for_memory = ("memories", user_id)
        memories = self.memory_store_service.get_memory(namespace_for_memory, thread_id)

        # read file images such as PDFs
        memories_list = []
        if memories and 'conversation_history' in memories.value:
            conversation_history = memories.value['conversation_history']
            for i, conversation_item in enumerate(conversation_history):
                # Check if it's a dict (new format) or string (old format)
                if isinstance(conversation_item, dict):
                    # New structured format
                    role = conversation_item.get('role')
                    content = conversation_item.get('content')
                    metadata = conversation_item.get('metadata', {})
                    
                    if role == 'user':
                        memories_list.append({
                            "role": "user",
                            "content": content
                        })
                    elif role == 'assistant':
                        memories_list.append({
                            "role": "assistant",
                            "content": content
                        })
                    elif role == 'user_image':
                        filename = metadata.get('filename', 'Uploaded file')
                        memories_list.append({
                            "role": "user",
                            "content": [
                            {
                                "type": "input_text",
                                "text": f"[Uploaded file: {filename}]"},
                            {
                                "type": "input_image",
                                "image_url": content
                            }
                            ]
                        })
                else:
                    # Old string format (backward compatibility)
                    role, text = conversation_item.split(',', 1)
                    if role == 'user':
                        memories_list.append({
                            "role": "user",
                            "content": text
                        })
                    elif role == 'assistant':
                        memories_list.append({
                            "role": "assistant",
                            "content": text
                        })
                    elif role == 'user_image':
                        memories_list.append({
                            "role": "user",
                            "content": [
                            {
                                "type": "input_text",
                                "text": ""},
                            {
                                "type": "input_image",
                                "image_url": text
                            }
                            ]
                        })

        # add new message
        formatted_new_message = {
            "role": "user",
            "content": new_message
        }

        messages:list = knowledge_base_list + memories_list + [formatted_new_message]
        return messages
    
    def on_agent_start(self):
        pass

    def on_agent_end(self, user_id: str, thread_id: str, new_message: str, final_output: str):
        # After finished streaming, save the memory
        namespace_for_memory = ("memories", user_id)
        # Store user message in new structured format
        self.memory_store_service.upsert_memory(
            namespace_for_memory, thread_id, 'conversation_history', 
            {"role": "user", "content": new_message})
        # Store assistant message in new structured format
        self.memory_store_service.upsert_memory(
            namespace_for_memory, thread_id, 'conversation_history', 
            {"role": "assistant", "content": final_output})
        self.memory_store_service.close()
    
    def detect_handoff_from_function_calls(self, function_calls: list) -> tuple[bool, str, str]:
        """
        Check if any function calls are handoff requests.
        Returns (is_handoff, target_agent_name, agent_id)
        
        Note: This is kept for backward compatibility but returns False
        since we're using SDK native handoffs.
        """
        return False, "", ""
    
    async def handoff_to_agent(self, agent_id: str, user, thread_id: str, conversation_history: list) -> 'BaseOpenAIAgent':
        """
        Create and return an instance of the specified sub-agent.
        Transfers the conversation history to maintain context.
        """
        
        # Get the specific sub-agent by ID
        try:
            target_sub_agent = await sync_to_async(Agent.objects.get)(id=agent_id)
        except Agent.DoesNotExist:
            raise ValueError(f"Sub-agent with ID '{agent_id}' not found")
        
        agent_id = str(target_sub_agent.id)
        
        # The target_sub_agent is already the Agent model instance
        agent_instance = target_sub_agent
        
        # Get the agent class and instantiate it
        agent_class_str = agent_instance.metadata.get('agent_class', 'core_agent.openai_agent.BaseOpenAIAgent')
        agent_class = await sync_to_async(Agent.objects.get_agent_class)(agent_class_str)
        
        # Create the sub-agent instance with config from the agent
        agent_config = await sync_to_async(agent_instance.get_config)()
        sub_agent = agent_class(config=agent_config)
        
        # Initialize the sub-agent
        await sub_agent.initialize()
        
        # Transfer conversation history by saving to memory store
        user_id = await sync_to_async(lambda: str(user.id))()
        namespace_for_memory = ("memories", user_id)
        
        # Clear existing memory for this thread and add the transferred history
        await sync_to_async(sub_agent.memory_store_service.delete_memory)(namespace_for_memory, thread_id)
        for msg in conversation_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            await sync_to_async(sub_agent.memory_store_service.upsert_memory)(
                namespace_for_memory, thread_id, 'conversation_history', f'{role},{content}'
            )
        # Set current agent id
        await sync_to_async(sub_agent.memory_store_service.set_current_agent_id)(user_id=user_id, thread_id=thread_id, agent_id=agent_id)
        
        return sub_agent

    async def process_chat(self, user, thread_id: str, new_message: str, data_type: str = "text", file_metadata: dict = None) -> AsyncGenerator[str, None]:
        # Ensure the agent is initialized
        if not self._initialized:
            await self.initialize()
        
        user_id = await sync_to_async(lambda: str(user.id))()
        is_stripecustomer = await sync_to_async(hasattr)(user, 'stripecustomer')
        record_usage = None
        if getattr(self.config, 'record_usage_for_payment', False) and is_stripecustomer:
            # check if user has enough units
            units_remaining = await sync_to_async(lambda: user.stripecustomer.units_remaining)()
            if units_remaining <= 0:
                yield "You have run out of units. Please purchase more units to continue using the service."
                return
            record_usage = await sync_to_async(get_record_usage_function)()
        if data_type == "text":
            openai_agent = await sync_to_async(self.create_agent)()
            messages = await sync_to_async(self.build_messages)(user_id=user_id, thread_id=thread_id, new_message=new_message)
            result = Runner.run_streamed(openai_agent, input=messages)
            final_output = ""
            function_calls = []
            handoff_detected = False
            target_agent_name = ""
            target_agent_id = ""
            
            try:
                async for event in result.stream_events():
                    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                        yield event.data.delta
                        final_output += event.data.delta
                    elif event.type == "run_item_stream_event" and event.name == "tool_called":
                        # Collect function calls for later processing
                        if hasattr(event, 'item') and hasattr(event.item, 'raw_item'):
                            function_calls.append(event.item.raw_item)
                    elif event.type == "run_item_stream_event" and event.name == "handoff_occured":
                        # Note: "handoff_occured" is the actual event name (misspelled) in openai-agents-python
                        handoff_detected = True
                        
                        if hasattr(event, 'item'):
                            # Extract handoff details from the event
                            handoff_item = event.item
                            
                            # Extract target agent information from the handoff item
                            if hasattr(handoff_item, 'target_agent'):
                                target_agent_name = handoff_item.target_agent.name
                            
                                # Get the target agent ID from our sub-agents mapping
                                sub_agents = await sync_to_async(Agent.objects.get_sub_agents)(self.config.id)
                                sub_agents_list = await sync_to_async(list)(sub_agents)
                                if sub_agents_list:
                                    for sub_agent in sub_agents_list:
                                        if sub_agent.name == target_agent_name:
                                            target_agent_id = str(sub_agent.id)
                                            break
            except Exception as e:
                logger.error(f"Error in process_chat: {str(e)}")
                yield f"\n[Stream Error]: {str(e)}\n"
            finally:
                # Check if SDK detected a handoff
                if handoff_detected and target_agent_id:
                    # Handoff detected, create the sub-agent and transfer conversation history
                    
                    # Build conversation history from messages
                    conversation_history = await sync_to_async(self.build_messages)(
                        user_id=user_id, thread_id=thread_id, new_message=new_message
                    )
                    
                    # Add the assistant's response to the conversation history
                    conversation_history.append({
                        "role": "assistant",
                        "content": final_output
                    })
                    
                    # Create the sub-agent instance and transfer conversation
                    sub_agent = await self.handoff_to_agent(
                        agent_id=target_agent_id,
                        user=user,
                        thread_id=thread_id,
                        conversation_history=conversation_history
                    )
                else:
                    # No handoff detected, normal completion
                    await sync_to_async(self.on_agent_end)(
                        user_id=user_id,
                        thread_id=thread_id,
                        new_message=new_message,
                        final_output=result.final_output)
                    
                if getattr(self.config, 'record_usage_for_payment', False) and hasattr(user, 'stripecustomer') and record_usage:
                    input_tokens = result.raw_responses[0].usage.input_tokens
                    output_tokens = result.raw_responses[0].usage.output_tokens
                    total_tokens = input_tokens + output_tokens
                    model_name = self.config.model_name if self.config.model_name else DEFAULT_MODEL_NAME
                    input_cost = (input_tokens / 1000000) * MODEL_CONFIG[model_name]["price_per_1m_tokens_input"]
                    output_cost = (output_tokens / 1000000) * MODEL_CONFIG[model_name]["price_per_1m_tokens_output"]
                    total_cost = input_cost + output_cost
                    success = await sync_to_async(record_usage)(
                        user_id=user_id, token_used=total_tokens, provider_cost=total_cost)
        elif data_type == "image":
            namespace_for_memory = ("memories", user_id)
            # add each page of the PDF as a separate memory
            page_count = await sync_to_async(get_page_count)(new_message)
            for page_index in range(page_count):
                base64_image = await sync_to_async(pdf_page_to_base64)(pdf_path=new_message, page_number=page_index)
                # Store as structured data with metadata
                if file_metadata and 'filename' in file_metadata:
                    # Store with new structure including metadata
                    memory_entry = {
                        "role": "user_image",
                        "content": f"data:image/jpeg;base64,{base64_image}",
                        "metadata": file_metadata
                    }
                    await sync_to_async(self.memory_store_service.upsert_memory)(
                        namespace_for_memory, thread_id, 'conversation_history', memory_entry)
                else:
                    # Backward compatible format
                    await sync_to_async(self.memory_store_service.upsert_memory)(
                        namespace_for_memory, thread_id, 'conversation_history', 
                        f'user_image,data:image/jpeg;base64,{base64_image}')
            await sync_to_async(self.memory_store_service.close)()
        else:
            raise ValueError(f"Unsupported data type: {data_type}")