"""Manager per l'interazione ad alto livello con la memoria.

Questo modulo fornisce la classe MemoryManager che astrae le operazioni
SQL grezze e restituisce oggetti Pydantic validati.
"""

import json
from typing import Any, List, Optional

from fluxa.memory.database import Database
from fluxa.memory.models import (
    ContextItem,
    Conversation,
    Image,
    Message,
    MessageRole,
    Task,
    TaskStatus,
    ToolExecution,
    VisionAnalysis,
)

from fluxa.utils.logger import get_logger

logger = get_logger(__name__)

class MemoryManager:
    """Gestore della memoria persistente.

    Fornisce metodi CRUD (Create, Read, Update, Delete) tipizzati
    per tutte le entità del sistema.
    """

    def __init__(self, db: Database):
        """Inizializza il manager con un'istanza del database."""
        self.db = db

    # --- HELPERS ---

    def _to_json(self, data: Any) -> str | None:
        """Converte dati in stringa JSON sicura per il DB."""
        if data is None:
            return None
        return json.dumps(data, default=str)

    def _from_json(self, data: str | None) -> Any:
        """Converte stringa JSON dal DB in dati Python."""
        if not data:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.warning(f"Impossibile decodificare JSON: {data}")
            return {}

    # --- CONVERSATIONS ---

    async def create_conversation(
        self, title: str, metadata: dict[str, Any] | None = None
    ) -> Conversation:
        """Crea una nuova conversazione."""
        query = "INSERT INTO conversations (title, metadata) VALUES (?, ?)"
        params = (title, self._to_json(metadata or {}))

        cursor = await self.db.execute(query, params)
        await self.db.commit()

        return Conversation(
            id=cursor.lastrowid,
            title=title,
            metadata=metadata or {},
        )

    async def get_conversation(self, conversation_id: int) -> Conversation:
        """Recupera una conversazione per ID."""
        query = "SELECT * FROM conversations WHERE id = ?"
        cursor = await self.db.execute(query, (conversation_id,))
        row = await cursor.fetchone()

        if not row:
            return None

        # Mapping manuale da tupla a modello (assumendo ordine colonne standard)
        # id, title, created_at, updated_at, metadata
        return Conversation(
            id=row[0],
            title=row[1],
            created_at=row[2],
            updated_at=row[3],
            metadata=self._from_json(row[4]),
        )

    async def list_conversations(
        self, limit: int = 20, offset: int = 0
    ) -> List[Conversation]:
        """Elenca le conversazioni recenti."""
        query = """
            SELECT * FROM conversations
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """
        cursor = await self.db.execute(query, (limit, offset))
        rows = await cursor.fetchall()

        return [
            Conversation(
                id=row[0],
                title=row[1],
                created_at=row[2],
                updated_at=row[3],
                metadata=self._from_json(row[4]),
            )
            for row in rows
        ]

    async def delete_conversation(self, conversation_id: int) -> bool:
        """Elimina una conversazione e tutti i dati correlati (CASCADE)."""
        query = "DELETE FROM conversations WHERE id = ?"
        cursor = await self.db.execute(query,(conversation_id,))
        await self.db.commit()
        return cursor.rowcount > 0

    # --- MESSAGES ---

    async def add_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        tokens: int = 0,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Aggiunge un messaggio a una conversazione."""
        query = """
            INSERT INTO messages
            (conversation_id, role, content, tokens, model, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            conversation_id,
            role.value,
            content,
            tokens,
            model,
            self._to_json(metadata or {})
        )

        cursor = await self.db.execute(query, params)

        await self.db.commit()

        return Message(
            id=cursor.lastrowid,
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens=tokens,
            model=model,
            metadata=metadata or {},
        )

    async def get_messages(self, conversation_id: int) -> List[Message]:
        """Recupera tutti i messaggi di una conversazione."""
        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC"
        cursor = await self.db.execute(query, (conversation_id,))
        rows = await cursor.fetchall()

        return [
            Message(
                id=row[0],
                conversation_id=row[1],
                role=row[2],
                content=row[3],
                tokens=row[4],
                model=row[5],
                created_at=row[6],
                metadata=self._from_json(row[7]),
            )
            for row in rows
        ]

    # --- IMAGES & VISION ---

    async def add_image(
        self,
        message_id: int,
        file_path: str,
        file_name: str,
        file_size: int,
        mime_type: str,
        width: int | None = None,
        height: int | None = None,
        hash_str: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Image:
        """Registra una nuova immagine nel database."""
        query = """
            INSERT INTO images 
            (message_id, file_path, file_name, file_size, mime_type, width, height, hash, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            message_id, file_path, file_name, file_size, mime_type,
            width, height, hash_str, self._to_json(metadata or {})
        )

        cursor = await self.db.execute(query, params)
        await self.db.commit()

        return Image(
            id=cursor.lastrowid,
            message_id=message_id,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            width=width,
            height=height,
            hash=hash_str,
            metadata=metadata or {}
        )

    async def add_vision_analysis(
        self,
        image_id: int,
        model: str,
        description: str | None = None,
        detected_objects: list[dict] | None = None,
        tags: list[str] | None = None,
        confidence: float | None = None,
        processing_time: float | None = None,
        message_id: int | None = None,
    ) -> VisionAnalysis:
        """Salva i risultati di un'analisi vision."""
        query = """
            INSERT INTO vision_analyses 
            (image_id, message_id, model, description, detected_objects, tags, confidence, processing_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            image_id,
            message_id,
            model,
            description,
            self._to_json(detected_objects or []),
            self._to_json(tags or []),
            confidence,
            processing_time
        )

        cursor = await self.db.execute(query, params)
        await self.db.commit()

        return VisionAnalysis(
            id=cursor.lastrowid,
            image_id=image_id,
            message_id=message_id,
            model=model,
            description=description,
            detected_objects=detected_objects or [],
            tags=tags or [],
            confidence=confidence,
            processing_time=processing_time
        )

    # --- TASKS ---

    async def create_task(
        self, title: str, description: str | None = None, priority: int = 0
    ) -> Task:
        """Crea un nuovo task."""
        query = """
            INSERT INTO tasks (title, description, status, priority)
            VALUES (?, ?, ?, ?)
        """
        cursor = await self.db.execute(query, (title, description, TaskStatus.PENDING.value, priority))
        await self.db.commit()

        return Task(
            id=cursor.lastrowid,
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority
        )

    async def list_tasks(self, status: TaskStatus | None = None) -> List[Task]:
        """Elenca i task, opzionalmente filtrati per stato."""
        if status:
            query = "SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC, created_at DESC"
            params = (status.value,)
        else:
            query = "SELECT * FROM tasks ORDER BY priority DESC, created_at DESC"
            params = ()

        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()

        # id, title, description, status, priority, created_at, updated_at, completed_at, metadata
        return [
            Task(
                id=row[0],
                title=row[1],
                description=row[2],
                status=row[3],
                priority=row[4],
                created_at=row[5],
                updated_at=row[6],
                completed_at=row[7],
                metadata=self._from_json(row[8]),
            )
            for row in rows
        ]

    # --- CONTEXT ---

    async def set_context(self, key: str, value: Any, category: str | None = None) -> ContextItem:
        """Imposta un valore nel contesto (upsert)."""
        query = """
            INSERT INTO context (key, value, category, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                updated_at = CURRENT_TIMESTAMP
        """
        json_val = self._to_json(value)
        await self.db.execute(query, (key, json_val, category))
        await self.db.commit()

        return ContextItem(key=key, value=value, category=category)

    async def get_context(self, key: str) -> Any | None:
        """Recupera un valore dal contesto."""
        query = "SELECT value FROM context WHERE key = ?"
        cursor = await self.db.execute(query, (key,))
        row = await cursor.fetchone()

        if row:
            return self._from_json(row[0])
        return None
