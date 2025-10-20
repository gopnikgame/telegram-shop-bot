"""
Обработчики донатов
"""
import logging
import contextlib
from pathlib import Path

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile, InputMediaPhoto
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.utils.texts import load_texts
from bot.keyboards import back_kb, payment_link_kb
from app.services.orders_client import OrdersClient

logger = logging.getLogger("shopbot")
router = Router()


class DonateStates(StatesGroup):
    waiting_for_amount = State()


@router.callback_query(F.data.startswith("donate:set:"))
async def donate_set_amount(call: CallbackQuery) -> None:
    """Установка фиксированной суммы доната"""
    _, _, amount = call.data.split(":")
    amount_int = int(amount)
    
    # Создаём донат сразу и показываем кнопку оплаты
    async with OrdersClient() as client:
        try:
            url = await client.create_order(None, call.from_user.id, amount_minor=amount_int * 100)
            try:
                texts = load_texts()
                thanks = texts.get("donate", {}).get("thanks", "Спасибо за поддержку!")
                if call.message.photo:
                    await call.message.edit_caption(caption=thanks, reply_markup=payment_link_kb(url))
                else:
                    await call.message.edit_text(text=thanks, reply_markup=payment_link_kb(url))
            except Exception:
                try:
                    thanks = load_texts().get("donate", {}).get("thanks", "Спасибо за поддержку!")
                    if call.message.photo:
                        await call.message.edit_caption(caption=thanks, reply_markup=payment_link_kb(url))
                    else:
                        await call.message.edit_text(text=thanks, reply_markup=payment_link_kb(url))
                except Exception:
                    await call.message.answer("Ссылка на оплату:", reply_markup=payment_link_kb(url))
        except Exception as e:
            logger.error(f"Failed to create donate order: {e}")
            await call.message.answer("Не удалось создать донат. Попробуйте позже.")
    await call.answer()


@router.callback_query(F.data == "donate:custom")
async def donate_custom_prompt(call: CallbackQuery, state: FSMContext) -> None:
    """Запрос пользовательской суммы доната"""
    donate_image = load_texts().get("donate", {}).get("image")
    image_exists = bool(donate_image and Path(donate_image).is_file())
    
    try:
        if call.message.photo:
            if image_exists:
                photo = FSInputFile(donate_image)
                await call.message.edit_media(
                    media=InputMediaPhoto(media=photo, caption="Введите сумму в рублях:"),
                    reply_markup=back_kb("menu:donate")
                )
            else:
                await call.message.edit_caption(
                    caption="Введите сумму в рублях:", 
                    reply_markup=back_kb("menu:donate")
                )
        else:
            if image_exists:
                photo = FSInputFile(donate_image)
                await call.message.answer_photo(
                    photo=photo, 
                    caption="Введите сумму в рублях:", 
                    reply_markup=back_kb("menu:donate")
                )
                await call.message.delete()
            else:
                await call.message.edit_text(
                    "Введите сумму в рублях:", 
                    reply_markup=back_kb("menu:donate")
                )
    except Exception:
        await call.message.answer("Введите сумму в рублях:", reply_markup=back_kb("menu:donate"))
        with contextlib.suppress(Exception):
            await call.message.delete()
    
    await state.set_state(DonateStates.waiting_for_amount)
    await call.answer()


@router.message(DonateStates.waiting_for_amount)
async def donate_custom_amount(message: Message, state: FSMContext) -> None:
    """Обработка пользовательской суммы доната"""
    text_val = (message.text or "").strip()
    
    if not text_val.isdigit() or int(text_val) <= 0:
        await message.answer("Некорректная сумма. Введите целое число больше 0.", reply_markup=back_kb("menu:donate"))
        return
    
    amount = int(text_val)
    
    # Создаём донат и сразу отдаём кнопку оплаты
    async with OrdersClient() as client:
        try:
            url = await client.create_order(None, message.from_user.id, amount_minor=amount * 100)
            thanks = load_texts().get("donate", {}).get("thanks", "Спасибо за поддержку!")
            await message.answer(thanks, reply_markup=payment_link_kb(url))
        except Exception as e:
            logger.error(f"Failed to create custom donate order: {e}")
            await message.answer("Не удалось создать донат. Попробуйте позже.")
    
    await state.clear()
