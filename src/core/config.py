"""Configurazione centralizzata per Fluxa AI Agent.

Questo modulo gestisce tutte le configurazioni dell'applicazione usando Pydantic Settings.
Supporta caricamento da:
- File .env nella root del progetto
- Variabili d'ambiente del sistema
- Valori di default

Esempio di utilizzo:
    >>> from fluxa.core.config import get_settings
    >>> settings = get_settings()
    >>> print(settings.lmstudio.base_url)
    'http://localhost:1234/v1'
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import HttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class LMStudioSettings(BaseSettings):
    """
    Configurazione per la connessione a LMStudio.

    Attributi
    ---------
    #? base_url : HttpUrl
        URL base dell'API di LMStudio (default: http://localhost:1234/v1)
    #? timeout : int
        Timeout in secondi per le richieste HTTP (default: 30)
    #? max_retries : int
        Numero massimo di tentativi in caso di errore (default: 3)
    #? model_name : str
        Nome del modello da utilizzare (default: vuoto, usa il modello attivo in LMStudio)
    #? temperature : float
        Temperatura per la generazione (0.0-2.0, default: 0.7)
    #? max_tokens : int
        Numero massimo di token da generare (default: 2048)
    #? stream : bool
        Abilita streaming delle risposte (default: True)
    #? model_config : SettingsConfigDict
        Configurazione per il caricamento da variabili d'ambiente
    """

    base_url: HttpUrl = Field(
        default="http://localhost:1234/v1",
        description="URL base dell'API di LMStudio",
    )

    timeout: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Timeout in secondi per le richieste HTTP",
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Numero massimo di tentativi in caso di errore",
    )

    model_name: str = Field(
        default="",
        description="Nome del modello da utilizzare (vuoto per il modello attivo)",
    )

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperatura per la generazione",
    )
    
    max_tokens: int = Field(
        default=2048,
        ge=1,
        le=16384,
        description="Numero massimo di token da generare",
    )

    stream: bool = Field(
        default=True,
        description="Abilita streaming delle risposte",
    )

    model_config = SettingsConfigDict(
        env_prefix="FLUXA_LMSTUDIO_",
        case_sensitive=False,
    )

class VisionSettings(BaseSettings):
    """Configurazione per le capacità di visione.

    Attributi
    ---------
    #? enabled : bool
        Abilita funzionalità di visione (default: True)
    #? model_name : str
        Nome del modello vision da utilizzare
    #? max_image_size : int
        Dimensione massima immagine in MB (default: 10)
    #? supported_formats : tuple
        Formati immagine supportati
    #? model_config : SettingsConfigDict
        Configurazione per il caricamento da variabili d'ambiente
    """

    enabled: bool = Field(
        default=True,
        description="Abilita funzionalità di visione",
    )

    model_name: str = Field(
        default="",
        description="Nome del modello vision da utilizzare",
    )

    max_image_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Dimensione massima immagine in MB",
    )

    supported_formats: tuple[str, ...] = Field(
        default=("jpg", "png"),
        description="Formati immagine supportati",
    )

    model_config = SettingsConfigDict(
        env_prefix="FLUXA_VISION_",
        case_sensitive=False,
    )

class DatabaseSettings(BaseSettings):
    """Configurazione per il database SQLite.

    Attributi
    ---------
    #? path : Path
        Percorso del file database (default: ./data/fluxa.db)
    #? enable_wal : bool
        Abilita Write-Ahead Logging per migliori performance (default: True)
    #? timeout : float
        Timeout in secondi per operazioni database (default: 5.0)
    #? max_connections : int
        Numero massimo di connessioni simultanee (default: 5)
    #? model_config : SettingsConfigDict
        Configurazione per il caricamento da variabili d'ambiente
    """

    path: Path = Field(
        default=Path("./data/fluxa.db"),
        description="Percorso del file database",
    )

    enable_wal: bool = Field(
        default=True,
        description="Abilita Write-Ahead Logging per migliori performance",
    )

    timeout: float = Field(
        default=5.0,
        ge=1.0,
        le=30.0,
        description="Timeout in secondi per operazioni database",
    )

    max_connections: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Numero massimo di connessioni simultanee",
    )

    @field_validator("path")
    def validate_path(cls, v: Path) -> Path:
        """Crea automaticamente le directory parent se non esistono."""
        v.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    model_config = SettingsConfigDict(
        env_prefix="FLUXA_DB_",
        case_sensitive=False,
    )

class ToolsSettings(BaseSettings):
    """Configurazione per strumenti esterni.

    Attributi
    ---------
    #? enabled : bool
        Abilita strumenti esterni (default: True)
    #? max_iterations : int
        Numero massimo di iterazioni per strumenti (default: 5)
    #? timeout : int
        Timeout in secondi per chiamate strumenti (default: 15)
    #? allowed_tools: list[str]
        Lista di tool abilitati (vuoto = tutti abilitati)
    #? model_config : SettingsConfigDict
        Configurazione per il caricamento da variabili d'ambiente
    """

    enabled: bool = Field(
        default=True,
        description="Abilita strumenti esterni",
    )

    max_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Numero massimo di iterazioni per strumenti",
    )

    timeout: int = Field(
        default=15,
        ge=1,
        le=60,
        description="Timeout in secondi per esecuzione tool",
    )

    allowed_tools: list[str] = Field(
        default=[],
        description="Lista di tool abilitati (vuoto = tutti abilitati)",
    )

    model_config = SettingsConfigDict(
        env_prefix="FLUXA_TOOLS_",
        case_sensitive=False,
    )

class LoggingSettings(BaseSettings):
    """Configurazione per il logging dell'applicazione.

    Attributi
    ---------
    #? level : str
        Livello di log (default: 'INFO')
    #? format : str
        Formato dei log
    #? file_path : Path | None
        Percorso file log (None = solo console)
    #? rotation : str
        Rotazione file log (es: "10 MB", "1 week")
    #? retention : str
        Retention file log (es: "1 month")
    #? model_config : SettingsConfigDict
        Configurazione per il caricamento da variabili d'ambiente
    """