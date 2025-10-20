from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.config import settings
from app.routers import health, orders, payments, admin
from bot.webhook_app import api_router as telegram_router, setup_webhook, delete_webhook
from app.utils.texts import load_texts

def create_app() -> FastAPI:
    app = FastAPI(title="Shop Bot API")
    # Routers
    from app.routers.health import router as health_router  # local import to avoid circular deps
    from app.routers.payments import router as payments_router
    from app.routers.orders import router as orders_router
    from app.routers.admin import router as admin_router
    from bot.webhook_app import api_router as tg_router, setup_webhook, delete_webhook

    app.include_router(health_router)
    app.include_router(payments_router)
    app.include_router(orders_router)
    app.include_router(admin_router)
    app.include_router(tg_router)

    # Static uploads
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

    # Redirect root to admin
    @app.get("/")
    async def root():
        return RedirectResponse(url="/admin/")

    @app.on_event("startup")
    async def _on_startup() -> None:
        # Initialize database tables
        try:
            from app.db.init_db import init_db
            await init_db()
            logger.bind(event="db_init").info("Database initialization completed")
        except Exception as e:
            logger.bind(event="db_init_error", error=str(e)).error("Ошибка инициализации базы данных")
            # Не прерываем запуск приложения, но логируем ошибку
        
        await setup_webhook()
        logger.bind(event="webhook_setup").info("Webhook configured", url=settings.webhook_url)

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        await delete_webhook()
        logger.bind(event="webhook_delete").info("Webhook removed")

    return app


app = create_app()


@logger.catch
def _startup_log() -> None:
    logger.bind(event="startup").info("FastAPI started", base_url=settings.base_url)

# Добавляем endpoint для возврата после оплаты
@app.get("/thanks")
async def payment_thanks(request: Request):
    """Страница благодарности после оплаты"""
    texts = load_texts()
    thanks_config = texts.get("thanks_page", {})
    
    # Получаем настройки из texts.yml или используем дефолты
    title = thanks_config.get("title", "Спасибо за покупку!")
    success_icon = thanks_config.get("success_icon", "✅")
    message = thanks_config.get("message", "Ваш платёж успешно обработан. Товар будет доставлен в Telegram-бот в течение нескольких минут.")
    additional_message = thanks_config.get("additional_message", "Если у вас возникли вопросы, свяжитесь с нами в боте.")
    button_text = thanks_config.get("button_text", "Вернуться в бот")
    
    # Цвета
    colors = thanks_config.get("colors", {})
    gradient_start = colors.get("gradient_start", "#667eea")
    gradient_end = colors.get("gradient_end", "#764ba2")
    button_bg = colors.get("button_background", "#667eea")
    
    # Формируем ссылку на бота
    bot_username = settings.bot_username or "your_bot"
    bot_link = f"https://t.me/{bot_username.lstrip('@')}"
    
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, {gradient_start} 0%, {gradient_end} 100%);
            }}
            .container {{
                text-align: center;
                background: white;
                padding: 3rem;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 500px;
                margin: 20px;
            }}
            .success-icon {{
                font-size: 4rem;
                margin-bottom: 1rem;
            }}
            h1 {{
                color: #333;
                margin-bottom: 1rem;
                font-size: 1.8rem;
            }}
            p {{
                color: #666;
                line-height: 1.6;
                margin-bottom: 1.5rem;
                font-size: 1rem;
            }}
            .btn {{
                display: inline-block;
                background: {button_bg};
                color: white;
                padding: 1rem 2rem;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 500;
                transition: transform 0.2s, box-shadow 0.2s;
                font-size: 1rem;
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
            }}
            @media (max-width: 600px) {{
                .container {{
                    padding: 2rem 1.5rem;
                }}
                h1 {{
                    font-size: 1.5rem;
                }}
                p {{
                    font-size: 0.9rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">{success_icon}</div>
            <h1>{title}</h1>
            <p>{message}</p>
            <p>{additional_message}</p>
            <a href="{bot_link}" class="btn">{button_text}</a>
        </div>
    </body>
    </html>
    """)

# Run with: uvicorn app.main:app --reload
