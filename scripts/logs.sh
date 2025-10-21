#!/bin/bash

# Просмотр логов telegram-shop-bot
# Использование: 
#   ./scripts/logs.sh          # Все логи
#   ./scripts/logs.sh api      # Только API
#   ./scripts/logs.sh db       # Только PostgreSQL
#   ./scripts/logs.sh errors   # Только ошибки
#   ./scripts/logs.sh follow   # Отслеживание в реальном времени

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Функция для запуска docker-compose
docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

LOG_TYPE="${1:-all}"

case $LOG_TYPE in
    api)
        echo "📊 Логи API:"
        docker_compose_cmd logs api --tail=100
        ;;
    db)
        echo "🗄️ Логи PostgreSQL:"
        docker_compose_cmd logs db --tail=100
        ;;
    errors)
        echo "❌ Логи ошибок:"
        docker_compose_cmd logs --tail=200 | grep -i "error\|exception\|failed\|critical"
        ;;
    follow|f)
        echo "📡 Отслеживание логов (Ctrl+C для выхода):"
        docker_compose_cmd logs -f
        ;;
    *)
        echo "📋 Все логи:"
        docker_compose_cmd logs --tail=100
        ;;
esac
