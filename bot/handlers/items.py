"""
Обработчики просмотра товаров и карточек
"""
import logging
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.filters import StateFilter
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, func

from app.utils.texts import load_texts
from bot.keyboards import (
    back_kb, item_card_kb, payment_method_kb, items_list_kb,
    main_menu_only_kb, payment_link_kb
)
from app.db.session import AsyncSessionLocal
from app.models import Item, ItemType, User, Purchase, CartItem
from app.config import settings
from app.services.orders_client import OrdersClient

logger = logging.getLogger("shopbot")
router = Router()


async def list_items(message: Message, item_type: ItemType, section: str = None, call: CallbackQuery = None, page: int = 1, page_size: int = 5) -> None:
    """Отображение списка товаров"""
    texts = load_texts()
    
    async with AsyncSessionLocal() as db:
        base_stmt = select(Item).where(Item.item_type == item_type, Item.is_visible == True)
        total = (await db.execute(select(func.count()).select_from(base_stmt.subquery()))).scalar_one()
        items = (await db.execute(
            base_stmt.order_by(Item.id.desc()).offset((page-1)*page_size).limit(page_size)
        )).scalars().all()
        
        purchased_ids: set[int] = set()
        try:
            tg = message.chat.id if message else (call.from_user.id if call else None)
            if tg:
                user = (await db.execute(select(User).where(User.tg_id == tg))).scalar_one_or_none()
                if user:
                    purchases = (await db.execute(
                        select(Purchase.item_id).where(Purchase.user_id == user.id)
                    )).scalars().all()
                    purchased_ids = set(int(x) for x in purchases if x)
        except Exception:
            purchased_ids = set()
    
    if not items:
        empty_key = {
            ItemType.DIGITAL: "items",
            ItemType.OFFLINE: "products",
            ItemType.SERVICE: "service",
        }.get(item_type, "items")
        empty_text = texts.get("empty", {}).get(empty_key, "Товаров пока-что нет, но вы держитесь!")
        
        if call:
            await call.answer(empty_text, show_alert=True)
            return
        else:
            await message.answer(empty_text, reply_markup=back_kb("back:main"))
            return
    
    if section is None:
        section_mapping = {
            ItemType.DIGITAL: "projects",
            ItemType.OFFLINE: "products",
            ItemType.SERVICE: "services",
        }
        section = section_mapping.get(item_type)
    
    description = texts["main_menu"]["section_descriptions"].get(section, "Список")
    image_path = texts["main_menu"].get("images", {}).get(section)
    
    try:
        if call:
            if image_path:
                photo = FSInputFile(image_path)
                try:
                    await call.message.edit_media(
                        media=InputMediaPhoto(media=photo, caption=description),
                        reply_markup=items_list_kb(items, item_type.value, purchased_ids, page=page, total=total, page_size=page_size)
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        logger.error(f"Ошибка редактирования: {e}")
                        await call.answer("Произошла ошибка", show_alert=True)
            else:
                try:
                    await call.message.edit_text(
                        text=description,
                        reply_markup=items_list_kb(items, item_type.value, purchased_ids, page=page, total=total, page_size=page_size)
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        raise
        else:
            if image_path:
                photo = FSInputFile(image_path)
                await message.answer_photo(
                    photo=photo,
                    caption=description,
                    reply_markup=items_list_kb(items, item_type.value, purchased_ids, page=page, total=total, page_size=page_size)
                )
            else:
                await message.answer(
                    text=description,
                    reply_markup=items_list_kb(items, item_type.value, purchased_ids, page=page, total=total, page_size=page_size)
                )
    except FileNotFoundError:
        if call:
            try:
                await call.message.edit_text(description, reply_markup=items_list_kb(items, item_type.value, page=page, total=total, page_size=page_size))
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
        else:
            await message.answer(description, reply_markup=items_list_kb(items, item_type.value, page=page, total=total, page_size=page_size))


@router.callback_query(F.data.startswith("list:"))
async def list_pagination(call: CallbackQuery) -> None:
    """Пагинация списков товаров"""
    try:
        _, type_str, page_str = call.data.split(":", 2)
        page_num = int(page_str) if page_str.isdigit() else 1
    except Exception:
        page_num = 1
        type_str = "digital"
    
    mapping = {
        "digital": (ItemType.DIGITAL, "projects"),
        "offline": (ItemType.OFFLINE, "products"),
        "service": (ItemType.SERVICE, "services"),
    }
    
    if type_str in mapping:
        itype, section = mapping[type_str]
        await list_items(call.message, itype, section=section, call=call, page=page_num)
    await call.answer()


@router.callback_query(F.data.startswith("item:"))
async def show_item(call: CallbackQuery) -> None:
    """Отображение карточки товара"""
    parts = call.data.split(":")
    item_id = parts[1]
    item_type = parts[2] if len(parts) > 2 else None
    page_from = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1
    
    logger.info("Карточка товара: callback получен, item_id=%s, type=%s", item_id, item_type)
    
    async with AsyncSessionLocal() as db:
        item = (await db.execute(select(Item).where(Item.id == int(item_id)))).scalar_one_or_none()
        purchased = False
        in_cart = False
        
        try:
            user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
            if user:
                purchased = (await db.execute(
                    select(Purchase).where(Purchase.user_id == user.id, Purchase.item_id == int(item_id))
                )).first() is not None
                in_cart = (await db.execute(
                    select(CartItem).where(CartItem.user_id == user.id, CartItem.item_id == int(item_id))
                )).scalar_one_or_none() is not None
        except Exception:
            purchased = False
            in_cart = False
        
        if not item:
            logger.error(f"Товар не найден: id={item_id}")
            await call.answer(f"Товар не найден: id={item_id}", show_alert=True)
            return
        
        caption = (
            f"*{item.title}*\n\n"
            f"{item.description}\n\n"
            f"?? Цена: `{item.price_minor/100:.2f}` ?"
        )
        
        logger.info("Показываем карточку: %s (id=%s, type=%s)", item.title, item.id, item.item_type)
        
        try:
            if call.message.photo:
                media_source = None
                if item.image_file_id:
                    if item.image_file_id.startswith("http") or item.image_file_id.startswith("AgAC"):
                        media_source = item.image_file_id
                    elif Path(item.image_file_id).is_file():
                        media_source = FSInputFile(item.image_file_id)

                if not media_source:
                    texts = load_texts()
                    defaults = texts.get("defaults", {}).get("images", {})
                    key = {
                        ItemType.SERVICE: "service",
                        ItemType.DIGITAL: "digital",
                    }.get(item.item_type)
                    default_path = defaults.get(key) if key else None
                    if default_path and Path(default_path).is_file():
                        media_source = FSInputFile(default_path)

                if media_source:
                    await call.message.edit_media(
                        media=InputMediaPhoto(media=media_source, caption=caption, parse_mode="Markdown"),
                        reply_markup=item_card_kb(item.id, item_type, purchased, from_purchased=(call.message.caption and "Ваши купленные проекты:" in call.message.caption), page=page_from, in_cart=in_cart)
                    )
                else:
                    await call.message.edit_caption(
                        caption=caption,
                        parse_mode="Markdown",
                        reply_markup=item_card_kb(item.id, item_type, purchased, from_purchased=(call.message.caption and "Ваши купленные проекты:" in call.message.caption), page=page_from, in_cart=in_cart)
                    )
            else:
                await call.message.edit_text(
                    text=caption,
                    parse_mode="Markdown",
                    reply_markup=item_card_kb(item.id, item_type, purchased, from_purchased=False, page=page_from, in_cart=in_cart)
                )
        except Exception as e:
            logger.error(f"Ошибка при показе карточки товара: {e}")
            await call.answer("Ошибка при показе карточки товара", show_alert=True)
        await call.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(call: CallbackQuery) -> None:
    """Обработчик кнопки 'Купить'"""
    _, item_id = call.data.split(":", 1)
    await call.message.edit_reply_markup(reply_markup=payment_method_kb(int(item_id)))
    await call.answer()


@router.callback_query(F.data.startswith("buy_one:"))
async def cb_buy_one(call: CallbackQuery) -> None:
    """Быстрая покупка одного товара"""
    _, item_id = call.data.split(":")
    item_id_int = int(item_id)
    
    async with OrdersClient() as client:
        try:
            url = await client.create_order(item_id_int, call.from_user.id)
            try:
                await call.message.edit_reply_markup(reply_markup=payment_link_kb(url))
            except Exception:
                try:
                    if call.message.photo:
                        await call.message.edit_caption(caption="Перейдите к оплате:", reply_markup=payment_link_kb(url))
                    else:
                        await call.message.edit_text("Перейдите к оплате:", reply_markup=payment_link_kb(url))
                except Exception:
                    await call.message.answer("Ссылка на оплату:", reply_markup=payment_link_kb(url))
        except Exception:
            await call.message.answer("Не удалось создать заказ. Попробуйте позже.")
    await call.answer()


@router.message(StateFilter(None))
async def fallback_message(message: Message) -> None:
    """Обработчик неизвестных сообщений"""
    texts = load_texts()
    text = texts.get("fallback", {}).get("text") or "Я пока не умею отвечать на такие сообщения."
    await message.answer(text, reply_markup=main_menu_only_kb())
