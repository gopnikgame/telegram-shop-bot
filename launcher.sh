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
    
    # Проверяем существование manage_bot.sh
    if [ ! -f "manage_bot.sh" ]; then
        log "YELLOW" "⚠️ manage_bot.sh не найден, обновление из репозитория..."
        
        # Создаем бэкап важных файлов
        BACKUP_DIR="$(mktemp -d)"
        log "BLUE" "💾 Создание бэкапа конфигурации в $BACKUP_DIR..."
        [ -f ".env" ] && cp ".env" "$BACKUP_DIR/"
        [ -f "app/texts.yml" ] && cp "app/texts.yml" "$BACKUP_DIR/"
        
        # Обновляем из репозитория
        if [ -d ".git" ]; then
            log "BLUE" "🔄 Обновление через git pull..."
            git fetch origin
            git reset --hard origin/main
        else
            log "BLUE" "🔄 Переустановка из репозитория..."
            cd ..
            rm -rf "$INSTALL_DIR"
            git clone "$REPO_URL" "$INSTALL_DIR"
            cd "$INSTALL_DIR"
        fi
        
        # Восстанавливаем конфигурацию
        if [ -f "$BACKUP_DIR/.env" ]; then
            log "BLUE" "♻️ Восстановление .env..."
            cp "$BACKUP_DIR/.env" ".env"
        fi
        if [ -f "$BACKUP_DIR/texts.yml" ]; then
            log "BLUE" "♻️ Восстановление texts.yml..."
            cp "$BACKUP_DIR/texts.yml" "app/texts.yml"
        fi
        
        log "GREEN" "✅ Обновление завершено"
    fi
    
    # Добавляем права на выполнение скрипта manage_bot.sh
    chmod +x manage_bot.sh
    
    # Запускаем скрипт manage_bot.sh
    log "BLUE" "🚀 Запуск основного скрипта управления..."
    ./manage_bot.sh
else
    log "BLUE" "⬇️ Клонирование репозитория..."
    # Создаем временную директорию
    TEMP_DIR=$(mktemp -d)
    # Переходим во временную директорию
    cd "$TEMP_DIR"
    # Клонируем репозиторий
    git clone "$REPO_URL" "$PROJECT_DIR"
    # Переходим в директорию проекта
    cd "$PROJECT_DIR"
    # Создаем директорию установки, если она не существует
    mkdir -p "$INSTALL_DIR"
    # Копируем файлы в директорию установки
    log "BLUE" "📦 Копирование файлов в директорию установки..."
    cp -r . "$INSTALL_DIR"
    # Переходим в директорию установки
    cd "$INSTALL_DIR"
    # Добавляем права на выполнение скрипта manage_bot.sh
    chmod +x manage_bot.sh
    # Запускаем скрипт manage_bot.sh
    log "BLUE" "🚀 Запуск основного скрипта управления..."
    ./manage_bot.sh
    # Удаляем временную директорию
    rm -rf "$TEMP_DIR"
fi

log "GREEN" "✅ Установка/обновление завершено"