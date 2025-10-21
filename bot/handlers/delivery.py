"""
Обработчики оффлайн доставки физических товаров
"""
import logging
import uuid

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete

from app.utils.texts import load_texts
from bot.keyboards import skip_kb, payment_link_kb
from app.db.session import AsyncSessionLocal
from app.models import Item, ItemType, User, Order, Purchase, CartItem, PaymentMethod, OrderStatus
from app.config import settings
from app.services.yookassa import YooKassaClient

logger = logging.getLogger("shopbot")
router = Router()


# States для сбора данных доставки
class OfflineDeliveryStates(StatesGroup):
    waiting_for_fullname = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_comment = State()


async def send_offline_order_to_admin(order_id: int, items: list, delivery_data: dict, bot) -> None:
    """Отправка уведомления администратору о новом оффлайн заказе"""
    if not settings.admin_chat_id:
        logger.warning("Admin chat ID not configured, skipping admin notification")
        return
    
    items_text = "\n".join([f"• {item.title} - {item.price_minor/100:.2f} ₽" for item in items])
    total = sum(item.price_minor for item in items)
    
    message = (
        f"📦 *Новый заказ #{order_id}*\n\n"
        f"*Товары:*\n{items_text}\n\n"
        f"*Итого:* `{total/100:.2f}` ₽\n\n"
        f"🚚 *Данные доставки:*\n"
        f"👤 ФИО: {delivery_data.get('fullname', '—')}\n"
        f"📞 Телефон: {delivery_data.get('phone', '—')}\n"
        f"📍 Адрес: {delivery_data.get('address', '—')}\n"
    )
    
    if delivery_data.get('comment'):
        message += f"💬 Комментарий: {delivery_data['comment']}\n"
    
    try:
        await bot.send_message(
            chat_id=int(settings.admin_chat_id),
            text=message,
            parse_mode="Markdown"
        )
        logger.info(f"Sent offline order notification to admin for order #{order_id}")
    except Exception as e:
        logger.error(f"Failed to send offline order notification: {e}")


@router.callback_query(F.data.startswith("buy_direct:"))
async def cb_buy_direct(call: CallbackQuery, state: FSMContext) -> None:
    """Быстрая покупка товара напрямую"""
    from app.services.orders_client import OrdersClient  # Локальный импорт
    
    _, item_id, _ = call.data.split(":")
    item_id_int = int(item_id)
    
    # Проверяем тип товара
    async with AsyncSessionLocal() as db:
        item = (await db.execute(select(Item).where(Item.id == item_id_int))).scalar_one_or_none()
        if not item:
            await call.answer("Товар не найден", show_alert=True)
            return
        
        # Если это физический товар - запрашиваем данные доставки
        if item.item_type == ItemType.OFFLINE:
            await state.update_data(
                quick_buy_item_id=item_id_int,
                total_amount=item.price_minor
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
    
    # Для цифровых товаров и услуг - создаём заказ сразу
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


@router.callback_query(F.data == "skip_fullname", OfflineDeliveryStates.waiting_for_fullname)
async def skip_fullname(call: CallbackQuery, state: FSMContext) -> None:
    """Пропуск ввода ФИО"""
    await state.update_data(delivery_fullname="")
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "phone",
        "📞 Введите номер телефона для связи:"
    )
    
    try:
        await call.message.edit_text(prompt, reply_markup=skip_kb("skip_phone"))
    except Exception:
        await call.message.answer(prompt, reply_markup=skip_kb("skip_phone"))
    
    await state.set_state(OfflineDeliveryStates.waiting_for_phone)
    await call.answer()


@router.callback_query(F.data == "skip_phone", OfflineDeliveryStates.waiting_for_phone)
async def skip_phone(call: CallbackQuery, state: FSMContext) -> None:
    """Пропуск ввода телефона"""
    await state.update_data(delivery_phone="")
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "address",
        "📍 Введите адрес доставки:"
    )
    
    try:
        await call.message.edit_text(prompt, reply_markup=skip_kb("skip_address"))
    except Exception:
        await call.message.answer(prompt, reply_markup=skip_kb("skip_address"))
    
    await state.set_state(OfflineDeliveryStates.waiting_for_address)
    await call.answer()


@router.callback_query(F.data == "skip_address", OfflineDeliveryStates.waiting_for_address)
async def skip_address(call: CallbackQuery, state: FSMContext) -> None:
    """Пропуск ввода адреса"""
    await state.update_data(delivery_address="")
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "comment",
        "💬 Введите комментарий к заказу (или нажмите 'Пропустить'):")
    
    try:
        await call.message.edit_text(prompt, reply_markup=skip_kb("skip_comment"))
    except Exception:
        await call.message.answer(prompt, reply_markup=skip_kb("skip_comment"))
    
    await state.set_state(OfflineDeliveryStates.waiting_for_comment)
    await call.answer()


@router.callback_query(F.data == "skip_comment", OfflineDeliveryStates.waiting_for_comment)
async def skip_comment(call: CallbackQuery, state: FSMContext) -> None:
    """Пропуск ввода комментария"""
    await state.update_data(delivery_comment="")
    
    data = await state.get_data()
    quick_buy_item_id = data.get("quick_buy_item_id")
    
    # ✅ ИСПРАВЛЕНО: Используем специальные функции для callback
    if quick_buy_item_id:
        await process_quick_offline_purchase_from_callback(call, state, data, quick_buy_item_id)
    else:
        await process_cart_offline_purchase_from_callback(call, state, data)
    
    await state.clear()
    await call.answer()


@router.message(OfflineDeliveryStates.waiting_for_fullname)
async def offline_capture_fullname(message: Message, state: FSMContext) -> None:
    """Обработка ввода ФИО"""
    fullname = (message.text or "").strip()
    
    if not fullname or len(fullname) < 2:
        await message.answer("❌ Пожалуйста, введите корректное ФИО")
        return
    
    await state.update_data(delivery_fullname=fullname)
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "phone",
        "📞 Введите номер телефона для связи:"
    )
    
    await message.answer(prompt, reply_markup=skip_kb("skip_phone"))
    await state.set_state(OfflineDeliveryStates.waiting_for_phone)


@router.message(OfflineDeliveryStates.waiting_for_phone)
async def offline_capture_phone(message: Message, state: FSMContext) -> None:
    """Обработка ввода телефона"""
    phone = (message.text or "").strip()
    
    phone_digits = ''.join(filter(str.isdigit, phone))
    if len(phone_digits) < 10:
        await message.answer("❌ Пожалуйста, введите корректный номер телефона (минимум 10 цифр)")
        return
    
    await state.update_data(delivery_phone=phone)
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "address",
        "📍 Введите адрес доставки:"
    )
    
    await message.answer(prompt, reply_markup=skip_kb("skip_address"))
    await state.set_state(OfflineDeliveryStates.waiting_for_address)


@router.message(OfflineDeliveryStates.waiting_for_address)
async def offline_capture_address(message: Message, state: FSMContext) -> None:
    """Обработка ввода адреса"""
    address = (message.text or "").strip()
    
    if not address or len(address) < 3:
        await message.answer("❌ Пожалуйста, введите корректный адрес доставки")
        return
    
    await state.update_data(delivery_address=address)
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "comment",
        "💬 Введите комментарий к заказу (или нажмите 'Пропустить'):",
    )
    
    await message.answer(prompt, reply_markup=skip_kb("skip_comment"))
    await state.set_state(OfflineDeliveryStates.waiting_for_comment)


@router.message(OfflineDeliveryStates.waiting_for_comment)
async def offline_capture_comment(message: Message, state: FSMContext) -> None:
    """Обработка ввода комментария"""
    comment = (message.text or "").strip()
    
    await state.update_data(delivery_comment=comment)
    
    data = await state.get_data()
    
    # Определяем: быстрая покупка или корзина
    quick_buy_item_id = data.get("quick_buy_item_id")
    
    if quick_buy_item_id:
        # Быстрая покупка одного товара
        await process_quick_offline_purchase(message, state, data, quick_buy_item_id)
    else:
        # Корзина
        await process_cart_offline_purchase(message, state, data)
    
    await state.clear()


async def process_quick_offline_purchase(message: Message, state: FSMContext, data: dict, item_id: int) -> None:
    """Обработка быстрой покупки физического товара"""
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
        if not user:
            await message.answer("Пользователь не найден")
            return
        
        item = (await db.execute(select(Item).where(Item.id == item_id))).scalar_one_or_none()
        if not item:
            await message.answer("Товар не найден")
            return
        
        # Создаем заказ
        order = Order(
            user_id=user.id,
            item_id=item.id,
            amount_minor=item.price_minor,
            currency="RUB",
            payment_method=PaymentMethod.CARD_RF,
            status=OrderStatus.CREATED,
            buyer_tg_id=str(message.from_user.id),
        )
        db.add(order)
        await db.flush()
        
        # Создаем покупку с данными доставки
        purchase = Purchase(
            order_id=order.id,
            user_id=user.id,
            item_id=item.id,
            delivery_info=None,
            delivery_fullname=data.get("delivery_fullname"),
            delivery_phone=data.get("delivery_phone"),
            delivery_address=data.get("delivery_address"),
            delivery_comment=data.get("delivery_comment"),
        )
        db.add(purchase)
        await db.flush()
        
        # Создаем платёж через YooKassa
        client = YooKassaClient()
        try:
            idem = str(uuid.uuid4())
            templates = load_texts().get("payment", {}).get("description_templates", {})
            description = (templates.get("offline") or "Оплата: {title} | Заказ {order_id}").format(
                title=item.title,
                order_id=order.id
            )
            
            resp = await client.create_payment(
                amount_minor=item.price_minor,
                description=description,
                payment_id=str(order.id),
                payment_method_type=None,
                metadata={"offline_order_id": str(order.id)},
                customer_email=f"{message.from_user.id}@{settings.email_domain}",
                idempotence_key=idem,
            )
            
            url = (resp or {}).get("confirmation", {}).get("confirmation_url")
            if not url:
                await db.rollback()
                await message.answer("Не удалось создать заказ. Попробуйте позже.")
                return
            
            order.fk_order_id = resp.get("id")
            order.fk_payment_url = url
            order.status = OrderStatus.PENDING
            
            await db.commit()
            
            await message.answer("✅ Данные сохранены. Перейдите к оплате:", reply_markup=payment_link_kb(url))
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating offline order: {e}")
            await message.answer("Не удалось создать заказ. Попробуйте позже.")
        finally:
            await client.close()


async def process_cart_offline_purchase(message: Message, state: FSMContext, data: dict) -> None:
    """Обработка оплаты корзины с физическими товарами"""
    cart_items = data.get("cart_items")
    total_amount = data.get("total_amount", 0)
    
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
        if not user:
            await message.answer("Пользователь не найден")
            return
        
        # Создаем заказ
        order = Order(
            user_id=user.id,
            item_id=None,
            amount_minor=total_amount,
            currency="RUB",
            payment_method=PaymentMethod.CARD_RF,
            status=OrderStatus.CREATED,
            buyer_tg_id=str(message.from_user.id),
        )
        db.add(order)
        await db.flush()
        
        # Создаём покупки с данными доставки
        for item_id in cart_items:
            purchase = Purchase(
                order_id=order.id,
                user_id=user.id,
                item_id=item_id,
                delivery_info=None,
                delivery_fullname=data.get("delivery_fullname"),
                delivery_phone=data.get("delivery_phone"),
                delivery_address=data.get("delivery_address"),
                delivery_comment=data.get("delivery_comment"),
            )
            db.add(purchase)
        
        await db.flush()
        
        # Создаём платёж через YooKassa
        client = YooKassaClient()
        try:
            idem = str(uuid.uuid4())
            templates = load_texts().get("payment", {}).get("description_templates", {})
            description = (templates.get("cart") or "Оплата корзины | Заказ {order_id}").format(order_id=order.id)
            
            items = (await db.execute(select(Item).where(Item.id.in_(cart_items)))).scalars().all()
            
            # ✅ ИСПРАВЛЕНО: используем правильный ключ metadata для оффлайн заказов
            resp = await client.create_payment(
                amount_minor=total_amount,
                description=description,
                payment_id=f"offline_cart:{order.id}",
                payment_method_type=None,
                metadata={"offline_order_id": str(order.id)},
                customer_email=f"{message.from_user.id}@{settings.email_domain}",
                idempotence_key=idem,
            )
            
            url = (resp or {}).get("confirmation", {}).get("confirmation_url")
            if not url:
                await db.rollback()
                await message.answer("Не удалось создать заказ. Попробуйте позже.")
                return
            
            order.fk_order_id = resp.get("id")
            order.fk_payment_url = url
            order.status = OrderStatus.PENDING
            
            await db.commit()
            
            # Очищаем корзину после успешного создания заказа
            await db.execute(delete(CartItem).where(CartItem.user_id == user.id))
            await db.commit()
            
            await message.answer("✅ Данные сохранены. Перейдите к оплате:", reply_markup=payment_link_kb(url))
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating cart offline order: {e}")
            await message.answer("Не удалось создать заказ. Попробуйте позже.")
        finally:
            await client.close()


async def process_quick_offline_purchase_from_callback(call: CallbackQuery, state: FSMContext, data: dict, item_id: int) -> None:
    """Обработка быстрой покупки физического товара из callback"""
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
        if not user:
            await call.message.answer("Пользователь не найден")
            return
        
        item = (await db.execute(select(Item).where(Item.id == item_id))).scalar_one_or_none()
        if not item:
            await call.message.answer("Товар не найден")
            return
        
        # Создаем заказ
        order = Order(
            user_id=user.id,
            item_id=item.id,
            amount_minor=item.price_minor,
            currency="RUB",
            payment_method=PaymentMethod.CARD_RF,
            status=OrderStatus.CREATED,
            buyer_tg_id=str(call.from_user.id),
        )
        db.add(order)
        await db.flush()
        
        # Создаем покупку с данными доставки
        purchase = Purchase(
            order_id=order.id,
            user_id=user.id,
            item_id=item.id,
            delivery_info=None,
            delivery_fullname=data.get("delivery_fullname"),
            delivery_phone=data.get("delivery_phone"),
            delivery_address=data.get("delivery_address"),
            delivery_comment=data.get("delivery_comment"),
        )
        db.add(purchase)
        await db.flush()
        
        # Создаем платёж через YooKassa
        client = YooKassaClient()
        try:
            idem = str(uuid.uuid4())
            templates = load_texts().get("payment", {}).get("description_templates", {})
            description = (templates.get("offline") or "Оплата: {title} | Заказ {order_id}").format(
                title=item.title,
                order_id=order.id
            )
            
            resp = await client.create_payment(
                amount_minor=item.price_minor,
                description=description,
                payment_id=str(order.id),
                payment_method_type=None,
                metadata={"offline_order_id": str(order.id)},
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
            
            await call.message.answer("✅ Данные сохранены. Перейдите к оплате:", reply_markup=payment_link_kb(url))
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating offline order: {e}")
            await call.message.answer("Не удалось создать заказ. Попробуйте позже.")
        finally:
            await client.close()


async def process_cart_offline_purchase_from_callback(call: CallbackQuery, state: FSMContext, data: dict) -> None:
    """Обработка оплаты корзины с физическими товарами из callback"""
    cart_items = data.get("cart_items")
    total_amount = data.get("total_amount", 0)
    
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == call.from_user.id))).scalar_one_or_none()
        if not user:
            await call.message.answer("Пользователь не найден")
            return
        
        # Создаем заказ
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
        
        # Создаём покупки с данными доставки
        for item_id in cart_items:
            purchase = Purchase(
                order_id=order.id,
                user_id=user.id,
                item_id=item_id,
                delivery_info=None,
                delivery_fullname=data.get("delivery_fullname"),
                delivery_phone=data.get("delivery_phone"),
                delivery_address=data.get("delivery_address"),
                delivery_comment=data.get("delivery_comment"),
            )
            db.add(purchase)
        
        await db.flush()
        
        # Создаём платёж через YooKassa
        client = YooKassaClient()
        try:
            idem = str(uuid.uuid4())
            templates = load_texts().get("payment", {}).get("description_templates", {})
            description = (templates.get("cart") or "Оплата корзины | Заказ {order_id}").format(order_id=order.id)
            
            items = (await db.execute(select(Item).where(Item.id.in_(cart_items)))).scalars().all()
            
            resp = await client.create_payment(
                amount_minor=total_amount,
                description=description,
                payment_id=f"offline_cart:{order.id}",
                payment_method_type=None,
                metadata={"offline_order_id": str(order.id)},
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
            
            await call.message.answer("✅ Данные сохранены. Перейдите к оплате:", reply_markup=payment_link_kb(url))
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating cart offline order: {e}")
            await call.message.answer("Не удалось создать заказ. Попробуйте позже.")
        finally:
            await client.close()