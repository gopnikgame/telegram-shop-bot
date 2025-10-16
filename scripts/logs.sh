#!/bin/bash

# �������� ����� telegram-shop-bot
# �������������: 
#   ./scripts/logs.sh          # ��� ����
#   ./scripts/logs.sh api      # ������ API
#   ./scripts/logs.sh db       # ������ PostgreSQL
#   ./scripts/logs.sh errors   # ������ ������
#   ./scripts/logs.sh follow   # ������������ � �������� �������

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# ������� ��� ������� docker-compose
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
        echo "?? ���� API:"
        docker_compose_cmd logs api --tail=100
        ;;
    db)
        echo "?? ���� PostgreSQL:"
        docker_compose_cmd logs db --tail=100
        ;;
    errors)
        echo "? ���� ������:"
        docker_compose_cmd logs --tail=200 | grep -i "error\|exception\|failed\|critical"
        ;;
    follow|f)
        echo "?? ������������ ����� (Ctrl+C ��� ������):"
        docker_compose_cmd logs -f
        ;;
    *)
        echo "?? ��� ����:"
        docker_compose_cmd logs --tail=100
        ;;
esac
