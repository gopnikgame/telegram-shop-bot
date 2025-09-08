<div align="center">

# Telegram Shop Bot

Лёгкий магазин для Telegram: FastAPI + aiogram, платежи через YooKassa, админка на Jinja2.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/Postgres-16-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

</div>

## Возможности
- Продажа услуг и цифровых товаров
- Оплата через YooKassa (карта, СБП)
- Донаты (фиксированные и произвольные)
- Админка: товары, заказы, пользователи, бэкап/восстановление
- Telegram-бот: каталог, карточки, покупка в один клик

## Быстрый старт (Docker)

1) Подготовьте `.env`:
```bash
cp .env.example .env
# отредактируйте обязательные переменные
```

2) Запуск:
```bash
docker compose up --build -d
```

3) Примените миграции (один раз):
```bash
docker compose exec api alembic upgrade head
```

4) Приложение:
- API: http://localhost:8000
- Health: http://localhost:8000/health/
- Вебхук Telegram: POST http://localhost:8000/telegram/webhook

## Ручной запуск (без Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Переменные окружения

Минимум нужно указать:
- `BOT_TOKEN` — токен Telegram-бота
- `DATABASE_URL` — подключение к БД (для Docker уже задано через compose)
- `YK_SHOP_ID`, `YK_SECRET_KEY`, `YK_RETURN_URL` — доступы YooKassa

Дополнительно:
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

## Интеграция YooKassa
- Создание заказа: `POST /orders/` — создаёт платёж, возвращает `payment_url`.
- Вебхук: `POST /payments/yookassa/webhook` — на `payment.succeeded` помечает заказ как `paid`, создаёт покупку, выполняет доставку.

## Структура
- `app/` — API (роуты, модели, схемы, сервисы, админка)
- `bot/` — обработчики aiogram + вебхук-роут
- `alembic/` — миграции БД (одна initial)
- `uploads/` — загруженные файлы/бэкапы (volume в Docker)

## Разработка
- Локально удобно запускать бота в polling-режиме: `python -m bot.run_bot`
- Для продакшна используйте вебхук (`WEBHOOK_URL`) и `docker compose`

## Лицензия
MIT
