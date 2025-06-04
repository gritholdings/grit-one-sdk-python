"""
Asynchronous Agent implementation using openai-agents.
"""

import uuid
import logging
from datetime import date
from typing import Generator, Optional
from asgiref.sync import sync_to_async
from django.apps import apps
from agents import Runner, WebSearchTool, ModelSettings
from agents import Agent as OpenAIAgent
from openai.types.responses import ResponseTextDeltaEvent
from .dataclasses import AgentConfig
from .store import MemoryStoreService
from .utils import get_page_count, pdf_page_to_base64


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Cost in USD per 1 million tokens
MODEL_CONFIG = {
    "gpt-4o": {
        "price_per_1m_tokens_input": 2.5,
        "price_per_1m_tokens_output": 10,
    },
    "gpt-4.5": {
        "price_per_1m_tokens_input": 75,
        "price_per_1m_tokens_output": 150,
    },
    "o1": {
        "price_per_1m_tokens_input": 15,
        "price_per_1m_tokens_output": 60,
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
    def __init__(self, config:Optional[AgentConfig] = None):
        agent = self.get_agent() # pylint: disable=assignment-from-none
        if agent is not None:
            self.config = agent.get_config()
        else:
            self.config = config if config is not None else self.get_agent_config()
        if self.config is None:
            raise ValueError("Config cannot be None")
        self.memory_store_service = MemoryStoreService()
        if self.config is not None and self.config.enable_knowledge_base:
            from core_agent.store import KnowledgeBaseVectorStoreService
            self.kb_vectorstore_service = KnowledgeBaseVectorStoreService()

    def get_agent(self) -> Optional['Agent']:
        """Override this method to provide a custom agent instance.
        If agent is passed from the constructor, that agent config will be used instead."""
        return None

    def get_agent_config(self):
        """Override this method to provide a custom agent config.
        If config is passed from the constructor, that will be used instead."""
        return None

    def create_new_thread(self, session_key: str) -> str:
        """Create a new thread and return its ID"""
        thread_id = str(uuid.uuid4())
        return thread_id

    def get_agent_instructions(self) -> str:
        """Override this method to provide a custom agent prompt"""
        today_date = date.today().strftime('%Y-%m-%d')
        agent_prompt_result = self.config.prompt_template.format(
            today_date=today_date)
        return agent_prompt_result

    def create_agent(self):
        instructions = self.get_agent_instructions()
        tools = []
        if self.config.enable_web_search:
            tools.append(WebSearchTool())
        model_name = self.config.model_name if self.config.model_name != '' else DEFAULT_MODEL_NAME
        created_agent = OpenAIAgent(name="Assistant", instructions=instructions,
                                    model=model_name, tools=tools,
                                    model_settings=ModelSettings(max_tokens=16000))
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
        self.memory_store_service.upsert_memory(
            namespace_for_memory, thread_id, 'conversation_history', f'user,{new_message}')
        self.memory_store_service.upsert_memory(
            namespace_for_memory, thread_id, 'conversation_history', f'assistant,{final_output}')
        self.memory_store_service.close()

    async def process_chat(self, user, thread_id: str, new_message: str, data_type: str = "text") -> Generator[str, None, None]:
        user_id = await sync_to_async(lambda: str(user.id))()
        is_stripecustomer = await sync_to_async(hasattr)(user, 'stripecustomer')
        if self.config.record_usage_for_payment and is_stripecustomer:
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
            try:
                async for event in result.stream_events():
                    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                        yield event.data.delta
            except Exception as e:
                logger.error(f"Error in process_chat: {str(e)}")
                yield f"\n[Stream Error]: {str(e)}\n"
            finally:
                await sync_to_async(self.on_agent_end)(
                    user_id=user_id,
                    thread_id=thread_id,
                    new_message=new_message,
                    final_output=result.final_output)
                if self.config.record_usage_for_payment and hasattr(user, 'stripecustomer'):
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
                await sync_to_async(self.memory_store_service.upsert_memory)(
                    namespace_for_memory, thread_id, 'conversation_history', f'user_image,data:image/jpeg;base64,{base64_image}')
            await sync_to_async(self.memory_store_service.close)()
        else:
            raise ValueError(f"Unsupported data type: {data_type}")