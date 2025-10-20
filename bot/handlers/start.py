"""
Обработчики команды /start и быстрых команд
"""
import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from sqlalchemy import select, func

from app.utils.texts import load_texts
from bot.keyboards import main_menu_kb, donate_amounts_kb
from app.db.session import AsyncSessionLocal
from app.models import Item, ItemType, User, Purchase, CartItem
from app.config import settings

logger = logging.getLogger("shopbot")
router = Router()


def _is_admin_user(tg_id: int | None, username: str | None) -> bool:
    """Проверка является ли пользователь администратором"""
    try:
        if settings.admin_chat_id and tg_id is not None:
            if str(tg_id) == str(settings.admin_chat_id):
                return True
    except Exception:
        pass
    if settings.admin_tg_username and username:
        return username.lstrip('@').lower() == settings.admin_tg_username.lstrip('@').lower()
    return False


@router.message(F.text == "/start")
async def start_handler(message: Message) -> None:
    """Обработчик команды /start"""
    texts = load_texts()

    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
        if not u:
            u = User(tg_id=message.from_user.id, username=message.from_user.username or None)
            db.add(u)
            await db.flush()
            total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
            if settings.admin_chat_id:
                try:
                    username = f"@{message.from_user.username}" if message.from_user.username else "—"
                    text = (
                        "? Новый пользователь "
                        f"{message.from_user.full_name}\n"
                        f"Username: {username}\n"
                        f"ID: {message.from_user.id}\n"
                        f"Всего: {total}"
                    )
                    await message.bot.send_message(int(settings.admin_chat_id), text)
                except Exception:
                    pass
        else:
            if (message.from_user.username or None) != u.username:
                u.username = message.from_user.username or None
        await db.commit()
        
        cart_count = (await db.execute(
            select(func.count()).select_from(CartItem).where(CartItem.user_id == u.id)
        )).scalar_one()

    # Отправляем главное меню с картинкой если есть
    try:
        if "image" in texts["main_menu"]:
            photo = FSInputFile(texts["main_menu"]["image"])
            await message.answer_photo(
                photo=photo,
                caption=texts["main_menu"]["title"],
                parse_mode="Markdown",
                reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(message.from_user.id, message.from_user.username), cart_count=cart_count)
            )
        else:
            await message.answer(
                texts["main_menu"]["title"], 
                parse_mode="Markdown", 
                reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(message.from_user.id, message.from_user.username), cart_count=cart_count)
            )
    except FileNotFoundError:
        await message.answer(
            texts["main_menu"]["title"], 
            reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(message.from_user.id, message.from_user.username), cart_count=cart_count)
        )


@router.message(F.text.startswith("/"))
async def quick_menu_commands(message: Message) -> None:
    """Обработчик быстрых команд меню"""
    from .items import list_items  # Локальный импорт для избежания циклических зависимостей
    
    cmd = (message.text or "").strip().lstrip("/").lower()
    
    if cmd == "projects":
        await list_items(message, ItemType.DIGITAL, section="projects", page=1)
        return
    
    if cmd in ("products", "shop", "товары"):
        await list_items(message, ItemType.OFFLINE, section="products", page=1)
        return
    
    if cmd == "services":
        await list_items(message, ItemType.SERVICE, section="services", page=1)
        return
    
    if cmd in ("buylist", "purchased", "my"):
        texts = load_texts()
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
            if not user:
                await message.answer(texts.get("empty", {}).get("purchased", "У вас нет купленных проектов."))
                return
            
            purchases = (await db.execute(select(Purchase).where(Purchase.user_id == user.id))).scalars().all()
            if not purchases:
                await message.answer(texts.get("empty", {}).get("purchased", "У вас нет купленных проектов."))
                return
            
            item_ids = [p.item_id for p in purchases if p.item_id is not None]
            items = (await db.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
        
        kb = []
        for it in items:
            kb.append([InlineKeyboardButton(text=it.title, callback_data=f"item:{it.id}:{it.item_type.value}")])
        kb.append([InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="back:main")])
        
        title = texts["main_menu"].get("purchased_title", "Ваши купленные проекты:")
        image_path = texts["main_menu"].get("images", {}).get("purchased")
        
        if image_path and Path(image_path).is_file():
            photo = FSInputFile(image_path)
            await message.answer_photo(photo=photo, caption=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        else:
            await message.answer(text=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        return
    
    if cmd in ("donat", "donate"):
        texts = load_texts()
        donate_image = texts.get("donate", {}).get("image")
        image_exists = bool(donate_image and Path(donate_image).is_file())
        
        if image_exists:
            photo = FSInputFile(donate_image)
            await message.answer_photo(photo=photo, caption="Выберите сумму доната:", reply_markup=donate_amounts_kb())
        else:
            await message.answer(text="Выберите сумму доната:", reply_markup=donate_amounts_kb())
        return
