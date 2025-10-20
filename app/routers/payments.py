from fastapi import APIRouter, Header, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from loguru import logger

from app.db.session import get_db_session
from app.models import Order, Item, Purchase, ItemType, OrderStatus, User, ItemCode, CartItem
from aiogram import Bot
from bot.webhook_app import bot as global_bot
from app.config import settings
from app.services.delivery import DeliveryService
from app.utils.texts import load_texts
from app.services.yookassa import verify_webhook_basic, is_trusted_yookassa_ip, YooKassaClient

router = APIRouter(prefix="/payments", tags=["payments"]) 


def get_bot() -> Bot:
    return global_bot


@router.post("/yookassa/webhook")
async def yookassa_webhook(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
    bot: Bot = Depends(get_bot),
) -> dict:
    if not verify_webhook_basic(authorization):
        raise HTTPException(status_code=401, detail="unauthorized")

    payload = await request.json()
    try:
        peer = request.client.host if request.client else None
    except Exception:
        peer = None
    if peer and not is_trusted_yookassa_ip(peer):
        logger.bind(event="yk.webhook").info("Webhook ЮKassa от IP вне списка доверенных: {ip}", ip=peer)

    obj = payload.get("object", {}) if isinstance(payload, dict) else {}
    event = payload.get("event") if isinstance(payload, dict) else None
    metadata = obj.get("metadata", {}) if isinstance(obj, dict) else {}
    status = obj.get("status")

    if not (event == "payment.succeeded" and status == "succeeded"):
        return {"ok": True}

    # ========== ДОНАТЫ ==========
    donation_raw = metadata.get("donation")
    donation_flag = False
    if isinstance(donation_raw, bool):
        donation_flag = donation_raw
    elif isinstance(donation_raw, str):
        donation_flag = donation_raw.strip().lower() in {"true", "1", "yes"}
    if donation_flag:
        if settings.admin_chat_id:
            try:
                amount_value = (obj.get("amount", {}) or {}).get("value")
                buyer_tg_id = metadata.get("buyer_tg_id")
                try:
                    buyer_tg_id_int = int(buyer_tg_id) if buyer_tg_id is not None and str(buyer_tg_id).isdigit() else None
                except Exception:
                    buyer_tg_id_int = None
                buyer_username = None
                if buyer_tg_id_int is not None:
                    buyer_username = (await db.execute(select(User.username).where(User.tg_id == buyer_tg_id_int))).scalar_one_or_none()
                texts = load_texts().get("notifications", {})
                template = texts.get("donation_received") or (
                    "🎁 Донат получен\nСумма: {amount} ₽\nОт: {buyer_username}"
                )
                text = template.format(
                    amount=amount_value or "0.00",
                    buyer_username=(f"@{buyer_username}" if buyer_username else "-"),
                )
                await bot.send_message(int(settings.admin_chat_id), text)
            except Exception:
                pass
        return {"ok": True}

    # ========== АДМИН-СЧЕТА ==========
    admin_invoice_raw = metadata.get("admin_invoice")
    admin_invoice_flag = False
    if isinstance(admin_invoice_raw, bool):
        admin_invoice_flag = admin_invoice_raw
    elif isinstance(admin_invoice_raw, str):
        admin_invoice_flag = admin_invoice_raw.strip().lower() in {"true", "1", "yes"}
    if admin_invoice_flag:
        if settings.admin_chat_id:
            try:
                amount_value = (obj.get("amount", {}) or {}).get("value")
                description = obj.get("description") or "—"
                text = (
                    "🧾 Админ-счёт оплачен\n"
                    f"Сумма: {amount_value or '0.00'} ₽\n"
                    f"Описание: {description}"
                )
                await bot.send_message(int(settings.admin_chat_id), text)
            except Exception:
                pass
        return {"ok": True}

    # ========== ОФФЛАЙН ЗАКАЗЫ (НОВОЕ) ==========
    offline_order_id_raw = metadata.get("offline_order_id")
    if offline_order_id_raw:
        try:
            order = (await db.execute(
                select(Order).where(Order.id == int(offline_order_id_raw))
            )).scalar_one_or_none()
            
            if not order:
                raise HTTPException(status_code=404, detail="offline order not found")
            
            if order.status == OrderStatus.PAID:
                return {"ok": True}
            
            # Получаем все покупки с данными доставки
            purchases = (await db.execute(
                select(Purchase).where(Purchase.order_id == order.id)
            )).scalars().all()
            
            if not purchases:
                logger.warning(f"No purchases found for offline order {order.id}")
            
            # Обновляем статус заказа
            order.status = OrderStatus.PAID
            await db.commit()
            
            # Отправляем уведомление пользователю
            if order.buyer_tg_id:
                try:
                    user_message = (
                        "✅ *Оплата получена!*\n\n"
                        f"📦 Заказ #{order.id} успешно оплачен\n"
                        f"💰 Сумма: `{order.amount_minor/100:.2f}` ₽\n\n"
                        "Администратор свяжется с вами в ближайшее время для уточнения деталей доставки."
                    )
                    await bot.send_message(
                        chat_id=int(order.buyer_tg_id),
                        text=user_message,
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(f"Failed to send confirmation to user: {e}")
            
            # Отправляем уведомление администратору с данными доставки
            if settings.admin_chat_id and purchases:
                try:
                    # Получаем товары
                    item_ids = [p.item_id for p in purchases if p.item_id]
                    items = (await db.execute(
                        select(Item).where(Item.id.in_(item_ids))
                    )).scalars().all()
                    
                    items_text = "\n".join([f"• {item.title} - {item.price_minor/100:.2f} ₽" for item in items])
                    
                    # Берём данные доставки из первой покупки (они одинаковые для всех товаров в заказе)
                    first_purchase = purchases[0]
                    
                    buyer_username = None
                    if order.buyer_tg_id:
                        buyer_username = (await db.execute(
                            select(User.username).where(User.tg_id == int(order.buyer_tg_id))
                        )).scalar_one_or_none()
                    
                    texts = load_texts().get("notifications", {})
                    template = texts.get("offline_order_paid") or (
                        "💳 ОФФЛАЙН ЗАКАЗ #{order_id} ОПЛАЧЕН\n\n"
                        "Товары:\n{items_text}\n\n"
                        "Сумма: {amount} ₽\n\n"
                        "📦 Данные доставки:\n"
                        "👤 ФИО: {fullname}\n"
                        "📞 Телефон: {phone}\n"
                        "📍 Адрес: {address}\n"
                        "💬 Комментарий: {comment}\n\n"
                        "👥 Покупатель: {buyer} {buyer_username}"
                    )
                    
                    message = template.format(
                        order_id=order.id,
                        items_text=items_text,
                        amount=f"{order.amount_minor/100:.2f}",
                        fullname=first_purchase.delivery_fullname or "—",
                        phone=first_purchase.delivery_phone or "—",
                        address=first_purchase.delivery_address or "—",
                        comment=first_purchase.delivery_comment or "—",
                        buyer=order.buyer_tg_id or "-",
                        buyer_username=(f"@{buyer_username}" if buyer_username else ""),
                    )
                    
                    await bot.send_message(
                        chat_id=int(settings.admin_chat_id),
                        text=message,
                        parse_mode="Markdown"
                    )
                    logger.info(f"Sent offline order paid notification to admin for order #{order.id}")
                except Exception as e:
                    logger.error(f"Failed to send offline order notification: {e}")
            
            return {"ok": True}
        
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Критическая ошибка обработки оффлайн заказа: {}", e)
            await db.rollback()
            raise HTTPException(status_code=500, detail="Internal server error")

    # ========== КОРЗИНА (цифровые товары) ==========
    cart_order_id_raw = metadata.get("cart_order_id")
    if cart_order_id_raw:
        try:
            order = (await db.execute(
                select(Order).where(Order.id == int(cart_order_id_raw))
            )).scalar_one_or_none()
            
            if not order:
                raise HTTPException(status_code=404, detail="cart order not found")
            
            if order.status == OrderStatus.PAID:
                return {"ok": True}
            
            purchases = (await db.execute(
                select(Purchase).where(Purchase.order_id == order.id)
            )).scalars().all()
            
            # Резервируем коды ДО изменения статуса заказа
            codes_to_deliver = []
            for purchase in purchases:
                item = (await db.execute(
                    select(Item).where(Item.id == purchase.item_id)
                )).scalar_one_or_none()
                
                if not item:
                    continue
                
                allocated_code: str | None = None
                if item.item_type == ItemType.DIGITAL and item.delivery_type == 'codes':
                    code_row = (await db.execute(
                        select(ItemCode)
                        .where(ItemCode.item_id == item.id, ItemCode.is_sold == False)
                        .limit(1)
                        .with_for_update(skip_locked=True)
                    )).scalars().first()
                    
                    if not code_row:
                        logger.error(
                            "Код закончился при обработке платежа | order_id={} item_id={}",
                            order.id, item.id
                        )
                        raise HTTPException(
                            status_code=500, 
                            detail=f"Item {item.title} out of stock"
                        )
                    
                    code_row.is_sold = True
                    code_row.sold_order_id = order.id
                    allocated_code = code_row.code
                
                codes_to_deliver.append((item, allocated_code))
            
            order.status = OrderStatus.PAID
            await db.commit()
            
            delivery = DeliveryService(bot)
            for item, code in codes_to_deliver:
                try:
                    if code:
                        text = f"<b>{code}</b>"
                        await bot.send_message(
                            int(order.buyer_tg_id), 
                            text, 
                            reply_markup=None, 
                            parse_mode="HTML"
                        )
                    await delivery.deliver(int(order.buyer_tg_id), item)
                except Exception as e:
                    logger.error(
                        "Ошибка доставки | order_id={} item={} error={}",
                        order.id, item.title, e
                    )
            
            if settings.admin_chat_id:
                try:
                    texts = load_texts().get("notifications", {})
                    template = texts.get("cart_paid") or (
                        "🛒 Оплата корзины получена\n"
                        "Товаров: {items_count}\nСумма: {amount} ₽\n"
                        "Покупатель: {buyer} {buyer_username}\nЗаказ: {order_id}"
                    )
                    buyer_username = None
                    if order.buyer_tg_id:
                        buyer_username = (await db.execute(
                            select(User.username).where(User.tg_id == int(order.buyer_tg_id))
                        )).scalar_one_or_none()
                    text = template.format(
                        items_count=len(purchases),
                        amount=f"{order.amount_minor/100:.2f}",
                        buyer=order.buyer_tg_id or "-",
                        buyer_username=(f"@{buyer_username}" if buyer_username else ""),
                        order_id=order.id,
                    )
                    await bot.send_message(int(settings.admin_chat_id), text)
                except Exception as e:
                    logger.error("Ошибка отправки уведомления админу: {}", e)
            
            return {"ok": True}
        
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Критическая ошибка обработки корзины: {}", e)
            await db.rollback()
            raise HTTPException(status_code=500, detail="Internal server error")
    
    # ========== ОБЫЧНЫЕ ЗАКАЗЫ (ОДИН ТОВАР) ==========
    payment_id = metadata.get("paymentId")
    if not payment_id:
        raise HTTPException(status_code=400, detail="paymentId missing")

    try:
        order = (await db.execute(
            select(Order).where(Order.id == int(payment_id))
        )).scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="order not found")

        if order.status == OrderStatus.PAID:
            return {"ok": True}

        order.status = OrderStatus.PAID

        item = (await db.execute(
            select(Item).where(Item.id == order.item_id)
        )).scalar_one_or_none()
        
        allocated_code: str | None = None
        if item:
            purchase = Purchase(
                order_id=order.id, 
                user_id=order.user_id, 
                item_id=item.id, 
                delivery_info=None
            )
            db.add(purchase)

            # ✅ Атомарная резервация кода
            if item.item_type == ItemType.DIGITAL and item.delivery_type == 'codes':
                code_row = (await db.execute(
                    select(ItemCode)
                    .where(ItemCode.item_id == item.id, ItemCode.is_sold == False)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )).scalars().first()
                
                if not code_row:
                    logger.error(
                        "Код закончился при обработке платежа | order_id={} item_id={}",
                        order.id, item.id
                    )
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Item {item.title} out of stock"
                    )
                
                code_row.is_sold = True
                code_row.sold_order_id = order.id
                allocated_code = code_row.code

        await db.commit()

        # ✅ Доставка вне транзакции
        if order.buyer_tg_id and item:
            delivery = DeliveryService(bot)
            try:
                if allocated_code:
                    text = f"<b>{allocated_code}</b>"
                    await bot.send_message(
                        int(order.buyer_tg_id), 
                        text, 
                        reply_markup=None, 
                        parse_mode="HTML"
                    )
                await delivery.deliver(int(order.buyer_tg_id), item)
            except Exception as e:
                logger.error(
                    "Ошибка доставки | order_id={} buyer={} error={}",
                    order.id, order.buyer_tg_id, e
                )

        # Уведомление админу
        if settings.admin_chat_id:
            try:
                texts = load_texts().get("notifications", {})
                template = texts.get("order_paid") or (
                    "💳 Оплата получена\n"
                    "Товар: {item}\nСумма: {amount} ₽\n"
                    "Покупатель: {buyer} {buyer_username}\nЗаказ: {order_id}"
                )
                buyer_username = None
                if order.buyer_tg_id:
                    buyer_username = (await db.execute(
                        select(User.username).where(User.tg_id == int(order.buyer_tg_id))
                    )).scalar_one_or_none()
                text = template.format(
                    item=item.title if item else "Донат",
                    amount=f"{order.amount_minor/100:.2f}",
                    buyer=order.buyer_tg_id or "-",
                    buyer_username=(f"@{buyer_username}" if buyer_username else ""),
                    order_id=order.id,
                )
                await bot.send_message(int(settings.admin_chat_id), text)
            except Exception as e:
                logger.error("Ошибка отправки уведомления админу: {}", e)

        return {"ok": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Критическая ошибка обработки платежа: {}", e)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
