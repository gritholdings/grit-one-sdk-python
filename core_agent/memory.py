from typing import Optional
from django.db import connection
from langgraph.store.postgres import PostgresStore
from core.settings import DATABASE_PASSWORD, AWS_RDS_ENDPOINT


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
    
    def upsert_memory(self, namespace_for_memory: str, thread_id: str, key: str, new_memory: str) -> None:
        if not self.get_memory(namespace_for_memory, thread_id):
            self.put_memory(namespace_for_memory, thread_id, {})
        if key not in self.get_memory(
                namespace_for_memory, thread_id).value:
            self.put_memory(
                namespace_for_memory, thread_id, {key: []})
        current_memory = self.get_memory(
            namespace_for_memory, thread_id).value[key]
        current_memory = current_memory + [new_memory]
        self.put_memory(namespace_for_memory, thread_id, {key: current_memory})