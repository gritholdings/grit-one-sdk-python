from openai import OpenAI
from enum import Enum
import json
import os
from typing import Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from django.contrib.sessions.backends.db import SessionStore
from typing import Dict, Any


class OpenaiModel(Enum):
    GPT_3_5 = "gpt-3.5-turbo"
    GPT_4 = "gpt-4-turbo"

    @classmethod
    def choices(cls):
        return [(key.name, key.value) for key in cls]


class OpenaiAdapter:
    """Openai Adapter"""
    def __init__(self):
        # it will access the API key from os.environ
        with open(os.getcwd() + '/credentials.json') as f:
            credentials = json.load(f)
            OPENAI_API_KEY = credentials['OPENAI_API_KEY']
            self.client = OpenAI(api_key=OPENAI_API_KEY)

    def chat(self, model: OpenaiModel = OpenaiModel.GPT_4, messages: list = []):
        formatted_messages = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        formatted_messages.extend(messages)
        completion = self.client.chat.completions.create(
            model=model.value,
            messages=formatted_messages
        )
        return completion.choices[0].message.content

openai_instance = OpenaiAdapter()


class DjangoSessionMemorySaver(MemorySaver):
    def __init__(self, session_key: str):
        super().__init__()
        self.session_key = session_key
        self.session = SessionStore(session_key=session_key)

    async def load(self) -> Dict[str, Any]:
        return self.session.get('langgraph_memory', {})

    async def save(self, data: Dict[str, Any]):
        self.session['langgraph_memory'] = data
        self.session.save()


@tool
def search(query: str):
    """Placeholder function"""
    pass


class ChatbotApp:
    def __init__(self):
        self.tools = [search]
        self.tool_node = ToolNode(self.tools)
        with open(os.getcwd() + '/credentials.json') as f:
            credentials = json.load(f)
            ANTHROPIC_API_KEY = credentials['ANTHROPIC_API_KEY']
            self.model = ChatAnthropic(
                model = "claude-3-5-sonnet-20240620",
                temperature = 0,
                api_key = ANTHROPIC_API_KEY
        ).bind_tools(self.tools)

        # Create the workflow once
        self.workflow = self._create_workflow()

    def _create_workflow(self):
        workflow = StateGraph(MessagesState)

        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", self.tool_node)

        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", self._should_continue)
        workflow.add_edge("tools", 'agent')

        return workflow

    def _should_continue(self, state: MessagesState) -> Literal["tools", END]:
        messages = state['messages']
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"
        return END

    def _call_model(self, state: MessagesState):
        messages = state['messages']
        response = self.model.invoke(messages)
        return {"messages": [response]}

    def get_app_for_session(self, session_key: str):
        """Get a compiled app instance for a specific session"""
        checkpointer = DjangoSessionMemorySaver(session_key)
        return self.workflow.compile(checkpointer=checkpointer)

    def process_chat(self, session_key: str, messages: list, config: dict = None) -> str:
        """Process chat messages and return the response"""
        session_app = self.get_app_for_session(session_key)

        if config is None:
            config = {
                "configurable": {
                    "thread_id": session_key
                }
            }

        final_state = session_app.invoke(
            {"messages": messages},
            config=config
        )

        return final_state["messages"][-1].content

chatbot_app = ChatbotApp()
