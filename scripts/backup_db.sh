#!/bin/bash

# ����� ���� ������ telegram-shop-bot
# �������������: ./scripts/backup_db.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUPS_DIR="$PROJECT_ROOT/backups"

cd "$PROJECT_ROOT"

# ������� ���������� ��� �������
mkdir -p "$BACKUPS_DIR"

# �����
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

BACKUP_FILE="$BACKUPS_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"

echo -e "${BLUE}?? �������� ������ ���� ������...${NC}"

if docker ps | grep -q "shopbot-postgres"; then
    docker exec shopbot-postgres pg_dump -U shopbot shopbot > "$BACKUP_FILE"
    echo -e "${GREEN}? ����� ������: $BACKUP_FILE${NC}"
    
    # ���������� ������ �����
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "   ������: $SIZE"
else
    echo -e "${RED}? ���� ������ �� ��������${NC}"
    exit 1
fi
