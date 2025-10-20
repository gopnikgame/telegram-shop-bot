"""
Обработчики административных функций
"""
import logging
import uuid
import contextlib

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.utils.texts import load_texts
from bot.keyboards import back_kb, payment_link_kb
from app.services.yookassa import YooKassaClient
from app.config import settings

logger = logging.getLogger("shopbot")
router = Router()


class AdminInvoiceStates(StatesGroup):
    waiting_for_description = State()
    waiting_for_amount = State()


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


@router.callback_query(F.data == "admin:create_invoice")
async def admin_create_invoice_start(call: CallbackQuery, state: FSMContext) -> None:
    """Начало создания счёта администратором"""
    if not _is_admin_user(call.from_user.id, call.from_user.username):
        await call.answer("Недоступно", show_alert=True)
        return
    
    prompt = load_texts().get("admin", {}).get("prompts", {}).get("description", "Введите описание платежа:")
    
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=prompt, reply_markup=back_kb("menu:admin"))
        else:
            await call.message.edit_text(text=prompt, reply_markup=back_kb("menu:admin"))
    except Exception:
        await call.message.answer(prompt, reply_markup=back_kb("menu:admin"))
        with contextlib.suppress(Exception):
            await call.message.delete()
    
    await state.set_state(AdminInvoiceStates.waiting_for_description)
    await call.answer()


@router.message(AdminInvoiceStates.waiting_for_description)
async def admin_invoice_capture_description(message: Message, state: FSMContext) -> None:
    """Обработка описания счёта"""
    if not _is_admin_user(message.from_user.id, message.from_user.username):
        await state.clear()
        return
    
    desc = (message.text or "").strip()
    await state.update_data(invoice_desc=desc)
    
    prompt = load_texts().get("admin", {}).get("prompts", {}).get("amount", "Введите сумму в рублях:")
    await message.answer(prompt, reply_markup=back_kb("menu:admin"))
    await state.set_state(AdminInvoiceStates.waiting_for_amount)


@router.message(AdminInvoiceStates.waiting_for_amount)
async def admin_invoice_capture_amount(message: Message, state: FSMContext) -> None:
    """Обработка суммы счёта и создание платежа"""
    if not _is_admin_user(message.from_user.id, message.from_user.username):
        await state.clear()
        return
    
    text_val = (message.text or "").strip().replace(" ", "")
    if not text_val.isdigit() or int(text_val) <= 0:
        await message.answer("Некорректная сумма. Введите целое число больше 0.", reply_markup=back_kb("menu:admin"))
        return
    
    amount_minor = int(text_val) * 100
    data = await state.get_data()
    description = data.get("invoice_desc") or "Счёт от администратора"
    
    # Создаем платёж через ЮKassa
    client = YooKassaClient()
    idem = str(uuid.uuid4())
    payment_id = f"admin:{message.from_user.id}:{idem}"
    
    try:
        resp = await client.create_payment(
            amount_minor=amount_minor,
            description=description,
            payment_id=payment_id,
            payment_method_type=None,
            metadata={"admin_invoice": True, "admin_tg_id": message.from_user.id},
            customer_email=None,
            idempotence_key=idem,
        )
        url = (resp or {}).get("confirmation", {}).get("confirmation_url")
        
        if not url:
            await message.answer("Не удалось получить ссылку на оплату. Попробуйте позже.")
        else:
            title = load_texts().get("admin", {}).get("result", {}).get("link_title", "Ссылка на оплату:")
            await message.answer(f"{title}\n{url}", reply_markup=payment_link_kb(url))
    except Exception as e:
        logger.error(f"Error creating admin invoice: {e}")
        await message.answer("Ошибка при создании счёта. Попробуйте позже.")
    finally:
        await client.close()
    
    await state.clear()
