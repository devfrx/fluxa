"""Test completo del sistema database con vision."""

import asyncio
import hashlib
from pathlib import Path

from fluxa.memory.database import Database
from fluxa.utils.logger import setup_logger, get_logger

logger = get_logger(__name__)


async def test_database_full() -> None:
    """Test completo del database con tutte le tabelle."""
    setup_logger()

    # Usa un database di test
    db = Database()
    db.db_path = Path("data/test_fluxa.db")

    print("\n" + "="*60)
    print("TEST DATABASE COMPLETO CON VISION")
    print("="*60 + "\n")

    async with db:
        # --- Test 1: CONVERSATIONS ---
        print("1️⃣  Test CONVERSATIONS")
        cursor = await db.execute(
            "INSERT INTO conversations (title, metadata) VALUES (?, ?)",
            ("Test Vision Conversation", '{"tags": ["vision", "test"]}'),
        )
        await db.commit()
        conversation_id = cursor.lastrowid
        print(f"   ✅ Conversazione creata | ID: {conversation_id}\n")

        # --- Test 2: MESSAGES (user) ---
        print("2️⃣  Test MESSAGES")
        cursor = await db.execute(
            "INSERT INTO messages (conversation_id, role, content, tokens) VALUES (?, ?, ?, ?)",
            (conversation_id, "user", "Analizza questa immagine", 5),
        )
        await db.commit()
        message_id = cursor.lastrowid
        print(f"   ✅ Messaggio utente creato | ID: {message_id}\n")

        # --- Test 3: IMAGES ---
        print("3️⃣  Test IMAGES")
        # Simula un hash SHA256
        image_hash = hashlib.sha256(b"fake_image_content").hexdigest()
        
        cursor = await db.execute("""
            INSERT INTO images (
                message_id, file_path, file_name, file_size, 
                mime_type, width, height, hash, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_id,
            "uploads/2024/01/test_image.jpg",
            "test_image.jpg",
            2048000,  # 2MB
            "image/jpeg",
            1920,
            1080,
            image_hash,
            '{"source": "test", "device": "test_suite"}',
        ))
        await db.commit()
        image_id = cursor.lastrowid
        print(f"   ✅ Immagine salvata | ID: {image_id}")
        print(f"   📄 Path: uploads/2024/01/test_image.jpg")
        print(f"   🔒 Hash: {image_hash[:16]}...\n")

        # --- Test 4: VISION_ANALYSES ---
        print("4️⃣  Test VISION_ANALYSES")
        cursor = await db.execute("""
            INSERT INTO vision_analyses (
                image_id, message_id, model, description,
                detected_objects, tags, confidence, processing_time, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            image_id,
            message_id,
            "llava-1.6-mistral-7b",
            "Un'immagine di test per il database",
            '[{"label": "test_object", "confidence": 0.95}]',
            '["test", "vision", "database"]',
            0.95,
            1234.56,
            '{"temperature": 0.7, "max_tokens": 512}',
        ))
        await db.commit()
        analysis_id = cursor.lastrowid
        print(f"   ✅ Analisi vision salvata | ID: {analysis_id}")
        print(f"   🤖 Modello: llava-1.6-mistral-7b")
        print(f"   📊 Confidence: 0.95")
        print(f"   ⏱️  Processing time: 1234.56ms\n")

        # --- Test 5: TOOL_EXECUTIONS ---
        print("5️⃣  Test TOOL_EXECUTIONS")
        cursor = await db.execute("""
            INSERT INTO tool_executions (
                message_id, tool_name, parameters, result, 
                status, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            message_id,
            "image_analysis",
            '{"image_path": "uploads/2024/01/test_image.jpg"}',
            "Analysis completed successfully",
            "success",
            1234.56,
        ))
        await db.commit()
        tool_id = cursor.lastrowid
        print(f"   ✅ Tool execution salvata | ID: {tool_id}\n")

        # --- Test 6: TASKS ---
        print("6️⃣  Test TASKS")
        cursor = await db.execute("""
            INSERT INTO tasks (title, description, status, priority)
            VALUES (?, ?, ?, ?)
        """, (
            "Analizza immagine di test",
            "Task di test per il database vision",
            "completed",
            5,
        ))
        await db.commit()
        task_id = cursor.lastrowid
        print(f"   ✅ Task creato | ID: {task_id}\n")

        # --- Test 7: CONTEXT ---
        print("7️⃣  Test CONTEXT")
        cursor = await db.execute("""
            INSERT INTO context (key, value, category)
            VALUES (?, ?, ?)
        """, (
            "test_preference",
            '{"vision_enabled": true, "default_model": "llava-1.6"}',
            "user_prefs",
        ))
        await db.commit()
        print(f"   ✅ Contesto salvato | Key: test_preference\n")

        # --- Test 8: Query complessa con JOIN ---
        print("8️⃣  Test Query Complessa (JOIN)")
        cursor = await db.execute("""
            SELECT
                c.title as conversation_title,
                m.content as message_content,
                i.file_name,
                va.description,
                va.confidence
            FROM conversations c
            JOIN messages m ON c.id = m.conversation_id
            JOIN images i ON m.id = i.message_id
            JOIN vision_analyses va ON i.id = va.image_id
            WHERE c.id = ?
        """, (conversation_id,))

        row = await cursor.fetchone()
        if row:
            print(f"   ✅ Query JOIN completata")
            print(f"   📝 Conversazione: {row[0]}")
            print(f"   💬 Messaggio: {row[1]}")
            print(f"   🖼️  File: {row[2]}")
            print(f"   🔍 Descrizione: {row[3]}")
            print(f"   📊 Confidence: {row[4]}\n")

        # --- Test 9: Verifica indici ---
        print("9️⃣  Test Indici")
        cursor = await db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
            ORDER BY name
        """)
        indices = await cursor.fetchall()
        print(f"   ✅ Indici trovati: {len(indices)}")
        for idx in indices:
            print(f"      - {idx[0]}")
        print()

        # --- Test 10: Verifica foreign keys ---
        print("🔟 Test Foreign Keys")
        cursor = await db.execute("PRAGMA foreign_key_list(images)")
        fks = await cursor.fetchall()
        print(f"   ✅ Foreign keys in 'images': {len(fks)}")

        cursor = await db.execute("PRAGMA foreign_key_list(vision_analyses)")
        fks = await cursor.fetchall()
        print(f"   ✅ Foreign keys in 'vision_analyses': {len(fks)}\n")

    print("="*60)
    print("✅ TUTTI I TEST COMPLETATI CON SUCCESSO!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_database_full())