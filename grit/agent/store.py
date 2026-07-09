from typing import Optional


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
        from django.core.exceptions import ValidationError
        current_agent = None
        try:
            current_agent = Agent.objects.get(id=agent_id)
        except (Agent.DoesNotExist, ValidationError, ValueError):
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
