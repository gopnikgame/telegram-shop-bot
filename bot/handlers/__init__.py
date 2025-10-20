"""
ќбработчики событий Telegram бота
"""
from aiogram import Router

# »мпортируем все роутеры
from .start import router as start_router
from .menu import router as menu_router
from .items import router as items_router
from .cart import router as cart_router
from .delivery import router as delivery_router
from .donate import router as donate_router
from .admin import router as admin_router

# √лавный роутер, объедин¤ющий все модули
main_router = Router()

# ѕодключаем роутеры в правильном пор¤дке (важно дл¤ приоритета обработки)
main_router.include_router(start_router)
main_router.include_router(admin_router)
main_router.include_router(menu_router)
main_router.include_router(items_router)
main_router.include_router(cart_router)
main_router.include_router(delivery_router)
main_router.include_router(donate_router)

__all__ = ['main_router']
