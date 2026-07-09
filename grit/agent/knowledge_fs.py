import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional
from .settings import agent_settings
logger = logging.getLogger(__name__)
_SYNC_MARKER = ".kb_sync.json"


def get_knowledge_base_root() -> Path:
    configured = getattr(agent_settings, 'KNOWLEDGE_BASE_ROOT', None)
    root = Path(configured) if configured else Path(tempfile.gettempdir()) / 'grit_knowledge_base'
    return root


def _safe_destination(base_dir: Path, relative_path: str) -> Optional[Path]:
    base_resolved = base_dir.resolve()
    candidate = (base_dir / relative_path).resolve()
    if candidate == base_resolved or base_resolved not in candidate.parents:
        logger.warning("Rejecting knowledge-base path outside its directory: %r", relative_path)
        return None
    return candidate


def upsert_knowledge_file(*, knowledge_base_id: str, path: str, content: str) -> None:
    from .models import KnowledgeBaseFile, KnowledgeBase
    if not isinstance(content, str):
        raise ValueError("content must be a string")
    kb, _ = KnowledgeBase.objects.get_or_create(
        id=knowledge_base_id,
        defaults={'name': f'KB-{knowledge_base_id}'}
    )
    KnowledgeBaseFile.objects.update_or_create(
        knowledge_base=kb,
        path=path,
        defaults={'content': content},
    )


def list_knowledge_file_paths(*, knowledge_base_id: str, prefix: str = "") -> List[str]:
    from .models import KnowledgeBaseFile
    queryset = KnowledgeBaseFile.objects.filter(knowledge_base_id=knowledge_base_id)
    if prefix:
        queryset = queryset.filter(path__startswith=prefix)
    return list(queryset.values_list('path', flat=True))


def delete_knowledge_file(*, knowledge_base_id: str, path: str) -> bool:
    from .models import KnowledgeBaseFile
    deleted, _ = KnowledgeBaseFile.objects.filter(
        knowledge_base_id=knowledge_base_id,
        path=path,
    ).delete()
    return deleted > 0


def materialize_knowledge_base(knowledge_base_id: str) -> Optional[str]:
    from .models import KnowledgeBaseFile
    knowledge_base_id = str(knowledge_base_id)
    dest = get_knowledge_base_root() / knowledge_base_id
    marker = dest / _SYNC_MARKER
    files = list(
        KnowledgeBaseFile.objects.filter(knowledge_base_id=knowledge_base_id)
        .values('path', 'content', 'updated_at')
    )
    if not files:
        return None
    latest = max((f['updated_at'] for f in files), default=None)
    signature = {'count': len(files), 'latest': latest.isoformat() if latest else None}
    if marker.exists():
        try:
            if json.loads(marker.read_text()) == signature:
                return str(dest)
        except (json.JSONDecodeError, OSError):
            pass
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)
    for file_row in files:
        destination = _safe_destination(dest, file_row['path'])
        if destination is None:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(file_row['content'] or "")
    marker.write_text(json.dumps(signature))
    return str(dest)


def materialize_knowledge_bases(knowledge_bases: Optional[List[dict]]) -> List[str]:
    if not knowledge_bases:
        return []
    directories: List[str] = []
    for knowledge_base in knowledge_bases:
        kb_id = knowledge_base.get('id') if isinstance(knowledge_base, dict) else None
        if not kb_id:
            continue
        try:
            directory = materialize_knowledge_base(str(kb_id))
        except Exception as exc:
            logger.warning("Failed to materialise knowledge base %s: %s", kb_id, exc, exc_info=True)
            directory = None
        if directory:
            directories.append(directory)
    return directories
KNOWLEDGE_BASE_SYSTEM_PROMPT_SUFFIX = (
    "\n\nYou have access to a knowledge base mounted as files in your working "
    "directory. When a question may be answered by that material, use the Glob, "
    "Grep, and Read tools to find and read the relevant files before answering. "
    "Cite the file paths you relied on."
)
_MAX_READ_CHARS = 20000
_MAX_SEARCH_HITS = 50


def _iter_knowledge_paths(directories: List[str]):
    for directory in directories:
        base = Path(directory)
        if not base.is_dir():
            continue
        for file_path in base.rglob('*'):
            if file_path.is_file() and file_path.name != _SYNC_MARKER:
                yield base, file_path.relative_to(base).as_posix()


def build_knowledge_base_tools(directories: List[str]) -> list:
    if not directories:
        return []
    try:
        from agents import function_tool
    except ImportError:
        logger.warning("openai-agents not installed; knowledge base tools unavailable")
        return []
    @function_tool
    def list_knowledge_files() -> str:
        paths = sorted(rel for _, rel in _iter_knowledge_paths(directories))
        return "\n".join(paths) if paths else "(knowledge base is empty)"
    @function_tool
    def read_knowledge_file(path: str) -> str:
        for base, rel in _iter_knowledge_paths(directories):
            if rel == path:
                text = (base / rel).read_text(errors='replace')
                return text[:_MAX_READ_CHARS]
        return f"File not found: {path}"
    @function_tool
    def search_knowledge(query: str) -> str:
        needle = query.lower()
        hits: List[str] = []
        for base, rel in _iter_knowledge_paths(directories):
            try:
                lines = (base / rel).read_text(errors='replace').splitlines()
            except OSError:
                continue
            for line_number, line in enumerate(lines, start=1):
                if needle in line.lower():
                    hits.append(f"{rel}:{line_number}: {line.strip()}")
                    if len(hits) >= _MAX_SEARCH_HITS:
                        return "\n".join(hits) + "\n... (more matches truncated)"
        return "\n".join(hits) if hits else f"No matches for: {query}"
    return [list_knowledge_files, read_knowledge_file, search_knowledge]
