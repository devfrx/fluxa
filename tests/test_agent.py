"""Test dell'Agente completo."""

import asyncio
from pathlib import Path

from fluxa.core.agent import Agent
from fluxa.llm.client import LLMClient
from fluxa.memory.database import Database
from fluxa.memory.manager import MemoryManager
from fluxa.utils.logger import setup_logger

async def test_agent_flow():
    setup_logger()
    print("\n=== TEST AGENT CORE ===\n")

    # 1. Setup Componenti
    # Usa un DB di test per non sporcare quello principale
    db = Database()
    db.db_path = Path("data/test_agent.db")

    await db.initialize()
    memory = MemoryManager(db)
    llm = LLMClient()

    # Verifica preliminare LLM
    if not await llm.check_connection():
        print("❌ LMStudio non connesso. Salto il test.")
        await db.close()
        return

    # 2. Inizializza Agente
    agent = Agent(memory=memory, llm=llm)
    print("✅ Agente inizializzato")

    # 3. Crea Conversazione
    conv_id = await agent.create_new_conversation(title="Test Agent Flow")
    print(f"✅ Conversazione creata: ID {conv_id}")

    # 4. Chat Loop (Simulato)
    user_msg = "Qual è la capitale d'Italia? Rispondi con una sola parola."
    print(f"\n👤 User: {user_msg}")
    print("🤖 Agent: ", end="", flush=True)

    full_reply = ""
    async for chunk in agent.chat(user_msg, conversation_id=conv_id):
        print(chunk, end="", flush=True)
        full_reply += chunk
    print("\n")

    # 5. Verifica Persistenza
    # Controlliamo se i messaggi sono stati salvati nel DB
    messages = await memory.get_messages(conv_id)
    print(f"\n💾 Verifica DB: Trovati {len(messages)} messaggi nello storico.")

    assert len(messages) >= 2 # System prompt (non salvato) + User + Assistant
    assert messages[-2].role == "user"
    assert messages[-2].content == user_msg
    assert messages[-1].role == "assistant"
    assert messages[-1].content == full_reply

    print("✅ Persistenza verificata correttamente!")

    # Cleanup
    await db.close()
    # Opzionale: rimuovi file db di test
    # Path("data/test_agent.db").unlink(missing_ok=True)

if __name__ == "__main__":
    asyncio.run(test_agent_flow())