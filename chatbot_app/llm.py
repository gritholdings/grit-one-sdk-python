import json
import os
from typing import Literal
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain.embeddings.base import Embeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores.chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from django.contrib.sessions.backends.db import SessionStore
from sentence_transformers import SentenceTransformer
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import uuid
import mimetypes


class ThreadInfo:
    def __init__(self, thread_id: str, created_at: datetime, title: str = None):
        self.thread_id = thread_id
        self.created_at = created_at
        self.title = title


class DjangoSessionMemorySaver(MemorySaver):
    def __init__(self, session_key: str, thread_id: str):
        super().__init__()
        self.session_key = session_key
        self.thread_id = thread_id
        self.session = SessionStore(session_key=session_key)

    def load(self) -> Dict[str, Any]:
        # Get all memory data for the session
        all_memory = self.session.get('langgraph_memory', {})
        # Return thread-specific memory or empty dict if thread doesn't exist
        return all_memory.get(self.thread_id, {})

    def save(self, data: Dict[str, Any]):
        # Get existing memory data
        all_memory = self.session.get('langgraph_memory', {})
        # Update memory for specific thread
        all_memory[self.thread_id] = data
        # Save all memory back to session
        self.session['langgraph_memory'] = all_memory
        self.session.save()

        # Update thread metadata when saving
        thread_metadata = self.session.get('thread_metadata', {})
        if self.thread_id not in thread_metadata:
            thread_metadata[self.thread_id] = {
                'created_at': datetime.now().isoformat(),
                'title': self._generate_thread_title(data)
            }
            self.session['thread_metadata'] = thread_metadata
            self.session.save()

    def _generate_thread_title(self, data: Dict[str, Any]) -> str:
        """Generate a title based on the first message in the thread"""
        messages = data.get('messages', [])
        if messages and len(messages) > 0:
            first_message = messages[0]
            # Truncate message content to create a title
            content = first_message.content if hasattr(first_message, 'content') else str(first_message)
            return content[:50] + ('...' if len(content) > 50 else '')
        return f"Thread {self.thread_id[:8]}"

    @classmethod
    def get_threads(cls, session_key: str) -> List[ThreadInfo]:
        """Get all threads for a session"""
        session = SessionStore(session_key=session_key)
        thread_metadata = session.get('thread_metadata', {})

        threads = []
        for thread_id, metadata in thread_metadata.items():
            thread = ThreadInfo(
                thread_id=thread_id,
                created_at=datetime.fromisoformat(metadata['created_at']),
                title=metadata.get('title')
            )
            threads.append(thread)

        # Sort threads by creation date, newest first
        return sorted(threads, key=lambda x: x.created_at, reverse=True)

@tool
def search(query: str):
    """Placeholder function"""
    pass


class CustomEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        return [self.model.encode(d).tolist() for d in documents]

    def embed_query(self, query: str) -> List[float]:
        return self.model.encode([query])[0].tolist()


class ChatbotApp:
    def __init__(self):
        self.tools = [search]
        self.tool_node = ToolNode(self.tools)
        with open(os.getcwd() + '/credentials.json') as f:
            credentials = json.load(f)
            ANTHROPIC_API_KEY = credentials['ANTHROPIC_API_KEY']
            self.model = ChatAnthropic(
                model="claude-3-5-sonnet-20240620",
                temperature=0,
                api_key=ANTHROPIC_API_KEY
            ).bind_tools(self.tools)

        # Create the workflow once
        self.workflow = self._create_workflow()

        # File upload configuration
        self.allowed_file_types = {
            'text/plain': ['.txt', '.md', '.py', '.json'],
            'application/pdf': ['.pdf'],
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png']
        }
        self.max_file_size = 20 * 1024 * 1024  # 20MB limit

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

    def get_thread_list(self, session_key: str) -> List[Dict[str, Any]]:
        """Get list of threads for a session"""
        threads = DjangoSessionMemorySaver.get_threads(session_key)
        return [
            {
                'thread_id': thread.thread_id,
                'created_at': thread.created_at.isoformat(),
                'title': thread.title
            }
            for thread in threads
        ]

    def create_new_thread(self, session_key: str) -> str:
        """Create a new thread and return its ID"""
        thread_id = str(uuid.uuid4())
        # Initialize the thread in session
        checkpointer = DjangoSessionMemorySaver(session_key, thread_id)
        # Save empty state to create thread metadata
        checkpointer.save({'messages': []})
        return thread_id

    def attach_file_to_thread(
            self,
            session_key: str,
            thread_id: str,
            file_path: str,
            file_name: str
        ):
        """
        Attach a file to a specific thread and process it for question answering.
        
        Args:
            session_key (str): Django session key
            thread_id (str): UUID of the thread
            file_path (str): Path to the temporary uploaded file
            file_name (str): Original filename
        
        Raises:
            ValueError: If file type is not supported or file is too large
        """
        # Validate file type
        file_extension = Path(file_name).suffix.lower()
        valid_extension = False
        file_type = None

        for mime_type, extensions in self.allowed_file_types.items():
            if file_extension in extensions:
                valid_extension = True
                file_type = mime_type
                break

        if not valid_extension:
            raise ValueError(f"Unsupported file type: {file_extension}")

        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size:
            raise ValueError(f"File too large. Maximum size is {self.max_file_size / (1024*1024)}MB")

        # Get current thread state
        checkpointer = DjangoSessionMemorySaver(session_key, thread_id)
        current_state = checkpointer.load()

        # Initialize or get file attachments from state
        if 'file_attachments' not in current_state:
            current_state['file_attachments'] = []
            current_state['vectorstore'] = None

        # Add file metadata to thread state
        file_info = {
            'file_name': file_name,
            'file_type': file_type,
            'upload_time': datetime.now().isoformat(),
        }
        current_state['file_attachments'].append(file_info)

        # Handle PDFs for question answering
        if file_type == 'application/pdf':
            # Initialize embedding model and vectorstore if not exists
            if current_state['vectorstore'] is None:
                embedding_model = CustomEmbeddings(model_name="all-MiniLM-L6-v2")
                current_state['vectorstore'] = Chroma(
                    embedding_function=embedding_model
                )

            # Initialize text splitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )

            try:
                # Load and process document
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                splits = text_splitter.split_documents(docs)

                # Add to vectorstore
                current_state['vectorstore'].add_documents(splits)

                # Add system message about the uploaded PDF
                if 'messages' not in current_state:
                    current_state['messages'] = []

                system_message = {
                    'role': 'system',
                    'content': f'PDF document "{file_name}" has been uploaded and processed for question answering. {len(splits)} chunks were added to the knowledge base.'
                }
                current_state['messages'].append(system_message)

            except Exception as e:
                system_message = {
                    'role': 'system',
                    'content': f'Error processing PDF document "{file_name}": {str(e)}'
                }
                current_state['messages'].append(system_message)

        # Save updated state
        checkpointer.save(current_state)



    def get_app_for_session(self, session_key: str, thread_id: str):
        """Get a compiled app instance for a specific session and thread"""
        checkpointer = DjangoSessionMemorySaver(session_key, thread_id)
        return self.workflow.compile(checkpointer=checkpointer)

    def process_chat(self, session_key: str, thread_id: str, messages: list, config: dict = None) -> str:
        """Process chat messages for a specific thread and return the response"""
        session_app = self.get_app_for_session(session_key, thread_id)

        if config is None:
            config = {
                "configurable": {
                    "session_key": session_key,
                    "thread_id": thread_id
                }
            }

        final_state = session_app.invoke(
            {"messages": messages},
            config=config
        )

        return final_state["messages"][-1].content

# Initialize the chatbot app as a singleton
chatbot_app = ChatbotApp()