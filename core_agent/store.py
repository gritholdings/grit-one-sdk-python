import random
import string
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from langchain_openai import OpenAIEmbeddings
from langgraph.store.postgres import PostgresStore
from core.settings import DATABASE_PASSWORD, AWS_RDS_ENDPOINT
from core.utils.env_config import load_credential
from core.utils.github import GithubClient


class MemoryStoreServiceConfig:
    pass


class MemoryStoreService:
    def __init__(self, config: Optional[MemoryStoreServiceConfig] = None):
        self.config = config
        self._store = None
        self._store_ctx = None
        # Store the conn_string as an attribute so we can set up the store lazily if desired.
        self._conn_string = f"postgresql://postgres:{DATABASE_PASSWORD}@{AWS_RDS_ENDPOINT}:5432/postgres"

    def get_store(self) -> PostgresStore:
        """
        Create a PostgresStore connection only once (lazy loading).
        If the store already exists, just return it.
        """
        if self._store is None:
            self._store_ctx = PostgresStore.from_conn_string(self._conn_string)
            # Manually enter the context
            self._store = self._store_ctx.__enter__()
            self._store.setup()
        return self._store
    
    def close(self):
        """
        Close the store connection if it's open.
        """
        if self._store is not None:
            # Manually exit the context
            self._store_ctx.__exit__(None, None, None)
            self._store = None
            self._store_ctx = None

    def put_memory(self, namespace_for_memory, thread_id, memory):
        store = self.get_store()
        store.put(namespace_for_memory, thread_id, memory)

    def get_memory(self, namespace_for_memory, thread_id):
        store = self.get_store()
        return store.get(namespace_for_memory, thread_id)
    
    def list_memories(self, namespace_for_memory):
        store = self.get_store()
        memories = store.search(namespace_for_memory, limit=20)
        return memories
    
    def upsert_memory(self, namespace_for_memory: tuple, thread_id: str, key: str, new_memory: str) -> None:
        if not isinstance(namespace_for_memory, tuple):
            raise TypeError("namespace_for_memory must be a tuple")
        
        now = datetime.now().isoformat()
        
        # Check if thread exists, if not create empty dict with timestamps
        memory_obj = self.get_memory(namespace_for_memory, thread_id)
        if not memory_obj:
            initial_data = {
                'created_at': now,
                'updated_at': now
            }
            self.put_memory(namespace_for_memory, thread_id, initial_data)
        
        # Check if key exists in memory, if not create empty list for that key
        memory_obj = self.get_memory(namespace_for_memory, thread_id)
        memory_data = memory_obj.value if memory_obj else {}
        
        # Set created_at if this is the first time creating the key
        if key not in memory_data:
            memory_data[key] = []
            memory_data['created_at'] = memory_data.get('created_at', now)
        
        # Always update updated_at when modifying memory
        memory_data['updated_at'] = now
        
        # Get the current memory for the key and append new memory
        current_memory = memory_data[key]
        current_memory = current_memory + [new_memory]
        memory_data[key] = current_memory
        
        self.put_memory(namespace_for_memory, thread_id, memory_data)
    
    def delete_memory(self, namespace_for_memory: tuple, thread_id: str) -> bool:
        """
        Delete a specific memory record.
        
        Args:
            namespace_for_memory: The namespace tuple for the memory
            thread_id: The thread ID for the memory
            
        Returns:
            True if memory was deleted, False if it didn't exist
        """
        store = self.get_store()
        memory_obj = self.get_memory(namespace_for_memory, thread_id)
        if not memory_obj:
            return False
        
        store.delete(namespace_for_memory, thread_id)
        return True
    
    def get_memories_by_date_range(self, user_ids: list, from_date: str, to_date: str) -> list:
        """
        Get memories for multiple users within a date range.
        
        Args:
            user_ids: List of user IDs to search
            from_date: Start date (ISO format string)
            to_date: End date (ISO format string)
            
        Returns:
            List of conversation histories with metadata
        """
        store = self.get_store()
        all_conversations = []
        
        for user_id in user_ids:
            namespace_for_memory = ("memories", str(user_id))
            memories = store.search(namespace_for_memory, limit=100)
            
            for memory in memories:
                memory_data = memory.value
                created_at = memory_data.get('created_at')
                updated_at = memory_data.get('updated_at')
                
                # Filter by date range using created_at or updated_at
                date_to_check = updated_at or created_at
                if date_to_check and from_date <= date_to_check <= to_date:
                    conversation_history = memory_data.get('conversation_history', [])
                    if conversation_history:
                        all_conversations.append({
                            'user_id': user_id,
                            'thread_id': memory.key,
                            'conversation_history': conversation_history,
                            'created_at': created_at,
                            'updated_at': updated_at
                        })
        
        return all_conversations


class KnowledgeBaseVectorStoreServiceConfig:
    def __init__(
        self,
        embedding_dims: int = 1536,
        openai_embedding_model: str = "text-embedding-3-small",
        base_document_namespace: Tuple = ("knowledge_base",),
    ):
        self.embedding_dims = embedding_dims
        self.openai_embedding_model = openai_embedding_model
        self.base_document_namespace = base_document_namespace


class KnowledgeBaseVectorStoreService:
    def __init__(self, config: Optional[KnowledgeBaseVectorStoreServiceConfig] = None):
        self.config = config or KnowledgeBaseVectorStoreServiceConfig()
        self._store = None
        self._store_ctx = None
        self._conn_string = f"postgresql://postgres:{DATABASE_PASSWORD}@{AWS_RDS_ENDPOINT}:5432/postgres"
        self.github_client = GithubClient(token=None)

    def get_store(self) -> PostgresStore:
        """
        Create a PostgresStore connection with vector search capability.
        """
        if self._store is None:
            # Configure vector search capability
            embed_fn = OpenAIEmbeddings(model=self.config.openai_embedding_model,
                                openai_api_key=load_credential("OPENAI_API_KEY"))
            
            # Create store with vector search capabilities
            self._store_ctx = PostgresStore.from_conn_string(
                self._conn_string,
                index={
                    "dims": self.config.embedding_dims,
                    "embed": embed_fn,
                    "fields": ["text"]  # We'll embed the text field
                }
            )
            # Enter the context
            self._store = self._store_ctx.__enter__()
            self._store.setup()
        return self._store
    
    def close(self):
        """Close the store connection if it's open."""
        if self._store is not None:
            self._store_ctx.__exit__(None, None, None)
            self._store = None
            self._store_ctx = None

    def create_knowledge_base_id(self):
        # Generate document ID if not provided
        # For knowledge base id, generate a random string of 10 uppercase letters
        knowledge_base_id = ''.join(random.choice(string.ascii_uppercase) for _ in range(10))
        return knowledge_base_id

    def add_document(
        self,
        *,
        knowledge_base_id: str,
        file_path: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 300
    ) -> str:
        """
        Add a single document to the vector store.
        
        Args:
            knowledge_base_id: Optional document ID, generated if not provided
            text: The document text to store and embed
            metadata: Optional metadata about the document

        Returns:
            The document ID
        """
        if not isinstance(text, str):
            raise ValueError("Text must be a string")
        store = self.get_store()

        # Store the document with vector indexing
        document_namespace = self.config.base_document_namespace + (knowledge_base_id,)
        # Naive splitting by whitespace into "tokens"/words
        tokens = text.split()
        total_tokens = len(tokens)
        # Split into chunks of size ~300 words
        for idx in range(0, total_tokens, chunk_size):
            chunk_tokens = tokens[idx : idx + chunk_size]
            chunk_text = " ".join(chunk_tokens)

            chunk_doc = {
                "text": chunk_text,
                "metadata": metadata or {}
            }
            # Optionally append a chunk index to distinguish each part
            chunk_file_path = f"{file_path}_chunk_{idx//chunk_size}"

            store.put(document_namespace, chunk_file_path, chunk_doc, index=["text"])
        return knowledge_base_id
    
    def get_document(
        self,
        knowledge_base_id: str,
        file_path: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by its ID.
        
        Args:
            doc_id: The document ID to retrieve
            
        Returns:
            The document if found, None otherwise
        """
        store = self.get_store()
        document_namespace = self.config.base_document_namespace + (knowledge_base_id,)
        item = store.get(document_namespace, file_path)
        return item.value if item else None
    
    def search_documents(
        self,
        *,
        knowledge_base_id: str,
        query: str,
        filter_metadata: Optional[Dict[str, Any]] = None,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Search documents by semantic similarity to the query.
        
        Args:
            query: Natural language query for semantic search
            filter_metadata: Optional metadata filter criteria
            limit: Maximum number of results to return
            
        Returns:
            List of documents sorted by relevance to the query
        """
        store = self.get_store()
        document_namespace = self.config.base_document_namespace + (knowledge_base_id,)
        results = store.search(
            document_namespace, 
            query=query, 
            filter=filter_metadata, 
            limit=limit
        )
        
        # Format results
        formatted_results = []
        for item in results:
            doc = item.value
            doc["knowledge_base_id"] = item.key
            doc["score"] = item.score  # Add similarity score
            formatted_results.append(doc)
            
        return formatted_results
    
    async def asearch_documents(
        self,
        *,
        knowledge_base_id: str,
        query: str, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Asynchronously search documents by semantic similarity.
        
        Args:
            query: Natural language query for semantic search
            filter_metadata: Optional metadata filter criteria
            limit: Maximum number of results to return
            
        Returns:
            List of documents sorted by relevance to the query
        """
        store = self.get_store()
        document_namespace = self.config.base_document_namespace + (knowledge_base_id,)
        results = await store.asearch(
            document_namespace, 
            query, 
            filter=filter_metadata, 
            limit=limit
        )
        
        # Format results
        formatted_results = []
        for item in results:
            doc = item.value
            doc["knowledge_base_id"] = item.key
            doc["score"] = item.score
            formatted_results.append(doc)
            
        return formatted_results
    
    def delete_document(
        self,
        knowledge_base_id: str,
        file_path: str
    ) -> bool:
        """
        Delete a document by its ID.
        
        Args:
            knowledge_base_id: The document ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        store = self.get_store()
        document_namespace = self.config.base_document_namespace + (knowledge_base_id,)
        item = store.get(document_namespace, file_path)
        if not item:
            return False
        
        store.delete(document_namespace, file_path)
        return True
    
    def list_documents(
        self,
        knowledge_base_id: str,
        prefix: str,
    ) -> List[str]:
        """
        List all documents in a knowledge base with a specific prefix.
        
        Args:
            knowledge_base_id: The knowledge base ID to search
            prefix: The prefix to filter documents
            max_depth: Maximum depth for listing"
        """
        store = self.get_store()
        document_namespace = self.config.base_document_namespace + (knowledge_base_id,)
        documents = store.search(document_namespace)
        filtered_documents = [item.key for item in documents if item.key.startswith(prefix)]
        return filtered_documents