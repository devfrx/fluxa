"""Test del sistema di logging."""

from fluxa.utils.logger import (
    get_logger,
    log_database_operation,
    log_llm_interaction,
    log_tool_execution,
    setup_logger,
)


def test_logger_setup() -> None:
    """Test che il logger si inizializzi correttamente."""
    setup_logger()
    logger = get_logger(__name__)

    logger.debug("Messaggio di debug")
    logger.info("Messaggio informativo")
    logger.warning("Messaggio di warning")
    logger.success("Operazione completata!")


def test_llm_logging() -> None:
    """Test logging interazioni LLM."""
    setup_logger()

    log_llm_interaction(
        direction="request",
        content="Ciao, come stai?",
        metadata={"model": "llama-3", "temperature": 0.7},
    )

    log_llm_interaction(
        direction="response",
        content="Ciao! Sto bene, grazie per aver chiesto.",
        metadata={"tokens": 15},
    )


def test_tool_logging() -> None:
    """Test logging esecuzione tools."""
    setup_logger()

    log_tool_execution(
        tool_name="file_read",
        status="started",
    )

    log_tool_execution(
        tool_name="file_read",
        status="success",
        duration=0.123,
        result="File content...",
    )


def test_database_logging() -> None:
    """Test logging operazioni database."""
    setup_logger()

    log_database_operation(
        operation="INSERT",
        table="conversations",
        success=True,
        affected_rows=1,
    )