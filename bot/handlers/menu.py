"""
Обработчики главного меню и навигации
"""
import logging
import contextlib
from pathlib import Path

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile, InputMediaPhoto
from sqlalchemy import select, func

from app.utils.texts import load_texts
from bot.keyboards import main_menu_kb, back_kb, admin_menu_kb, donate_amounts_kb
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


@router.callback_query(F.data.startswith("menu:"))
async def main_menu_callback(call: CallbackQuery) -> None:
    """Обработчик inline-кнопок главного меню"""
    from .items import list_items  # Локальный импорт
    from .cart import show_cart
    
    texts = load_texts()
    data = call.data.split(":", 1)[1]

    # Маппинг для определения типа элементов и секции
    section_mapping = {
        "projects": (ItemType.DIGITAL, "projects"),
        "products": (ItemType.OFFLINE, "products"),
        "services": (ItemType.SERVICE, "services"),
    }

    if data in section_mapping:
        item_type, section = section_mapping[data]
        await list_items(call.message, item_type, section=section, call=call, page=1)
        await call.answer()
        return
    
    if data == "admin":
        # Доступ только администратору
        if not _is_admin_user(call.from_user.id, call.from_user.username):
            await call.answer("Недоступно", show_alert=True)
            return
        
        admin_text = load_texts().get("admin", {}).get("title", "Администрирование")
        try:
            if call.message.photo:
                await call.message.edit_caption(caption=admin_text, reply_markup=admin_menu_kb())
            else:
                await call.message.edit_text(text=admin_text, reply_markup=admin_menu_kb())
        except Exception:
            await call.message.answer(admin_text, reply_markup=admin_menu_kb())
            with contextlib.suppress(Exception):
                await call.message.delete()
        await call.answer()
        return

    if data == "cart":
        await show_cart(call)
        return

    if data == "donate":
        donate_image = load_texts().get("donate", {}).get("image")
        image_exists = bool(donate_image and Path(donate_image).is_file())
        try:
            if call.message.photo:
                # Если сообщение уже с фото - просто меняем caption
                await call.message.edit_caption(
                    caption="Выберите сумму доната:", 
                    reply_markup=donate_amounts_kb()
                )
            else:
                # Если текстовое сообщение - удаляем и создаем новое с фото
                if image_exists:
                    await call.message.delete()
                    photo = FSInputFile(donate_image)
                    await call.message.answer_photo(
                        photo=photo, 
                        caption="Выберите сумму доната:", 
                        reply_markup=donate_amounts_kb()
                    )
                else:
                    await call.message.edit_text(
                        text="Выберите сумму доната:", 
                        reply_markup=donate_amounts_kb()
                    )
        except Exception:
            await call.message.answer(text="Выберите сумму доната:", reply_markup=donate_amounts_kb())
            with contextlib.suppress(Exception):
                await call.message.delete()
        await call.answer()
        return

    if data == "purchased":
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
            empty_text = texts.get("empty", {}).get("purchased", "У вас нет купленных проектов.")
            if not user:
                await call.answer(empty_text, show_alert=True)
                return
            
            purchases = (await db.execute(select(Purchase).where(Purchase.user_id == user.id))).scalars().all()
            if not purchases:
                await call.answer(empty_text, show_alert=True)
                return
            
            item_ids = [p.item_id for p in purchases if p.item_id is not None]
            items = (await db.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
            
            kb = []
            for item in items:
                kb.append([InlineKeyboardButton(text=item.title, callback_data=f"item:{item.id}:{item.item_type.value}")])
            kb.append([InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="back:main")])

            title = texts["main_menu"].get("purchased_title", "Ваши купленные проекты:")
            image_path = texts["main_menu"].get("images", {}).get("purchased")
            
            try:
                if call.message.photo:
                    # Если сообщение с фото - просто меняем caption
                    await call.message.edit_caption(
                        caption=title,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
                    )
                else:
                    # Если текстовое - удаляем и создаем с фото
                    if image_path and Path(image_path).is_file():
                        await call.message.delete()
                        photo = FSInputFile(image_path)
                        await call.message.answer_photo(
                            photo=photo, 
                            caption=title, 
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
                        )
                    else:
                        await call.message.edit_text(
                            text=title, 
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
                        )
            except Exception:
                await call.message.answer(text=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
                with contextlib.suppress(Exception):
                    await call.message.delete()
            await call.answer()
        return


@router.callback_query(F.data.startswith("back:"))
async def cb_back(call: CallbackQuery) -> None:
    """Обработчик кнопки 'Назад'"""
    from .items import list_items  # Локальный импорт
    
    parts = call.data.split(":")
    action = parts[1]
    item_type = parts[2] if len(parts) > 2 else None
    page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
    texts = load_texts()
    
    if action == "list" and item_type:
        item_type_mapping = {
            "digital": ItemType.DIGITAL,
            "service": ItemType.SERVICE,
        }
        section_mapping = {
            "digital": "projects",
            "service": "services",
        }
        item_type_enum = item_type_mapping.get(item_type)
        if item_type_enum:
            await list_items(call.message, item_type_enum, section=section_mapping[item_type], call=call, page=page)
            await call.answer()
            return
    
    if action == "purchased":
        async with AsyncSessionLocal() as db:
            user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
            empty_text = texts.get("empty", {}).get("purchased", "У вас нет купленных проектов.")
            if not user:
                await call.answer(empty_text, show_alert=True)
                return
            
            purchases = (await db.execute(select(Purchase).where(Purchase.user_id == user.id))).scalars().all()
            if not purchases:
                await call.answer(empty_text, show_alert=True)
                return
            
            item_ids = [p.item_id for p in purchases if p.item_id is not None]
            items = (await db.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
            
            kb = []
            for item in items:
                kb.append([InlineKeyboardButton(text=item.title, callback_data=f"item:{item.id}:{item.item_type.value}")])
            kb.append([InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="back:main")])

            title = texts["main_menu"].get("purchased_title", "Ваши купленные проекты:")
            image_path = texts["main_menu"].get("images", {}).get("purchased")
            
            try:
                if call.message.photo:
                    # Если сообщение с фото - просто меняем caption
                    await call.message.edit_caption(
                        caption=title,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
                    )
                else:
                    # Если текстовое - удаляем и создаем с фото
                    if image_path and Path(image_path).is_file():
                        await call.message.delete()
                        photo = FSInputFile(image_path)
                        await call.message.answer_photo(
                            photo=photo, 
                            caption=title, 
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
                        )
                    else:
                        await call.message.edit_text(
                            text=title, 
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
                        )
            except Exception:
                await call.message.answer(text=title, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
                with contextlib.suppress(Exception):
                    await call.message.delete()
            await call.answer()
        return
    
    # Возврат в главное меню - получаем счетчик корзины
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
        cart_count = 0
        if user:
            cart_count = (await db.execute(
                select(func.count()).select_from(CartItem).where(CartItem.user_id == user.id)
            )).scalar_one()
    
    try:
        image_path = texts["main_menu"].get("image")
        if call.message.photo:
            # Если сообщение с фото - просто меняем caption
            await call.message.edit_caption(
                caption=texts["main_menu"]["title"],
                parse_mode="Markdown",
                reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username), cart_count=cart_count)
            )
        else:
            # Если текстовое - удаляем и создаем с фото
            if image_path and Path(image_path).is_file():
                await call.message.delete()
                photo = FSInputFile(image_path)
                await call.message.answer_photo(
                    photo=photo,
                    caption=texts["main_menu"]["title"],
                    parse_mode="Markdown",
                    reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username), cart_count=cart_count)
                )
            else:
                await call.message.edit_text(
                    texts["main_menu"]["title"], 
                    parse_mode="Markdown", 
                    reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username), cart_count=cart_count)
                )
    except Exception:
        await call.message.answer(
            texts["main_menu"]["title"], 
            parse_mode="Markdown", 
            reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username), cart_count=cart_count)
        )

