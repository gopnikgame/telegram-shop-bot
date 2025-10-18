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

echo -e "${BLUE}🔄 Обновление Telegram Shop Bot...${NC}\n"

# Проверка git репозитория
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Текущая директория не является git-репозиторием${NC}"
    exit 1
fi

# Создаем бэкап конфигурационных файлов
BACKUPS_DIR="$PROJECT_ROOT/backups"
mkdir -p "$BACKUPS_DIR"
BACKUP_DIR="$BACKUPS_DIR/config_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo -e "${BLUE}💾 Создание бэкапа конфигурации...${NC}"
if [ -f ".env" ]; then
    cp .env "$BACKUP_DIR/"
    echo -e "  ${GREEN}✅ .env сохранен${NC}"
fi
if [ -f "app/texts.yml" ]; then
    cp app/texts.yml "$BACKUP_DIR/"
    echo -e "  ${GREEN}✅ app/texts.yml сохранен${NC}"
fi

# Получаем обновления
echo -e "${BLUE}📡 Получение обновлений...${NC}"
git fetch origin

# Показываем изменения
CURRENT=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$CURRENT" != "$REMOTE" ]; then
    echo -e "${BLUE}📋 Новые изменения:${NC}"
    git log HEAD..origin/main --oneline --graph --decorate
    echo ""
    read -p "Применить обновления? [Y/n] " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        # Останавливаем контейнеры
        echo -e "${BLUE}⏹️ Остановка контейнеров...${NC}"
        if command -v docker-compose &> /dev/null; then
            docker-compose down
        else
            docker compose down
        fi
        
        # Сохраняем URL репозитория
        REPO_URL=$(git config --get remote.origin.url)
        
        # Удаляем все файлы кроме backups и uploads
        echo -e "${BLUE}🗑️ Очистка директории (сохраняем backups и uploads)...${NC}"
        find . -maxdepth 1 ! -name '.' ! -name '..' ! -name 'backups' ! -name 'uploads' -exec rm -rf {} + 2>/dev/null || true
        
        # Клонируем репозиторий заново
        echo -e "${BLUE}📥 Клонирование свежей версии репозитория...${NC}"
        git clone "$REPO_URL" temp_clone
        
        # Перемещаем файлы из temp_clone в текущую директорию
        echo -e "${BLUE}📦 Распаковка файлов...${NC}"
        mv temp_clone/.git .
        mv temp_clone/* . 2>/dev/null || true
        mv temp_clone/.* . 2>/dev/null || true
        rm -rf temp_clone
        
        echo -e "${GREEN}✅ Репозиторий обновлен${NC}"
        
        # Восстанавливаем конфигурацию
        echo -e "${BLUE}♻️ Восстановление конфигурации...${NC}"
        
        if [ -f "$BACKUP_DIR/.env" ]; then
            cp "$BACKUP_DIR/.env" .env
            echo -e "  ${GREEN}✅ .env восстановлен${NC}"
        else
            echo -e "  ${YELLOW}⚠️ Бэкап .env не найден${NC}"
        fi
        
        if [ -f "$BACKUP_DIR/texts.yml" ]; then
            cp "$BACKUP_DIR/texts.yml" app/texts.yml
            echo -e "  ${GREEN}✅ texts.yml восстановлен${NC}"
        else
            echo -e "  ${YELLOW}⚠️ Бэкап texts.yml не найден${NC}"
        fi
        
        # Предлагаем пересобрать контейнеры
        echo ""
        read -p "Пересобрать и перезапустить контейнеры? [Y/n] " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            if command -v docker-compose &> /dev/null; then
                docker-compose build
                docker-compose up -d
            else
                docker compose build
                docker compose up -d
            fi
            echo -e "${GREEN}✅ Контейнеры перезапущены${NC}"
        else
            echo -e "${YELLOW}⚠️ Не забудьте перезапустить контейнеры:${NC}"
            echo "   docker compose build"
            echo "   docker compose up -d"
        fi
    else
        echo -e "${YELLOW}⚠️ Обновление отменено${NC}"
    fi
else
    echo -e "${GREEN}✅ Уже на последней версии${NC}"
fi

echo ""
echo -e "${BLUE}📋 Бэкап конфигурации сохранен в:${NC}"
echo "   $BACKUP_DIR"
