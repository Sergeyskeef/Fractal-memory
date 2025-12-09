#!/bin/bash
# ═══════════════════════════════════════════════════════
# Fix Imports Script - Настройка PYTHONPATH
# ═══════════════════════════════════════════════════════

set -e

# Получить директорию проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🔧 Fixing Python imports..."
echo "📁 Project directory: $PROJECT_DIR"

# Экспортировать PYTHONPATH
export PYTHONPATH="${PROJECT_DIR}/src:${PROJECT_DIR}:${PYTHONPATH}"

echo "✅ PYTHONPATH set to: $PYTHONPATH"
echo ""

# Проверить что модули доступны
echo "🔍 Testing imports..."

python3 << EOF
import sys
sys.path.insert(0, '${PROJECT_DIR}/src')
sys.path.insert(0, '${PROJECT_DIR}')

try:
    from core.memory import FractalMemory
    print("✅ FractalMemory imported successfully")
except ImportError as e:
    print(f"❌ Failed to import FractalMemory: {e}")

try:
    from core.retrieval import HybridRetriever
    print("✅ HybridRetriever imported successfully")
except ImportError as e:
    print(f"❌ Failed to import HybridRetriever: {e}")

try:
    from core.reasoning import ReasoningBank
    print("✅ ReasoningBank imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ReasoningBank: {e}")
EOF

echo ""
echo "🚀 Ready to run tests!"
echo ""
echo "To use this environment, run:"
echo "  source scripts/fix_imports.sh"
echo ""
echo "Then run audit:"
echo "  python -m audit.run_audit"
