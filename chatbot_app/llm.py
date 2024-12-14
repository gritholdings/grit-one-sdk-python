import json
import os
from typing import Literal
from langchain import hub
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate
from langchain.embeddings.base import Embeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores.chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.tools.retriever import create_retriever_tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from django.contrib.sessions.backends.db import SessionStore
from sentence_transformers import SentenceTransformer
from typing import Dict, Any, List
from datetime import datetime
import uuid
from pydantic import BaseModel, Field


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
        print(f"[DEBUG] Loading memory for thread: {self.thread_id}")
        all_memory = self.session.get('langgraph_memory', {})
        thread_memory = all_memory.get(self.thread_id, {'messages': []})

        if 'messages' not in thread_memory:
            thread_memory['messages'] = []
            print("[DEBUG] Initialized empty messages list for thread")
        else:
            print(f"[DEBUG] Loaded {len(thread_memory['messages'])} existing messages")

        return thread_memory

    def save(self, data: Dict[str, Any]):
        print(f"[DEBUG] Saving memory for thread: {self.thread_id}")
        print(f"[DEBUG] Data to save: {data}")

        all_memory = self.session.get('langgraph_memory', {})
        existing_thread_data = all_memory.get(self.thread_id, {'messages': []})

        if 'messages' in data:
            if isinstance(data['messages'], list):
                existing_messages = existing_thread_data.get('messages', [])
                updated_messages = existing_messages + data['messages']
                data['messages'] = updated_messages
                print(f"[DEBUG] Combined messages count: {len(updated_messages)}")

        all_memory[self.thread_id] = data
        self.session['langgraph_memory'] = all_memory
        self.session.save()
        print("[DEBUG] Memory saved successfully")

        # Update thread metadata
        thread_metadata = self.session.get('thread_metadata', {})
        if self.thread_id not in thread_metadata:
            thread_metadata[self.thread_id] = {
                'created_at': datetime.now().isoformat(),
                'title': self._generate_thread_title(data)
            }
            self.session['thread_metadata'] = thread_metadata
            self.session.save()
            print("[DEBUG] Thread metadata updated")

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


class CustomEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        return [self.model.encode(d).tolist() for d in documents]

    def embed_query(self, query: str) -> List[float]:
        return self.model.encode([query])[0].tolist()


class ChatWorkflow:
    def __init__(self):
        # self.tools = [search]
        # self.tool_node = ToolNode(self.tools)
        self.retriever_tool, self.tools = self.build_tools()
        self.model, self.workflow = self.build_model_and_workflow()

    def build_model_and_workflow(self):
        with open(os.getcwd() + '/credentials.json') as f:
            credentials = json.load(f)
            ANTHROPIC_API_KEY = credentials['ANTHROPIC_API_KEY']
        model = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            temperature=0,
            api_key=ANTHROPIC_API_KEY
        ).bind_tools(self.tools)
        workflow = self._create_workflow()
        return model, workflow

    def build_tools(self):
        retriever = self.create_vectorstore()
        retriever_tool = create_retriever_tool(
            retriever,
            "retrieve_documents",
            "Search and return information.",
        )
        return retriever_tool, [retriever_tool]

    def create_vectorstore(self):
        # Create path to .tmp directory
        tmp_dir = os.path.join(os.getcwd(), '.tmp')

        # Initialize empty list for documents
        docs = []

        # Walk through .tmp directory and find PDF files
        for root, _, files in os.walk(tmp_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_path = os.path.join(root, file)
                    print(f"[DEBUG] Attempting to load PDF: {pdf_path}")
                    try:
                        # Load PDF documents
                        loader = PyPDFLoader(pdf_path)
                        pdf_docs = loader.load()
                        print(f"[DEBUG] Sample content from the first document:\n{pdf_docs[0].page_content[:200]}")
                        docs.extend(pdf_docs)
                    except Exception as e:
                        print(f"Error loading PDF {file}: {str(e)}")

        # If no documents were found, return None or handle appropriately
        if not docs:
            print("No PDF documents found in .tmp directory")
            return None

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=100,
            chunk_overlap=50
        )
        doc_splits = text_splitter.split_documents(docs)

        # Create and return the vectorstore
        vectorstore = Chroma.from_documents(
            documents=doc_splits,
            collection_name="rag-chroma",
            embedding=OpenAIEmbeddings(),
        )
        return vectorstore.as_retriever()

    def refresh_vectorstore(self):
        self.retriever_tool, self.tools = self.build_tools()
        self.model, self.workflow = self.build_model_and_workflow()

    def add_pdf_to_vectorstore(self, pdf_path: str):
        """
        Add a new PDF to the existing vectorstore and update it.
        
        Args:
            pdf_path (str): Path to the PDF file to be added
        """
        try:
            # Load the PDF
            loader = PyPDFLoader(pdf_path)
            new_docs = loader.load()
            print(f"[DEBUG] Loaded PDF from: {pdf_path}")

            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=100,
                chunk_overlap=50
            )
            new_splits = text_splitter.split_documents(new_docs)
            print(f"[DEBUG] Created {len(new_splits)} splits from new PDF")

            # Get the existing vectorstore
            vectorstore = Chroma(
                collection_name="rag-chroma",
                embedding_function=OpenAIEmbeddings()
            )

            # Add new documents to the existing vectorstore
            vectorstore.add_documents(new_splits)
            print(f"[DEBUG] Added {len(new_splits)} new document splits to vectorstore")

            # The vectorstore is automatically persisted in Chroma
            return True

        except Exception as e:
            print(f"Error adding PDF to vectorstore: {str(e)}")
            return False

    def invoke_agent(self, state):
        """
        Invokes the agent model to generate a response based on the current state. Given
        the question, it will decide to retrieve using the retriever tool, or simply end.

        Args:
            state (messages): The current state

        Returns:
            dict: The updated state with the agent response appended to messages
        """
        print("---INVOKE AGENT---")
        messages = state["messages"]
        model_with_tools = self.model.bind_tools(self.tools)
        response = model_with_tools.invoke(messages)
        # We return a list, because this will get added to the existing list
        return {"messages": [response]}

    def determine_documents_relevant(self, state) -> Literal["provide_answer", END]:
        """
        Determines whether the retrieved documents are relevant to the question.

        Args:
            state (messages): The current state

        Returns:
            str: A decision for whether the documents are relevant or not
        """

        print("---CHECK RELEVANCE---")

        # Data model
        class grade(BaseModel):
            """Binary score for relevance check."""

            binary_score: str = Field(description="Relevance score 'yes' or 'no'")

        # LLM with tool and validation
        llm_with_tool = self.model.with_structured_output(grade)

        # Prompt
        prompt = PromptTemplate(
            template="""You are a grader assessing relevance of a retrieved document to a user question. \n 
            Here is the retrieved document: \n\n {context} \n\n
            Here is the user question: {question} \n
            If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
            Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.""",
            input_variables=["context", "question"],
        )

        # Chain
        chain = prompt | llm_with_tool

        messages = state["messages"]
        last_message = messages[-1]

        question = messages[0].content
        docs = last_message.content

        scored_result = chain.invoke({"question": question, "context": docs})

        score = scored_result.binary_score

        if score == "yes":
            print("---DECISION: DOCS RELEVANT---")
            return "provide_answer"

        else:
            print("---DECISION: DOCS NOT RELEVANT---")
            print(score)
            return END

    def provide_answer(self, state):
        """
        Generate answer

        Args:
            state (messages): The current state

        Returns:
            dict: The updated state with re-phrased question
        """
        print("---PROVIDE ANSWER---")
        messages = state["messages"]
        question = messages[0].content
        last_message = messages[-1]

        docs = last_message.content

        # Prompt
        prompt = hub.pull("rlm/rag-prompt")

        # Post-processing
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Chain
        rag_chain = prompt | self.model | StrOutputParser()

        # Run
        response = rag_chain.invoke({"context": docs, "question": question})
        return {"messages": [response]}

    def _create_workflow(self):
        workflow = StateGraph(MessagesState)

        workflow.add_node("invoke_agent", self.invoke_agent)
        retrieve = ToolNode([self.retriever_tool])
        workflow.add_node("retrieve", retrieve)
        workflow.add_node("provide_answer", self.provide_answer)

        workflow.add_edge(START, "invoke_agent")
        # Decide whether to retrieve
        workflow.add_conditional_edges(
            "invoke_agent",
            # Assess agent decision
            tools_condition,
            {
                # Translate the condition outputs to nodes in our graph
                "tools": "retrieve",
                END: END,
            },
        )
        workflow.add_conditional_edges(
            "invoke_agent",
            # Assess agent decision
            self.determine_documents_relevant
        )
        workflow.add_edge("provide_answer", END)
        return workflow

    def get_compiled_workflow(self, checkpointer=None):
        if checkpointer is None:
            checkpointer = MemorySaver()
        return self.workflow.compile(checkpointer=checkpointer)


class ChatbotApp:
    def __init__(self):
        self.vectorstore_path = os.path.join(os.getcwd(), 'vectorstores')
        os.makedirs(self.vectorstore_path, exist_ok=True)

        # Create the workflow once
        self._initialize_workflow()

        # File upload configuration
        self.allowed_file_types = {
            'text/plain': ['.txt', '.md', '.py', '.json'],
            'application/pdf': ['.pdf'],
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png']
        }
        self.max_file_size = 20 * 1024 * 1024  # 20MB limit

    def _initialize_workflow(self):
        self.chat_workflow = ChatWorkflow()
        self.session_app = self.chat_workflow.get_compiled_workflow()

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
        return thread_id

    def _get_thread_vectorstore_path(self, thread_id: str) -> str:
        """Get the path for a thread's vectorstore"""
        return os.path.join(os.path.join(os.getcwd(), '.tmp'), f'vectorstore_{thread_id}')

    def get_app_for_session(self, session_key: str, thread_id: str):
        """Get a compiled app instance for a specific session and thread"""
        # checkpointer = DjangoSessionMemorySaver(session_key, thread_id)
        chat_workflow = ChatWorkflow()
        return chat_workflow.get_compiled_workflow()

    def process_chat(self, session_key: str, thread_id: str, new_message: str, config: dict = None) -> str:
        """Process chat messages for a specific thread and return the response"""
        print(f"[DEBUG] Processing message for thread: {thread_id}, session: {session_key}")

        if config is None:
            config = {
                "configurable": {
                    "thread_id": thread_id
                }
            }

        final_state = self.session_app.invoke(
            {"messages": [{"role": "user", "content": new_message}]},
            config=config
        )

        return final_state["messages"][-1].content

# Initialize the chatbot app as a singleton
chatbot_app = ChatbotApp()