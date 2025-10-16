# ?? Миграция и обновление

## Миграция со старой версии

### Из telegram-publisher-bot

Если вы использовали telegram-publisher-bot и хотите мигрировать:

#### 1. Сохраните данные

```bash
# Создайте бэкап старой БД (если была)
docker exec old-container pg_dump -U user dbname > old_backup.sql

# Сохраните конфигурацию
cp old-project/.env ~/backup_env
```

#### 2. Установите telegram-shop-bot

```bash
curl -o launcher.sh https://raw.githubusercontent.com/gopnikgame/telegram-shop-bot/main/launcher.sh
chmod +x launcher.sh
sudo ./launcher.sh
```

#### 3. Настройте конфигурацию

```bash
cd /opt/telegram-shop-bot
./scripts/manage_bot.sh
# Выберите пункт 1: Создать/редактировать .env
```

**Важные изменения в .env:**

```ini
# Старые переменные (telegram-publisher-bot)
BOT_TOKEN=...
ADMIN_IDS=...
CHANNEL_ID=...

# Новые переменные (telegram-shop-bot)
BOT_TOKEN=...              # Тот же токен
ADMIN_CHAT_ID=...          # Вместо ADMIN_IDS (один ID)
YK_SHOP_ID=...             # Новое: YooKassa
YK_SECRET_KEY=...          # Новое: YooKassa
DATABASE_URL=...           # Новое: PostgreSQL вместо SQLite
```

#### 4. Миграция данных (опционально)

Если у вас была БД в старом проекте, можно перенести пользователей:

```python
# migration_script.py
import sqlite3
import psycopg2

# Подключение к старой БД
old_db = sqlite3.connect('old_bot.db')
old_cursor = old_db.cursor()

# Подключение к новой БД
new_db = psycopg2.connect(
    host='localhost',
    port=5432,
    user='shopbot',
    password='shopbot',
    database='shopbot'
)
new_cursor = new_db.cursor()

# Перенос пользователей
old_cursor.execute("SELECT tg_id, username, first_name FROM users")
users = old_cursor.fetchall()

for user in users:
    new_cursor.execute(
        "INSERT INTO users (tg_id, username, first_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        user
    )

new_db.commit()
print(f"Migrated {len(users)} users")
```

### Обновление с предыдущей версии telegram-shop-bot

#### Метод 1: Через скрипт обновления (рекомендуется)

```bash
cd /opt/telegram-shop-bot
./scripts/update.sh
```

Скрипт автоматически:
- ? Создаст бэкап конфигурации
- ? Сохранит локальные изменения
- ? Покажет новые изменения
- ? Применит обновления
- ? Восстановит конфигурацию
- ? Предложит пересборку

#### Метод 2: Ручное обновление

```bash
cd /opt/telegram-shop-bot

# 1. Бэкап
./scripts/backup_db.sh
cp .env .env.backup
cp app/texts.yml app/texts.yml.backup

# 2. Получение обновлений
git fetch origin
git log HEAD..origin/main --oneline  # Посмотреть изменения

# 3. Применение обновлений
git pull origin main

# 4. Восстановление конфигурации (если конфликты)
cp .env.backup .env
cp app/texts.yml.backup app/texts.yml

# 5. Пересборка и перезапуск
docker compose down
docker compose build
docker compose up -d

# 6. Применение миграций
docker exec shopbot-api alembic upgrade head
```

## Откат на предыдущую версию

### Откат кода

```bash
cd /opt/telegram-shop-bot

# Посмотреть историю коммитов
git log --oneline

# Откатиться на конкретный коммит
git reset --hard <commit-hash>

# Пересборка
docker compose down
docker compose build
docker compose up -d
```

### Откат БД

```bash
# 1. Остановите контейнеры
./scripts/quick_stop.sh

# 2. Восстановите БД из бэкапа
docker compose up -d db
sleep 5

# 3. Откатите миграции до нужной версии
docker exec shopbot-api alembic downgrade <revision>

# 4. Или восстановите из SQL бэкапа
./scripts/manage_bot.sh
# Выберите пункт 9: Восстановить БД из бэкапа

# 5. Запустите контейнеры
./scripts/quick_start.sh
```

## Миграция базы данных

### Применение новых миграций

```bash
# Через менеджер
./scripts/manage_bot.sh
# Выберите пункт 7: Инициализация/миграции БД

# Напрямую
docker exec shopbot-api alembic upgrade head
```

### Проверка текущей версии

```bash
docker exec shopbot-api alembic current
```

### История миграций

```bash
docker exec shopbot-api alembic history
```

### Откат миграции

```bash
# Откат на одну версию назад
docker exec shopbot-api alembic downgrade -1

# Откат до конкретной версии
docker exec shopbot-api alembic downgrade <revision>

# Откат всех миграций
docker exec shopbot-api alembic downgrade base
```

## Изменения в конфигурации

### Новые параметры в версии 1.0.0

Добавьте в `.env` если их нет:

```ini
# Оффлайн заказы (новое)
# (автоматически поддерживается)

# Корзина (новое)
# (автоматически поддерживается)

# Донаты - новый формат
DONATE_AMOUNTS=100,200,500,1000

# Webhook для продакшена (опционально)
WEBHOOK_URL=https://your-domain.com/telegram/webhook
WEBHOOK_SECRET=your_secret_here
```

### Изменения в texts.yml

Новые секции:

```yaml
# Оффлайн доставка
offline_delivery:
  prompts:
    fullname: "?? Введите ваше ФИО для доставки:"
    phone: "?? Введите номер телефона для связи:"
    address: "?? Введите адрес доставки:"
    comment: "?? Добавьте комментарий к заказу (или пропустите):"

# Корзина
buttons:
  add_to_cart: "? В корзину"
  remove_from_cart: "? Убрать из корзины"
  cart: "?? Корзина"
  checkout: "?? Оплатить ({total} ?)"
  clear_cart: "?? Очистить корзину"
```

Скопируйте их из `app/texts.yml.example` или обновленного репозитория.

## Проверка после миграции

### 1. Проверьте статус системы

```bash
./scripts/check_requirements.sh
```

### 2. Проверьте контейнеры

```bash
docker compose ps
```

Должны быть запущены:
- `shopbot-api`
- `shopbot-postgres`

### 3. Проверьте API

```bash
curl http://localhost:8000/health/
```

Ответ: `{"status": "ok", "database": "connected"}`

### 4. Проверьте БД

```bash
docker exec shopbot-api alembic current
```

Должна быть версия: `20250903_000001`

### 5. Проверьте логи

```bash
./scripts/logs.sh errors
```

Не должно быть критических ошибок.

## Частые проблемы при миграции

### Конфликты конфигурации

**Проблема:** Git не может применить обновления из-за изменений в `.env`

**Решение:**
```bash
# Сохраните изменения
git stash

# Обновитесь
git pull origin main

# Восстановите изменения
git stash pop

# Разрешите конфликты вручную
nano .env
```

### Ошибки миграций БД

**Проблема:** Миграции не применяются

**Решение:**
```bash
# 1. Проверьте текущую версию
docker exec shopbot-api alembic current

# 2. Откатитесь на base
docker exec shopbot-api alembic downgrade base

# 3. Примените заново
docker exec shopbot-api alembic upgrade head

# 4. Если не помогло - пересоздайте БД (?? удалит данные!)
docker compose down -v
docker compose up -d
```

### Несовместимость версий

**Проблема:** Старая версия Docker/Docker Compose

**Решение:**
```bash
# Обновите Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установите Docker Compose plugin
sudo apt-get install docker-compose-plugin
```

## Откат к предыдущей стабильной версии

Если обновление вызвало проблемы:

```bash
cd /opt/telegram-shop-bot

# 1. Остановите контейнеры
./scripts/quick_stop.sh

# 2. Откатитесь к последнему рабочему коммиту
git log --oneline
git reset --hard <working-commit-hash>

# 3. Восстановите БД из бэкапа
./scripts/manage_bot.sh
# Пункт 9: Восстановить БД

# 4. Пересоберите и запустите
docker compose build
./scripts/quick_start.sh
```

## Поддержка

Если возникли проблемы с миграцией:

1. Проверьте [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#-troubleshooting)
2. Создайте Issue: https://github.com/gopnikgame/telegram-shop-bot/issues
3. Приложите:
   - Версию системы (`cat VERSION.md`)
   - Логи (`./scripts/logs.sh errors`)
   - Версию Docker (`docker --version`)

---

**Успешной миграции! ??**
