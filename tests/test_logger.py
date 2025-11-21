"""Test rapido del logger."""

import sys
from pathlib import Path

# Aggiungi src al path solo se necessario
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Ora importa
from fluxa.utils.logger import setup_logger, get_logger

# Test
setup_logger()
logger = get_logger(__name__)

print("\n=== TEST LOGGER ===\n")
logger.debug("🔍 Debug message")
logger.info("ℹ️  Info message")
logger.warning("⚠️  Warning message")
logger.success("✅ Success message")
logger.error("❌ Error message")
print("\n=== DONE ===\n")