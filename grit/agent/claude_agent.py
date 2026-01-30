import uuid
import logging
from typing import AsyncGenerator, Optional
from asgiref.sync import sync_to_async
from django.apps import apps
import anthropic
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock
from claude_agent_sdk.types import StreamEvent
from .dataclasses import AgentConfig
from .models import Agent
from .store import MemoryStoreService
from .utils import get_page_count, pdf_page_to_base64
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
MODEL_CONFIG = {
    "claude-sonnet-4-5": {
        "price_per_1m_tokens_input": 3,
        "price_per_1m_tokens_output": 15,
    },
    "claude-haiku-4-5": {
        "price_per_1m_tokens_input": 1,
        "price_per_1m_tokens_output": 5,
    },
    "claude-opus-4-5": {
        "price_per_1m_tokens_input": 15,
        "price_per_1m_tokens_output": 75,
    },
}
DEFAULT_PRICING = {
    "price_per_1m_tokens_input": 3,
    "price_per_1m_tokens_output": 15,
}
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5"


class SimpleClaudeChat:
    async def send(self, message: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        options = ClaudeAgentOptions(model=DEFAULT_CLAUDE_MODEL)
        if system_prompt:
            options = ClaudeAgentOptions(model=DEFAULT_CLAUDE_MODEL, system_prompt=system_prompt)
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(message)
                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                yield block.text
        except Exception as e:
            logger.error(f"SimpleClaudeChat error: {e}")
            yield f"[Error]: {str(e)}"


def get_record_usage_function():
    if apps.is_installed("core_payments"):
        from grit.payments.utils import record_usage
        return record_usage
    else:
        return lambda *args, **kwargs: None


class BaseClaudeAgent:
    def __init__(self, config: Optional[AgentConfig] = None, handoff_context: Optional[dict] = None, **kwargs):
        self._config = config
        self._initialized = False
        self.memory_store_service = None
        self.kb_vectorstore_service = None
        self.config = config if config is not None else self.get_agent_config()
        if self.config is None:
            raise ValueError("Agent configuration is not initialized")
        self.current_agent = None
        self.agent_instance = None
        self.handoff_context = handoff_context
    async def initialize(self):
        if self._initialized:
            return
        self.config = self._config if self._config is not None else await sync_to_async(self.get_agent_config)()
        if self.config is None:
            raise ValueError("Config cannot be None")
        self.memory_store_service = MemoryStoreService()
        if self.config is not None and self.config.enable_knowledge_base:
            from .store import KnowledgeBaseVectorStoreService
            self.kb_vectorstore_service = KnowledgeBaseVectorStoreService()
        self._initialized = True
    @classmethod
    async def create(cls, config: Optional[AgentConfig] = None, **kwargs) -> 'BaseClaudeAgent':
        instance = cls(config=config, **kwargs)
        await instance.initialize()
        return instance
    def get_agent_config(self):
        return None
    def create_new_thread(self, session_key: str) -> str:
        thread_id = str(uuid.uuid4())
        return thread_id
    def get_agent_instructions_context(self) -> dict:
        return {}
    def get_agent_instructions(self) -> str:
        context = self.get_agent_instructions_context()
        return Agent.objects.get_formatted_prompt_template(self.config.id, context)
    def _build_claude_options(self) -> ClaudeAgentOptions:
        instructions = self.get_agent_instructions()
        options = ClaudeAgentOptions(
            model=DEFAULT_CLAUDE_MODEL,
            system_prompt=instructions,
            max_turns=1,
            include_partial_messages=True,
        )
        return options
    def build_messages(self, user_id: str, thread_id: str, new_message: str) -> list:
        if user_id is None or thread_id is None or new_message is None:
            raise ValueError("user_id, thread_id and new_message cannot be None")
        knowledge_base_context = ""
        if self.config.enable_knowledge_base:
            knowledge_bases = self.config.knowledge_bases
            if len(knowledge_bases) > 0:
                knowledge_base_context = '\n\n<retrieved_knowledge>\n'
                for knowledge_base in knowledge_bases:
                    retrieval_results = self.kb_vectorstore_service.search_documents(
                        knowledge_base_id=str(knowledge_base['id']),
                        query=new_message
                    )
                    if retrieval_results:
                        for i, result in enumerate(retrieval_results):
                            knowledge_base_context += f"<document id='{i+1}'>\n"
                            knowledge_base_context += f"{result['text']}\n"
                            knowledge_base_context += "</document>\n\n"
                knowledge_base_context += '</retrieved_knowledge>\n\n'
        namespace_for_memory = ("memories", user_id)
        memories = self.memory_store_service.get_memory(namespace_for_memory, thread_id)
        messages_list = []
        if memories and 'conversation_history' in memories.value:
            conversation_history = memories.value['conversation_history']
            for conversation_item in conversation_history:
                if isinstance(conversation_item, dict):
                    role = conversation_item.get('role')
                    content = conversation_item.get('content')
                    metadata = conversation_item.get('metadata', {})
                    if role == 'user':
                        messages_list.append({
                            "role": "user",
                            "content": content
                        })
                    elif role == 'assistant':
                        messages_list.append({
                            "role": "assistant",
                            "content": content
                        })
                    elif role == 'user_image' and content:
                        filename = metadata.get('filename', 'Uploaded file')
                        media_type = metadata.get('media_type')
                        base64_data = content
                        if content.startswith('data:'):
                            if not media_type:
                                media_type = content.split(';')[0].replace('data:', '')
                            base64_data = content.split(',', 1)[1]
                        if not media_type:
                            media_type = 'image/png'
                        messages_list.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"[Uploaded file: {filename}]"
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": base64_data
                                    }
                                }
                            ]
                        })
                else:
                    parts = conversation_item.split(',', 1)
                    role, text = parts if len(parts) == 2 else (parts[0], '')
                    if role in ('user', 'assistant'):
                        messages_list.append({
                            "role": role,
                            "content": text
                        })
                    elif role == 'user_image' and text:
                        base64_data = text
                        media_type = 'image/png'
                        if text.startswith('data:'):
                            media_type = text.split(';')[0].replace('data:', '')
                            base64_data = text.split(',', 1)[1]
                        messages_list.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "[Uploaded file]"
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": base64_data
                                    }
                                }
                            ]
                        })
        final_message = knowledge_base_context + new_message if knowledge_base_context else new_message
        messages_list.append({
            "role": "user",
            "content": final_message
        })
        return messages_list
    def _format_conversation_for_prompt(self, messages: list) -> str:
        if not messages:
            return ""
        if len(messages) == 1:
            return messages[0].get('content', '')
        formatted_parts = []
        history_messages = messages[:-1]
        current_message = messages[-1]
        if history_messages:
            formatted_parts.append("<conversation_history>")
            for msg in history_messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'user':
                    formatted_parts.append(f"<user>{content}</user>")
                elif role == 'assistant':
                    formatted_parts.append(f"<assistant>{content}</assistant>")
            formatted_parts.append("</conversation_history>\n")
        formatted_parts.append(current_message.get('content', ''))
        return '\n'.join(formatted_parts)
    def _has_images_in_messages(self, messages: list) -> bool:
        for msg in messages:
            content = msg.get('content')
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'image':
                        return True
        return False
    async def _create_multimodal_message_generator(self, messages: list):
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            msg_type = "user" if role == "user" else "assistant"
            yield {
                "type": msg_type,
                "message": {"role": role, "content": content},
                "parent_tool_use_id": None,
            }
    def on_agent_start(self):
        pass
    def on_agent_end(self, user_id: str, thread_id: str, new_message: str, final_output: str):
        namespace_for_memory = ("memories", user_id)
        self.memory_store_service.upsert_memory(
            namespace_for_memory, thread_id, 'conversation_history',
            {"role": "assistant", "content": final_output})
        self.memory_store_service.close()
    async def process_chat(
        self,
        user,
        thread_id: str,
        new_message: str,
        data_type: str = "text",
        file_metadata: dict = None
    ) -> AsyncGenerator[str, None]:
        if not self._initialized:
            await self.initialize()
        user_id = await sync_to_async(lambda: str(user.id))()
        is_stripecustomer = await sync_to_async(hasattr)(user, 'stripecustomer')
        record_usage = None
        if getattr(self.config, 'record_usage_for_payment', False) and is_stripecustomer:
            units_remaining = await sync_to_async(lambda: user.stripecustomer.units_remaining)()
            if units_remaining <= 0:
                yield "You have run out of units. Please purchase more units to continue using the service."
                return
            record_usage = await sync_to_async(get_record_usage_function)()
        if data_type == "text":
            namespace_for_memory = ("memories", user_id)
            await sync_to_async(self.memory_store_service.upsert_memory)(
                namespace_for_memory, thread_id, 'conversation_history',
                {"role": "user", "content": new_message}
            )
            messages = await sync_to_async(self.build_messages)(
                user_id=user_id, thread_id=thread_id, new_message=new_message
            )
            options = await sync_to_async(self._build_claude_options)()
            has_images = self._has_images_in_messages(messages)
            final_output = ""
            total_input_tokens = 0
            total_output_tokens = 0
            try:
                if has_images:
                    client = anthropic.AsyncAnthropic()
                    system_prompt = await sync_to_async(self.get_agent_instructions)()
                    async with client.messages.stream(
                        model=DEFAULT_CLAUDE_MODEL,
                        max_tokens=4096,
                        system=system_prompt,
                        messages=messages,
                    ) as stream:
                        async for text in stream.text_stream:
                            yield text
                            final_output += text
                        response = await stream.get_final_message()
                        if response.usage:
                            total_input_tokens = response.usage.input_tokens
                            total_output_tokens = response.usage.output_tokens
                else:
                    async with ClaudeSDKClient(options=options) as client:
                        prompt = self._format_conversation_for_prompt(messages)
                        await client.query(prompt)
                        async for message in client.receive_response():
                            if isinstance(message, StreamEvent):
                                event = message.event
                                if event.get('type') == 'content_block_delta':
                                    delta = event.get('delta', {})
                                    if delta.get('type') == 'text_delta':
                                        text = delta.get('text', '')
                                        if text:
                                            yield text
                                            final_output += text
                            elif isinstance(message, AssistantMessage):
                                if hasattr(message, 'usage'):
                                    if hasattr(message.usage, 'input_tokens'):
                                        total_input_tokens += message.usage.input_tokens
                                    if hasattr(message.usage, 'output_tokens'):
                                        total_output_tokens += message.usage.output_tokens
            except Exception as e:
                logger.error(f"Error in process_chat: {str(e)}", exc_info=True)
                yield f"\n[Stream Error]: {type(e).__name__}: {str(e)}\n"
            finally:
                await sync_to_async(self.on_agent_end)(
                    user_id=user_id,
                    thread_id=thread_id,
                    new_message=new_message,
                    final_output=final_output
                )
                if getattr(self.config, 'record_usage_for_payment', False) and is_stripecustomer and record_usage:
                    if total_input_tokens > 0 or total_output_tokens > 0:
                        total_tokens = total_input_tokens + total_output_tokens
                        input_cost = (total_input_tokens / 1000000) * DEFAULT_PRICING["price_per_1m_tokens_input"]
                        output_cost = (total_output_tokens / 1000000) * DEFAULT_PRICING["price_per_1m_tokens_output"]
                        total_cost = input_cost + output_cost
                        await sync_to_async(record_usage)(
                            user_id=user_id, token_used=total_tokens, provider_cost=total_cost
                        )
        elif data_type == "image":
            namespace_for_memory = ("memories", user_id)
            page_count = await sync_to_async(get_page_count)(new_message)
            for page_index in range(page_count):
                base64_image, media_type = await sync_to_async(pdf_page_to_base64)(
                    pdf_path=new_message, page_number=page_index
                )
                if file_metadata and 'filename' in file_metadata:
                    enhanced_metadata = {
                        **file_metadata,
                        'pageCount': f"{page_count} page{'s' if page_count > 1 else ''}",
                        'media_type': media_type
                    }
                    memory_entry = {
                        "role": "user_image",
                        "content": f"data:{media_type};base64,{base64_image}",
                        "metadata": enhanced_metadata
                    }
                    await sync_to_async(self.memory_store_service.upsert_memory)(
                        namespace_for_memory, thread_id, 'conversation_history', memory_entry
                    )
                else:
                    await sync_to_async(self.memory_store_service.upsert_memory)(
                        namespace_for_memory, thread_id, 'conversation_history',
                        f'user_image,data:{media_type};base64,{base64_image}'
                    )
            await sync_to_async(self.memory_store_service.close)()
        else:
            raise ValueError(f"Unsupported data type: {data_type}. Supported types are 'text' and 'image'.")


class BaseClaudeUserModeAgent(BaseClaudeAgent):
    def __init__(self, config: Optional[AgentConfig] = None, handoff_context: Optional[dict] = None, **kwargs):
        super().__init__(config, handoff_context, **kwargs)
        self.request = kwargs.get('request', None)
    def _get_mcp_tools(self) -> list:
        from .mcp_server import mcp_registry
        models_with_scoped = mcp_registry.get_models_with_user_mode()
        if not models_with_scoped:
            return []
        model_names = [model.__name__ for model in models_with_scoped]
        model_list_str = ", ".join(model_names)
        return [{
            "name": "mcp_query",
            "description": f"""Query Django database models through MCP (Model Context Protocol).
Available models: {model_list_str}
Available operations: list, retrieve, search
This tool allows querying registered Django models with read-only access.
Only models with scoped managers are accessible.
Examples:
- List records: {{"model_name": "Account", "operation": "list", "params": {{"limit": 10}}}}
- Retrieve by ID: {{"model_name": "Account", "operation": "retrieve", "params": {{"pk": "uuid-here"}}}}
- Search records: {{"model_name": "Account", "operation": "search", "params": {{"query": "search term", "limit": 20}}}}
The params argument is optional and varies by operation:
- list: {{"filters": {{"field__lookup": "value"}}, "limit": 50}}
- retrieve: {{"pk": "record-id"}}
- search: {{"query": "search text", "search_fields": ["field1", "field2"], "limit": 20}}""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": f"Name of the model to query. Available: {model_list_str}"
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["list", "retrieve", "search"],
                        "description": "Operation to perform on the model"
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional parameters for the operation (filters, limit, pk, query, etc.)"
                    }
                },
                "required": ["model_name", "operation"]
            }
        }]
    async def _execute_mcp_query(self, model_name: str, operation: str, params: Optional[dict] = None) -> str:
        import json
        from .mcp_server import mcp_registry
        valid_operations = ['list', 'retrieve', 'search']
        if operation not in valid_operations:
            return json.dumps({"error": f"Invalid operation '{operation}'. Must be one of: {', '.join(valid_operations)}"})
        toolset_class, model_class = await sync_to_async(mcp_registry.get_by_name)(model_name)
        if not toolset_class:
            available_models_list = await sync_to_async(mcp_registry.get_models_with_user_mode)()
            available_models = ", ".join([m.__name__ for m in available_models_list])
            return json.dumps({"error": f"Model '{model_name}' is not registered for MCP access. Available models: {available_models}"})
        if not hasattr(model_class, 'scoped'):
            return json.dumps({"error": f"Model '{model_name}' does not have a scoped manager and cannot be queried."})
        if not self.request:
            return json.dumps({"error": "No request context available. MCP queries require authentication."})
        toolset = await sync_to_async(toolset_class)(request=self.request)
        if params is None:
            params = {}
        try:
            result = None
            if operation == 'list':
                filters = params.get('filters')
                limit = params.get('limit')
                result = await sync_to_async(toolset.list)(filters=filters, limit=limit)
            elif operation == 'retrieve':
                pk = params.get('pk')
                if not pk:
                    return json.dumps({"error": "'pk' parameter is required for retrieve operation"})
                result = await sync_to_async(toolset.retrieve)(pk=pk)
            elif operation == 'search':
                query = params.get('query')
                if not query:
                    return json.dumps({"error": "'query' parameter is required for search operation"})
                search_fields = params.get('search_fields')
                limit = params.get('limit')
                result = await sync_to_async(toolset.search)(query=query, search_fields=search_fields, limit=limit)
            if result is None:
                return json.dumps({"error": f"Operation '{operation}' did not return a result"})
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            logger.error(f"MCP query error: {str(e)}")
            return json.dumps({"error": f"Error executing {operation} on {model_name}: {str(e)}"})
    async def process_chat(
        self,
        user,
        thread_id: str,
        new_message: str,
        data_type: str = "text",
        file_metadata: dict = None
    ) -> AsyncGenerator[str, None]:
        if data_type != "text":
            async for chunk in super().process_chat(user, thread_id, new_message, data_type, file_metadata):
                yield chunk
            return
        if not self._initialized:
            await self.initialize()
        user_id = await sync_to_async(lambda: str(user.id))()
        is_stripecustomer = await sync_to_async(hasattr)(user, 'stripecustomer')
        record_usage = None
        if getattr(self.config, 'record_usage_for_payment', False) and is_stripecustomer:
            units_remaining = await sync_to_async(lambda: user.stripecustomer.units_remaining)()
            if units_remaining <= 0:
                yield "You have run out of units. Please purchase more units to continue using the service."
                return
            record_usage = await sync_to_async(get_record_usage_function)()
        namespace_for_memory = ("memories", user_id)
        await sync_to_async(self.memory_store_service.upsert_memory)(
            namespace_for_memory, thread_id, 'conversation_history',
            {"role": "user", "content": new_message}
        )
        messages = await sync_to_async(self.build_messages)(
            user_id=user_id, thread_id=thread_id, new_message=new_message
        )
        system_prompt = await sync_to_async(self.get_agent_instructions)()
        tools = self._get_mcp_tools()
        final_output = ""
        total_input_tokens = 0
        total_output_tokens = 0
        try:
            client = anthropic.AsyncAnthropic()
            max_tool_iterations = 5
            iteration = 0
            while iteration < max_tool_iterations:
                iteration += 1
                api_params = {
                    "model": DEFAULT_CLAUDE_MODEL,
                    "max_tokens": 4096,
                    "system": system_prompt,
                    "messages": messages,
                }
                if tools:
                    api_params["tools"] = tools
                async with client.messages.stream(**api_params) as stream:
                    tool_use_block = None
                    tool_input_json = ""
                    async for event in stream:
                        if event.type == "content_block_start":
                            if event.content_block.type == "tool_use":
                                tool_use_block = {
                                    "id": event.content_block.id,
                                    "name": event.content_block.name,
                                    "input": {}
                                }
                                tool_input_json = ""
                        elif event.type == "content_block_delta":
                            if hasattr(event.delta, 'text'):
                                yield event.delta.text
                                final_output += event.delta.text
                            elif hasattr(event.delta, 'partial_json'):
                                tool_input_json += event.delta.partial_json
                    response = await stream.get_final_message()
                    if response.usage:
                        total_input_tokens += response.usage.input_tokens
                        total_output_tokens += response.usage.output_tokens
                    if response.stop_reason == "tool_use":
                        for block in response.content:
                            if block.type == "tool_use":
                                tool_name = block.name
                                tool_input = block.input
                                tool_use_id = block.id
                                if tool_name == "mcp_query":
                                    model_name = tool_input.get("model_name", "")
                                    operation = tool_input.get("operation", "")
                                    params = tool_input.get("params")
                                    tool_result = await self._execute_mcp_query(
                                        model_name=model_name,
                                        operation=operation,
                                        params=params
                                    )
                                    messages.append({
                                        "role": "assistant",
                                        "content": response.content
                                    })
                                    messages.append({
                                        "role": "user",
                                        "content": [{
                                            "type": "tool_result",
                                            "tool_use_id": tool_use_id,
                                            "content": tool_result
                                        }]
                                    })
                                    break
                    else:
                        break
        except Exception as e:
            logger.error(f"Error in process_chat: {str(e)}", exc_info=True)
            yield f"\n[Stream Error]: {type(e).__name__}: {str(e)}\n"
        finally:
            await sync_to_async(self.on_agent_end)(
                user_id=user_id,
                thread_id=thread_id,
                new_message=new_message,
                final_output=final_output
            )
            if getattr(self.config, 'record_usage_for_payment', False) and is_stripecustomer and record_usage:
                if total_input_tokens > 0 or total_output_tokens > 0:
                    total_tokens = total_input_tokens + total_output_tokens
                    input_cost = (total_input_tokens / 1000000) * DEFAULT_PRICING["price_per_1m_tokens_input"]
                    output_cost = (total_output_tokens / 1000000) * DEFAULT_PRICING["price_per_1m_tokens_output"]
                    total_cost = input_cost + output_cost
                    await sync_to_async(record_usage)(
                        user_id=user_id, token_used=total_tokens, provider_cost=total_cost
                    )
