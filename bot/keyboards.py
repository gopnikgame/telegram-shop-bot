from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Set

from app.utils.texts import load_texts
from app.config import settings

def main_menu_kb(texts: dict, is_admin: bool = False, cart_count: int = 0) -> InlineKeyboardMarkup:
    b = texts["main_menu"]["buttons"]
    show_btns = texts["main_menu"].get("show_buttons", {})
    
    rows = []
    
    # Первая строка: Проекты, Товары, Услуги (в зависимости от настроек)
    row1 = []
    if show_btns.get("projects", False):
        row1.append(InlineKeyboardButton(text=b["projects"], callback_data="menu:projects"))
    if show_btns.get("products", True):
        row1.append(InlineKeyboardButton(text=b["products"], callback_data="menu:products"))
    if show_btns.get("services", True):
        row1.append(InlineKeyboardButton(text=b["services"], callback_data="menu:services"))
    
    if row1:
        # Если кнопок больше 2, разбиваем на строки по 2
        if len(row1) > 2:
            rows.append(row1[:2])
            rows.append(row1[2:])
        else:
            rows.append(row1)
    
    # Купленные товары
    if show_btns.get("purchased", True):
        rows.append([InlineKeyboardButton(text=b["purchased"], callback_data="menu:purchased")])
    
    # Корзина с количеством товаров
    if show_btns.get("cart", True):
        cart_text = b.get("cart", "🛒 Корзина")
        if cart_count > 0:
            cart_text = f"{cart_text} ({cart_count})"
        rows.append([InlineKeyboardButton(text=cart_text, callback_data="menu:cart")])
    
    # Донат (также проверяем настройки из env)
    if show_btns.get("donate", True) and settings.show_donate_button:
        rows.append([InlineKeyboardButton(text=b["donate"], callback_data="menu:donate")])
    
    # Администрирование
    if is_admin:
        rows.append([InlineKeyboardButton(text=b.get("admin", "🛠 Администрирование"), callback_data="menu:admin")])
    
    # Связаться (также проверяем настройки из env)
    if show_btns.get("contact", True) and settings.show_contact_button:
        if settings.admin_tg_username:
            rows.append([InlineKeyboardButton(text=b["contact"], url=f"https://t.me/{settings.admin_tg_username.lstrip('@')}")])
        else:
            rows.append([InlineKeyboardButton(text=b["contact"], callback_data="menu:contact")])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def back_kb(cb_data: str = "back:main") -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = [[InlineKeyboardButton(text=texts["buttons"]["back"], callback_data=cb_data)]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def items_list_kb(items: list, item_type: str, purchased_ids: set[int] | None = None, page: int = 1, total: int | None = None, page_size: int = 5) -> InlineKeyboardMarkup:
    texts = load_texts()
    purchased_ids = purchased_ids or set()
    # Create buttons for each item
    kb = []
    for item in items:
        title = item.title
        if item_type == "digital" and item.id in purchased_ids:
            title = f"{title} (✅ Уже куплено)"
        kb.append([InlineKeyboardButton(text=title, callback_data=f"item:{item.id}:{item_type}:{page}")])
    # Add back button
    # Pagination controls + Back in one row
    controls = [InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="back:main")]
    if total is not None:
        if page > 1:
            controls.append(InlineKeyboardButton(text="◀️", callback_data=f"list:{item_type}:{page-1}"))
        if page * page_size < total:
            controls.append(InlineKeyboardButton(text="▶️", callback_data=f"list:{item_type}:{page+1}"))
    if controls:
        kb.append(controls)
    return InlineKeyboardMarkup(inline_keyboard=kb)

def item_card_kb(item_id: int, item_type: str, purchased: bool = False, from_purchased: bool = False, page: int = 1, in_cart: bool = False) -> InlineKeyboardMarkup:
    texts = load_texts()
    rows = []
    back_cb = "back:purchased" if from_purchased else f"back:list:{item_type}:{page}"
    
    # Кнопки покупки всегда активны, независимо от статуса purchased
    # Кнопка "Купить сейчас"
    rows.append([InlineKeyboardButton(text=texts["buttons"].get("buy_now", "🛒 Купить сейчас"), callback_data=f"buy_one:{item_id}")])
    
    # Кнопка "Добавить в корзину" / "Убрать из корзины"
    if in_cart:
        rows.append([InlineKeyboardButton(text=texts["buttons"].get("remove_from_cart", "❌ Убрать из корзины"), callback_data=f"cart:remove:{item_id}")])
    else:
        rows.append([InlineKeyboardButton(text=texts["buttons"].get("add_to_cart", "➕ В корзину"), callback_data=f"cart:add:{item_id}")])
 
    rows.append([InlineKeyboardButton(text=texts["buttons"]["back"], callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_method_kb(item_id: int) -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = [
        [InlineKeyboardButton(text=texts["buttons"].get("buy", "Купить"), callback_data=f"buy_one:{item_id}")],
        [InlineKeyboardButton(text=texts["buttons"]["back"], callback_data=f"back:item:{item_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def main_menu_only_kb() -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = [[InlineKeyboardButton(text=texts["buttons"]["main_menu"], callback_data="back:main")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def payment_link_kb(url: str) -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = [
        [InlineKeyboardButton(text=texts["payment"]["buttons"]["pay"], url=url)],
        [InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="back:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def admin_menu_kb() -> InlineKeyboardMarkup:
    texts = load_texts()
    b = texts.get("admin", {}).get("buttons", {})
    kb = [
        [InlineKeyboardButton(text=b.get("create_invoice", "🧾 Создать счёт"), callback_data="admin:create_invoice")],
        [InlineKeyboardButton(text=load_texts()["buttons"]["back"], callback_data="back:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def donate_amounts_kb() -> InlineKeyboardMarkup:
    # Читаем суммы из env: формат "100,200,500"
    raw = settings.donate_amounts or "100,200,500"
    amounts = []
    try:
        amounts = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
    except Exception:
        amounts = [100, 200, 500]
    rows = []
    row = []
    for i, val in enumerate(amounts):
        row.append(InlineKeyboardButton(text=f"{val} ₽", callback_data=f"donate:set:{val}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="Ввести сумму", callback_data="donate:custom")])
    rows.append([InlineKeyboardButton(text=load_texts()["buttons"]["back"], callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def cart_kb(items_in_cart: list, total_price: int) -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = []
    
    for item in items_in_cart:
        kb.append([
            InlineKeyboardButton(
                text=f"❌ {item.title} - {item.price_minor/100:.2f} ₽",
                callback_data=f"cart:remove:{item.id}"
            )
        ])
    
    if items_in_cart:
        # Форматируем текст кнопки оплаты с подстановкой суммы
        checkout_text = texts["buttons"].get("checkout", "💳 Оплатить ({total} ₽)")
        checkout_text = checkout_text.format(total=f"{total_price/100:.2f}")
        
        kb.append([InlineKeyboardButton(
            text=checkout_text,
            callback_data="cart:checkout"
        )])
        kb.append([InlineKeyboardButton(
            text=texts["buttons"].get("clear_cart", "🗑 Очистить корзину"),
            callback_data="cart:clear"
        )])
    
    kb.append([InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def skip_kb(callback_data: str = "skip_comment") -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Пропустить'"""
    texts = load_texts()
    kb = [
        [InlineKeyboardButton(
            text=texts.get("buttons", {}).get("skip", "⏭ Пропустить"),
            callback_data=callback_data
        )],
        [InlineKeyboardButton(
            text=texts["buttons"]["back"],
            callback_data="back:main"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def order_confirmation_kb(order_id: str, is_pharmacy: bool=False) -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = []
    if is_pharmacy:
        kb.append([InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="menu:cart")])
    else:
        kb.append([InlineKeyboardButton(text="💰 Оплатить заказ", callback_data=f"pay:{order_id}")])
        kb.append([InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order:{order_id}")])
        kb.append([InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="menu:cart")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def offline_delivery_kb() -> InlineKeyboardMarkup:
    texts = load_texts()
    kb = [
        [InlineKeyboardButton(text=texts["buttons"].get("confirm", "✅ Подтвердить"), callback_data="order:confirm")],
        [InlineKeyboardButton(text=texts["buttons"]["back"], callback_data="menu:cart")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
