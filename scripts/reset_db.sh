#!/bin/bash
# Скрипт для сброса базы данных

set -e

# Функция для запуска docker-compose
docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

echo "⚠️  ВНИМАНИЕ: Все данные будут удалены!"
read -p "Продолжить? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Отменено"
    exit 0
fi

echo "⏹️  Останавливаем контейнеры..."
docker_compose_cmd down

echo "🗑️  Удаляем volume с базой данных..."
docker volume rm telegram-shop-bot_postgres_data || true

echo "▶️ Запускаем контейнеры..."
docker_compose_cmd up -d

echo "⏳ Ждём запуска базы данных..."
sleep 5

echo "🔄 Применяем миграции..."
docker_compose_cmd exec -T api alembic upgrade head

echo "✅ База данных пересоздана!"
