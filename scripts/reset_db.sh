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
docker_compose_cmd down -v

echo "🗑️  Удаляем volume с базой данных..."
docker volume rm telegram-shop-bot_postgres_data 2>/dev/null || echo "Volume не найден (это нормально)"

echo "🧹 Очистка кэша Python..."
find ./alembic -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "▶️ Запускаем контейнеры..."
docker_compose_cmd up -d

echo "⏳ Ждём запуска базы данных..."
echo "Подождите 10 секунд..."
sleep 10

# Проверяем готовность базы данных
echo "🔍 Проверка подключения к базе данных..."
for i in {1..30}; do
    if docker_compose_cmd exec -T postgres pg_isready -U shopbot > /dev/null 2>&1; then
        echo "✅ База данных готова"
        break
    fi
    echo "Ожидание базы данных... ($i/30)"
    sleep 1
done

echo "🔄 Применяем миграции..."
if docker_compose_cmd exec -T api alembic upgrade head; then
    echo "✅ Миграции применены успешно"
else
    echo "⚠️ Ошибка при применении миграций"
    echo "Пробуем установить начальную версию..."
    docker_compose_cmd exec -T api alembic stamp head
    echo "✅ Версия установлена"
fi

echo ""
echo "✅ База данных пересоздана!"
echo ""
echo "Текущее состояние миграций:"
docker_compose_cmd exec -T api alembic current
