#!/bin/bash
# Скрипт для проверки завершения рефакторинга

echo "?? Проверка структуры bot/handlers/..."
echo ""

# Проверяем наличие всех модулей
modules=("__init__.py" "start.py" "menu.py" "items.py" "cart.py" "delivery.py" "donate.py" "admin.py")

all_present=true
for module in "${modules[@]}"; do
    if [ -f "bot/handlers/$module" ]; then
        echo "? bot/handlers/$module"
    else
        echo "? bot/handlers/$module - НЕ НАЙДЕН!"
        all_present=false
    fi
done

echo ""

# Проверяем синтаксис Python
echo "?? Проверка синтаксиса Python..."
if python -m py_compile bot/handlers/*.py 2>/dev/null; then
    echo "? Все модули без синтаксических ошибок"
else
    echo "? Обнаружены синтаксические ошибки!"
    all_present=false
fi

echo ""

# Проверяем импорт в webhook_app.py
echo "?? Проверка bot/webhook_app.py..."
if grep -q "from .handlers import main_router" bot/webhook_app.py; then
    echo "? Импорт main_router корректен"
else
    echo "? Некорректный импорт в bot/webhook_app.py!"
    all_present=false
fi

echo ""

if [ "$all_present" = true ]; then
    echo "? ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!"
    echo ""
    echo "Следующие шаги:"
    echo "1. docker compose restart"
    echo "2. docker compose logs api -f"
    echo "3. Протестируйте бота"
    echo "4. Если всё работает: rm bot/handlers.py"
    echo ""
    echo "?? Подробная документация: docs/REFACTORING_COMPLETE.md"
else
    echo "? ЕСТЬ ПРОБЛЕМЫ - см. выше"
    exit 1
fi
