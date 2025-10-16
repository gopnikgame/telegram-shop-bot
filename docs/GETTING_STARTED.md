# ?? Первая настройка Telegram Shop Bot

Пошаговое руководство для новых пользователей.

## Шаг 1: Подготовка

### 1.1 Создайте Telegram бота

1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям (имя и username бота)
4. **Сохраните токен** - он понадобится для `.env`
5. Настройте бота:
   ```
   /setdescription - описание бота
   /setabouttext - текст "О боте"
   /setuserpic - загрузите аватар
   ```

### 1.2 Зарегистрируйтесь в YooKassa

1. Перейдите на [yookassa.ru](https://yookassa.ru)
2. Зарегистрируйтесь и создайте магазин
3. В разделе "Интеграция" получите:
   - **shopId** (ID магазина)
   - **Секретный ключ**
4. Настройте способы оплаты (карты, СБП)

### 1.3 Узнайте свой Telegram ID

1. Найдите [@userinfobot](https://t.me/userinfobot)
2. Отправьте `/start`
3. **Сохраните ваш ID** - он понадобится для `ADMIN_CHAT_ID`

## Шаг 2: Установка

### 2.1 Автоматическая установка (рекомендуется)

```bash
# Загрузите установщик
curl -o launcher.sh https://raw.githubusercontent.com/gopnikgame/telegram-shop-bot/main/launcher.sh

# Сделайте его исполняемым
chmod +x launcher.sh

# Запустите (нужны права sudo для установки Docker)
sudo ./launcher.sh
```

Установщик автоматически:
- ? Установит зависимости (git, docker, nano)
- ? Клонирует репозиторий в `/opt/telegram-shop-bot`
- ? Запустит интерактивное меню

### 2.2 Ручная установка

```bash
# Установите зависимости
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin nano

# Клонируйте репозиторий
git clone https://github.com/gopnikgame/telegram-shop-bot.git
cd telegram-shop-bot

# Сделайте скрипты исполняемыми
chmod +x scripts/*.sh
chmod +x launcher.sh

# Запустите менеджер
./scripts/manage_bot.sh
```

## Шаг 3: Настройка конфигурации

### 3.1 Настройте .env

В интерактивном меню:
- Выберите **пункт 1: Создать/редактировать .env**

Или вручную:
```bash
cp .env.example .env
nano .env
```

**Обязательно заполните:**

```ini
# 1. TELEGRAM BOT (из шага 1.1)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# 2. YOOKASSA (из шага 1.2)
YK_SHOP_ID=123456
YK_SECRET_KEY=live_abc123xyz456
YK_RETURN_URL=http://localhost:8000/thanks

# 3. DATABASE (для Docker оставьте как есть)
DATABASE_URL=postgresql+asyncpg://shopbot:shopbot@db:5432/shopbot

# 4. ADMIN (из шага 1.3)
ADMIN_CHAT_ID=123456789
ADMIN_TG_USERNAME=@your_username
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ВашСложныйПароль123!

# 5. SERVER (для локального тестирования оставьте как есть)
SERVER_IP=127.0.0.1
BASE_URL=http://localhost:8000
PORT=8000
```

**Опционально (можно настроить позже):**

```ini
# Webhook для продакшена
WEBHOOK_URL=https://your-domain.com/telegram/webhook
WEBHOOK_SECRET=your_webhook_secret

# Донаты
DONATE_AMOUNTS=100,200,500,1000

# Кнопки в боте
SHOW_CONTACT_BUTTON=true
CONTACT_ADMIN=@your_username
SHOW_DONATE_BUTTON=true
```

### 3.2 Настройте texts.yml (опционально)

В интерактивном меню:
- Выберите **пункт 2: Редактировать texts.yml**

Или вручную:
```bash
nano app/texts.yml
```

Измените тексты под ваш проект:

```yaml
main_menu:
  title: "?? Онлайн магазин ВАШЕ_НАЗВАНИЕ"
  buttons:
    projects: "?? Наши проекты"
    services: "????? Наши услуги"
    # ...
```

## Шаг 4: Запуск

### 4.1 Запустите контейнеры

В интерактивном меню:
- Выберите **пункт 3: Запустить контейнеры**

Или вручную:
```bash
./scripts/quick_start.sh
```

Подождите 10-15 секунд, пока запустятся сервисы.

### 4.2 Примените миграции БД

В интерактивном меню:
- Выберите **пункт 7: Инициализация/миграции БД**

Или вручную:
```bash
docker exec shopbot-api alembic upgrade head
```

### 4.3 Проверьте статус

```bash
# Через менеджер
./scripts/manage_bot.sh
# Выберите пункт 15: Проверить статус системы

# Или вручную
curl http://localhost:8000/health/
```

**Ожидаемый ответ:**
```json
{"status": "ok", "database": "connected"}
```

## Шаг 5: Первое использование

### 5.1 Откройте админку

1. Откройте в браузере: http://localhost:8000/admin/
2. Войдите с учетными данными из `.env`:
   - Логин: `ADMIN_USERNAME`
   - Пароль: `ADMIN_PASSWORD`

### 5.2 Добавьте первый товар

1. В админке перейдите в "Items" ? "Create New Item"
2. Заполните форму:
   - **Title:** Название товара
   - **Description:** Описание
   - **Price:** Цена в рублях
   - **Type:** Выберите тип:
     - `service` - услуга (доставка через сообщение)
     - `digital` - цифровой товар (файл/GitHub/коды)
     - `offline` - физический товар (с доставкой)
   - **Is Active:** ? (чтобы товар был виден)

3. Для **digital товаров** выберите способ доставки:
   - **file** - загрузите файл
   - **github** - укажите URL репозитория и токен доступа
   - **codes** - загрузите TXT файл с кодами (по одному на строку)

4. Нажмите **Create**

### 5.3 Протестируйте бота

1. Найдите своего бота в Telegram (username из шага 1.1)
2. Отправьте `/start`
3. Должно появиться главное меню
4. Перейдите в раздел с товарами
5. Попробуйте добавить товар в корзину
6. Оформите тестовый заказ

## Шаг 6: Настройка автозапуска (опционально)

### 6.1 Systemd service

Для автозапуска при перезагрузке сервера:

```bash
sudo ./scripts/install_service.sh
```

Теперь бот будет автоматически запускаться при старте системы.

**Управление сервисом:**
```bash
sudo systemctl start telegram-shop-bot     # Запустить
sudo systemctl stop telegram-shop-bot      # Остановить
sudo systemctl restart telegram-shop-bot   # Перезапустить
sudo systemctl status telegram-shop-bot    # Статус
```

### 6.2 Автоматические бэкапы

Настройте регулярные бэкапы БД:

```bash
sudo ./scripts/setup_cron.sh
```

Выберите частоту (рекомендуется: ежедневно в 02:00).

## Шаг 7: Настройка для продакшена (опционально)

### 7.1 Настройте домен

1. Купите домен
2. Настройте A-запись на IP вашего сервера
3. Установите nginx:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx
   ```

4. Создайте конфиг nginx:
   ```nginx
   # /etc/nginx/sites-available/shopbot
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

5. Включите конфиг:
   ```bash
   sudo ln -s /etc/nginx/sites-available/shopbot /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

6. Получите SSL сертификат:
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

### 7.2 Настройте webhook

В `.env` измените:
```ini
BASE_URL=https://your-domain.com
WEBHOOK_URL=https://your-domain.com/telegram/webhook
WEBHOOK_SECRET=сгенерируйте_случайную_строку
```

Перезапустите:
```bash
./scripts/manage_bot.sh
# Выберите пункт 5: Перезапустить контейнеры
```

### 7.3 Настройте YooKassa webhook

1. Войдите в панель YooKassa
2. Перейдите в "Интеграция" ? "HTTP-уведомления"
3. Добавьте URL: `https://your-domain.com/payments/yookassa/webhook`
4. Включите уведомления для события `payment.succeeded`

## Шаг 8: Мониторинг

### 8.1 Просмотр логов

```bash
# В реальном времени
./scripts/logs.sh follow

# Только ошибки
./scripts/logs.sh errors

# Все логи API
./scripts/logs.sh api
```

### 8.2 Проверка статуса

```bash
./scripts/check_requirements.sh
```

### 8.3 Статус сервисов

```bash
curl http://localhost:8000/health/
docker compose ps
```

## Частые вопросы

### Бот не отвечает

1. Проверьте токен:
   ```bash
   grep BOT_TOKEN .env
   ```

2. Проверьте логи:
   ```bash
   ./scripts/logs.sh api
   ```

3. Перезапустите:
   ```bash
   ./scripts/manage_bot.sh
   # Пункт 5: Перезапустить контейнеры
   ```

### Платежи не работают

1. Проверьте настройки YooKassa:
   ```bash
   grep YK_ .env
   ```

2. Убедитесь, что магазин активирован в YooKassa
3. Проверьте способы оплаты (должны быть включены)
4. Для продакшена настройте webhook (см. шаг 7.3)

### Админка не открывается

1. Проверьте, что контейнеры запущены:
   ```bash
   docker compose ps
   ```

2. Проверьте учетные данные в `.env`:
   ```bash
   grep ADMIN_USERNAME .env
   grep ADMIN_PASSWORD .env
   ```

3. Попробуйте другой порт в `.env`:
   ```ini
   PORT=8001
   ```

### Миграции не применяются

1. Проверьте БД:
   ```bash
   docker compose logs db
   ```

2. Примените миграции заново:
   ```bash
   docker exec shopbot-api alembic upgrade head
   ```

3. Если не помогло, пересоздайте БД (?? удалит данные):
   ```bash
   docker compose down -v
   docker compose up -d
   docker exec shopbot-api alembic upgrade head
   ```

## Следующие шаги

1. ?? Изучите [полную документацию](docs/DEPLOYMENT.md)
2. ?? Настройте тексты и изображения в `texts.yml`
3. ??? Добавьте больше товаров через админку
4. ?? Настройте SSL и webhook для продакшена
5. ?? Настройте мониторинг и автобэкапы
6. ?? Запустите рекламу бота!

## Поддержка

Нужна помощь?

- ?? [Документация](docs/DEPLOYMENT.md)
- ?? [GitHub Issues](https://github.com/gopnikgame/telegram-shop-bot/issues)
- ?? [Шпаргалка](CHEATSHEET.md)

---

**Удачного запуска! ??**
