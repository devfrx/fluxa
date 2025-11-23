"""Core Agent di Fluxa.

Questo modulo implementa l'agente principale che orchestra:
1. Gestione della memoria (salvataggio/recupero messaggi)
2. Interazione con LLM (invio prompt, streaming)
3. Gestione del contesto
"""

from typing import AsyncGenerator, Any

from fluxa.core.config import get_settings
from fluxa.llm.client import LLMClient
from fluxa.memory.manager import MemoryManager
from fluxa.memory.models import MessageRole
from fluxa.utils.logger import get_logger

logger = get_logger(__name__)


class Agent:
    """Agente principale di Fluxa.

    Collega il client LLM con il gestore della memoria per fornire
    un'esperienza di chat persistente e contestuale.
    """

    def __init__(self, memory: MemoryManager, llm: LLMClient) -> None:
        """Inizializza l'agente.

        Parameters
        ----------
        memory : MemoryManager
            Gestore della memoria persistente
        llm : LLMClient
            Client per l'interazione con l'AI
        """
        self.memory = memory
        self.llm = llm
        self.settings = get_settings()

    async def create_new_conversation(self, title: str = "Nuova Chat") -> int:
        """Crea una nuova conversazione e restituisce l'ID."""
        conv = await self.memory.create_conversation(title=title)
        logger.info(f"Creata nuova conversazione: {conv.id} - {title}")
        if conv.id is None:
            raise ValueError("Impossibile creare la conversazione (ID nullo)")
        return conv.id

    async def chat(
        self,
        user_input: str,
        conversation_id: int,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Invia un messaggio all'agente e ottieni la risposta.

        Questo metodo:
        1. Salva il messaggio utente nel DB
        2. Recupera lo storico della conversazione
        3. Invia tutto all'LLM
        4. Restituisce la risposta (streaming)
        5. Salva la risposta completa nel DB

        Parameters
        ----------
        user_input : str
            Messaggio dell'utente
        conversation_id : int
            ID della conversazione attiva
        stream : bool
            Se True, usa lo streaming (default: True)

        Yields
        ------
        str
            Chunk di testo della risposta
        """
        # 1. Salva messaggio utente
        await self.memory.add_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=user_input
        )

        # 2. Recupera storico messaggi
        # (Qui potremmo implementare logica per troncare se troppo lungo)
        history = await self.memory.get_messages(conversation_id)

        # Converti modelli DB in formato per LLM
        llm_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in history
        ]

        # Aggiungi System Prompt (opzionale, hardcoded per ora o da config)
        system_prompt = {
            "role": "system", 
            "content": (
                f"Sei {self.settings.app_name}, un assistente AI intelligente e utile. "
                "Rispondi in modo chiaro e conciso."
            )
        }
        llm_messages.insert(0, system_prompt)

        # 3. Chiama LLM e gestisci risposta
        full_response_content = ""

        try:
            if stream:
                # Modalità Streaming
                generator = await self.llm.chat(messages=llm_messages, stream=True)

                # Itera sul generatore asincrono
                if isinstance(generator, dict):
                     # Fallback se per qualche motivo non è un generatore
                     chunk = generator.get("choices", [{}])[0].get("message", {}).get("content", "")
                     full_response_content += chunk
                     yield chunk
                else:
                    async for chunk in generator:
                        full_response_content += chunk
                        yield chunk
            else:
                # Modalità Unary (no streaming)
                response = await self.llm.chat(messages=llm_messages, stream=False)
                if isinstance(response, dict):
                    content = response["choices"][0]["message"]["content"]
                    full_response_content = content
                    yield content

            # 4. Salva risposta Assistant nel DB
            if full_response_content:
                await self.memory.add_message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=full_response_content,
                    model=self.settings.lmstudio.model_name or "local-model"
                )

        except Exception as e:
            logger.error(f"Errore durante la chat: {e}")
            yield f"\n Errore: {str(e)}"