#!/bin/bash

# Обновление telegram-shop-bot из репозитория
# Использование: ./scripts/update.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}?? Обновление Telegram Shop Bot...${NC}\n"

# Проверка git репозитория
if [ ! -d ".git" ]; then
    echo -e "${RED}? Текущая директория не является git-репозиторием${NC}"
    exit 1
fi

# Создаем бэкап конфигурационных файлов
BACKUPS_DIR="$PROJECT_ROOT/backups"
mkdir -p "$BACKUPS_DIR"
BACKUP_DIR="$BACKUPS_DIR/config_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}?? Создание бэкапа конфигурации...${NC}"
[ -f ".env" ] && cp .env "$BACKUP_DIR/" && echo "  ? .env"
[ -f "app/texts.yml" ] && cp app/texts.yml "$BACKUP_DIR/" && echo "  ? app/texts.yml"

# Сохраняем локальные изменения
STASHED="false"
if ! git diff --quiet HEAD -- .env app/texts.yml 2>/dev/null; then
    echo -e "${BLUE}?? Сохранение локальных изменений...${NC}"
    git stash push .env app/texts.yml 2>/dev/null || true
    STASHED="true"
fi

# Получаем обновления
echo -e "${BLUE}?? Получение обновлений...${NC}"
git fetch origin

# Показываем изменения
CURRENT=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$CURRENT" != "$REMOTE" ]; then
    echo -e "${BLUE}?? Новые изменения:${NC}"
    git log HEAD..origin/main --oneline --graph --decorate
    echo ""
    read -p "Применить обновления? [Y/n] " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        git reset --hard origin/main
        echo -e "${GREEN}? Обновления применены${NC}"
        
        # Восстанавливаем конфигурацию
        if [ "$STASHED" = "true" ]; then
            echo -e "${BLUE}?? Восстановление конфигурации...${NC}"
            git stash pop 2>/dev/null || {
                echo -e "${YELLOW}?? Конфликты при восстановлении. Используйте бэкап:${NC}"
                echo "   $BACKUP_DIR"
            }
        fi
        
        # Предлагаем пересобрать контейнеры
        echo ""
        read -p "Пересобрать и перезапустить контейнеры? [Y/n] " -n 1 -r
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
            echo -e "${GREEN}? Контейнеры перезапущены${NC}"
        fi
    else
        echo -e "${YELLOW}?? Обновление отменено${NC}"
    fi
else
    echo -e "${GREEN}? Уже на последней версии${NC}"
fi
