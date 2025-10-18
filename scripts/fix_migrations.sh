#!/bin/bash

# Скрипт для исправления проблем с миграциями

set -e

echo "?? Исправление миграций..."

# Проверяем, запущена ли база данных
if ! docker compose ps | grep -q "shopbot-postgres.*running"; then
    echo "? База данных не запущена. Сначала запустите контейнеры."
    exit 1
fi

echo "1?? Очистка кэша Python..."
docker compose exec -T api find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "2?? Проверка состояния базы данных..."
# Проверяем, существуют ли таблицы
HAS_TABLES=$(docker compose exec -T postgres psql -U shopbot -d shopbot -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" 2>/dev/null || echo "0")

echo "Найдено таблиц: $HAS_TABLES"

if [ "$HAS_TABLES" -gt "0" ]; then
    echo "3?? Таблицы существуют. Проверяем версию Alembic..."
    
    # Проверяем, существует ли таблица alembic_version
    HAS_ALEMBIC=$(docker compose exec -T postgres psql -U shopbot -d shopbot -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='alembic_version';" 2>/dev/null || echo "0")
    
    if [ "$HAS_ALEMBIC" -eq "0" ]; then
        echo "?? Таблица alembic_version отсутствует. Создаём и ставим штамп..."
        docker compose exec -T api alembic stamp head
        echo "? Версия установлена"
    else
        echo "? Таблица alembic_version существует"
        CURRENT_VERSION=$(docker compose exec -T api alembic current 2>/dev/null | grep -oP '^\w+' || echo "none")
        echo "Текущая версия: $CURRENT_VERSION"
        
        if [ "$CURRENT_VERSION" = "none" ] || [ -z "$CURRENT_VERSION" ]; then
            echo "?? Версия не установлена. Устанавливаем штамп..."
            docker compose exec -T api alembic stamp head
            echo "? Версия установлена"
        fi
    fi
else
    echo "3?? Таблицы отсутствуют. Применяем миграции с нуля..."
    docker compose exec -T api alembic upgrade head
    echo "? Миграции применены"
fi

echo ""
echo "? Исправление завершено!"
echo ""
echo "Текущее состояние:"
docker compose exec -T api alembic current
