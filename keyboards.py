from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from texts import DESIRE_DATA, ENCYCLOPEDIA, PACKAGES


def kb_desire() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, data in DESIRE_DATA.items():
        builder.button(text=data["label"], callback_data=f"desire:{key}")
    builder.adjust(2)
    return builder.as_markup()


def kb_final_offer() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, хочу свой браслет", callback_data="order:start")],
        [InlineKeyboardButton(text="💬 Задать вопрос мастеру", callback_data="master:contact")],
        [InlineKeyboardButton(text="📖 Узнать больше о камнях", callback_data="enc:menu")],
    ])


def kb_size() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📏 14–15 см (S)", callback_data="size:S"),
            InlineKeyboardButton(text="📏 16–17 см (M)", callback_data="size:M"),
        ],
        [
            InlineKeyboardButton(text="📏 18–19 см (L)", callback_data="size:L"),
            InlineKeyboardButton(text="🤔 Не знаю, помогите", callback_data="size:help"),
        ],
    ])


def kb_size_after_help() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📏 Беру S", callback_data="size:S"),
            InlineKeyboardButton(text="📏 Беру M", callback_data="size:M"),
            InlineKeyboardButton(text="📏 Беру L", callback_data="size:L"),
        ],
    ])


def kb_metal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Золото (тёплый)", callback_data="metal:gold")],
        [InlineKeyboardButton(text="🤍 Серебро (холодный)", callback_data="metal:silver")],
        [InlineKeyboardButton(text="💎 На ваш вкус — доверяю", callback_data="metal:choice")],
    ])


def kb_packages() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, data in PACKAGES.items():
        builder.button(
            text=f"{data['name']} — {data['price']:,} ₽".replace(",", " "),
            callback_data=f"pkg:{key}",
        )
    builder.button(text="💬 Хочу обсудить с мастером", callback_data="master:contact")
    builder.adjust(1)
    return builder.as_markup()


def kb_pay(price: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 Оплатить {price:,} ₽".replace(",", " "), callback_data="pay:show")],
        [InlineKeyboardButton(text="💬 Написать мастеру лично", callback_data="master:contact")],
    ])


def kb_retry_screenshot() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Отправить новый скриншот", callback_data="pay:retry")],
        [InlineKeyboardButton(text="💬 Написать мастеру лично", callback_data="master:contact")],
    ])


def kb_admin_verify(user_id: int, order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Подтвердить оплату",
            callback_data=f"admin:approve:{user_id}:{order_id}",
        )],
        [InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"admin:reject:{user_id}:{order_id}",
        )],
    ])


def kb_after_payment() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Жду фото камней", callback_data="noop")],
        [InlineKeyboardButton(text="💬 Написать мастеру", callback_data="master:contact")],
    ])


def kb_encyclopedia() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label, _ in ENCYCLOPEDIA:
        builder.button(text=label, callback_data=f"enc:{key}")
    builder.button(text="⬅️ Назад", callback_data="enc:back")
    builder.adjust(2)
    return builder.as_markup()


def kb_stone_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="enc:menu")],
    ])
