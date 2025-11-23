"""Modelli dati Pydantic per il sistema di memoria.

Questo modulo definisce le strutture dati utilizzate per interagire
con il database, garantendo validazione e type safety.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- ENUMS ---

class MessageRole(str, Enum):
    """Ruoli possibili per un messaggio."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"

class ToolStatus(str, Enum):
    """Stati possibili per l'esecuzione di un tool."""
    STARTED = "started"
    SUCCESS = "success"
    ERROR = "error"

class TaskStatus(str, Enum):
    """Stati possibili per un task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# --- BASE MODELS ---
class DBModel(BaseModel):
    """Classe base per modelli database."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True
    )

# --- CONVERSATION MODELS ---
class Conversation(DBModel):
    """Rappresenta una conversazione nel database."""
    id: int | None = Field(default=None, description="ID univoco (None se ancora salvato)")
    title: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)

# --- MESSAGE MODELS ---
class Message(DBModel):
    """Rappresenta un singolo messaggio."""
    id: int | None = None
    conversation_id: int
    role: MessageRole
    content: str
    tokens: int = 0
    model: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)

# --- TOOL EXECUTION MODELS ---
class ToolExecution(DBModel):
    """Rappresenta l'esecuzione di un tool"""
    id: int | None = None
    message_id: int | None = None
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    result: str | None = None
    status: ToolStatus = ToolStatus.STARTED
    duration_ms: float | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)

# --- VISION MODELS ---
class Image(DBModel):
    """Rappresenta un'immagine caricata o generata."""
    id: int | None = None
    message_id: int
    file_path: str
    file_name: str
    file_size: int
    mime_type: str
    width: int | None = None
    height: int | None = None
    hash: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)

class VisionAnalysis(DBModel):
    """Rappresenta il risultato dell'analisi di un'immagine."""
    id: int | None = None
    image_id: int
    message_id: int | None = None
    model: str
    description: str | None = None
    detected_objects: list[dict[str, Any]] = Field(default_factory=list)
    extracted_text: str | None = None
    tags: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    processing_time: float | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)

# --- TASK MODELS ---

class Task(DBModel):
    """Rappresenta un task o to-do."""
    id: int | None = None
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = Field(default=0, ge=0, le=10)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- CONTEXT MODELS ---

class ContextItem(DBModel):
    """Rappresenta un elemento nel key-value store."""
    key: str
    value: Any  # Può essere qualsiasi tipo JSON-serializzabile
    category: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)