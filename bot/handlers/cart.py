"""
Модуль корзины покупок
"""
import logging
import contextlib
import uuid

from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, delete

from app.utils.texts import load_texts
from bot.keyboards import main_menu_kb, cart_kb, skip_kb, item_card_kb, payment_link_kb
from app.db.session import AsyncSessionLocal
from app.models import Item, ItemType, User, Purchase, CartItem, Order, PaymentMethod, OrderStatus, ItemCode
from app.config import settings
from app.services.yookassa import YooKassaClient

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


async def has_offline_items(items: list) -> bool:
    """Проверка наличия оффлайн товаров в списке"""
    return any(item.item_type == ItemType.OFFLINE for item in items)


@router.callback_query(F.data == "menu:cart")
async def show_cart(call: CallbackQuery) -> None:
    """Отображение корзины"""
    logger.info(f"Showing cart for user {call.from_user.id}")
    texts = load_texts()
    
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
        if not user:
            logger.warning(f"User {call.from_user.id} not found in database")
            await call.answer("Пользователь не найден", show_alert=True)
            return
        
        cart_items_rows = (await db.execute(
            select(CartItem).where(CartItem.user_id == user.id)
        )).scalars().all()
        
        if not cart_items_rows:
            logger.info(f"Cart is empty for user {call.from_user.id}")
            empty_cart_msg = texts.get("empty", {}).get("cart", "🛒 Корзина пуста")
            await call.answer(empty_cart_msg, show_alert=True)
            return
        
        item_ids = [ci.item_id for ci in cart_items_rows]
        items = (await db.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
        
        unavailable = []
        available_items = []
        for item in items:
            if not item.is_visible:
                unavailable.append(item.title)
            else:
                available_items.append(item)
        
        if unavailable:
            msg = f"⚠️ Товары недоступны: {', '.join(unavailable)}"
            logger.warning(f"Unavailable items in cart for user {call.from_user.id}: {unavailable}")
            await call.answer(msg, show_alert=True)
        
        total = sum(it.price_minor for it in available_items)
        
        caption = "🛒 *Корзина*\n\n"
        for it in available_items:
            caption += f"• {it.title} — `{it.price_minor/100:.2f}` ₽\n"
        caption += f"\n*Итого:* `{total/100:.2f}` ₽"
        
        logger.info(f"Cart displayed for user {call.from_user.id}: {len(available_items)} items, total {total/100:.2f} RUB")
        
        try:
            if call.message.photo:
                await call.message.edit_caption(
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=cart_kb(available_items, total)
                )
            else:
                await call.message.edit_text(
                    text=caption,
                    parse_mode="Markdown",
                    reply_markup=cart_kb(available_items, total)
                )
        except Exception as e:
            logger.error(f"Failed to display cart for user {call.from_user.id}: {e}")
            await call.message.answer(caption, parse_mode="Markdown", reply_markup=cart_kb(available_items, total))
            with contextlib.suppress(Exception):
                await call.message.delete()
    await call.answer()


@router.callback_query(F.data.startswith("cart:add:"))
async def add_to_cart(call: CallbackQuery) -> None:
    """Добавление товара в корзину"""
    _, _, item_id = call.data.split(":")
    item_id_int = int(item_id)
    
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
        if not user:
            await call.answer("Пользователь не найден", show_alert=True)
            return
        
        item = (await db.execute(select(Item).where(Item.id == item_id_int))).scalar_one_or_none()
        if not item:
            await call.answer("Товар не найден", show_alert=True)
            return
        
        purchased = (await db.execute(
            select(Purchase).where(Purchase.user_id == user.id, Purchase.item_id == item_id_int)
        )).first() is not None
        
        if purchased and item.item_type == ItemType.DIGITAL:
            await call.answer("Вы уже купили этот товар", show_alert=True)
            return
        
        existing = (await db.execute(
            select(CartItem).where(CartItem.user_id == user.id, CartItem.item_id == item_id_int)
        )).scalar_one_or_none()
        
        if existing:
            await call.answer("Товар уже в корзине", show_alert=True)
            return
        
        cart_item = CartItem(user_id=user.id, item_id=item_id_int)
        db.add(cart_item)
        await db.commit()
    
    await call.answer("✅ Добавлено в корзину", show_alert=True)
    
    # Обновляем карточку товара
    try:
        async with AsyncSessionLocal() as db:
            item = (await db.execute(select(Item).where(Item.id == item_id_int))).scalar_one_or_none()
            user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
            in_cart = True
            purchased = False
            if user:
                purchased = (await db.execute(
                    select(Purchase).where(Purchase.user_id == user.id, Purchase.item_id == item_id_int)
                )).first() is not None
            
            caption = (
                f"*{item.title}*\n\n"
                f"{item.description}\n\n"
                f"💰 Цена: `{item.price_minor/100:.2f}` ₽"
            )
            await call.message.edit_caption(
                caption=caption,
                parse_mode="Markdown",
                reply_markup=item_card_kb(item.id, item.item_type.value, purchased, from_purchased=False, page=1, in_cart=in_cart)
            )
    except Exception:
        pass


@router.callback_query(F.data.startswith("cart:remove:"))
async def remove_from_cart(call: CallbackQuery) -> None:
    """Удаление товара из корзины"""
    _, _, item_id = call.data.split(":")
    item_id_int = int(item_id)
    
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
        if not user:
            await call.answer("Пользователь не найден", show_alert=True)
            return
        
        await db.execute(
            delete(CartItem).where(CartItem.user_id == user.id, CartItem.item_id == item_id_int)
        )
        await db.commit()
    
    await call.answer("✅ Удалено из корзины", show_alert=True)
    
    # Если мы в корзине - обновляем её
    if call.message and call.message.caption and "Корзина" in call.message.caption:
        await show_cart(call)
    else:
        # Если в карточке товара - обновляем карточку
        try:
            async with AsyncSessionLocal() as db:
                item = (await db.execute(select(Item).where(Item.id == item_id_int))).scalar_one_or_none()
                user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
                in_cart = False
                purchased = False
                if user:
                    purchased = (await db.execute(
                        select(Purchase).where(Purchase.user_id == user.id, Purchase.item_id == item_id_int)
                    )).first() is not None
                
                caption = (
                    f"*{item.title}*\n\n"
                    f"{item.description}\n\n"
                    f"💰 Цена: `{item.price_minor/100:.2f}` ₽"
                )
                await call.message.edit_caption(
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=item_card_kb(item.id, item.item_type.value, purchased, from_purchased=False, page=1, in_cart=in_cart)
                )
        except Exception:
            pass


@router.callback_query(F.data == "cart:clear")
async def clear_cart(call: CallbackQuery) -> None:
    """Очистка корзины"""
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
        if not user:
            await call.answer("Пользователь не найден", show_alert=True)
            return
        
        await db.execute(delete(CartItem).where(CartItem.user_id == user.id))
        await db.commit()
    
    await call.answer("🗑️ Корзина очищена", show_alert=True)
    
    texts = load_texts()
    try:
        if "image" in texts["main_menu"]:
            photo = FSInputFile(texts["main_menu"]["image"])
            await call.message.edit_media(
                media=InputMediaPhoto(media=photo, caption=texts["main_menu"]["title"], parse_mode="Markdown"),
                reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username), cart_count=0)
            )
        else:
            await call.message.edit_text(
                texts["main_menu"]["title"],
                parse_mode="Markdown",
                reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username), cart_count=0)
            )
    except Exception:
        await call.message.answer(
            texts["main_menu"]["title"],
            parse_mode="Markdown",
            reply_markup=main_menu_kb(texts, is_admin=_is_admin_user(call.from_user.id, call.from_user.username), cart_count=0)
        )


@router.callback_query(F.data == "cart:checkout")
async def checkout_cart(call: CallbackQuery, state: FSMContext) -> None:
    """Оформление заказа из корзины"""
    # Импортируем OfflineDeliveryStates локально чтобы избежать циклических импортов
    from .delivery import OfflineDeliveryStates
    
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
        if not user:
            await call.answer("Пользователь не найден", show_alert=True)
            return
        
        cart_items_rows = (await db.execute(
            select(CartItem).where(CartItem.user_id == user.id)
        )).scalars().all()
        
        if not cart_items_rows:
            await call.answer("Корзина пуста", show_alert=True)
            return
        
        item_ids = [ci.item_id for ci in cart_items_rows]
        items = (await db.execute(select(Item).where(Item.id.in_(item_ids), Item.is_visible == True))).scalars().all()
        
        if not items:
            await call.answer("Нет доступных товаров для оплаты", show_alert=True)
            return
        
        # Проверка наличия кодов для цифровых товаров
        for item in items:
            if item.item_type == ItemType.DIGITAL and item.delivery_type == 'codes':
                available_codes = (await db.execute(
                    select(func.count()).select_from(ItemCode).where(
                        ItemCode.item_id == item.id,
                        ItemCode.is_sold == False
                    )
                )).scalar_one()
                
                if available_codes < 1:
                    await call.answer(f"❌ Товар '{item.title}' закончился", show_alert=True)
                    return
        
        total_amount = sum(it.price_minor for it in items)
        
        # Если есть физические товары, запрашиваем данные доставки
        if await has_offline_items(items):
            await state.update_data(
                cart_items=item_ids,
                total_amount=total_amount
            )
            
            texts = load_texts()
            prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
                "fullname", 
                "📝 Введите ваше ФИО для доставки:"
            )
            
            try:
                if call.message.photo:
                    await call.message.edit_caption(
                        caption=prompt,
                        reply_markup=skip_kb("skip_fullname")
                    )
                else:
                    await call.message.edit_text(
                        text=prompt,
                        reply_markup=skip_kb("skip_fullname")
                    )
            except Exception:
                await call.message.answer(prompt, reply_markup=skip_kb("skip_fullname"))
            
            await state.set_state(OfflineDeliveryStates.waiting_for_fullname)
            await call.answer()
            return
        
        # Создание заказа для цифровых товаров/услуг (БЕЗ данных доставки)
        order = Order(
            user_id=user.id,
            item_id=None,
            amount_minor=total_amount,
            currency="RUB",
            payment_method=PaymentMethod.CARD_RF,
            status=OrderStatus.CREATED,
            buyer_tg_id=str(call.from_user.id),
        )
        db.add(order)
        await db.flush()
        
        # Создаём покупки БЕЗ данных доставки
        for item in items:
            purchase = Purchase(
                order_id=order.id,
                user_id=user.id,
                item_id=item.id,
                delivery_info=None
            )
            db.add(purchase)
        
        await db.flush()
        
        client = YooKassaClient()
        try:
            idem = str(uuid.uuid4())
            templates = load_texts().get("payment", {}).get("description_templates", {})
            description = (templates.get("cart") or "Оплата корзины | Заказ {order_id}").format(order_id=order.id)
            
            resp = await client.create_payment(
                amount_minor=total_amount,
                description=description,
                payment_id=f"cart:{order.id}",
                payment_method_type=None,
                metadata={"cart_order_id": str(order.id), "item_ids": ",".join(str(i.id) for i in items)},
                customer_email=f"{call.from_user.id}@{settings.email_domain}",
                idempotence_key=idem,
            )
            url = (resp or {}).get("confirmation", {}).get("confirmation_url")
            if not url:
                await db.rollback()
                await call.message.answer("Не удалось создать заказ. Попробуйте позже.")
                return
            
            order.fk_order_id = resp.get("id")
            order.fk_payment_url = url
            order.status = OrderStatus.PENDING
            
            await db.commit()
            
            # Очищаем корзину после успешного создания заказа
            await db.execute(delete(CartItem).where(CartItem.user_id == user.id))
            await db.commit()
            
            try:
                if call.message.photo:
                    await call.message.edit_caption(
                        caption="Перейдите к оплате:",
                        reply_markup=payment_link_kb(url)
                    )
                else:
                    await call.message.edit_text(
                        "Перейдите к оплате:",
                        reply_markup=payment_link_kb(url)
                    )
            except Exception:
                await call.message.answer("Ссылка на оплату:", reply_markup=payment_link_kb(url))
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating cart order: {e}")
            await call.message.answer("Не удалось создать заказ. Попробуйте позже.")
        finally:
            await client.close()
    
    await call.answer()
