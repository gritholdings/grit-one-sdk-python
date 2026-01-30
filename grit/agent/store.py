import random
import string
from typing import Optional, Dict, Any, List
from grit.core.utils.env_config import load_credential
from grit.core.utils.github import GithubClient


class MemoryStoreServiceConfig:
    pass


class MemoryWrapper:
    def __init__(self, memory):
        self.key = str(memory.thread_id)
        self.value = {
            'conversation_history': memory.conversation_history or [],
            'current_agent_id': str(memory.current_agent_id) if memory.current_agent_id else None,
            'created_at': memory.created_at.isoformat() if memory.created_at else None,
            'updated_at': memory.updated_at.isoformat() if memory.updated_at else None,
        }


class MemoryStoreService:
    def __init__(self, config: Optional[MemoryStoreServiceConfig] = None):
        self.config = config
    def close(self):
        pass
    def _get_user_id_from_namespace(self, namespace_for_memory: tuple) -> str:
        return namespace_for_memory[1]
    def put_memory(self, namespace_for_memory, thread_id, memory):
        from .models import ConversationMemory, Agent
        user_id = self._get_user_id_from_namespace(namespace_for_memory)
        current_agent = None
        current_agent_id = memory.get('current_agent_id') if isinstance(memory, dict) else None
        if current_agent_id:
            try:
                current_agent = Agent.objects.get(id=current_agent_id)
            except Agent.DoesNotExist:
                pass
        ConversationMemory.objects.update_or_create(
            user_id=user_id,
            thread_id=thread_id,
            defaults={
                'conversation_history': memory.get('conversation_history', []) if isinstance(memory, dict) else [],
                'current_agent': current_agent,
            }
        )
    def get_memory(self, namespace_for_memory, thread_id):
        from .models import ConversationMemory
        user_id = self._get_user_id_from_namespace(namespace_for_memory)
        try:
            memory = ConversationMemory.objects.get(user_id=user_id, thread_id=thread_id)
            return MemoryWrapper(memory)
        except ConversationMemory.DoesNotExist:
            return None
    def list_memories(self, namespace_for_memory):
        from .models import ConversationMemory
        user_id = self._get_user_id_from_namespace(namespace_for_memory)
        memories = ConversationMemory.objects.filter(user_id=user_id).order_by('-updated_at')[:20]
        return [MemoryWrapper(m) for m in memories]
    def upsert_memory(self, namespace_for_memory: tuple, thread_id: str, key: str, new_memory: str) -> None:
        if not isinstance(namespace_for_memory, tuple):
            raise TypeError("namespace_for_memory must be a tuple")
        from .models import ConversationMemory
        user_id = self._get_user_id_from_namespace(namespace_for_memory)
        memory, created = ConversationMemory.objects.get_or_create(
            user_id=user_id,
            thread_id=thread_id,
            defaults={'conversation_history': []}
        )
        if key == 'conversation_history':
            history = memory.conversation_history or []
            history.append(new_memory)
            memory.conversation_history = history
            memory.save(update_fields=['conversation_history', 'updated_at'])
    def delete_memory(self, namespace_for_memory: tuple, thread_id: str) -> bool:
        from .models import ConversationMemory
        user_id = self._get_user_id_from_namespace(namespace_for_memory)
        deleted, _ = ConversationMemory.objects.filter(
            user_id=user_id,
            thread_id=thread_id
        ).delete()
        return deleted > 0
    def get_current_agent_id(self, user_id: str, thread_id: str) -> Optional[str]:
        from .models import ConversationMemory
        try:
            memory = ConversationMemory.objects.get(user_id=user_id, thread_id=thread_id)
            return str(memory.current_agent_id) if memory.current_agent_id else None
        except ConversationMemory.DoesNotExist:
            return None
    def set_current_agent_id(self, user_id: str, thread_id: str, agent_id: str) -> None:
        from .models import ConversationMemory, Agent
        current_agent = None
        try:
            current_agent = Agent.objects.get(id=agent_id)
        except Agent.DoesNotExist:
            pass
        ConversationMemory.objects.update_or_create(
            user_id=user_id,
            thread_id=thread_id,
            defaults={
                'current_agent': current_agent,
            }
        )
    def get_memories_by_date_range(self, user_ids: list, from_date: str, to_date: str) -> list:
        from .models import ConversationMemory
        from django.utils.dateparse import parse_datetime
        from_dt = parse_datetime(from_date)
        to_dt = parse_datetime(to_date)
        memories = ConversationMemory.objects.filter(
            user_id__in=user_ids,
            updated_at__gte=from_dt,
            updated_at__lte=to_dt
        ).exclude(conversation_history=[])
        return [
            {
                'user_id': str(m.user_id),
                'thread_id': str(m.thread_id),
                'conversation_history': m.conversation_history,
                'created_at': m.created_at.isoformat() if m.created_at else None,
                'updated_at': m.updated_at.isoformat() if m.updated_at else None,
            }
            for m in memories
        ]


class KnowledgeBaseVectorStoreServiceConfig:
    def __init__(
        self,
        embedding_dims: int = 1536,
        openai_embedding_model: str = "text-embedding-3-small",
    ):
        self.embedding_dims = embedding_dims
        self.openai_embedding_model = openai_embedding_model


class KnowledgeBaseVectorStoreService:
    def __init__(self, config: Optional[KnowledgeBaseVectorStoreServiceConfig] = None):
        self.config = config or KnowledgeBaseVectorStoreServiceConfig()
        self._client = None
        self.github_client = GithubClient(token=None)
    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=load_credential("OPENAI_API_KEY"))
        return self._client
    def _get_embedding(self, text: str) -> List[float]:
        response = self._get_client().embeddings.create(
            model=self.config.openai_embedding_model,
            input=text
        )
        return response.data[0].embedding
    def close(self):
        pass
    def create_knowledge_base_id(self) -> str:
        return ''.join(random.choice(string.ascii_uppercase) for _ in range(10))
    def add_document(
        self,
        *,
        knowledge_base_id: str,
        file_path: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 300
    ) -> str:
        from .models import KnowledgeBaseChunk, KnowledgeBase
        from django.db import connection
        if not isinstance(text, str):
            raise ValueError("Text must be a string")
        kb, _ = KnowledgeBase.objects.get_or_create(
            id=knowledge_base_id,
            defaults={'name': f'KB-{knowledge_base_id}'}
        )
        tokens = text.split()
        total_tokens = len(tokens)
        for idx in range(0, total_tokens, chunk_size):
            chunk_tokens = tokens[idx:idx + chunk_size]
            chunk_text = " ".join(chunk_tokens)
            chunk_index = idx // chunk_size
            embedding = self._get_embedding(chunk_text)
            chunk, created = KnowledgeBaseChunk.objects.update_or_create(
                knowledge_base=kb,
                file_path=file_path,
                chunk_index=chunk_index,
                defaults={
                    'text': chunk_text,
                    'metadata': metadata or {},
                    'embedding': embedding,
                }
            )
            if connection.vendor == 'postgresql':
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE core_agent_knowledgebasechunk
                        SET embedding_vector = json_to_vector(%s::jsonb)
                        WHERE id = %s
                    """, [chunk.embedding, str(chunk.id)])
        return knowledge_base_id
    def get_document(
        self,
        knowledge_base_id: str,
        file_path: str,
    ) -> Optional[Dict[str, Any]]:
        from .models import KnowledgeBaseChunk
        try:
            chunk = KnowledgeBaseChunk.objects.get(
                knowledge_base_id=knowledge_base_id,
                file_path=file_path,
                chunk_index=0
            )
            return {'text': chunk.text, 'metadata': chunk.metadata}
        except KnowledgeBaseChunk.DoesNotExist:
            return None
    def search_documents(
        self,
        *,
        knowledge_base_id: str,
        query: str,
        filter_metadata: Optional[Dict[str, Any]] = None,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        from .models import KnowledgeBaseChunk
        from django.db import connection
        query_embedding = self._get_embedding(query)
        if connection.vendor == 'postgresql':
            return self._search_with_pgvector(
                knowledge_base_id, query_embedding, filter_metadata, limit
            )
        else:
            return self._search_fallback(knowledge_base_id, query, limit)
    def _search_with_pgvector(
        self,
        knowledge_base_id: str,
        query_embedding: List[float],
        filter_metadata: Optional[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        from django.db import connection
        base_query = """
            SELECT id, text, metadata, file_path, chunk_index,
                   1 - (embedding_vector <=> %s::vector) as score
            FROM core_agent_knowledgebasechunk
            WHERE knowledge_base_id = %s
              AND embedding_vector IS NOT NULL
        """
        params = [str(query_embedding), knowledge_base_id]
        if filter_metadata:
            for key, value in filter_metadata.items():
                base_query += f" AND metadata->>'{key}' = %s"
                params.append(str(value))
        base_query += " ORDER BY embedding_vector <=> %s::vector LIMIT %s"
        params.extend([str(query_embedding), limit])
        with connection.cursor() as cursor:
            cursor.execute(base_query, params)
            rows = cursor.fetchall()
        return [
            {
                'text': row[1],
                'metadata': row[2] or {},
                'knowledge_base_id': f"{row[3]}_chunk_{row[4]}",
                'score': float(row[5]) if row[5] else 0.0,
            }
            for row in rows
        ]
    def _search_fallback(
        self,
        knowledge_base_id: str,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        from .models import KnowledgeBaseChunk
        chunks = KnowledgeBaseChunk.objects.filter(
            knowledge_base_id=knowledge_base_id,
            text__icontains=query.split()[0] if query.split() else ''
        )[:limit]
        return [
            {
                'text': chunk.text,
                'metadata': chunk.metadata or {},
                'knowledge_base_id': f"{chunk.file_path}_chunk_{chunk.chunk_index}",
                'score': 0.5,
            }
            for chunk in chunks
        ]
    async def asearch_documents(
        self,
        *,
        knowledge_base_id: str,
        query: str,
        filter_metadata: Optional[Dict[str, Any]] = None,
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        from asgiref.sync import sync_to_async
        return await sync_to_async(self.search_documents)(
            knowledge_base_id=knowledge_base_id,
            query=query,
            filter_metadata=filter_metadata,
            limit=limit
        )
    def delete_document(
        self,
        knowledge_base_id: str,
        file_path: str
    ) -> bool:
        from .models import KnowledgeBaseChunk
        deleted, _ = KnowledgeBaseChunk.objects.filter(
            knowledge_base_id=knowledge_base_id,
            file_path=file_path
        ).delete()
        return deleted > 0
    def list_documents(
        self,
        knowledge_base_id: str,
        prefix: str,
    ) -> List[str]:
        from .models import KnowledgeBaseChunk
        file_paths = KnowledgeBaseChunk.objects.filter(
            knowledge_base_id=knowledge_base_id,
            file_path__startswith=prefix
        ).values_list('file_path', flat=True).distinct()
        return list(file_paths)