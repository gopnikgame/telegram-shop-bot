#!/bin/bash

# Включаем строгий режим
set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
NC='\033[0m' # No Color

# Конфигурация проекта
PROJECT_NAME="telegram-shop-bot"
INSTALL_DIR="/opt/$PROJECT_NAME"
LOGS_DIR="$INSTALL_DIR/logs"
BACKUPS_DIR="$INSTALL_DIR/backups"

# Файлы конфигурации
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"
TEXTS_FILE="app/texts.yml"

# Файлы логов
BOT_LOG_FILE="$LOGS_DIR/bot.log"
ERROR_LOG_FILE="$LOGS_DIR/error.log"
DOCKER_LOG_FILE="$LOGS_DIR/docker.log"

# Скрипты
RESET_DB_SCRIPT="scripts/reset_db.sh"

# Создаем директории для логов и бэкапов
mkdir -p "$LOGS_DIR" "$BACKUPS_DIR"

# Функция для логирования
log() {
    local level=$1
    local message=$2
    echo -e "${!level}${message}${NC}"
}

# Функция для запуска docker-compose
docker_compose_cmd() {
    if command -v docker-compose &> /dev/null; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

# Функция для управления .env файлом
manage_env_file() {
    local created=false

    log "BLUE" "📝 Управление конфигурацией .env..."
    log "BLUE" "📍 Текущая директория: $(pwd)"

    # Проверяем существование файлов
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE" ]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            created=true
            log "GREEN" "✅ Создан новый .env файл из примера"
        else
            log "RED" "❌ Файл .env.example не найден!"
            return 1
        fi
    fi

    # Показываем текущие значения (без паролей)
    log "CYAN" "\n📋 Текущие переменные окружения:"
    grep -v '^#' "$ENV_FILE" | grep -v '^$' | while read -r line; do
        key=$(echo "$line" | cut -d'=' -f1)
        value=$(echo "$line" | cut -d'=' -f2-)
        
        # Скрывачем чувствительные данные
        if [[ "$key" == *"PASSWORD"* ]] || [[ "$key" == *"SECRET"* ]] || [[ "$key" == *"TOKEN"* ]]; then
            if [ -n "$value" ]; then
                echo "  $key=***"
            else
                log "YELLOW" "  $key= (не заполнено)"
            fi
        else
            if [ -n "$value" ]; then
                echo "  $key=$value"
            else
                log "YELLOW" "  $key= (не заполнено)"
            fi
        fi
    done

    # Предлагаем отредактировать файл
    echo ""
    read -r -p "Редактировать .env файл сейчас? [Y/n] " response
    response=${response:-Y}
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        if command -v nano &> /dev/null; then
            log "BLUE" "🚀 Запускаем nano для редактирования .env..."
            nano "$ENV_FILE"
            editor_result=$?
        elif command -v vim &> /dev/null; then
            log "BLUE" "🚀 Запускаем vim для редактирования .env..."
            vim "$ENV_FILE"
            editor_result=$?
        else
            log "BLUE" "🚀 Запускаем vi для редактирования .env..."
            vi "$ENV_FILE"
            editor_result=$?
        fi

        if [ "$editor_result" -ne 0 ]; then
            log "RED" "❌ Редактор вернул код ошибки: $editor_result"
            return 1
        fi
        
        log "GREEN" "✅ Файл .env обновлен"
    fi

    # Проверка обязательных параметров
    log "BLUE" "\n🔍 Проверка обязательных параметров..."
    
    local required_vars=("BOT_TOKEN" "DATABASE_URL" "YK_SHOP_ID" "YK_SECRET_KEY")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=..*" "$ENV_FILE"; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log "YELLOW" "⚠️ Не заполнены обязательные параметры:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        log "YELLOW" "⚠️ Бот не запустится без этих параметров!"
        return 1
    fi
    
    log "GREEN" "✅ Все обязательные параметры заполнены"
    return 0
}

# Функция для редактирования texts.yml
manage_texts_file() {
    log "BLUE" "📝 Редактирование texts.yml..."
    
    if [ ! -f "$TEXTS_FILE" ]; then
        log "RED" "❌ Файл $TEXTS_FILE не найден!"
        return 1
    fi
    
    log "CYAN" "📄 Файл содержит настройки текстов бота:"
    echo "  - Тексты кнопок"
    echo "  - Сообщения главного меню"
    echo "  - Описания секций"
    echo "  - Настройки оплаты"
    echo "  - Уведомления"
    echo ""
    
    read -r -p "Редактировать texts.yml? [y/N] " response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        if command -v nano &> /dev/null; then
            nano "$TEXTS_FILE"
        elif command -v vim &> /dev/null; then
            vim "$TEXTS_FILE"
        else
            vi "$TEXTS_FILE"
        fi
        log "GREEN" "✅ Файл texts.yml обновлен"
    fi
}

# Функция для обновления репозитория
update_repo() {
    log "BLUE" "🔄 Обновление репозитория..."

    # Проверяем, находимся ли мы в git-репозитории
    if [ ! -d ".git" ]; then
        log "RED" "❌ Текущая директория не является git-репозиторием"
        return 1
    fi

    # Создаем бэкап конфигурационных файлов
    local backup_dir="$BACKUPS_DIR/backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    log "BLUE" "💾 Создание бэкапа конфигурации в $backup_dir..."
    
    # Бэкап .env
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$backup_dir/"
        log "GREEN" "  ✅ .env сохранен"
    fi
    
    # Бэкап texts.yml
    if [ -f "$TEXTS_FILE" ]; then
        cp "$TEXTS_FILE" "$backup_dir/"
        log "GREEN" "  ✅ texts.yml сохранен"
    fi
    
    # Бэкап папки static (изображения)
    if [ -d "static" ]; then
        cp -r "static" "$backup_dir/"
        log "GREEN" "  ✅ static/ сохранен ($(du -sh static 2>/dev/null | cut -f1))"
    fi
    
    # Бэкап папки uploads (загруженные файлы)
    if [ -d "uploads" ] && [ "$(ls -A uploads 2>/dev/null)" ]; then
        cp -r "uploads" "$backup_dir/"
        log "GREEN" "  ✅ uploads/ сохранен ($(du -sh uploads 2>/dev/null | cut -f1))"
    fi
    
    # Получаем информацию о репозитории
    git fetch origin
    
    # Показываем изменения
    if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
        log "CYAN" "\n📋 Новые изменения в репозитории:"
        git log HEAD..origin/main --oneline --graph --decorate
        echo ""
        read -r -p "Применить обновления? [Y/n] " response
        response=${response:-Y}
        
        if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            log "YELLOW" "⚠️ Обновление отменено"
            return 0
        fi
    else
        log "GREEN" "✅ Репозиторий уже актуален"
        return 0
    fi
    
    # Останавливаем контейнеры
    log "BLUE" "⏹️ Остановка контейнеров..."
    docker_compose_cmd down
    
    # Сохраняем URL репозитория
    local repo_url=$(git config --get remote.origin.url)
    
    # Удаляем все файлы кроме backups и uploads
    log "BLUE" "🗑️ Очистка директории (сохраняем backups и uploads)..."
    find . -maxdepth 1 ! -name '.' ! -name '..' ! -name 'backups' ! -name 'uploads' -exec rm -rf {} + 2>/dev/null || true
    
    # Клонируем репозиторий заново
    log "BLUE" "📥 Клонирование свежей версии репозитория..."
    git clone "$repo_url" temp_clone
    
    # Перемещаем файлы из temp_clone в текущую директорию
    log "BLUE" "📦 Распаковка файлов..."
    mv temp_clone/.git .
    mv temp_clone/* . 2>/dev/null || true
    mv temp_clone/.* . 2>/dev/null || true
    rm -rf temp_clone
    
    log "GREEN" "✅ Репозиторий обновлен"

    # Восстановление конфигурации
    log "BLUE" "♻️ Восстановление конфигурации..."
    
    # Восстановление .env
    if [ -f "$backup_dir/.env" ]; then
        cp "$backup_dir/.env" "$ENV_FILE"
        log "GREEN" "  ✅ .env восстановлен"
    else
        log "YELLOW" "  ⚠️ Бэкап .env не найден, нужно настроить заново"
    fi
    
    # Восстановление texts.yml
    if [ -f "$backup_dir/texts.yml" ]; then
        cp "$backup_dir/texts.yml" "$TEXTS_FILE"
        log "GREEN" "  ✅ texts.yml восстановлен"
    else
        log "YELLOW" "  ⚠️ Бэкап texts.yml не найден, используется версия из репозитория"
    fi
    
    # Восстановление static (изображения)
    if [ -d "$backup_dir/static" ]; then
        # Создаем папку static если её нет
        mkdir -p "static"
        
        # Копируем содержимое
        cp -r "$backup_dir/static/"* "static/" 2>/dev/null || true
        log "GREEN" "  ✅ static/ восстановлен (изображения)"
    else
        log "YELLOW" "  ⚠️ Бэкап static/ не найден, используется версия из репозитория"
    fi
    
    # Восстановление uploads (если были загруженные файлы в бэкапе)
    if [ -d "$backup_dir/uploads" ] && [ "$(ls -A "$backup_dir/uploads" 2>/dev/null)" ]; then
        # Объединяем старые и новые uploads (не перезаписываем существующие)
        cp -rn "$backup_dir/uploads/"* "uploads/" 2>/dev/null || true
        log "GREEN" "  ✅ uploads/ восстановлен (загруженные файлы)"
    fi
    
    log "GREEN" "✅ Обновление завершено"
    
    # Информация о сохраненном бэкапе
    log "CYAN" "\n💾 Бэкап сохранен в: $backup_dir"
    log "CYAN" "   Содержимое:"
    ls -lh "$backup_dir" | tail -n +2 | awk '{print "     - " $9 " (" $5 ")"}'
    
    # Предлагаем перезапустить контейнеры
    echo ""
    read -r -p "Перезапустить контейнеры? [Y/n] " response
    response=${response:-Y}
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        manage_containers "start"
    else
        log "YELLOW" "⚠️ Не забудьте перезапустить контейнеры: docker compose up -d"
    fi
}

# Функция для инициализации базы данных
init_database() {
    log "BLUE" "🗄️ Инициализация базы данных..."
    
    # Проверяем, запущен ли контейнер БД
    if ! docker ps | grep -q "shopbot-postgres"; then
        log "YELLOW" "⚠️ База данных не запущена. Запускаем..."
        docker_compose_cmd up -d db
        log "BLUE" "⏳ Ожидание запуска PostgreSQL..."
        sleep 10
    fi
    
    # Применяем миграции
    log "BLUE" "🔄 Применение миграций..."
    
    if docker exec shopbot-api alembic current 2>/dev/null; then
        log "CYAN" "📋 Текущая версия БД:"
        docker exec shopbot-api alembic current
        
        echo ""
        read -r -p "Применить миграции? [Y/n] " response
        response=${response:-Y}
        
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            docker exec shopbot-api alembic upgrade head
            log "GREEN" "✅ Миграции применены"
        fi
    else
        log "YELLOW" "⚠️ Контейнер API не запущен. Миграции будут применены при запуске."
    fi
}

# Функция для управления контейнерами
manage_containers() {
    local action=$1

    log "BLUE" "🐳 Управление контейнерами..."

    case $action in
        "start")
            log "BLUE" "▶️ Запуск контейнеров..."
            docker_compose_cmd up -d
            
            log "BLUE" "⏳ Ожидание запуска сервисов..."
            sleep 5
            
            # Проверка статуса
            if docker ps | grep -q "shopbot-api" && docker ps | grep -q "shopbot-postgres"; then
                log "GREEN" "✅ Контейнеры запущены"
                log "CYAN" "\n📊 Статус сервисов:"
                docker_compose_cmd ps
                
                log "CYAN" "\n🔗 Доступные URL:"
                echo "  - API: http://localhost:8000"
                echo "  - Health: http://localhost:8000/health/"
                echo "  - Admin: http://localhost:8000/admin/"
                echo "  - PostgreSQL: localhost:5432"
            else
                log "RED" "❌ Ошибка запуска контейнеров"
                docker_compose_cmd logs --tail=20
                return 1
            fi
            ;;
            
        "stop")
            log "BLUE" "⏹️ Остановка контейнеров..."
            docker_compose_cmd down
            log "GREEN" "✅ Контейнеры остановлены"
            ;;
            
        "restart")
            log "BLUE" "🔄 Перезапуск контейнеров..."
            docker_compose_cmd restart
            
            log "BLUE" "⏳ Ожидание перезапуска..."
            sleep 5
            
            if docker ps | grep -q "shopbot-api"; then
                log "GREEN" "✅ Контейнеры перезапущены"
                docker_compose_cmd logs --tail=10
            else
                log "RED" "❌ Ошибка перезапуска"
                return 1
            fi
            ;;
            
        "rebuild")
            log "BLUE" "🔨 Пересборка контейнеров..."
            docker_compose_cmd down
            docker_compose_cmd build --no-cache
            docker_compose_cmd up -d
            
            log "BLUE" "⏳ Ожидание запуска..."
            sleep 10
            
            if docker ps | grep -q "shopbot-api"; then
                log "GREEN" "✅ Контейнеры пересобраны и запущены"
            else
                log "RED" "❌ Ошибка при пересборке"
                return 1
            fi
            ;;
    esac
}

# Функция для просмотра логов
view_logs() {
    local log_type=$1
    
    case $log_type in
        "all")
            log "CYAN" "📊 Все логи контейнеров:"
            docker_compose_cmd logs --tail=50
            ;;
        "api")
            log "CYAN" "📊 Логи API:"
            docker_compose_cmd logs api --tail=50
            ;;
        "db")
            log "CYAN" "📊 Логи PostgreSQL:"
            docker_compose_cmd logs db --tail=50
            ;;
        "errors")
            log "RED" "❌ Логи ошибок:"
            docker_compose_cmd logs --tail=100 | grep -i "error\|exception\|failed"
            ;;
        "follow")
            log "CYAN" "📊 Отслеживание логов (Ctrl+C для выхода):"
            docker_compose_cmd logs -f
            ;;
    esac
}

# Функция для очистки
cleanup() {
    log "BLUE" "🧹 Очистка..."
    
    echo ""
    log "CYAN" "Что очистить?"
    echo "1. Старые логи (старше 30 дней)"
    echo "2. Старые бэкапы (старше 30 дней)"
    echo "3. Docker volumes (⚠️ удалит базу данных!)"
    echo "4. Docker images и build cache"
    echo "5. Всё вышеперечисленное (кроме volumes)"
    echo "0. Отмена"
    
    read -r -p "Выберите действие (0-5): " choice
    
    case $choice in
        1)
            log "BLUE" "🗑️ Удаление старых логов..."
            find "$LOGS_DIR" -type f -mtime +30 -delete 2>/dev/null || true
            log "GREEN" "✅ Старые логи удалены"
            ;;
        2)
            log "BLUE" "🗑️ Удаление старых бэкапов..."
            find "$BACKUPS_DIR" -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true
            log "GREEN" "✅ Старые бэкапы удалены"
            ;;
        3)
            log "RED" "⚠️ ВНИМАНИЕ! Это удалит базу данных!"
            read -r -p "Продолжить? [y/N] " confirm
            if [[ "$confirm" =~ ^([yY])$ ]]; then
                docker_compose_cmd down -v
                log "GREEN" "✅ Volumes удалены"
            fi
            ;;
        4)
            log "BLUE" "🗑️ Очистка Docker..."
            docker system prune -af
            log "GREEN" "✅ Docker очищен"
            ;;
        5)
            log "BLUE" "🗑️ Полная очистка..."
            find "$LOGS_DIR" -type f -mtime +30 -delete 2>/dev/null || true
            find "$BACKUPS_DIR" -type d -mtime +30 -exec rm -rf {} + 2>/dev/null || true
            docker system prune -af
            log "GREEN" "✅ Очистка завершена"
            ;;
        0)
            log "YELLOW" "⚠️ Отменено"
            ;;
        *)
            log "RED" "❌ Неверный выбор"
            ;;
    esac
}

# Функция для создания бэкапа БД
backup_database() {
    log "BLUE" "💾 Создание бэкапа базы данных..."
    
    local backup_file="$BACKUPS_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    if docker ps | grep -q "shopbot-postgres"; then
        docker exec shopbot-postgres pg_dump -U shopbot shopbot > "$backup_file"
        log "GREEN" "✅ Бэкап создан: $backup_file"
    else
        log "RED" "❌ База данных не запущена"
        return 1
    fi
}

# Функция для восстановления БД
restore_database() {
    log "BLUE" "♻️ Восстановление базы данных..."
    
    # Показываем доступные бэкапы
    log "CYAN" "\n📋 Доступные бэкапы:"
    local backups=($(ls -t "$BACKUPS_DIR"/db_backup_*.sql 2>/dev/null))
    
    if [ ${#backups[@]} -eq 0 ]; then
        log "RED" "❌ Бэкапы не найдены"
        return 1
    fi
    
    local i=1
    for backup in "${backups[@]}"; do
        echo "$i. $(basename "$backup")"
        i=$((i+1))
    done
    
    read -r -p "Выберите номер бэкапа (0 для отмены): " choice
    
    if [ "$choice" -eq 0 ] 2>/dev/null; then
        log "YELLOW" "⚠️ Отменено"
        return 0
    fi
    
    if [ "$choice" -ge 1 ] 2>/dev/null && [ "$choice" -le "${#backups[@]}" ]; then
        local backup_file="${backups[$((choice-1))]}"
        
        log "RED" "⚠️ ВНИМАНИЕ! Текущие данные будут заменены!"
        read -r -p "Продолжить? [y/N] " confirm
        
        if [[ "$confirm" =~ ^([yY])$ ]]; then
            if docker ps | grep -q "shopbot-postgres"; then
                docker exec -i shopbot-postgres psql -U shopbot shopbot < "$backup_file"
                log "GREEN" "✅ База данных восстановлена"
            else
                log "RED" "❌ База данных не запущена"
                return 1
            fi
        fi
    else
        log "RED" "❌ Неверный выбор"
    fi
}

# Функция для полного сброса базы данных
reset_database() {
    log "RED" "💣 Полный сброс базы данных..."
    log "RED" "⚠️ ВНИМАНИЕ! Все данные будут удалены безвозвратно!"
    echo ""
    log "YELLOW" "Это действие:"
    echo "  - Остановит все контейнеры"
    echo "  - Удалит volume с базой данных"
    echo "  - Пересоздаст базу данных с нуля"
    echo "  - Применит все миграции заново"
    echo ""
    
    read -r -p "Введите 'yes' для подтверждения: " confirm
    
    if [ "$confirm" != "yes" ]; then
        log "YELLOW" "⚠️ Отменено"
        return 0
    fi
    
    # Создаем бэкап перед сбросом
    log "BLUE" "💾 Создание бэкапа перед сбросом..."
    backup_database || log "YELLOW" "⚠️ Не удалось создать бэкап"
    
    # Проверяем наличие скрипта reset_db.sh
    if [ -f "$RESET_DB_SCRIPT" ]; then
        log "BLUE" "🚀 Запуск скрипта сброса..."
        bash "$RESET_DB_SCRIPT"
    else
        # Выполняем сброс вручную
        log "BLUE" "⏹️ Останавливаем контейнеры..."
        docker_compose_cmd down
        
        log "BLUE" "🗑️ Удаляем volume с базой данных..."
        docker volume rm "${PROJECT_NAME}_postgres_data" 2>/dev/null || true
        
        log "BLUE" "▶️ Запускаем контейнеры..."
        docker_compose_cmd up -d
        
        log "BLUE" "⏳ Ожидание запуска базы данных..."
        sleep 10
        
        log "BLUE" "🔄 Применяем миграции..."
        docker exec shopbot-api alembic upgrade head
        
        log "GREEN" "✅ База данных пересоздана!"
    fi
}

# Функция для проверки статуса
check_status() {
    log "CYAN" "📊 Статус системы:"
    echo ""
    
    # Статус контейнеров
    log "BLUE" "🐳 Docker контейнеры:"
    docker_compose_cmd ps
    
    echo ""
    
    # Статус сервисов
    log "BLUE" "🔍 Проверка сервисов:"
    
    if curl -s http://localhost:8000/health/ | grep -q '"status": "ok"'; then
        log "GREEN" "  ✅ API доступен (http://localhost:8000)"
    else
        log "RED" "  ❌ API недоступен"
    fi
    
    if docker ps | grep -q "shopbot-postgres"; then
        log "GREEN" "  ✅ PostgreSQL запущен"
    else
        log "RED" "  ❌ PostgreSQL не запущен"
    fi
    
    echo ""
    
    # Версия БД
    if docker exec shopbot-api alembic current 2>/dev/null; then
        log "BLUE" "🗄️ Версия БД:"
        docker exec shopbot-api alembic current
    fi
}

# Функция для управления бэкапами
manage_backups() {
    log "BLUE" "💾 Управление бэкапами..."
    
    echo ""
    log "CYAN" "Выберите действие:"
    echo "1. Показать все бэкапы"
    echo "2. Создать полный бэкап (БД + конфигурация + изображения)"
    echo "3. Восстановить из бэкапа"
    echo "4. Удалить старые бэкапы (старше 30 дней)"
    echo "5. Удалить конкретный бэкап"
    echo "0. Назад"
    
    read -r -p "Выберите действие (0-5): " choice
    
    case $choice in
        1)
            log "CYAN" "\n📋 Доступные бэкапы:"
            echo ""
            
            # Бэкапы конфигурации
            local config_backups=($(ls -dt "$BACKUPS_DIR"/backup_* 2>/dev/null))
            if [ ${#config_backups[@]} -gt 0 ]; then
                log "BLUE" "📁 Бэкапы конфигурации:"
                for backup in "${config_backups[@]}"; do
                    local size=$(du -sh "$backup" 2>/dev/null | cut -f1)
                    local date=$(basename "$backup" | sed 's/backup_//' | sed 's/_/ /g')
                    echo "  - $(basename "$backup") ($size) - $date"
                    
                    # Показываем содержимое
                    if [ -d "$backup" ]; then
                        ls -lh "$backup" 2>/dev/null | tail -n +2 | awk '{print "      • " $9 " (" $5 ")"}'
                    fi
                done
                echo ""
            fi
            
            # Бэкапы БД
            local db_backups=($(ls -t "$BACKUPS_DIR"/db_backup_*.sql 2>/dev/null))
            if [ ${#db_backups[@]} -gt 0 ]; then
                log "BLUE" "🗄️ Бэкапы базы данных:"
                for backup in "${db_backups[@]}"; do
                    local size=$(du -sh "$backup" 2>/dev/null | cut -f1)
                    local date=$(basename "$backup" | sed 's/db_backup_//' | sed 's/.sql//' | sed 's/_/ /g')
                    echo "  - $(basename "$backup") ($size) - $date"
                done
                echo ""
            fi
            
            if [ ${#config_backups[@]} -eq 0 ] && [ ${#db_backups[@]} -eq 0 ]; then
                log "YELLOW" "⚠️ Бэкапы не найдены"
            fi
            
            # Показываем общий размер
            local total_size=$(du -sh "$BACKUPS_DIR" 2>/dev/null | cut -f1)
            log "CYAN" "📦 Общий размер бэкапов: $total_size"
            ;;
            
        2)
            log "BLUE" "💾 Создание полного бэкапа..."
            
            local backup_dir="$BACKUPS_DIR/backup_$(date +%Y%m%d_%H%M%S)"
            mkdir -p "$backup_dir"
            
            # Бэкап .env
            if [ -f "$ENV_FILE" ]; then
                cp "$ENV_FILE" "$backup_dir/"
                log "GREEN" "  ✅ .env сохранен"
            fi
            
            # Бэкап texts.yml
            if [ -f "$TEXTS_FILE" ]; then
                cp "$TEXTS_FILE" "$backup_dir/"
                log "GREEN" "  ✅ texts.yml сохранен"
            fi
            
            # Бэкап static
            if [ -d "static" ]; then
                cp -r "static" "$backup_dir/"
                log "GREEN" "  ✅ static/ сохранен ($(du -sh static 2>/dev/null | cut -f1))"
            fi
            
            # Бэкап uploads
            if [ -d "uploads" ] && [ "$(ls -A uploads 2>/dev/null)" ]; then
                cp -r "uploads" "$backup_dir/"
                log "GREEN" "  ✅ uploads/ сохранен ($(du -sh uploads 2>/dev/null | cut -f1))"
            fi
            
            # Бэкап БД
            if docker ps | grep -q "shopbot-postgres"; then
                local db_backup_file="$BACKUPS_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
                docker exec shopbot-postgres pg_dump -U shopbot shopbot > "$db_backup_file"
                log "GREEN" "  ✅ База данных сохранена ($(du -sh "$db_backup_file" 2>/dev/null | cut -f1))"
            else
                log "YELLOW" "  ⚠️ База данных не запущена, пропускаем"
            fi
            
            log "GREEN" "✅ Полный бэкап создан: $backup_dir"
            log "CYAN" "   Размер: $(du -sh "$backup_dir" 2>/dev/null | cut -f1)"
            ;;
            
        3)
            log "BLUE" "♻️ Восстановление из бэкапа..."
            
            local backups=($(ls -dt "$BACKUPS_DIR"/backup_* 2>/dev/null))
            
            if [ ${#backups[@]} -eq 0 ]; then
                log "RED" "❌ Бэкапы не найдены"
                return 1
            fi
            
            log "CYAN" "\n📋 Доступные бэкапы:"
            local i=1
            for backup in "${backups[@]}"; do
                local size=$(du -sh "$backup" 2>/dev/null | cut -f1)
                echo "$i. $(basename "$backup") ($size)"
                i=$((i+1))
            done
            
            read -r -p "Выберите номер бэкапа (0 для отмены): " choice
            
            if [ "$choice" -eq 0 ] 2>/dev/null; then
                log "YELLOW" "⚠️ Отменено"
                return 0
            fi
            
            if [ "$choice" -ge 1 ] 2>/dev/null && [ "$choice" -le "${#backups[@]}" ]; then
                local backup_dir="${backups[$((choice-1))]}"
                
                log "RED" "⚠️ ВНИМАНИЕ! Текущие файлы будут заменены!"
                read -r -p "Продолжить? [y/N] " confirm
                
                if [[ "$confirm" =~ ^([yY])$ ]]; then
                    # Восстановление .env
                    if [ -f "$backup_dir/.env" ]; then
                        cp "$backup_dir/.env" "$ENV_FILE"
                        log "GREEN" "  ✅ .env восстановлен"
                    fi
                    
                    # Восстановление texts.yml
                    if [ -f "$backup_dir/texts.yml" ]; then
                        cp "$backup_dir/texts.yml" "$TEXTS_FILE"
                        log "GREEN" "  ✅ texts.yml восстановлен"
                    fi
                    
                    # Восстановление static
                    if [ -d "$backup_dir/static" ]; then
                        mkdir -p "static"
                        cp -r "$backup_dir/static/"* "static/" 2>/dev/null || true
                        log "GREEN" "  ✅ static/ восстановлен"
                    fi
                    
                    # Восстановление uploads
                    if [ -d "$backup_dir/uploads" ]; then
                        cp -rn "$backup_dir/uploads/"* "uploads/" 2>/dev/null || true
                        log "GREEN" "  ✅ uploads/ восстановлен"
                    fi
                    
                    log "GREEN" "✅ Конфигурация восстановлена из бэкапа"
                    log "YELLOW" "⚠️ Для восстановления БД используйте пункт '9. Восстановить БД из бэкапа'"
                fi
            else
                log "RED" "❌ Неверный выбор"
            fi
            ;;
            
        4)
            log "BLUE" "🗑️ Удаление старых бэкапов (старше 30 дней)..."
            
            # Подсчитываем количество старых бэкапов
            local old_backups=$(find "$BACKUPS_DIR" -type d -name "backup_*" -mtime +30 2>/dev/null | wc -l)
            local old_db_backups=$(find "$BACKUPS_DIR" -type f -name "db_backup_*.sql" -mtime +30 2>/dev/null | wc -l)
            
            if [ "$old_backups" -eq 0 ] && [ "$old_db_backups" -eq 0 ]; then
                log "GREEN" "✅ Старых бэкапов не найдено"
                return 0
            fi
            
            log "YELLOW" "⚠️ Будет удалено:"
            [ "$old_backups" -gt 0 ] && echo "  - Бэкапов конфигурации: $old_backups"
            [ "$old_db_backups" -gt 0 ] && echo "  - Бэкапов БД: $old_db_backups"
            
            read -r -p "Продолжить? [y/N] " confirm
            
            if [[ "$confirm" =~ ^([yY])$ ]]; then
                find "$BACKUPS_DIR" -type d -name "backup_*" -mtime +30 -exec rm -rf {} + 2>/dev/null || true
                find "$BACKUPS_DIR" -type f -name "db_backup_*.sql" -mtime +30 -delete 2>/dev/null || true
                log "GREEN" "✅ Старые бэкапы удалены"
            fi
            ;;
            
        5)
            log "BLUE" "🗑️ Удаление конкретного бэкапа..."
            
            local all_backups=($(ls -dt "$BACKUPS_DIR"/* 2>/dev/null))
            
            if [ ${#all_backups[@]} -eq 0 ]; then
                log "RED" "❌ Бэкапы не найдены"
                return 1
            fi
            
            log "CYAN" "\n📋 Доступные бэкапы:"
            local i=1
            for backup in "${all_backups[@]}"; do
                local size=$(du -sh "$backup" 2>/dev/null | cut -f1)
                echo "$i. $(basename "$backup") ($size)"
                i=$((i+1))
            done
            
            read -r -p "Выберите номер бэкапа для удаления (0 для отмены): " choice
            
            if [ "$choice" -eq 0 ] 2>/dev/null; then
                log "YELLOW" "⚠️ Отменено"
                return 0
            fi
            
            if [ "$choice" -ge 1 ] 2>/dev/null && [ "$choice" -le "${#all_backups[@]}" ]; then
                local backup_to_delete="${all_backups[$((choice-1))]}"
                
                log "RED" "⚠️ Будет удален: $(basename "$backup_to_delete")"
                read -r -p "Подтвердите удаление [y/N]: " confirm
                
                if [[ "$confirm" =~ ^([yY])$ ]]; then
                    rm -rf "$backup_to_delete"
                    log "GREEN" "✅ Бэкап удален"
                fi
            else
                log "RED" "❌ Неверный выбор"
            fi
            ;;
            
        0)
            return 0
            ;;
            
        *)
            log "RED" "❌ Неверный выбор"
            ;;
    esac
}

# Основное меню
main_menu() {
    while true; do
        echo ""
        log "YELLOW" "╔════════════════════════════════════════╗"
        log "YELLOW" "║   🛒 Telegram Shop Bot Manager       ║"
        log "YELLOW" "╚════════════════════════════════════════╝"
        echo ""
        log "GREEN" "📝 Конфигурация:"
        echo "  1. Создать/редактировать .env"
        echo "  2. Редактировать texts.yml"
        echo ""
        log "GREEN" "🐳 Управление контейнерами:"
        echo "  3. Запустить контейнеры"
        echo "  4. Остановить контейнеры"
        echo "  5. Перезапустить контейнеры"
        echo "  6. Пересобрать контейнеры"
        echo ""
        log "GREEN" "🗄️ База данных:"
        echo "  7. Инициализация/миграции БД"
        echo "  8. Создать бэкап БД"
        echo "  9. Восстановить БД из бэкапа"
        echo "  10. 💣 Полный сброс БД (удалит все данные!)"
        echo ""
        log "GREEN" "💾 Управление бэкапами:"
        echo "  11. Управление бэкапами (просмотр/создание/восстановление)"
        echo ""
        log "GREEN" "📊 Логи и мониторинг:"
        echo "  12. Показать все логи"
        echo "  13. Показать логи API"
        echo "  14. Показать логи PostgreSQL"
        echo "  15. Показать только ошибки"
        echo "  16. Отслеживать логи (follow)"
        echo "  17. Проверить статус системы"
        echo ""
        log "GREEN" "🔧 Обслуживание:"
        echo "  18. Обновить из репозитория"
        echo "  19. Очистка (логи, старые бэкапы, Docker)"
        echo ""
        log "GREEN" "0. 🚪 Выйти"
        echo ""

        read -r -p "Выберите действие (0-19): " choice

        case "$choice" in
            1) manage_env_file ;;
            2) manage_texts_file ;;
            3) manage_containers "start" ;;
            4) manage_containers "stop" ;;
            5) manage_containers "restart" ;;
            6) manage_containers "rebuild" ;;
            7) init_database ;;
            8) backup_database ;;
            9) restore_database ;;
            10) reset_database ;;
            11) manage_backups ;;
            12) view_logs "all" ;;
            13) view_logs "api" ;;
            14) view_logs "db" ;;
            15) view_logs "errors" ;;
            16) view_logs "follow" ;;
            17) check_status ;;
            18) update_repo ;;
            19) cleanup ;;
            0)
                log "BLUE" "🚪 Выход..."
                break
                ;;
            *)
                log "RED" "❌ Неверный выбор. Пожалуйста, выберите действие от 0 до 19."
                ;;
        esac
        
        echo ""
        read -r -p "Нажмите Enter для продолжения..."
    done
}

# Проверка, что скрипт запущен из правильной директории
if [ ! -f "docker-compose.yml" ]; then
    log "RED" "❌ Ошибка: docker-compose.yml не найден"
    log "YELLOW" "Запустите скрипт из корня проекта telegram-shop-bot"
    exit 1
fi

# Запускаем основное меню
main_menu