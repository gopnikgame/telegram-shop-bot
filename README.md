<div align="center">

# Telegram Shop Bot

Лёгкий магазин для Telegram: FastAPI + aiogram, платежи через YooKassa, админка на Jinja2.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/Postgres-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Возможности](#возможности) • [Быстрый старт](#быстрый-старт-docker) • [Документация](#документация) • [Скрины](#скрины)

</div>

## Возможности

- ✅ Продажа услуг и цифровых товаров
- ✅ Оффлайн заказы с доставкой (физические товары)
- ✅ Корзина покупок
- ✅ Оплата через YooKassa (карта, СБП)
- ✅ Донаты (фиксированные и произвольные)
- ✅ Админка: товары, заказы, пользователи, бэкап/восстановление
- ✅ Digital-товары: три способа доставки
    - **file** - загрузка файла и отправка покупателю
    - **github** - доступ к репозиторию
    - **codes** - выдача позиций из TXT (каждая строка — отдельный код)
- ✅ Telegram-бот: каталог, карточки, покупка в один клик
- ✅ Комплексная система управления и мониторинга

## Скрины

<p align="center">
  <img src="docs/orders.png" alt="Заказы" width="480" />
</p>
<p align="center">
  <img src="docs/admin.png" alt="Админка" width="320" />
  <img src="docs/new-item.png" alt="Новый заказ" width="320" />
</p>
<p align="center">
  <img src="docs/bot.png" alt="Бот" width="240" />
</p>

## Быстрый старт (Docker)

### 🚀 Автоматическая установка (рекомендуется)

```bash
# Загрузите и запустите установщик
curl -o launcher.sh https://raw.githubusercontent.com/gopnikgame/telegram-shop-bot/main/launcher.sh
chmod +x launcher.sh
sudo ./launcher.sh
```

Скрипт автоматически:
- ✅ Установит зависимости (git, docker, nano)
- ✅ Клонирует репозиторий в `/opt/telegram-shop-bot`
- ✅ Запустит интерактивное меню управления
- ✅ Поможет настроить `.env` и `texts.yml`

### 🛠️ Ручная установка

1) Подготовьте `.env`:

```bash
cp .env.example .env
nano .env  # отредактируйте обязательные переменные
```

**Обязательные параметры:**
- `BOT_TOKEN` - токен Telegram-бота
- `YK_SHOP_ID` - ID магазина YooKassa
- `YK_SECRET_KEY` - секретный ключ YooKassa

2) Запуск:

```bash
docker compose up --build -d
```

3) Примените миграции (один раз):

```bash
docker compose exec api alembic upgrade head
```

4) Приложение доступно:

- API: http://localhost:8000
- Health: http://localhost:8000/health/
- Admin: http://localhost:8000/admin/
- Webhook: POST http://localhost:8000/telegram/webhook

## 📚 Документация

### Система управления

После установки используйте интерактивный менеджер:

```bash
cd /opt/telegram-shop-bot
./manage_bot.sh
```

**Возможности менеджера:**
- 📝 Управление конфигурацией (.env, texts.yml)
- 🐳 Управление контейнерами
- 🗄️ Управление БД (миграции, бэкапы)
- 📊 Просмотр логов
- 🔄 Обновление из репозитория
- 🧹 Очистка и обслуживание

### Быстрые команды

```bash
./scripts/quick_start.sh    # Быстрый запуск
./scripts/quick_stop.sh     # Быстрая остановка
./scripts/logs.sh           # Просмотр логов
./scripts/backup_db.sh      # Бэкап БД
./scripts/update.sh         # Обновление
```

Подробная документация: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

## Ручной запуск (без Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Переменные окружения

### Минимальная конфигурация

```ini
# Telegram
BOT_TOKEN=your_bot_token

# YooKassa
YK_SHOP_ID=your_shop_id
YK_SECRET_KEY=your_secret_key
YK_RETURN_URL=http://localhost:8000/thanks

# Database (для Docker уже настроено)
DATABASE_URL=postgresql+asyncpg://shopbot:shopbot@localhost:5432/shopbot
```

### Дополнительно

- `YK_WEBHOOK_USER`, `YK_WEBHOOK_PASSWORD` — Basic защита вебхука YooKassa
- `BASE_URL`, `PORT` — базовый URL API и порт
- `ADMIN_USERNAME`, `ADMIN_PASSWORD` — логин/пароль админки
- `ADMIN_CHAT_ID` — куда слать уведомления
- `ADMIN_TG_USERNAME` — username для кнопки «Связаться»
- `SHOW_CONTACT_BUTTON`, `SHOW_DONATE_BUTTON` — флаги видимости кнопок
- `EMAIL_DOMAIN` — домен для генерации email по tg_id
- `UPLOAD_DIR` — каталог загрузок (мапится в Docker в volume)
- `WEBHOOK_URL`, `WEBHOOK_SECRET` — вебхук Telegram
- `DONATE_AMOUNTS` — суммы донатов, список через запятую (например: 100,200,500)

Полная документация: [.env.example](.env.example)

## Интеграция YooKassa

- **Создание заказа:** `POST /orders/` — создаёт платёж, возвращает `payment_url`
- **Вебхук:** `POST /payments/yookassa/webhook` — на `payment.succeeded`:
  - Помечает заказ как `paid`
  - Создаёт покупку
  - Выполняет доставку
  - Для `delivery_type=codes`: резервирует позицию, отправляет код жирным шрифтом

## Структура

```
telegram-shop-bot/
├── app/                    # API (роуты, модели, схемы, сервисы, админка)
├── bot/                    # Обработчики aiogram + вебхук-роут
├── alembic/                # Миграции БД
├── scripts/                # Скрипты управления
│   ├── logs.sh             # Просмотр логов
│   ├── backup_db.sh        # Бэкап БД
│   └── update.sh           # Обновление
├── uploads/                # Загруженные файлы/бэкапы (volume в Docker)
├── docs/                   # Документация
│   └── DEPLOYMENT.md       # Руководство по развертыванию
├── launcher.sh             # Автоматический установщик
├── manage_bot.sh           # Интерактивный менеджер
└── docker-compose.yml      # Docker конфигурация
```

## Админка — работа с TXT кодами

- При создании/редактировании digital‑товара выберите способ доставки `codes`
- Загрузите TXT с позициями (обязательно), по одной на строку
- В списке товаров отображается «Остаток»
- Для догрузки кодов используйте кнопку «➕TXT»

## Разработка

- Локально удобно запускать бота в polling-режиме: `python -m bot.run_bot`
- Для продакшна используйте вебхук (`WEBHOOK_URL`) и `docker compose`

## 🔧 Обслуживание

### Обновление

```bash
./scripts/update.sh
```

Или через менеджер: `./scripts/manage_bot.sh` → пункт 16

### Бэкап базы данных

```bash
./scripts/backup_db.sh
```

Бэкапы сохраняются в `/opt/telegram-shop-bot/backups/`

### Просмотр логов

```bash
./scripts/logs.sh [all|api|db|errors|follow]
```

### Проверка статуса

```bash
curl http://localhost:8000/health/
docker compose ps
```

## 🆘 Troubleshooting

См. подробное руководство: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#-troubleshooting)

**Основные проблемы:**
- Docker не запускается → `sudo systemctl start docker`
- Порт занят → измените `PORT` в `.env`
- БД не подключается → проверьте `docker compose logs db`
- Бот не отвечает → проверьте `BOT_TOKEN` в `.env`

## Лицензия

[MIT](LICENSE)

---

<div align="center">

**Репозиторий:** https://github.com/gopnikgame/telegram-shop-bot

**Upstream:** https://github.com/TrackLine/telegram-shop-bot

Made with ❤️ for Telegram Shop Bot

Documentation prepared using Claude...

</div>
