# ??? Система управления Telegram Shop Bot

Комплексная система для развертывания, настройки и управления telegram-shop-bot.

## ?? Содержание

- [Быстрый старт](#быстрый-старт)
- [Установка](#установка)
- [Скрипты управления](#скрипты-управления)
- [Конфигурация](#конфигурация)
- [База данных](#база-данных)
- [Обслуживание](#обслуживание)

---

## ?? Быстрый старт

### Автоматическая установка

```bash
# Загрузите и запустите установщик
curl -o launcher.sh https://raw.githubusercontent.com/gopnikgame/telegram-shop-bot/main/launcher.sh
chmod +x launcher.sh
sudo ./launcher.sh
```

Скрипт автоматически:
- Установит зависимости (git, docker, nano)
- Клонирует репозиторий в `/opt/telegram-shop-bot`
- Запустит интерактивное меню управления

### Ручная установка

```bash
# Клонирование репозитория
git clone https://github.com/gopnikgame/telegram-shop-bot.git
cd telegram-shop-bot

# Настройка конфигурации
cp .env.example .env
nano .env  # Заполните обязательные параметры

# Запуск контейнеров
docker-compose up -d

# Применение миграций
docker exec shopbot-api alembic upgrade head
```

---

## ?? Установка

### Требования

- **ОС:** Linux (Ubuntu 20.04+, Debian 10+, CentOS 7+)
- **Docker:** 20.10+
- **Docker Compose:** 2.0+ или docker-compose 1.29+
- **Git:** 2.0+
- **RAM:** минимум 1GB
- **Disk:** минимум 5GB свободного места

### Зависимости

Автоматически устанавливаются скриптом `launcher.sh`:
- git
- docker / docker.io
- docker-compose-plugin / docker-compose
- nano (или vim)

---

## ?? Скрипты управления

### Основной менеджер

```bash
# Запуск интерактивного меню
./scripts/manage_bot.sh
```

**Возможности:**
1. ? Управление конфигурацией (.env, texts.yml)
2. ? Управление контейнерами (запуск, остановка, перезапуск, пересборка)
3. ? Управление БД (миграции, бэкапы, восстановление)
4. ? Просмотр логов (все, API, PostgreSQL, ошибки)
5. ? Обновление из репозитория
6. ? Очистка (логи, бэкапы, Docker)
7. ? Мониторинг статуса системы

### Быстрые команды

```bash
# Быстрый запуск
./scripts/quick_start.sh

# Быстрая остановка
./scripts/quick_stop.sh

# Просмотр логов
./scripts/logs.sh              # Все логи
./scripts/logs.sh api          # Только API
./scripts/logs.sh db           # Только PostgreSQL
./scripts/logs.sh errors       # Только ошибки
./scripts/logs.sh follow       # Отслеживание в реальном времени

# Бэкап базы данных
./scripts/backup_db.sh

# Обновление из репозитория
./scripts/update.sh
```

### Добавление прав на выполнение

```bash
chmod +x scripts/*.sh
chmod +x launcher.sh
```

---

## ?? Конфигурация

### Файл .env

**Обязательные параметры:**

```ini
# Telegram Bot
BOT_TOKEN=your_bot_token_here

# YooKassa (для приема платежей)
YK_SHOP_ID=your_shop_id
YK_SECRET_KEY=your_secret_key
YK_RETURN_URL=http://localhost:8000/thanks
```

**Опциональные параметры:**

```ini
# База данных (для Docker используется значение по умолчанию)
DATABASE_URL=postgresql+asyncpg://shopbot:shopbot@localhost:5432/shopbot

# Сервер
SERVER_IP=127.0.0.1
BASE_URL=http://localhost:8000
PORT=8000

# Администратор
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password
ADMIN_CHAT_ID=123456789
ADMIN_TG_USERNAME=@your_username

# Webhook (для продакшена)
WEBHOOK_URL=https://your-domain.com/telegram/webhook
WEBHOOK_SECRET=your_webhook_secret

# Донаты
DONATE_AMOUNTS=100,200,500,1000
```

### Редактирование конфигурации

```bash
# Через менеджер (рекомендуется)
./scripts/manage_bot.sh
# Выберите пункт 1: "Создать/редактировать .env"

# Напрямую
nano .env
```

### Файл texts.yml

Содержит все тексты бота (кнопки, меню, уведомления).

**Редактирование:**

```bash
# Через менеджер
./scripts/manage_bot.sh
# Выберите пункт 2: "Редактировать texts.yml"

# Напрямую
nano app/texts.yml
```

**Основные секции:**
- `buttons` - тексты кнопок
- `main_menu` - главное меню и секции
- `payment` - настройки оплаты
- `notifications` - уведомления администратору
- `delivery` - сообщения о доставке
- `offline_delivery` - промпты для оффлайн заказов

---

## ??? База данных

### Инициализация

При первом запуске миграции применяются автоматически в `docker-entrypoint.sh`.

**Ручное применение:**

```bash
# Через менеджер
./scripts/manage_bot.sh
# Выберите пункт 7: "Инициализация/миграции БД"

# Напрямую
docker exec shopbot-api alembic upgrade head
```

### Миграции

**Текущая версия:**

```bash
docker exec shopbot-api alembic current
```

**История миграций:**

```bash
docker exec shopbot-api alembic history
```

**Откат на предыдущую версию:**

```bash
docker exec shopbot-api alembic downgrade -1
```

### Бэкапы

**Создание бэкапа:**

```bash
# Через скрипт (рекомендуется)
./scripts/backup_db.sh

# Через менеджер
./scripts/manage_bot.sh
# Выберите пункт 8: "Создать бэкап БД"

# Напрямую
docker exec shopbot-postgres pg_dump -U shopbot shopbot > backup.sql
```

**Восстановление из бэкапа:**

```bash
# Через менеджер (рекомендуется)
./scripts/manage_bot.sh
# Выберите пункт 9: "Восстановить БД из бэкапа"

# Напрямую
docker exec -i shopbot-postgres psql -U shopbot shopbot < backup.sql
```

**Автоматические бэкапы:**

Бэкапы сохраняются в `/opt/telegram-shop-bot/backups/` при:
- Обновлении из репозитория
- Ручном создании через менеджер

---

## ?? Обслуживание

### Обновление из репозитория

```bash
# Через скрипт (рекомендуется)
./scripts/update.sh

# Через менеджер
./scripts/manage_bot.sh
# Выберите пункт 16: "Обновить из репозитория"
```

**Что происходит при обновлении:**
1. ? Создается бэкап конфигурации (.env, texts.yml)
2. ? Сохраняются локальные изменения (git stash)
3. ? Показываются новые изменения
4. ? Применяются обновления
5. ? Восстанавливаются локальные изменения
6. ? Предлагается пересборка контейнеров

### Просмотр логов

```bash
# Все логи
docker-compose logs --tail=100

# Только API
docker-compose logs api --tail=100

# Только PostgreSQL
docker-compose logs db --tail=100

# Отслеживание в реальном времени
docker-compose logs -f

# Через скрипт
./scripts/logs.sh [all|api|db|errors|follow]
```

### Очистка

```bash
# Через менеджер (рекомендуется)
./scripts/manage_bot.sh
# Выберите пункт 17: "Очистка"
```

**Опции очистки:**
1. Старые логи (>30 дней)
2. Старые бэкапы (>30 дней)
3. Docker volumes (?? удалит БД!)
4. Docker images и build cache
5. Всё вышеперечисленное (кроме volumes)

### Проверка статуса

```bash
# Через менеджер
./scripts/manage_bot.sh
# Выберите пункт 15: "Проверить статус системы"

# Напрямую
docker-compose ps
curl http://localhost:8000/health/
```

### Перезапуск сервисов

```bash
# Все контейнеры
docker-compose restart

# Только API
docker-compose restart api

# Только PostgreSQL
docker-compose restart db
```

### Пересборка контейнеров

```bash
# Через менеджер
./scripts/manage_bot.sh
# Выберите пункт 6: "Пересобрать контейнеры"

# Напрямую
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## ?? Мониторинг

### Endpoints для проверки

- **Health Check:** http://localhost:8000/health/
- **API Docs:** http://localhost:8000/docs
- **Admin Panel:** http://localhost:8000/admin/

### Логи контейнеров

Логи сохраняются в `/opt/telegram-shop-bot/logs/`:
- `bot.log` - общие логи бота
- `error.log` - только ошибки
- `docker.log` - логи Docker

### Метрики контейнеров

```bash
# Использование ресурсов
docker stats shopbot-api shopbot-postgres

# Размер контейнеров
docker ps -s
```

---

## ?? Безопасность

### Рекомендации

1. **Используйте сложные пароли** для:
   - `ADMIN_PASSWORD`
   - `YK_SECRET_KEY`
   - `WEBHOOK_SECRET`

2. **Ограничьте доступ к файлам:**
   ```bash
   chmod 600 .env
   ```

3. **Используйте HTTPS** в продакшене:
   - Настройте reverse proxy (nginx/traefik)
   - Получите SSL сертификат (Let's Encrypt)

4. **Регулярные бэкапы:**
   ```bash
   # Настройте cron для автоматических бэкапов
   0 2 * * * /opt/telegram-shop-bot/scripts/backup_db.sh
   ```

5. **Обновления:**
   - Регулярно обновляйте из репозитория
   - Следите за обновлениями безопасности Docker

---

## ?? Troubleshooting

### Проблемы с запуском

**Ошибка: "Cannot connect to Docker daemon"**
```bash
# Проверьте статус Docker
sudo systemctl status docker

# Запустите Docker
sudo systemctl start docker

# Добавьте пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker
```

**Ошибка: "Port 8000 already in use"**
```bash
# Найдите процесс, использующий порт
sudo lsof -i :8000

# Измените порт в .env
PORT=8001
```

### Проблемы с БД

**Ошибка: "Database connection failed"**
```bash
# Проверьте статус PostgreSQL
docker-compose logs db

# Проверьте подключение
docker exec shopbot-postgres pg_isready -U shopbot

# Пересоздайте контейнер БД
docker-compose down
docker volume rm telegram-shop-bot_db_data
docker-compose up -d
```

**Ошибка миграций:**
```bash
# Откатите миграции и примените заново
docker exec shopbot-api alembic downgrade base
docker exec shopbot-api alembic upgrade head
```

### Проблемы с ботом

**Бот не отвечает:**
```bash
# Проверьте токен
grep BOT_TOKEN .env

# Проверьте логи
./scripts/logs.sh api

# Перезапустите контейнер
docker-compose restart api
```

**Ошибки платежей:**
```bash
# Проверьте настройки YooKassa
grep YK_ .env

# Проверьте webhook
curl -X POST http://localhost:8000/payments/yookassa/webhook \
  -H "Content-Type: application/json" \
  -d '{"event":"test"}'
```

---

## ?? Поддержка

- **GitHub Issues:** https://github.com/gopnikgame/telegram-shop-bot/issues
- **Документация:** https://github.com/gopnikgame/telegram-shop-bot
- **Upstream:** https://github.com/TrackLine/telegram-shop-bot

---

## ?? Changelog

### v1.0.0 (2025-01-13)
- ? Полная система управления
- ? Интерактивный менеджер
- ? Быстрые команды
- ? Автоматические бэкапы
- ? Поддержка оффлайн заказов
- ? Система корзины

---

**Made with ?? for Telegram Shop Bot**
