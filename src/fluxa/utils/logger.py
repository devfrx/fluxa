"""Sistema di logging centralizzato per Fluxa.

Questo modulo configura Loguru per fornire un sistema di logging
avanzato con rotazione file, colori, e supporto per diversi livelli.

Esempio di utilizzo:
    >>> from fluxa.utils.logger import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Applicazione avviata")
    >>> logger.debug("Dettagli debug", extra={"user_id": 123})
"""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from fluxa.core.config import get_settings

def setup_logger() -> None:
    """Configura il sistema di logging globale.

    Questa funzione:
    1. Rimuove i logger di default di Loguru
    2. Configura un logger per la console (sempre attivo)
    3. Configura un logger per file (opzionale, con rotazione)
    4. Applica le impostazioni dal config

    Note
    ----
    Questa funzione dovrebbe essere chiamata una sola volta
    all'avvio dell'applicazione.

    Raises
    ------
    Exception
        Se c'è un errore nella creazione delle directory o dei file di log
    """

    settings = get_settings()

    # Rimuovo i logger di default
    logger.remove()

    # --- Logger console ---
    # Sempre attivo
    logger.add(
        sink=sys.stderr, # Output su console
        format=settings.logging.format, # Formato del log
        level=settings.logging.level, # Livello di log
        colorize=True, # Colori abilitati
        backtrace=True, # Stack trace dettagliati
        diagnose=True, # Diagnostica avanzata
    )

    # --- Logger file ---
    if settings.logging.file_path:
        # Crea la directory se non esiste
        settings.logging.file_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            sink=str(settings.logging.file_path), # Percorso del file di log
            format=settings.logging.format, # Formato del log
            level=settings.logging.level, # Livello di log
            rotation=settings.logging.rotation, # Rotazione del file
            retention=settings.logging.retention, # Conservazione dei file
            compression=settings.logging.compression, # Compressione dei file vecchi
            backtrace=True, # Stack trace dettagliati
            diagnose=True, # Diagnostica avanzata
            enqueue=True, # Thread-safe per app async
        )

    # Log di avvio
    logger.info(
        f"Logger inizializzato | Level: {settings.logging.level} | "
        f"File: {settings.logging.file_path or 'Console only'}"
    )

     # Se debug è attivo, mostra config completa
    if settings.debug:
        logger.debug(f"Configurazione caricata: {settings.model_dump()}")

def get_logger(name: str) -> Any:
    """Ottieni un logger con un nome specifico.

    Parameters
    ----------
    name : str
        Nome del logger, tipicamente `__name__` del modulo chiamante

    Returns
    -------
    Any
        Istanza del logger di Loguru

    Example
    -------
    >>> from fluxa.utils.logger import get_logger
    >>> logger = get_logger(__name__)
    >>> logger.info("Messaggio informativo")
    >>> logger.warning("Attenzione!", extra={"user_id": 123})
    >>> logger.error("Errore critico", exc_info=True)

    Notes
    -----
    Loguru gestisce automaticamente il nome del modulo nel formato,
    quindi non è necessario fare binding esplicito.
    """
    return logger.bind(name=name)

def log_function_call(func_name: str, **kwargs: Any) -> None:
    """Helper per loggare chiamate a funzioni con parametri.

    Utile per tracciare chiamate a LLM, tools, database, etc.

    Parameters
    ----------
    func_name : str
        Nome della funzione chiamata
    **kwargs : Any
        Parametri della funzione

    Example
    -------
    >>> from fluxa.utils.logger import log_function_call
    >>> log_function_call(
    ...     "generate_response",
    ...     model="llama-3",
    ...     temperature=0.7,
    ...     max_tokens=100
    ... )
    """

    logger.debug(f"Chiamata a {func_name}", extra={"params": kwargs})

def log_llm_interaction(
    direction: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Helper per loggare interazioni con LLM.

    Parameters
    ----------
    direction : str
        "request" o "response"
    content : str
        Contenuto del messaggio (troncato se troppo lungo)
    metadata : dict[str, Any] | None
        Metadati aggiuntivi (model, tokens, temperature, etc.)

    Example
    -------
    >>> from fluxa.utils.logger import log_llm_interaction
    >>> log_llm_interaction(
    ...     direction="request",
    ...     content="Ciao, come stai?",
    ...     metadata={"model": "llama-3", "temperature": 0.7}
    ... )
    """
    max_length = 200
    truncated_content = (
        content if len(content) <= max_length else content[:max_length] + "..."
    )

    logger.info(
        f"LLM {direction.upper()}: {truncated_content}",
        extra={"metadata": metadata or {}},
    )

def log_tool_execution(
    tool_name: str,
    status: str,
    duration: float | None = None,
    result: Any | None = None,
    error: str | None = None,
) -> None:
    """Helper per loggare esecuzioni di tools.

    Parameters
    ----------
    tool_name : str
        Nome del tool eseguito
    status : str
        "started", "success", o "error"
    duration : float | None
        Durata dell'esecuzione in secondi
    result : Any | None
        Risultato dell'esecuzione (troncato se troppo grande)
    error : str | None
        Messaggio di errore se status="error"

    Example
    -------
    >>> from fluxa.utils.logger import log_tool_execution
    >>> log_tool_execution(
    ...     tool_name="file_read",
    ...     status="success",
    ...     duration=0.123,
    ...     result="File content..."
    ... )
    """
    extra_data: dict[str, Any] = {
        "tool": tool_name,
        "status": status,
    }

    if duration is not None:
        extra_data["duration_ms"] = round(duration * 1000, 2)

    if status == "started":
        logger.info(f"Tool '{tool_name}' avviato", extra=extra_data)
    elif status == "success":
        # Tronca il risultato se troppo grande
        result_str = str(result)[:200] if result else "N/A"
        logger.success(
            f"Tool '{tool_name}' completato | Risultato: {result_str}",
            extra=extra_data,
        )
    elif status == "error":
        logger.error(
            f"Tool '{tool_name}' fallito | Errore: {error}",
            extra=extra_data,
        )


def log_database_operation(
    operation: str,
    table: str,
    success: bool,
    affected_rows: int | None = None,
    error: str | None = None,
) -> None:
    """Helper per loggare operazioni sul database.

    Parameters
    ----------
    operation : str
        Tipo di operazione ("INSERT", "SELECT", "UPDATE", "DELETE")
    table : str
        Nome della tabella
    success : bool
        True se l'operazione è riuscita
    affected_rows : int | None
        Numero di righe interessate
    error : str | None
        Messaggio di errore se success=False

    Example
    -------
    >>> from fluxa.utils.logger import log_database_operation
    >>> log_database_operation(
    ...     operation="INSERT",
    ...     table="conversations",
    ...     success=True,
    ...     affected_rows=1
    ... )
    """
    extra_data: dict[str, Any] = {
        "operation": operation,
        "table": table,
    }

    if affected_rows is not None:
        extra_data["affected_rows"] = affected_rows

    if success:
        logger.debug(
            f"DB {operation} su '{table}' completato",
            extra=extra_data,
        )
    else:
        logger.error(
            f"DB {operation} su '{table}' fallito | Errore: {error}",
            extra=extra_data,
        )


# Export pubblici
__all__ = [
    "setup_logger",
    "get_logger",
    "log_function_call",
    "log_llm_interaction",
    "log_tool_execution",
    "log_database_operation",
]
