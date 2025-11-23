"""Gestione database SQLite per Fluxa.

Questo modulo fornisce una classe Database per gestire la connessione
e le operazioni sul database SQLite usando aiosqlite (async).

Esempio di utilizzo:
    >>> from fluxa.memory.database import Database
    >>> db = Database()
    >>> await db.initialize()
    >>> await db.close()
"""

import aiosqlite
from pathlib import Path
from typing import Any

from fluxa.core.config import get_settings
from fluxa.utils.logger import get_logger, log_database_operation

logger = get_logger(__name__)

class Database:
    """Gestisce la connessione e le operazioni sul database SQLite.

    Questa classe fornisce metodi per:
    - Inizializzare il database con lo schema
    - Gestire la connessione in modo async
    - Eseguire operazioni CRUD
    - Gestire transazioni

    Attributes
    ----------
    db_path : Path
        Percorso del file database
    connection : aiosqlite.Connection | None
        Connessione attiva al database
    """

    def __init__(self) -> None:
        """Inizializza il Database manager.

        Carica le impostazioni dal config e prepara il percorso del database.
        """
        settings = get_settings()
        self.db_path: Path = settings.database.path
        self.timeout: float = settings.database.timeout
        self.enable_wal: bool = settings.database.enable_wal
        self.connection: aiosqlite.Connection | None = None

        logger.info(f"Database manager inizializzato | Path: {self.db_path}")

    async def initialize(self)-> None:
        """Inizializza il database creando lo schema se necessario.

        Questa funzione:
        1. Crea il file database se non esiste
        2. Abilita WAL mode (Write-Ahead Logging) se configurato
        3. Crea tutte le tabelle necessarie
        4. Crea gli indici per performance

        Raises
        ------
        Exception
            Se c'è un errore nella creazione del database o dello schema
        """
        try:
            # Crea la directory se non esiste
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Apro connessione
            self.connection = await aiosqlite.connect(
                str(self.db_path),
                timeout=self.timeout,
            )

            # Abilita foreign keys
            await self.connection.execute("PRAGMA foreign_keys = ON")

            # Abilita WAL mode per migliori performance
            if self.enable_wal:
                await self.connection.execute("PRAGMA journal_mode = WAL")
                logger.debug("WAL mode abilitato")

            # Creo schema
            await self._create_schema()

            logger.success(f"Database inizializzato correttamente | Path: {self.db_path}")

        except Exception as e:
            logger.error(f"Errore durante l'inizializzazione del database: {e}")
            log_database_operation(
                operation="INITIALIZE",
                table="ALL",
                success=False,
                error=str(e),
            )
            raise

    async def _create_schema(self) -> None:
        """Crea lo schema completo del database.

        Tabelle create:
        - conversations: Traccia conversazioni
        - messages: Singoli messaggi in una conversazione
        - tasks: Compiti dell'agente
        - tool_executions: Esecuzioni di tools
        - images: Immagini caricate/generate
        - vision_analyses: Analisi vision delle immagini
        - context: Memoria a lungo termine (key-value store)
        """
        if not self.connection:
            raise RuntimeError("Database non connesso")

        # --- Tabella CONVERSATIONS ---
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # --- Tabella MESSAGES ---
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system', 'tool')),
                content TEXT NOT NULL,
                tokens INTEGER DEFAULT 0,
                model TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
            )
        """)

        # --- Tabella TASKS ---
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL CHECK(status IN ('pending', 'in_progress', 'completed', 'failed')),
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT
            )
        """)

        # --- Tabella TOOL_EXECUTIONS ---
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS tool_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                tool_name TEXT NOT NULL,
                parameters TEXT,
                result TEXT,
                status TEXT NOT NULL CHECK(status IN ('started', 'success', 'error')),
                duration_ms REAL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
            )
        """)

        # --- Tabella IMAGES (NUOVA) ---
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                width INTEGER,
                height INTEGER,
                hash TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
            )
        """)

        # --- Tabella VISION_ANALYSES (NUOVA) ---
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS vision_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER NOT NULL,
                message_id INTEGER,
                model TEXT NOT NULL,
                description TEXT,
                detected_objects TEXT,
                extracted_text TEXT,
                tags TEXT,
                confidence REAL CHECK(confidence >= 0 AND confidence <= 1),
                processing_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (image_id) REFERENCES images (id) ON DELETE CASCADE,
                FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
            )
        """)

        # --- Tabella CONTEXT (Key-Value Store) ---
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS context (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # --- INDICI per performance ---
        # Indici per MESSAGES
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON messages(conversation_id)
        """)

        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_created
            ON messages(created_at DESC)
        """)

        # Indici per TASKS
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status
            ON tasks(status)
        """)

        # Indici per TOOL_EXECUTIONS
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_tool_executions_message
            ON tool_executions(message_id)
        """)

        # Indici per IMAGES (NUOVI)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_images_message
            ON images(message_id)
        """)

        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_images_hash
            ON images(hash)
        """)

        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_images_created
            ON images(created_at DESC)
        """)

        # Indici per VISION_ANALYSES (NUOVI)
        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_vision_analyses_image
            ON vision_analyses(image_id)
        """)

        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_vision_analyses_message
            ON vision_analyses(message_id)
        """)

        await self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_vision_analyses_created
            ON vision_analyses(created_at DESC)
        """)

        await self.connection.commit()
        log_database_operation(
            operation="CREATE_SCHEMA",
            table="ALL",
            success=True,
        )

    async def execute(
        self,
        query: str,
        parameters: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> aiosqlite.Cursor:
        """Esegui una query SQL.

        Parameters
        ----------
        query : str
            Query SQL da eseguire
        parameters : tuple | dict | None
            Parametri della query (? o :name)

        Returns
        -------
        aiosqlite.Cursor
            Cursore con i risultati

        Raises
        ------
        RuntimeError
            Se il database non è connesso
        """
        if not self.connection:
            raise RuntimeError("Database non connesso")

        try:
            if parameters is not None:
                cursor = await self.connection.execute(query, parameters)
            else:
                cursor = await self.connection.execute(query)

            return cursor

        except Exception as e:
            logger.error(f"Errore esecuzione query: {e}")
            raise

    async def executemany(
        self,
        query: str,
        parameters: list[tuple[Any, ...]] | list[dict[str, Any]],
    ) -> aiosqlite.Cursor:
        """Esegui una query SQL multipla (batch insert).

        Parameters
        ----------
        query : str
            Query SQL da eseguire
        parameters : list[tuple] | list[dict]
            Lista di parametri per ogni esecuzione

        Returns
        -------
        aiosqlite.Cursor
            Cursore con i risultati
        """
        if not self.connection:
            raise RuntimeError("Database non connesso")

        try:
            cursor = await self.connection.executemany(query, parameters)
            return cursor

        except Exception as e:
            logger.error(f"Errore esecuzione query multipla: {e}")
            raise

    async def commit(self) -> None:
        """Commit delle modifiche al database."""
        if not self.connection:
            raise RuntimeError("Database non connesso")

        await self.connection.commit()

    async def rollback(self) -> None:
        """Rollback delle modifiche."""
        if not self.connection:
            raise RuntimeError("Database non connesso")

        await self.connection.rollback()

    async def close(self) -> None:
        """Chiudi la connessione al database."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("Database chiuso")

    async def __aenter__(self) -> "Database":
        """Context manager: inizializza il database."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager: chiudi il database."""
        await self.close()

# Export
__all__ = ["Database"]