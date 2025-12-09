#!/bin/bash
# Скрипт для запуска CLI без poetry

cd "$(dirname "$0")"

# Проверка зависимостей
python3 -c "import typer, rich, httpx" 2>/dev/null || {
    echo "❌ Отсутствуют зависимости. Устанавливаю..."
    pip install typer rich httpx --quiet
}

# Запуск CLI
python3 -m cli.main "$@"

