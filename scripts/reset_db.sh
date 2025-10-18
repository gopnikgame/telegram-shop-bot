#!/bin/bash
# Скрипт для сброса базы данных

set -e

echo "??  ВНИМАНИЕ: Все данные будут удалены!"
read -p "Продолжить? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Отменено"
    exit 0
fi

echo "???  Останавливаем контейнеры..."
docker-compose down

echo "???  Удаляем volume с базой данных..."
docker volume rm telegram-shop-bot_postgres_data || true

echo "?? Запускаем контейнеры..."
docker-compose up -d

echo "? Ждём запуска базы данных..."
sleep 5

echo "?? Применяем миграции..."
docker-compose exec -T shopbot-api alembic upgrade head

echo "? База данных пересоздана!"
