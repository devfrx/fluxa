"""Test del client LLM."""

import asyncio
import pytest
from fluxa.llm.client import LLMClient
from fluxa.utils.logger import setup_logger

# Se non hai pytest-asyncio installato, usiamo asyncio.run nel main
async def run_tests():
    setup_logger()
    client = LLMClient()
    
    print("\n=== TEST LLM CLIENT ===\n")
    
    # 1. Test Connessione
    print("📡 Verifica connessione LMStudio...")
    is_connected = await client.check_connection()
    
    if not is_connected:
        print("❌ LMStudio non rilevato. Assicurati che il server sia attivo su http://localhost:1234")
        return

    print("✅ Connesso a LMStudio!")
    
    # 2. Lista Modelli
    models = await client.get_models()
    print(f"📚 Modelli trovati: {models}")
    
    # 3. Test Chat (Streaming)
    print("\n💬 Test Chat (Streaming):")
    messages = [{"role": "user", "content": "Ciao! Rispondi con una sola frase breve."}]
    
    print("🤖 Assistant: ", end="", flush=True)
    async for chunk in await client.chat(messages, stream=True):
        print(chunk, end="", flush=True)
    print("\n")
    
    print("=== TEST COMPLETATO ===")

if __name__ == "__main__":
    asyncio.run(run_tests())