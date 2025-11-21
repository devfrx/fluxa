"""Sistema di memoria persistente per Fluxa.

Gestisce il database SQLite per conversazioni, task, e contesto.
"""

from fluxa.memory.database import Database

__all__ = [
    "Database",
]