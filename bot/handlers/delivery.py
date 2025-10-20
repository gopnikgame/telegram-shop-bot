"""
����������� ������� �������� ���������� �������

���� ������ ��������:
- ��������� ��� ����� ������ ��������
- ����������� ����� ������ (���, �������, �����, �����������)
- ����������� ������ "����������"
- ������� �������� ������� �������

TODO: ��������� �� bot/handlers.py:
1. class OfflineDeliveryStates(StatesGroup)
2. send_offline_order_to_admin()
3. has_offline_items()
4. cb_buy_direct() - � ������������ skip_kb("skip_fullname")
5. ����������� ������ "����������":
   - skip_fullname (�����)
   - skip_phone (�����)
   - skip_address (�����)  
   - skip_comment
6. ����������� ����� ������:
   - offline_capture_fullname - � ������������ skip_kb("skip_phone")
   - offline_capture_phone - � ������������ skip_kb("skip_address")
   - offline_capture_address - � ������������ skip_kb("skip_comment")
   - offline_capture_comment
7. ������� ���������:
   - process_quick_offline_purchase()
   - process_cart_offline_purchase()
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


# States ��� ����� ������ ��������
class OfflineDeliveryStates(StatesGroup):
    waiting_for_fullname = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_comment = State()


async def send_offline_order_to_admin(order_id: int, items: list, delivery_data: dict, bot) -> None:
    """�������� ����������� �������������� � ����� ������� ������"""
    if not settings.admin_chat_id:
        logger.warning("Admin chat ID not configured, skipping admin notification")
        return
    
    items_text = "\n".join([f"� {item.title} - {item.price_minor/100:.2f} ?" for item in items])
    total = sum(item.price_minor for item in items)
    
    message = (
        f"?? *����� ����� #{order_id}*\n\n"
        f"*������:*\n{items_text}\n\n"
        f"*�����:* `{total/100:.2f}` ?\n\n"
        f"?? *������ ��������:*\n"
        f"?? ���: {delivery_data.get('fullname', '�')}\n"
        f"?? �������: {delivery_data.get('phone', '�')}\n"
        f"?? �����: {delivery_data.get('address', '�')}\n"
    )
    
    if delivery_data.get('comment'):
        message += f"?? �����������: {delivery_data['comment']}\n"
    
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
    """������� ������� ������ ��������"""
    from app.services.orders_client import OrdersClient  # ��������� ������
    
    _, item_id, _ = call.data.split(":")
    item_id_int = int(item_id)
    
    # ��������� ��� ������
    async with AsyncSessionLocal() as db:
        item = (await db.execute(select(Item).where(Item.id == item_id_int))).scalar_one_or_none()
        if not item:
            await call.answer("����� �� ������", show_alert=True)
            return
        
        # ���� ��� ���������� ����� - ����������� ������ ��������
        if item.item_type == ItemType.OFFLINE:
            await state.update_data(
                quick_buy_item_id=item_id_int,
                total_amount=item.price_minor
            )
            
            texts = load_texts()
            prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
                "fullname", 
                "?? ������� ���� ��� ��� ��������:"
            )
            
            try:
                if call.message.photo:
                    await call.message.edit_caption(
                        caption=prompt,
                        reply_markup=skip_kb("skip_fullname")  # ? ����������
                    )
                else:
                    await call.message.edit_text(
                        text=prompt,
                        reply_markup=skip_kb("skip_fullname")  # ? ����������
                    )
            except Exception:
                await call.message.answer(prompt, reply_markup=skip_kb("skip_fullname"))  # ? ����������
            
            await state.set_state(OfflineDeliveryStates.waiting_for_fullname)
            await call.answer()
            return
    
    # ��� �������� ������� � ����� - ������ ����� �����
    async with OrdersClient() as client:
        try:
            url = await client.create_order(item_id_int, call.from_user.id)
            try:
                await call.message.edit_reply_markup(reply_markup=payment_link_kb(url))
            except Exception:
                try:
                    if call.message.photo:
                        await call.message.edit_caption(caption="��������� � ������:", reply_markup=payment_link_kb(url))
                    else:
                        await call.message.edit_text("��������� � ������:", reply_markup=payment_link_kb(url))
                except Exception:
                    await call.message.answer("������ �� ������:", reply_markup=payment_link_kb(url))
        except Exception:
            await call.message.answer("�� ������� ������� �����. ���������� �����.")
    await call.answer()


@router.callback_query(F.data == "skip_fullname", OfflineDeliveryStates.waiting_for_fullname)
async def skip_fullname(call: CallbackQuery, state: FSMContext) -> None:
    """������� ����� ���"""
    await state.update_data(delivery_fullname="")
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "phone",
        "?? ������� ����� �������� ��� �����:"
    )
    
    try:
        await call.message.edit_text(prompt, reply_markup=skip_kb("skip_phone"))
    except Exception:
        await call.message.answer(prompt, reply_markup=skip_kb("skip_phone"))
    
    await state.set_state(OfflineDeliveryStates.waiting_for_phone)
    await call.answer()


@router.callback_query(F.data == "skip_phone", OfflineDeliveryStates.waiting_for_phone)
async def skip_phone(call: CallbackQuery, state: FSMContext) -> None:
    """������� ����� ��������"""
    await state.update_data(delivery_phone="")
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "address",
        "?? ������� ����� ��������:"
    )
    
    try:
        await call.message.edit_text(prompt, reply_markup=skip_kb("skip_address"))
    except Exception:
        await call.message.answer(prompt, reply_markup=skip_kb("skip_address"))
    
    await state.set_state(OfflineDeliveryStates.waiting_for_address)
    await call.answer()


@router.callback_query(F.data == "skip_address", OfflineDeliveryStates.waiting_for_address)
async def skip_address(call: CallbackQuery, state: FSMContext) -> None:
    """������� ����� ������"""
    await state.update_data(delivery_address="")
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "comment",
        "?? ������� ����������� � ������ (��� ������� '����������'):"
    )
    
    try:
        await call.message.edit_text(prompt, reply_markup=skip_kb("skip_comment"))
    except Exception:
        await call.message.answer(prompt, reply_markup=skip_kb("skip_comment"))
    
    await state.set_state(OfflineDeliveryStates.waiting_for_comment)
    await call.answer()


@router.callback_query(F.data == "skip_comment", OfflineDeliveryStates.waiting_for_comment)
async def skip_comment(call: CallbackQuery, state: FSMContext) -> None:
    """������� ����� �����������"""
    await state.update_data(delivery_comment="")
    
    data = await state.get_data()
    quick_buy_item_id = data.get("quick_buy_item_id")
    
    if quick_buy_item_id:
        await process_quick_offline_purchase(call.message, state, data, quick_buy_item_id)
    else:
        await process_cart_offline_purchase(call.message, state, data)
    
    await state.clear()
    await call.answer()


@router.message(OfflineDeliveryStates.waiting_for_fullname)
async def offline_capture_fullname(message: Message, state: FSMContext) -> None:
    """��������� ����� ���"""
    fullname = (message.text or "").strip()
    
    if not fullname or len(fullname) < 2:
        await message.answer("? ����������, ������� ���������� ���")
        return
    
    await state.update_data(delivery_fullname=fullname)
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "phone",
        "?? ������� ����� �������� ��� �����:"
    )
    
    await message.answer(prompt, reply_markup=skip_kb("skip_phone"))  # ? ����������
    await state.set_state(OfflineDeliveryStates.waiting_for_phone)


@router.message(OfflineDeliveryStates.waiting_for_phone)
async def offline_capture_phone(message: Message, state: FSMContext) -> None:
    """��������� ����� ��������"""
    phone = (message.text or "").strip()
    
    phone_digits = ''.join(filter(str.isdigit, phone))
    if len(phone_digits) < 10:
        await message.answer("? ����������, ������� ���������� ����� �������� (������� 10 ����)")
        return
    
    await state.update_data(delivery_phone=phone)
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "address",
        "?? ������� ����� ��������:"
    )
    
    await message.answer(prompt, reply_markup=skip_kb("skip_address"))  # ? ����������
    await state.set_state(OfflineDeliveryStates.waiting_for_address)


@router.message(OfflineDeliveryStates.waiting_for_address)
async def offline_capture_address(message: Message, state: FSMContext) -> None:
    """��������� ����� ������"""
    address = (message.text or "").strip()
    
    if not address or len(address) < 3:
        await message.answer("? ����������, ������� ���������� ����� ��������")
        return
    
    await state.update_data(delivery_address=address)
    
    texts = load_texts()
    prompt = texts.get("offline_delivery", {}).get("prompts", {}).get(
        "comment",
        "?? ������� ����������� � ������ (��� ������� '����������'):",
    )
    
    await message.answer(prompt, reply_markup=skip_kb("skip_comment"))  # ? ����������
    await state.set_state(OfflineDeliveryStates.waiting_for_comment)


@router.message(OfflineDeliveryStates.waiting_for_comment)
async def offline_capture_comment(message: Message, state: FSMContext) -> None:
    """��������� ����� �����������"""
    comment = (message.text or "").strip()
    
    await state.update_data(delivery_comment=comment)
    
    data = await state.get_data()
    
    # ����������: ������� ������� ��� �������
    quick_buy_item_id = data.get("quick_buy_item_id")
    
    if quick_buy_item_id:
        # ������� ������� ������ ������
        await process_quick_offline_purchase(message, state, data, quick_buy_item_id)
    else:
        # �������
        await process_cart_offline_purchase(message, state, data)
    
    await state.clear()


async def process_quick_offline_purchase(message: Message, state: FSMContext, data: dict, item_id: int) -> None:
    """��������� ������� ������� ����������� ������"""
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
        if not user:
            await message.answer("������������ �� ������")
            return
        
        item = (await db.execute(select(Item).where(Item.id == item_id))).scalar_one_or_none()
        if not item:
            await message.answer("����� �� ������")
            return
        
        # ������� �����
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
        
        # ������� ������� � ������� ��������
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
        
        # ������� ����� ����� YooKassa
        client = YooKassaClient()
        try:
            idem = str(uuid.uuid4())
            templates = load_texts().get("payment", {}).get("description_templates", {})
            description = (templates.get("offline") or "������: {title} | ����� {order_id}").format(
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
                await message.answer("�� ������� ������� �����. ���������� �����.")
                return
            
            order.fk_order_id = resp.get("id")
            order.fk_payment_url = url
            order.status = OrderStatus.PENDING
            
            await db.commit()
            
            await message.answer("? ������ ���������. ��������� � ������:", reply_markup=payment_link_kb(url))
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating offline order: {e}")
            await message.answer("�� ������� ������� �����. ���������� �����.")
        finally:
            await client.close()


async def process_cart_offline_purchase(message: Message, state: FSMContext, data: dict) -> None:
    """��������� ������ ������� � ����������� ��������"""
    cart_items = data.get("cart_items")
    total_amount = data.get("total_amount", 0)
    
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.tg_id == message.from_user.id))).scalar_one_or_none()
        if not user:
            await message.answer("������������ �� ������")
            return
        
        # ������� �����
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
        
        # ������ ������� � ������� ��������
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
        
        # ������ ����� ����� YooKassa
        client = YooKassaClient()
        try:
            idem = str(uuid.uuid4())
            templates = load_texts().get("payment", {}).get("description_templates", {})
            description = (templates.get("cart") or "������ ������� | ����� {order_id}").format(order_id=order.id)
            
            items = (await db.execute(select(Item).where(Item.id.in_(cart_items)))).scalars().all()
            
            resp = await client.create_payment(
                amount_minor=total_amount,
                description=description,
                payment_id=f"offline_cart:{order.id}",
                payment_method_type=None,
                metadata={"offline_order_id": str(order.id), "item_ids": ",".join(str(i.id) for i in items)},
                customer_email=f"{message.from_user.id}@{settings.email_domain}",
                idempotence_key=idem,
            )
            
            url = (resp or {}).get("confirmation", {}).get("confirmation_url")
            if not url:
                await db.rollback()
                await message.answer("�� ������� ������� �����. ���������� �����.")
                return
            
            order.fk_order_id = resp.get("id")
            order.fk_payment_url = url
            order.status = OrderStatus.PENDING
            
            await db.commit()
            
            # ������� ������� ����� ��������� �������� ������
            await db.execute(delete(CartItem).where(CartItem.user_id == user.id))
            await db.commit()
            
            await message.answer("? ������ ���������. ��������� � ������:", reply_markup=payment_link_kb(url))
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating cart offline order: {e}")
            await message.answer("�� ������� ������� �����. ���������� �����.")
        finally:
            await client.close()
