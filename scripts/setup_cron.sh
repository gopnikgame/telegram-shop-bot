#!/bin/bash

# Установка cron задач для автоматических бэкапов
# Использование: sudo ./scripts/setup_cron.sh

set -euo pipefail

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_SCRIPT="$PROJECT_ROOT/scripts/backup_db.sh"

echo -e "${BLUE}? Настройка cron для автоматических бэкапов...${NC}\n"

# Проверка существования скрипта бэкапа
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo -e "${RED}? Скрипт бэкапа не найден: $BACKUP_SCRIPT${NC}"
    exit 1
fi

# Меню выбора частоты
echo "Выберите частоту автоматических бэкапов:"
echo "1. Ежедневно в 02:00"
echo "2. Дважды в день (02:00 и 14:00)"
echo "3. Еженедельно (воскресенье в 02:00)"
echo "4. Ежемесячно (1-го числа в 02:00)"
echo "5. Пользовательское расписание"
echo "0. Отмена"
echo ""

read -p "Выберите вариант (0-5): " choice

case $choice in
    1)
        CRON_SCHEDULE="0 2 * * *"
        DESCRIPTION="ежедневно в 02:00"
        ;;
    2)
        CRON_SCHEDULE="0 2,14 * * *"
        DESCRIPTION="дважды в день (02:00 и 14:00)"
        ;;
    3)
        CRON_SCHEDULE="0 2 * * 0"
        DESCRIPTION="еженедельно (воскресенье в 02:00)"
        ;;
    4)
        CRON_SCHEDULE="0 2 1 * *"
        DESCRIPTION="ежемесячно (1-го числа в 02:00)"
        ;;
    5)
        echo ""
        echo "Введите расписание в формате cron (например: 0 2 * * *):"
        read -r CRON_SCHEDULE
        DESCRIPTION="пользовательское расписание: $CRON_SCHEDULE"
        ;;
    0)
        echo -e "${YELLOW}?? Отменено${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}? Неверный выбор${NC}"
        exit 1
        ;;
esac

# Создание cron задачи
CRON_JOB="$CRON_SCHEDULE $BACKUP_SCRIPT >> $PROJECT_ROOT/logs/cron_backup.log 2>&1"

echo ""
echo -e "${BLUE}?? Будет создана cron задача:${NC}"
echo "  Расписание: $DESCRIPTION"
echo "  Команда: $BACKUP_SCRIPT"
echo ""

read -p "Продолжить? [Y/n] " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    # Удаляем старые задачи для этого скрипта
    (crontab -l 2>/dev/null | grep -v "$BACKUP_SCRIPT" || true) | crontab -
    
    # Добавляем новую задачу
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    
    echo -e "${GREEN}? Cron задача установлена${NC}\n"
    
    echo -e "${BLUE}?? Текущие cron задачи:${NC}"
    crontab -l
    
    echo ""
    echo -e "${YELLOW}?? Логи бэкапов будут сохраняться в:${NC}"
    echo "   $PROJECT_ROOT/logs/cron_backup.log"
else
    echo -e "${YELLOW}?? Отменено${NC}"
fi
