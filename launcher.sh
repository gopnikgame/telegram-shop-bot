#!/bin/bash

# Включаем строгий режим
set -euo pipefail

# Конфигурация
REPO_URL="https://github.com/gopnikgame/telegram-shop-bot.git"
PROJECT_DIR="telegram-shop-bot"
INSTALL_DIR="/opt/$PROJECT_DIR" # Постоянная директория для установки
LOG_FILE="/var/log/telegram-shop-bot.log"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для логирования
log() {
    local level=$1
    local message=$2
    echo -e "${!level}${message}${NC}" | tee -a "$LOG_FILE"
}

# Функция для создания wrapper-скриптов
create_symlinks() {
    log "BLUE" "🔗 Создание wrapper-скриптов для быстрого запуска..."
    
    local manage_script="$INSTALL_DIR/manage_bot.sh"
    local bin_dir="/usr/local/bin"
    
    # Проверяем существование скрипта
    if [ ! -f "$manage_script" ]; then
        log "RED" "❌ Файл $manage_script не найден"
        return 1
    fi
    
    # Создаем wrapper-скрипты
    local commands=("shopbot" "manager")
    for cmd in "${commands[@]}"; do
        local wrapper_path="$bin_dir/$cmd"
        
        # Удаляем старый файл, если существует
        if [ -f "$wrapper_path" ]; then
            log "YELLOW" "⚠️ Удаление существующего скрипта $cmd..."
            rm -f "$wrapper_path"
        fi
        
        # Создаем wrapper-скрипт
        cat > "$wrapper_path" << EOF
#!/bin/bash
# Wrapper script for telegram-shop-bot manager
cd "$INSTALL_DIR" && exec bash manage_bot.sh "\$@"
EOF
        
        # Устанавливаем права на выполнение
        chmod +x "$wrapper_path"
        
        if [ -x "$wrapper_path" ]; then
            log "GREEN" "✅ Создан wrapper-скрипт: $cmd"
        else
            log "RED" "❌ Не удалось создать wrapper-скрипт $cmd"
        fi
    done
    
    log "GREEN" "✅ Wrapper-скрипты созданы. Теперь можно запускать из любой директории:"
    echo "  - shopbot"
    echo "  - manager"
}

# Проверка зависимостей
log "BLUE" "🔍 Проверка зависимостей..."
if ! command -v git &> /dev/null || ! command -v docker &> /dev/null || ! command -v nano &> /dev/null; then
    log "YELLOW" "⚠️ Установка необходимых пакетов..."
    
    # Определяем менеджер пакетов
    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y git docker.io nano
    elif command -v yum &> /dev/null; then
        yum install -y git docker nano
    elif command -v dnf &> /dev/null; then
        dnf install -y git docker nano
    else
        log "RED" "❌ Неизвестный менеджер пакетов"
        exit 1
    fi
fi

# Проверка docker-compose или docker compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    log "YELLOW" "⚠️ Установка Docker Compose..."
    if command -v apt-get &> /dev/null; then
        apt-get install -y docker-compose-plugin
    else
        # Установка через pip как fallback
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
fi

# Проверка существования директории установки
if [ -d "$INSTALL_DIR" ]; then
    log "BLUE" "🚀 Директория установки существует: $INSTALL_DIR"
    
    # Переходим в директорию установки
    cd "$INSTALL_DIR"
    
    # Проверяем, является ли директория git репозиторием
    if [ -d ".git" ]; then
        log "BLUE" "🔄 Обнаружен git репозиторий, проверяем обновления..."
        
        # Создаем бэкап конфигурации
        BACKUP_DIR="/opt/$PROJECT_DIR/backups/backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        log "BLUE" "💾 Создание бэкапа конфигурации..."
        
        # Бэкап .env
        if [ -f ".env" ]; then
            cp ".env" "$BACKUP_DIR/"
            log "GREEN" "  ✅ .env сохранен"
        fi
        
        # Бэкап texts.yml
        if [ -f "app/texts.yml" ]; then
            cp "app/texts.yml" "$BACKUP_DIR/"
            log "GREEN" "  ✅ texts.yml сохранен"
        fi
        
        # Бэкап папки static (изображения)
        if [ -d "static" ]; then
            cp -r "static" "$BACKUP_DIR/"
            log "GREEN" "  ✅ static/ сохранен ($(du -sh static 2>/dev/null | cut -f1))"
        fi
        
        # Бэкап папки uploads (загруженные файлы)
        if [ -d "uploads" ] && [ "$(ls -A uploads 2>/dev/null)" ]; then
            cp -r "uploads" "$BACKUP_DIR/"
            log "GREEN" "  ✅ uploads/ сохранен ($(du -sh uploads 2>/dev/null | cut -f1))"
        fi
        
        # Получаем обновления
        git fetch origin
        
        CURRENT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        REMOTE=$(git rev-parse origin/main 2>/dev/null || echo "unknown")
        
        if [ "$CURRENT" != "$REMOTE" ] && [ "$CURRENT" != "unknown" ]; then
            log "YELLOW" "⚠️ Доступны обновления"
            log "BLUE" "📋 Новые изменения:"
            git log HEAD..origin/main --oneline --graph --decorate 2>/dev/null || true
            
            echo ""
            read -r -p "Обновить до последней версии? [Y/n] " response
            response=${response:-Y}
            
            if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
                log "BLUE" "🔄 Обновление..."
                
                # Сохраняем URL репозитория
                REPO_URL=$(git config --get remote.origin.url)
                
                # Удаляем все файлы кроме backups и uploads
                log "BLUE" "🗑️ Очистка директории (сохраняем backups и uploads)..."
                find . -maxdepth 1 ! -name '.' ! -name '..' ! -name 'backups' ! -name 'uploads' -exec rm -rf {} + 2>/dev/null || true
                
                # Клонируем репозиторий заново
                log "BLUE" "📥 Клонирование свежей версии..."
                git clone "$REPO_URL" temp_clone
                
                # Перемещаем файлы
                log "BLUE" "📦 Распаковка файлов..."
                mv temp_clone/.git .
                mv temp_clone/* . 2>/dev/null || true
                mv temp_clone/.* . 2>/dev/null || true
                rm -rf temp_clone
                
                # Восстанавливаем конфигурацию
                log "BLUE" "♻️ Восстановление конфигурации..."
                
                # Восстановление .env
                if [ -f "$BACKUP_DIR/.env" ]; then
                    cp "$BACKUP_DIR/.env" ".env"
                    log "GREEN" "  ✅ .env восстановлен"
                fi
                
                # Восстановление texts.yml
                if [ -f "$BACKUP_DIR/texts.yml" ]; then
                    cp "$BACKUP_DIR/texts.yml" "app/texts.yml"
                    log "GREEN" "  ✅ texts.yml восстановлен"
                fi
                
                # Восстановление static (изображения)
                if [ -d "$BACKUP_DIR/static" ]; then
                    mkdir -p "static"
                    cp -r "$BACKUP_DIR/static/"* "static/" 2>/dev/null || true
                    log "GREEN" "  ✅ static/ восстановлен (изображения)"
                fi
                
                # Восстановление uploads
                if [ -d "$BACKUP_DIR/uploads" ] && [ "$(ls -A "$BACKUP_DIR/uploads" 2>/dev/null)" ]; then
                    cp -rn "$BACKUP_DIR/uploads/"* "uploads/" 2>/dev/null || true
                    log "GREEN" "  ✅ uploads/ восстановлен (загруженные файлы)"
                fi
                
                log "GREEN" "✅ Обновление завершено"
            fi
        else
            log "GREEN" "✅ Уже используется последняя версия"
        fi
    else
        log "YELLOW" "⚠️ Директория не является git репозиторием, переустановка..."
        
        # Создаем бэкап
        BACKUP_DIR="/opt/$PROJECT_DIR/backups/backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        log "BLUE" "💾 Создание бэкапа..."
        [ -f ".env" ] && cp ".env" "$BACKUP_DIR/"
        [ -f "app/texts.yml" ] && cp "app/texts.yml" "$BACKUP_DIR/"
        [ -d "static" ] && cp -r "static" "$BACKUP_DIR/"
        [ -d "uploads" ] && [ "$(ls -A uploads 2>/dev/null)" ] && cp -r "uploads" "$BACKUP_DIR/"
        
        # Удаляем и клонируем заново
        cd /opt
        rm -rf "$INSTALL_DIR"
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
        
        # Восстанавливаем конфигурацию
        log "BLUE" "♻️ Восстановление конфигурации..."
        [ -f "$BACKUP_DIR/.env" ] && cp "$BACKUP_DIR/.env" ".env"
        [ -f "$BACKUP_DIR/texts.yml" ] && cp "$BACKUP_DIR/texts.yml" "app/texts.yml"
        [ -d "$BACKUP_DIR/static" ] && mkdir -p "static" && cp -r "$BACKUP_DIR/static/"* "static/" 2>/dev/null || true
        [ -d "$BACKUP_DIR/uploads" ] && cp -rn "$BACKUP_DIR/uploads/"* "uploads/" 2>/dev/null || true
    fi
    
    # Добавляем права на выполнение
    chmod +x manage_bot.sh
    
    # Создаем wrapper-скрипты
    create_symlinks
    
    # Запускаем менеджер
    log "BLUE" "🚀 Запуск менеджера..."
    ./manage_bot.sh
else
    log "BLUE" "⬇️ Первая установка, клонирование репозитория..."
    
    # Создаем директорию установки
    mkdir -p "$INSTALL_DIR"
    
    # Клонируем репозиторий
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Добавляем права на выполнение
    chmod +x manage_bot.sh
    
    # Создаем wrapper-скрипты
    create_symlinks
    
    # Запускаем менеджер
    log "BLUE" "🚀 Запуск менеджера..."
    ./manage_bot.sh
fi

log "GREEN" "✅ Готово!"