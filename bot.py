import asyncio
import logging
import ssl
import certifi
import aiohttp

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, ErrorEvent

import config
from database import init_db, save_user, create_order, set_order_status
from keyboards import (
    kb_desire, kb_final_offer, kb_size, kb_size_after_help,
    kb_metal, kb_packages, kb_pay, kb_after_payment,
    kb_admin_verify, kb_retry_screenshot, kb_encyclopedia, kb_stone_back,
)
from numerology import parse_date, soul_number, destiny_number
from states import Flow, Encyclopedia
from texts import NUMBER_DATA, DESIRE_DATA, ENCYCLOPEDIA, PACKAGES, resolve_desire_stone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

router = Router()
storage = MemoryStorage()

METAL_LABELS = {"gold": "Золото ✨", "silver": "Серебро 🤍", "choice": "На ваш вкус 💎"}

DELIVERY_COST = 350
FREE_DELIVERY_FROM = 5000


class ProxySession(AiohttpSession):
    async def create_session(self) -> aiohttp.ClientSession:
        if self._should_reset_connector:
            await self.close()
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(
                    ssl=ssl.create_default_context(cafile=certifi.where()),
                    limit=100,
                    ttl_dns_cache=3600,
                ),
                headers={"User-Agent": "aiogram"},
                trust_env=True,
            )
            self._should_reset_connector = False
        return self._session


def calc_total(pkg_price: int) -> tuple[int, int]:
    delivery = 0 if pkg_price >= FREE_DELIVERY_FROM else DELIVERY_COST
    return delivery, pkg_price + delivery


async def notify_admin(bot: Bot, text: str) -> None:
    if config.ADMIN_ID:
        try:
            await bot.send_message(config.ADMIN_ID, text, parse_mode="HTML")
        except Exception as e:
            log.warning("Admin notify failed: %s", e)


def _number_message(label: str, num: int) -> str:
    d = NUMBER_DATA[num]
    return f"<b>{d['title']}</b>\n\n{d['text']}\n\n{d['stone_text']}"


def _final_offer_text(soul_stone: str, destiny_stone: str, desire_stone: str) -> str:
    if soul_stone == destiny_stone:
        stones_line = (
            f"Твои числа Души и Судьбы совпадают — оба указывают на <b>{soul_stone}</b>. "
            "Это особенно мощный сигнал.\n"
            f"А прямо сейчас тебе нужен <b>{desire_stone}</b>."
        )
    else:
        stones_line = (
            f"Твоя <b>Душа</b> звучит через <b>{soul_stone}</b>.\n"
            f"Твоя <b>Судьба</b> ведёт тебя через <b>{destiny_stone}</b>.\n"
            f"А прямо сейчас тебе нужен <b>{desire_stone}</b>."
        )
    return (
        "Ну вот, родная, теперь ты знаешь свои камни ✨\n\n"
        + stones_line + "\n\n"
        "Эти камни — не случайность. Это твоя личная формула, рассчитанная по древним соответствиям. "
        "И они работают в связке — усиливая друг друга.\n\n"
        "🌿 Я собираю авторские браслеты-обереги именно по такой формуле — под твою дату рождения.\n\n"
        "Это не «украшение из магазина». Это личный амулет, собранный под твой запрос. "
        "Он носится годами и становится твоим спутником.\n\n"
        "<b>Хочешь, я соберу твой браслет?</b> 💞"
    )


def _order_summary(data: dict) -> str:
    pkg = PACKAGES[data["package"]]
    size_label = {"S": "14–15 см (S)", "M": "16–17 см (M)", "L": "18–19 см (L)"}[data["size"]]
    delivery_cost, total = calc_total(pkg["price"])
    delivery_str = "бесплатно" if delivery_cost == 0 else f"{delivery_cost} ₽"
    return (
        f"💎 Камни: <b>{data['stone1']}</b> + <b>{data['stone2']}</b> + <b>{data['stone3']}</b>\n"
        f"📏 Размер: {size_label}\n"
        f"✨ Фурнитура: {METAL_LABELS[data['metal']]}\n"
        f"🌙 Намерение: «{data['intention']}»\n"
        f"📦 Пакет: {pkg['name']} — {pkg['price']:,} ₽\n"
        f"🚚 Доставка: {delivery_str}\n"
        f"💰 <b>Итого: {total:,} ₽</b>"
    ).replace(",", " ")


def _payment_text(price: int) -> str:
    return (
        f"💳 <b>Реквизиты для оплаты:</b>\n\n"
        f"Карта ({config.BANK_NAME}): <code>{config.CARD_NUMBER}</code>\n"
        f"СБП: <code>{config.PHONE_SBP}</code>\n"
        f"Получатель: {config.RECIPIENT_NAME}\n\n"
        f"Сумма: <b>{price:,} ₽</b>\n\n"
    ).replace(",", " ")


@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext) -> None:
    await state.clear()
    await save_user(msg.from_user.id, msg.from_user.username, msg.from_user.full_name)
    await msg.answer(
        "Привет, родная! Я — Татьяна Бредня — проводник в мир камней ✨\n\n"
        "Сейчас я рассчитаю для тебя три твоих числа — Душу, Судьбу и Желание. "
        "И подберу три камня, которые работают именно на твою энергию.\n\n"
        "Это не гадание и не магия. Это древнее знание о том, как дата рождения "
        "связана с минералами земли. Камень, подобранный по числу — носится годами "
        "и становится твоим личным талисманом 💎\n\n"
        "Готова? Введи свою дату рождения в формате <b>ДД.ММ.ГГГГ</b>\n"
        "<i>Например: 15.08.1990</i>",
        parse_mode="HTML",
    )
    await state.set_state(Flow.waiting_birthdate)


@router.message(Flow.waiting_birthdate)
async def handle_birthdate(msg: Message, state: FSMContext) -> None:
    try:
        day, month, year = parse_date(msg.text or "")
    except ValueError:
        await msg.answer(
            "Не могу разобрать дату 🙈\n\n"
            "Пожалуйста, введи в формате <b>ДД.ММ.ГГГГ</b>\n"
            "<i>Например: 15.08.1990</i>",
            parse_mode="HTML",
        )
        return

    birth_str = f"{day:02d}.{month:02d}.{year}"
    sn = soul_number(day)
    dn = destiny_number(day, month, year)
    soul_stone = NUMBER_DATA[sn]["stone_name"]
    destiny_stone = NUMBER_DATA[dn]["stone_name"]

    await state.update_data(
        birth_date=birth_str,
        soul_number=sn,
        destiny_number=dn,
        soul_stone=soul_stone,
        destiny_stone=destiny_stone,
    )
    await save_user(
        msg.from_user.id, msg.from_user.username, msg.from_user.full_name,
        birth_date=birth_str, soul_number=sn, destiny_number=dn,
        soul_stone=soul_stone, destiny_stone=destiny_stone,
    )

    calc_msg = await msg.answer("Считаю твои числа... ✨")
    await asyncio.sleep(1.2)
    await calc_msg.edit_text("Открываю древнюю таблицу соответствий... 🔮")
    await asyncio.sleep(1.2)
    await calc_msg.edit_text("Готово! Сейчас расскажу всё по порядку.")
    await asyncio.sleep(0.8)

    await msg.answer(
        f"<b>🌙 Твоё Число Души — {sn}</b>\n\n" + _number_message("Душа", sn),
        parse_mode="HTML",
    )
    await asyncio.sleep(1.0)

    if dn == sn:
        await msg.answer(
            f"<b>⭐ Твоё Число Судьбы — тоже {dn}</b>\n\n"
            "Это очень редкое совпадение ✨ Когда Душа и Судьба резонируют на одном числе — "
            "это знак цельности: ты живёшь в согласии со своей природой. "
            "Оба твоих числа усиливают друг друга и один и тот же камень.",
            parse_mode="HTML",
        )
    else:
        await msg.answer(
            f"<b>⭐ Твоё Число Судьбы — {dn}</b>\n\n" + _number_message("Судьба", dn),
            parse_mode="HTML",
        )
    await asyncio.sleep(1.0)

    await msg.answer(
        "А теперь — самое интересное.\n\n"
        "У каждой из нас есть актуальный запрос — то, что нужно прямо сейчас. "
        "Выбери, что для тебя важнее всего в этот период жизни, "
        "и я подберу третий камень — камень-исполнитель 💎",
        reply_markup=kb_desire(),
    )
    await state.set_state(Flow.waiting_desire)


@router.callback_query(Flow.waiting_desire, F.data.startswith("desire:"))
async def handle_desire(call: CallbackQuery, state: FSMContext) -> None:
    desire_key = call.data.split(":")[1]
    if desire_key not in DESIRE_DATA:
        await call.answer()
        return

    data = await state.get_data()
    stone_name, stone_text = resolve_desire_stone(
        desire_key, data["soul_stone"], data["destiny_stone"]
    )

    await state.update_data(desire_key=desire_key, desire_stone=stone_name)
    await save_user(
        call.from_user.id, call.from_user.username, call.from_user.full_name,
        desire_key=desire_key, desire_stone=stone_name,
    )

    await call.message.edit_reply_markup()
    await call.message.answer(stone_text, parse_mode="HTML")
    await asyncio.sleep(0.8)

    await call.message.answer(
        _final_offer_text(data["soul_stone"], data["destiny_stone"], stone_name),
        parse_mode="HTML",
        reply_markup=kb_final_offer(),
    )
    await state.set_state(Flow.waiting_bracelet_decision)
    await call.answer()


@router.callback_query(Flow.waiting_bracelet_decision, F.data == "order:start")
async def order_start(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.edit_reply_markup()
    await call.message.answer(
        "Какая ты молодец, что прислушалась к себе 💞\n\n"
        "Я уже вижу твой браслет — он будет особенным. "
        "Каждый браслет я делаю вручную, под конкретного человека. "
        "Это не конвейер — это маленький ритуал. "
        "Камни перебираются, очищаются, нанизываются под твоё имя и дату рождения 🌙\n\n"
        "Готова? Тогда поехали.\n\n"
        "<b>Вопрос 1. Размер запястья</b>\n\n"
        "Как измерить: возьми сантиметровую ленту (или нитку + линейку) "
        "и оберни запястье в самом узком месте. Прибавь 1–1,5 см на свободу.",
        parse_mode="HTML",
        reply_markup=kb_size(),
    )
    await state.set_state(Flow.waiting_size)
    await call.answer()


@router.callback_query(F.data == "master:contact")
async def master_contact(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.answer(
        f"Напиши мне напрямую — отвечу на все вопросы 💞\n\n"
        f"👉 {config.MASTER_USERNAME}"
    )


@router.callback_query(Flow.waiting_size, F.data == "size:help")
async def size_help(call: CallbackQuery) -> None:
    await call.message.edit_reply_markup()
    await call.message.answer(
        "Не переживай, это частая история 💗\n\n"
        "Средний женский размер — 16–17 см (M). "
        "Если ты миниатюрная и носишь кольца до 16-го размера — бери S. "
        "Если запястье крупнее или ты любишь свободную посадку — L.\n\n"
        "В любом случае, я делаю браслет на резинке-стрейч, "
        "так что небольшая погрешность не критична. "
        "А если совсем не подойдёт — переделаю бесплатно, такое у меня правило 🌿",
        reply_markup=kb_size_after_help(),
    )
    await call.answer()


@router.callback_query(Flow.waiting_size, F.data.startswith("size:"))
async def handle_size(call: CallbackQuery, state: FSMContext) -> None:
    size = call.data.split(":")[1]
    if size == "help":
        return
    await state.update_data(size=size)
    await call.message.edit_reply_markup()
    await call.message.answer(
        "<b>Вопрос 2. Цвет фурнитуры</b>\n\n"
        "Между камнями я добавляю маленькие разделители-бусины. "
        "Какой металл тебе ближе?",
        parse_mode="HTML",
        reply_markup=kb_metal(),
    )
    await state.set_state(Flow.waiting_metal)
    await call.answer()


@router.callback_query(Flow.waiting_metal, F.data.startswith("metal:"))
async def handle_metal(call: CallbackQuery, state: FSMContext) -> None:
    metal = call.data.split(":")[1]
    await state.update_data(metal=metal)
    await call.message.edit_reply_markup()
    await call.message.answer(
        "<b>Вопрос 3. Пожелание / намерение</b>\n\n"
        "Когда я собираю браслет, я держу в голове твоё пожелание. "
        "Это не магия — это внимание. Камень, собранный с намерением, носится иначе.\n\n"
        "Напиши одной фразой — что ты хочешь, чтобы пришло в твою жизнь?\n\n"
        "<i>Например: «спокойствие в семье», «новая работа», "
        "«встретить своего человека», «вернуть себе силы»</i>\n\n"
        "Можно очень коротко. Я услышу 💞",
        parse_mode="HTML",
    )
    await state.set_state(Flow.waiting_intention)
    await call.answer()


@router.message(Flow.waiting_intention)
async def handle_intention(msg: Message, state: FSMContext) -> None:
    intention = (msg.text or "").strip()
    if not intention:
        await msg.answer("Напиши своё пожелание — одной фразой 💞")
        return

    fsm = await state.get_data()
    await state.update_data(
        intention=intention,
        stone1=fsm["soul_stone"],
        stone2=fsm["destiny_stone"],
        stone3=fsm["desire_stone"],
    )
    fsm = await state.get_data()

    pkg_lines = "\n\n".join(
        f"<b>{d['name']} — {d['price']:,} ₽</b>\n{d['description']}".replace(",", " ")
        for d in PACKAGES.values()
    )

    size_label = {"S": "14–15 см (S)", "M": "16–17 см (M)", "L": "18–19 см (L)"}[fsm["size"]]
    await msg.answer(
        f"Записала ✨\n\n"
        f"<b>Итак, твой браслет:</b>\n\n"
        f"💎 Камни: {fsm['soul_stone']} + {fsm['destiny_stone']} + {fsm['desire_stone']}\n"
        f"📏 Размер: {size_label}\n"
        f"✨ Фурнитура: {METAL_LABELS[fsm['metal']]}\n"
        f"🌙 Намерение: «{intention}»\n\n"
        f"У меня есть три варианта сборки — выбирай, какой откликается:\n\n"
        + pkg_lines,
        parse_mode="HTML",
        reply_markup=kb_packages(),
    )
    await state.set_state(Flow.waiting_package)


@router.callback_query(Flow.waiting_package, F.data.startswith("pkg:"))
async def handle_package(call: CallbackQuery, state: FSMContext) -> None:
    pkg_key = call.data.split(":")[1]
    if pkg_key not in PACKAGES:
        await call.answer()
        return

    pkg = PACKAGES[pkg_key]
    await state.update_data(package=pkg_key)
    await call.message.edit_reply_markup()
    await call.message.answer(
        f"Прекрасный выбор 💞\n\n"
        f"Выбран пакет: <b>{pkg['name']} — {pkg['price']:,} ₽</b>\n\n"
        "Что дальше:\n"
        "1️⃣ Оплачиваешь по реквизитам (карта или СБП — на выбор)\n"
        "2️⃣ Я начинаю собирать твой браслет в течение 24 часов\n"
        "3️⃣ Готовность — 3–5 дней\n"
        "4️⃣ Отправляю Почтой / СДЭКом / Boxberry\n\n"
        "📦 Доставка по России — 350 ₽, от 5 000 ₽ — в подарок.\n\n"
        "Напиши, пожалуйста, <b>адрес доставки</b> 📬\n"
        "<i>(Город, улица, дом, квартира, индекс, ФИО получателя)</i>",
        parse_mode="HTML",
    )
    await state.set_state(Flow.waiting_address)
    await call.answer()


@router.message(Flow.waiting_address)
async def handle_address(msg: Message, state: FSMContext) -> None:
    address = (msg.text or "").strip()
    if len(address) < 10:
        await msg.answer(
            "Пожалуйста, напиши полный адрес 📬\n"
            "<i>(Город, улица, дом, квартира, индекс, ФИО получателя)</i>",
            parse_mode="HTML",
        )
        return

    await state.update_data(address=address)
    fsm = await state.get_data()
    pkg = PACKAGES[fsm["package"]]
    _, total = calc_total(pkg["price"])

    order_id = await create_order(
        msg.from_user.id,
        stone1=fsm["stone1"],
        stone2=fsm["stone2"],
        stone3=fsm["stone3"],
        size=fsm["size"],
        metal=fsm["metal"],
        intention=fsm["intention"],
        package=fsm["package"],
        price=total,
        address=address,
    )
    await state.update_data(order_id=order_id, total_price=total)

    await msg.answer(
        f"Адрес сохранила 📦\n\n"
        + _order_summary({**fsm, "address": address}) + "\n\n"
        "🎁 К каждому браслету кладу карточку с описанием твоих камней "
        "и короткую инструкцию по уходу.\n\n"
        "Нажми кнопку ниже — отправлю реквизиты для оплаты 👇",
        parse_mode="HTML",
        reply_markup=kb_pay(total),
    )
    await state.set_state(Flow.waiting_payment)


@router.callback_query(Flow.waiting_payment, F.data == "pay:show")
async def pay_show(call: CallbackQuery, state: FSMContext) -> None:
    fsm = await state.get_data()
    total = fsm.get("total_price") or calc_total(PACKAGES[fsm["package"]]["price"])[1]

    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await call.message.answer(
        _payment_text(total) + "\n\n"
        "📸 После оплаты пришли <b>скриншот чека</b> прямо сюда — "
        "я проверю и подтвержу в течение нескольких минут.",
        parse_mode="HTML",
    )
    await state.set_state(Flow.waiting_screenshot)
    await call.answer()


@router.message(Flow.waiting_screenshot, F.photo)
async def handle_screenshot(msg: Message, state: FSMContext, bot: Bot) -> None:
    fsm = await state.get_data()
    pkg = PACKAGES.get(fsm.get("package", "basic"), PACKAGES["basic"])
    order_id = fsm.get("order_id", 0)

    await msg.answer(
        "Скриншот получен! 📸\n\n"
        "Проверяю оплату — обычно это занимает несколько минут. "
        "Как только подтвержу — сразу напишу тебе 💞"
    )

    if config.ADMIN_ID:
        caption = (
            f"🧾 <b>Скриншот оплаты — заказ #{order_id}</b>\n\n"
            f"👤 @{msg.from_user.username or '—'} "
            f"(id: <code>{msg.from_user.id}</code>)\n"
            f"💎 Камни: {fsm.get('stone1')} + {fsm.get('stone2')} + {fsm.get('stone3')}\n"
            f"📏 Размер: {fsm.get('size')}\n"
            f"✨ Фурнитура: {METAL_LABELS.get(fsm.get('metal', ''), '—')}\n"
            f"🌙 Намерение: «{fsm.get('intention')}»\n"
            f"📦 Пакет: {pkg['name']} — {pkg['price']:,} ₽\n"
            f"🏠 Адрес: {fsm.get('address')}\n"
            f"📅 Дата рождения: {fsm.get('birth_date')}"
        ).replace(",", " ")

        try:
            await bot.send_photo(
                chat_id=config.ADMIN_ID,
                photo=msg.photo[-1].file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb_admin_verify(msg.from_user.id, order_id),
            )
        except Exception as e:
            log.warning("Не удалось отправить скриншот админу: %s", e)
    else:
        await set_order_status(order_id, "paid")
        await msg.answer(
            "Оплата подтверждена! 🌿✨\n\n"
            "📦 Начинаю собирать твой браслет. Отправлю в течение 3–5 дней.",
            reply_markup=kb_after_payment(),
        )

    await state.set_state(Flow.waiting_admin_review)


@router.message(Flow.waiting_admin_review)
async def handle_review_pending(msg: Message) -> None:
    await msg.answer(
        "Скриншот уже отправлен на проверку 📸\n"
        "Ожидай подтверждения — обычно это несколько минут 💞"
    )


@router.callback_query(Flow.waiting_admin_review, F.data == "pay:retry")
async def pay_retry(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    fsm = await state.get_data()
    total = fsm.get("total_price", 0)
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.message.answer(
        _payment_text(total) + "\n\n"
        "📸 Пришли новый скриншот чека прямо сюда — как фотографию 👇",
        parse_mode="HTML",
    )
    await state.set_state(Flow.waiting_screenshot)


@router.message(Flow.waiting_screenshot)
async def handle_screenshot_wrong(msg: Message) -> None:
    await msg.answer(
        "Пожалуйста, пришли именно <b>фото</b> скриншота чека 📸\n\n"
        "Сделай скриншот в банковском приложении и отправь его сюда как фотографию.",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin:approve:"))
async def admin_approve(call: CallbackQuery, bot: Bot) -> None:
    await call.answer("Оплата подтверждена ✅")
    parts = call.data.split(":")
    user_id, order_id = int(parts[2]), int(parts[3])

    await set_order_status(order_id, "paid")

    key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
    user_fsm = FSMContext(storage=storage, key=key)
    await user_fsm.clear()

    try:
        await bot.send_message(
            user_id,
            "Оплата подтверждена, родная! 🌿✨\n\n"
            "📩 В течение 24 часов пришлю тебе фото камней, "
            "которые отобрала для тебя — чтобы ты увидела свой будущий браслет ещё до сборки.\n\n"
            "📦 Готовый браслет улетит к тебе через 3–5 дней.\n\n"
            "А пока — сохрани этот чат, я напишу тебе сама. "
            "И если будут вопросы — пиши, я всегда на связи 💞",
            reply_markup=kb_after_payment(),
        )
    except Exception as e:
        log.warning("Не удалось уведомить пользователя: %s", e)

    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.message.answer(f"✅ Заказ #{order_id} подтверждён, пользователь уведомлён.")


@router.callback_query(F.data.startswith("admin:reject:"))
async def admin_reject(call: CallbackQuery, bot: Bot) -> None:
    await call.answer("Оплата отклонена ❌")
    parts = call.data.split(":")
    user_id, order_id = int(parts[2]), int(parts[3])

    await set_order_status(order_id, "rejected")

    try:
        await bot.send_message(
            user_id,
            "Не смогла подтвердить оплату по этому скриншоту 🙈\n\n"
            "Возможно, что-то пошло не так с переводом. "
            "Пришли новый скриншот — или напиши мастеру напрямую, разберёмся вместе 💞",
            reply_markup=kb_retry_screenshot(),
        )
    except Exception as e:
        log.warning("Не удалось уведомить пользователя: %s", e)

    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await call.message.answer(f"❌ Заказ #{order_id} отклонён, пользователь уведомлён.")


ENC_MAP = {key: (label, text) for key, label, text in ENCYCLOPEDIA}


@router.callback_query(F.data == "enc:menu")
async def enc_menu(call: CallbackQuery, state: FSMContext) -> None:
    current = await state.get_state()
    if current != Encyclopedia.stone.state and current != Encyclopedia.menu.state:
        await state.update_data(_pre_enc_state=current)

    await call.message.answer(
        "Выбери камень, о котором хочешь узнать больше ✨",
        reply_markup=kb_encyclopedia(),
    )
    await state.set_state(Encyclopedia.menu)
    await call.answer()


@router.callback_query(Encyclopedia.menu, F.data.startswith("enc:"))
async def enc_stone(call: CallbackQuery, state: FSMContext) -> None:
    key = call.data.split(":")[1]

    if key == "back":
        await call.message.answer(
            "Возвращаемся к твоему предложению 💎\n\n"
            "Хочешь, я соберу твой браслет? 💞",
            reply_markup=kb_final_offer(),
        )
        fsm = await state.get_data()
        prev = fsm.get("_pre_enc_state", Flow.waiting_bracelet_decision.state)
        await state.set_state(prev)
        await call.answer()
        return

    if key == "menu":
        await enc_menu(call, state)
        return

    if key not in ENC_MAP:
        await call.answer()
        return

    _, text = ENC_MAP[key]
    await call.message.answer(text, parse_mode="HTML", reply_markup=kb_stone_back())
    await state.set_state(Encyclopedia.stone)
    await call.answer()


@router.callback_query(Encyclopedia.stone, F.data == "enc:menu")
async def enc_back_to_menu(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.answer(
        "Выбери камень, о котором хочешь узнать больше ✨",
        reply_markup=kb_encyclopedia(),
    )
    await state.set_state(Encyclopedia.menu)
    await call.answer()


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery) -> None:
    await call.answer("Ждём вместе! 💞")


@router.callback_query()
async def fallback_callback(call: CallbackQuery) -> None:
    await call.answer("Пожалуйста, начни сначала — /start", show_alert=False)


@router.errors()
async def on_error(event: ErrorEvent) -> None:
    err_text = str(event.exception)
    if "query is too old" in err_text or "query ID is invalid" in err_text:
        return
    log.exception("Unhandled error: %s", event.exception, exc_info=event.exception)
    if event.update.callback_query:
        try:
            await event.update.callback_query.answer(
                "Что-то пошло не так. Попробуй ещё раз или напиши мастеру.", show_alert=True
            )
        except Exception:
            pass


async def main() -> None:
    if not config.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан в .env")

    session = ProxySession()
    bot = Bot(token=config.BOT_TOKEN, session=session)
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    await init_db()
    log.info("Бот запущен")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    asyncio.run(main())
