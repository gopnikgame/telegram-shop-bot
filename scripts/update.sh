#!/bin/bash

# ���������� telegram-shop-bot �� �����������
# �������������: ./scripts/update.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# �����
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}?? ���������� Telegram Shop Bot...${NC}\n"

# �������� git �����������
if [ ! -d ".git" ]; then
    echo -e "${RED}? ������� ���������� �� �������� git-������������${NC}"
    exit 1
fi

# ������� ����� ���������������� ������
BACKUPS_DIR="$PROJECT_ROOT/backups"
mkdir -p "$BACKUPS_DIR"
BACKUP_DIR="$BACKUPS_DIR/config_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}?? �������� ������ ������������...${NC}"
[ -f ".env" ] && cp .env "$BACKUP_DIR/" && echo "  ? .env"
[ -f "app/texts.yml" ] && cp app/texts.yml "$BACKUP_DIR/" && echo "  ? app/texts.yml"

# ��������� ��������� ���������
STASHED="false"
if ! git diff --quiet HEAD -- .env app/texts.yml 2>/dev/null; then
    echo -e "${BLUE}?? ���������� ��������� ���������...${NC}"
    git stash push .env app/texts.yml 2>/dev/null || true
    STASHED="true"
fi

# �������� ����������
echo -e "${BLUE}?? ��������� ����������...${NC}"
git fetch origin

# ���������� ���������
CURRENT=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$CURRENT" != "$REMOTE" ]; then
    echo -e "${BLUE}?? ����� ���������:${NC}"
    git log HEAD..origin/main --oneline --graph --decorate
    echo ""
    read -p "��������� ����������? [Y/n] " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        git reset --hard origin/main
        echo -e "${GREEN}? ���������� ���������${NC}"
        
        # ��������������� ������������
        if [ "$STASHED" = "true" ]; then
            echo -e "${BLUE}?? �������������� ������������...${NC}"
            git stash pop 2>/dev/null || {
                echo -e "${YELLOW}?? ��������� ��� ��������������. ����������� �����:${NC}"
                echo "   $BACKUP_DIR"
            }
        fi
        
        # ���������� ����������� ����������
        echo ""
        read -p "����������� � ������������� ����������? [Y/n] " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            if command -v docker-compose &> /dev/null; then
                docker-compose down
                docker-compose build
                docker-compose up -d
            else
                docker compose down
                docker compose build
                docker compose up -d
            fi
            echo -e "${GREEN}? ���������� ������������${NC}"
        fi
    else
        echo -e "${YELLOW}?? ���������� ��������${NC}"
    fi
else
    echo -e "${GREEN}? ��� �� ��������� ������${NC}"
fi
