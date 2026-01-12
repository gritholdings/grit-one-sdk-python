"""
Asynchronous Agent implementation using Claude Agent SDK.
"""

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


# Cost in USD per 1 million tokens
# Note: These are display names for the UI; the SDK uses its default model internally
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

# Default pricing for cost calculations
DEFAULT_PRICING = {
    "price_per_1m_tokens_input": 3,
    "price_per_1m_tokens_output": 15,
}

# Default Claude model - centralized for easy updates
# Use full model identifier with date suffix for API compatibility
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5"


class SimpleClaudeChat:
    """
    Minimal Claude chat implementation for debugging.

    This class strips away all complexity to isolate SDK issues.
    Usage:
        chat = SimpleClaudeChat()
        async for chunk in chat.send("Hello"):
            print(chunk)
    """

    async def send(self, message: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Send a message and stream the response.

        Args:
            message: The user's message
            system_prompt: Optional system prompt

        Yields:
            str: Text chunks from the response
        """
        # Build options with centralized model configuration
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
    """
    Returns the appropriate record_usage function based on whether core_payments is installed.
    If not installed, returns a no-op function.
    """
    if apps.is_installed("core_payments"):
        from grit.payments.utils import record_usage
        return record_usage
    else:
        return lambda *args, **kwargs: None


class BaseClaudeAgent:
    """
    Base Claude Agent class using the Claude Agent SDK.

    This class mirrors the structure of BaseOpenAIAgent but uses
    Anthropic's Claude Agent SDK for streaming chat interactions.
    """

    def __init__(self, config: Optional[AgentConfig] = None, handoff_context: Optional[dict] = None, **kwargs):
        """Regular synchronous __init__ method"""
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
        """
        Async initialization method to be called after __init__
        Do not create agent yet, just set up the configuration and services.
        """
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

    def get_agent_instructions_context(self) -> dict:
        """Override to provide context variables for the agent instructions template."""
        return {}

    def get_agent_instructions(self) -> str:
        """Override this method to provide a custom agent prompt"""
        context = self.get_agent_instructions_context()
        return Agent.objects.get_formatted_prompt_template(self.config.id, context)

    def _build_claude_options(self) -> ClaudeAgentOptions:
        """
        Build ClaudeAgentOptions for the Claude Agent SDK.

        Returns:
            ClaudeAgentOptions: Configured options for Claude Agent
        """
        instructions = self.get_agent_instructions()

        # Use centralized model configuration for API compatibility
        # Enable include_partial_messages for token-by-token streaming
        options = ClaudeAgentOptions(
            model=DEFAULT_CLAUDE_MODEL,
            system_prompt=instructions,
            max_turns=1,  # Single turn for basic chat
            include_partial_messages=True,  # Enable streaming of partial text deltas
        )

        return options

    def build_messages(self, user_id: str, thread_id: str, new_message: str) -> list:
        """
        Build the message history for the conversation.

        This method retrieves conversation history from the memory store
        and formats it for the Claude Agent SDK.
        """
        if user_id is None or thread_id is None or new_message is None:
            raise ValueError("user_id, thread_id and new_message cannot be None")

        # Add knowledge base using RAG
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

        # Build conversation history
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
                        # Handle image content for Claude's multimodal API
                        # content is base64 data URL: "data:image/png;base64,..."
                        filename = metadata.get('filename', 'Uploaded file')
                        # Get media_type from metadata, or extract from data URL
                        media_type = metadata.get('media_type')
                        base64_data = content
                        # Extract just the base64 data if it's a data URL
                        if content.startswith('data:'):
                            # Format: data:image/png;base64,<actual_base64_data>
                            # Extract media type from data URL if not in metadata
                            if not media_type:
                                media_type = content.split(';')[0].replace('data:', '')
                            base64_data = content.split(',', 1)[1]
                        # Default to image/png if media_type still not determined
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
                    # Old string format (backward compatibility)
                    parts = conversation_item.split(',', 1)
                    role, text = parts if len(parts) == 2 else (parts[0], '')
                    if role in ('user', 'assistant'):
                        messages_list.append({
                            "role": role,
                            "content": text
                        })
                    elif role == 'user_image' and text:
                        # Handle old format image: user_image,data:image/png;base64,...
                        base64_data = text
                        media_type = 'image/png'  # Default to PNG
                        if text.startswith('data:'):
                            # Extract media type from data URL
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

        # Prepend knowledge base context to new message if available
        final_message = knowledge_base_context + new_message if knowledge_base_context else new_message

        # Add new message
        messages_list.append({
            "role": "user",
            "content": final_message
        })

        return messages_list

    def _format_conversation_for_prompt(self, messages: list) -> str:
        """
        Format conversation history as a string for the Claude Agent SDK prompt.

        The Claude Agent SDK query() takes a single prompt string, so we need
        to format the conversation history appropriately.
        """
        if not messages:
            return ""

        # If there's only one message (the new user message), just return it
        if len(messages) == 1:
            return messages[0].get('content', '')

        # Format conversation history as context
        formatted_parts = []

        # All messages except the last one are history
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

        # Add the current message
        formatted_parts.append(current_message.get('content', ''))

        return '\n'.join(formatted_parts)

    def _has_images_in_messages(self, messages: list) -> bool:
        """Check if any messages contain image content."""
        for msg in messages:
            content = msg.get('content')
            if isinstance(content, list):
                # Content is a list of blocks, could contain images
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'image':
                        return True
        return False

    async def _create_multimodal_message_generator(self, messages: list):
        """
        Create an async generator that yields message dictionaries for the Claude SDK.

        The SDK expects messages in format:
        {
            "type": "user",
            "message": {"role": "user", "content": <str or list>},
            "session_id": session_id
        }
        """
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')

            # Map role to SDK type
            msg_type = "user" if role == "user" else "assistant"

            yield {
                "type": msg_type,
                "message": {"role": role, "content": content},
                "parent_tool_use_id": None,
            }

    def on_agent_start(self):
        """Hook called when agent starts processing."""
        pass

    def on_agent_end(self, user_id: str, thread_id: str, new_message: str, final_output: str):
        """Hook called when agent finishes processing."""
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
        """
        Process a chat message and stream the response.

        This is the main entry point for chat interactions. It:
        1. Persists the user message
        2. Builds conversation context
        3. Streams the response from Claude Agent SDK
        4. Persists the assistant response

        Args:
            user: The Django user object
            thread_id: The conversation thread ID
            new_message: The user's message (or file path for image uploads)
            data_type: Type of data ("text" for messages, "image" for PDF uploads)
            file_metadata: Optional metadata for file uploads (e.g., filename)

        Yields:
            str: Text chunks from the streaming response
        """
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
            # Persist user message immediately
            namespace_for_memory = ("memories", user_id)
            await sync_to_async(self.memory_store_service.upsert_memory)(
                namespace_for_memory, thread_id, 'conversation_history',
                {"role": "user", "content": new_message}
            )

            # Build messages and format for Claude
            messages = await sync_to_async(self.build_messages)(
                user_id=user_id, thread_id=thread_id, new_message=new_message
            )
            options = await sync_to_async(self._build_claude_options)()

            # Check if conversation contains images - use Anthropic API directly if so
            # (ClaudeSDKClient doesn't support multimodal content)
            has_images = self._has_images_in_messages(messages)

            final_output = ""
            total_input_tokens = 0
            total_output_tokens = 0

            try:
                if has_images:
                    # Use Anthropic API directly for multimodal content
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

                        # Get final message for usage stats
                        response = await stream.get_final_message()
                        if response.usage:
                            total_input_tokens = response.usage.input_tokens
                            total_output_tokens = response.usage.output_tokens
                else:
                    # Use ClaudeSDKClient for text-only conversations
                    # With include_partial_messages=True, we receive StreamEvent objects
                    # containing text deltas for real-time streaming
                    async with ClaudeSDKClient(options=options) as client:
                        prompt = self._format_conversation_for_prompt(messages)
                        await client.query(prompt)
                        async for message in client.receive_response():
                            if isinstance(message, StreamEvent):
                                # Handle streaming text deltas (token-by-token)
                                event = message.event
                                if event.get('type') == 'content_block_delta':
                                    delta = event.get('delta', {})
                                    if delta.get('type') == 'text_delta':
                                        text = delta.get('text', '')
                                        if text:
                                            yield text
                                            final_output += text
                            elif isinstance(message, AssistantMessage):
                                # AssistantMessage contains the complete response and usage stats
                                # Text is already yielded via StreamEvent, so just track usage
                                if hasattr(message, 'usage'):
                                    if hasattr(message.usage, 'input_tokens'):
                                        total_input_tokens += message.usage.input_tokens
                                    if hasattr(message.usage, 'output_tokens'):
                                        total_output_tokens += message.usage.output_tokens

            except Exception as e:
                logger.error(f"Error in process_chat: {str(e)}", exc_info=True)
                yield f"\n[Stream Error]: {type(e).__name__}: {str(e)}\n"
            finally:
                # Save assistant response
                await sync_to_async(self.on_agent_end)(
                    user_id=user_id,
                    thread_id=thread_id,
                    new_message=new_message,
                    final_output=final_output
                )

                # Record usage for payment if applicable
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
            # Handle PDF file uploads by converting each page to base64 images
            namespace_for_memory = ("memories", user_id)
            # Add each page of the PDF as a separate memory entry
            page_count = await sync_to_async(get_page_count)(new_message)
            for page_index in range(page_count):
                base64_image, media_type = await sync_to_async(pdf_page_to_base64)(
                    pdf_path=new_message, page_number=page_index
                )
                # Store as structured data with metadata
                if file_metadata and 'filename' in file_metadata:
                    # Enhance metadata with page count information
                    enhanced_metadata = {
                        **file_metadata,
                        'pageCount': f"{page_count} page{'s' if page_count > 1 else ''}",
                        'media_type': media_type
                    }
                    # Store with new structure including metadata
                    memory_entry = {
                        "role": "user_image",
                        "content": f"data:{media_type};base64,{base64_image}",
                        "metadata": enhanced_metadata
                    }
                    await sync_to_async(self.memory_store_service.upsert_memory)(
                        namespace_for_memory, thread_id, 'conversation_history', memory_entry
                    )
                else:
                    # Backward compatible format
                    await sync_to_async(self.memory_store_service.upsert_memory)(
                        namespace_for_memory, thread_id, 'conversation_history',
                        f'user_image,data:{media_type};base64,{base64_image}'
                    )
            await sync_to_async(self.memory_store_service.close)()
        else:
            raise ValueError(f"Unsupported data type: {data_type}. Supported types are 'text' and 'image'.")


class BaseClaudeUserModeAgent(BaseClaudeAgent):
    """
    Claude Agent with MCP database querying capabilities.

    This agent extends BaseClaudeAgent by adding the ability to query Django models
    that are registered with MCP and have a .scoped manager.

    Note: MCP tool integration is planned for future implementation.
    """

    def __init__(self, config: Optional[AgentConfig] = None, handoff_context: Optional[dict] = None, **kwargs):
        """Initialize with request context for MCP queries."""
        super().__init__(config, handoff_context, **kwargs)
        self.request = kwargs.get('request', None)
