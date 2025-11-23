"""Interfaccia Utente (TUI) per Fluxa basata su Textual."""

import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer, Input, Static, Markdown
from textual.message import Message as TextualMessage

from fluxa.core.agent import Agent
from fluxa.llm.client import LLMClient
from fluxa.memory.database import Database
from fluxa.memory.manager import MemoryManager
from fluxa.utils.logger import get_logger

logger = get_logger(__name__)


class ChatMessage(Static):
    """Widget per visualizzare un singolo messaggio di chat."""

    def __init__(self, role: str, content: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.role = role
        self.content_text = content

        # Icone e stili per ruolo
        if role == "user":
            self.icon = "👤"
            self.add_class("message-user")
            self.title = "Tu"
        elif role == "assistant":
            self.icon = "🤖"
            self.add_class("message-assistant")
            self.title = "Fluxa"
        elif role == "system":
            self.icon = "⚙️"
            self.add_class("message-system")
            self.title = "Sistema"
        else:
            self.icon = "🔧"
            self.add_class("message-tool")
            self.title = "Tool"

    def compose(self) -> ComposeResult:
        """Componi il widget del messaggio."""
        yield Static(f"{self.icon} {self.title}", classes="message-header")
        yield Markdown(self.content_text, classes="message-content")

    def update_content(self, new_content: str) -> None:
        """Aggiorna il contenuto (utile per lo streaming)."""
        self.content_text = new_content
        # Trova il widget Markdown e aggiornalo
        for child in self.children:
            if isinstance(child, Markdown):
                child.update(new_content)
                break


class FluxaApp(App):
    """Applicazione principale TUI."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #chat-container {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
        background: $surface;
    }

    #input-container {
        height: auto;
        dock: bottom;
        padding: 1;
        background: $surface-darken-1;
        border-top: solid $primary;
    }

    Input {
        width: 100%;
    }

    .message-user {
        background: $primary-darken-2;
        color: $text;
        margin: 1 0;
        padding: 1;
        border: solid $primary;
    }

    .message-assistant {
        background: $secondary-darken-2;
        color: $text;
        margin: 1 0;
        padding: 1;
        border: solid $secondary;
    }

    .message-system {
        background: $surface-darken-1;
        color: $text-muted;
        margin: 1 0;
        padding: 1;
        border: solid $surface;
    }

    .message-header {
        text-style: bold;
        margin-bottom: 1;
        color: $text-muted;
    }

    .message-content {
        padding: 0;
    }
    """

    TITLE = "Fluxa AI Agent"
    SUB_TITLE = "Powered by LMStudio"

    def __init__(self) -> None:
        super().__init__()
        self.db: Database | None = None
        self.agent: Agent | None = None
        self.conversation_id: int | None = None
        self.is_processing = False

    def compose(self) -> ComposeResult:
        """Struttura dell'interfaccia."""
        yield Header()

        with VerticalScroll(id="chat-container"):
            yield Static("Benvenuto in Fluxa! 🚀\nAssicurati che LMStudio sia attivo.", classes="message-system")

        with Container(id="input-container"):
            yield Input(placeholder="Scrivi un messaggio...", id="chat-input")

        yield Footer()

    async def on_mount(self) -> None:
        """Inizializzazione all'avvio."""
        try:
            # 1. Inizializza DB
            self.db = Database()
            await self.db.initialize()

            # 2. Inizializza Componenti
            memory = MemoryManager(self.db)
            llm = LLMClient()

            # Verifica connessione
            if not await llm.check_connection():
                self.notify("⚠️ Impossibile connettersi a LMStudio", severity="error")
                return

            self.agent = Agent(memory, llm)

            # 3. Crea/Carica conversazione
            self.conversation_id = await self.agent.create_new_conversation()
            self.notify("Agente pronto! 🟢", severity="information")

            # Focus sull'input
            self.query_one(Input).focus()

        except Exception as e:
            logger.error(f"Errore avvio TUI: {e}")
            self.notify(f"Errore critico: {e}", severity="error")

    async def on_unmount(self) -> None:
        """Cleanup alla chiusura."""
        if self.db:
            await self.db.close()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Gestione invio messaggio."""
        if self.is_processing or not event.value.strip():
            return

        user_input = event.value
        event.input.value = ""  # Pulisci input
        self.is_processing = True

        # 1. Mostra messaggio utente
        chat_container = self.query_one("#chat-container")
        await chat_container.mount(ChatMessage("user", user_input))
        chat_container.scroll_end(animate=False)

        # 2. Prepara messaggio assistente vuoto
        assistant_msg = ChatMessage("assistant", "...")
        await chat_container.mount(assistant_msg)
        chat_container.scroll_end(animate=False)

        # 3. Genera risposta in background
        asyncio.create_task(self.process_chat(user_input, assistant_msg))

    async def process_chat(self, user_input: str, message_widget: ChatMessage) -> None:
        """Processa la chat e aggiorna la UI in streaming."""
        if not self.agent or not self.conversation_id:
            message_widget.update_content("❌ Agente non inizializzato")
            self.is_processing = False
            return

        full_response = ""
        try:
            async for chunk in self.agent.chat(user_input, self.conversation_id):
                full_response += chunk
                message_widget.update_content(full_response)
                self.query_one("#chat-container").scroll_end(animate=False)

        except Exception as e:
            logger.error(f"Errore process_chat: {e}")
            message_widget.update_content(f"❌ Errore: {str(e)}")

        finally:
            self.is_processing = False