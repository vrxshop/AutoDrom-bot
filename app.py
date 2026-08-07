import logging
import asyncio
import os
import json
import uuid
import aiohttp
import threading
from datetime import datetime, timedelta
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ==================================================
# FLASK
# ==================================================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "🚗 Автосервис работает!"

@flask_app.route('/health')
def health():
    return "OK", 200

# ==================================================
# КОНФИГУРАЦИЯ
# ==================================================
ROLLYPAY_API_KEY = os.getenv("ROLLYPAY_API_KEY")
ROLLYPAY_CALLBACK_URL = "https://center-drombot.onrender.com/webhook"

BOT_TOKEN = os.getenv("BOT_TOKEN_AUTO")
ADMIN_IDS = [8370080332, 8559381302]

# ==================================================
# ТЕКСТЫ (ВСЕ @Nastia_sup ЗАМЕНЕНЫ НА @kasgd)
# ==================================================
LANG = {
    "ru": {
        "start_welcome": "🚗 <b>Добро пожаловать в Автосервис Premium!</b>\n\n🔧 Профессиональный ремонт и обслуживание автомобилей\n⚡ Быстрое выполнение заказов\n🛡️ Гарантия на все виды работ\n💎 Индивидуальный подход к каждому клиенту\n\n📞 Поддержка: @kasgd",
        "main_menu": "🚗 <b>Наши услуги</b>\n\nВыберите услугу для оформления заказа.",
        "tariff_desc": "📋 <b>{name}</b>\n\n💰 Цена: {price} ₽\n⏱ Срок: {duration}\n\n{desc}",
        "pay_rub": "📋 <b>{name}</b>\n💰 Цена: {final} ₽\n\n✅ Счет на оплату сформирован!",
        "payment_success": "✅ <b>Оплата прошла успешно!</b>\n\n📋 <b>Ваш заказ №{order_id}</b>\n💰 Сумма: {price} ₽\n\n📌 <b>ЧТО ДАЛЬШЕ?</b>\n\n1️⃣ Сделайте скриншот этого сообщения\n\n2️⃣ Отправьте скриншот менеджеру:\n👉 @kasgd\n\n3️⃣ В сообщении укажите:\n• Название тарифа\n• Ваш ID: <code>{user_id}</code>\n\n⏰ Время ожидания: 5-20 минут\n\nСпасибо за заказ! 🚗",
        "btn_back": "👈 НАЗАД",
        "btn_pay": "💳 ОПЛАТИТЬ",
        "btn_goto_pay": "✅ ПЕРЕЙТИ К ОПЛАТЕ",
        "btn_new_link": "🔄 Новая ссылка"
    }
}

# ==================================================
# ТАРИФЫ
# ==================================================
TARIFFS = {
    "engine_diagnostic": {
        "name_ru": "🔧 Диагностика двигателя",
        "price_rub": 239,
        "duration_ru": "30 мин",
        "desc_ru": "📋 Профессиональная диагностика двигателя:\n\n✅ Визуальный осмотр\n✅ Проверка уровня масла\n✅ Чтение ошибок OBD2\n✅ Рекомендации по ремонту"
    },
    "oil_change": {
        "name_ru": "🛢️ Замена масла",
        "price_rub": 250,
        "duration_ru": "30 мин",
        "desc_ru": "⛽ Быстрая замена масла:\n\n✅ Слив отработанного масла\n✅ Замена масляного фильтра\n✅ Заливка нового масла\n✅ Проверка уровня"
    },
    "suspension_check": {
        "name_ru": "🛞 Проверка подвески",
        "price_rub": 299,
        "duration_ru": "30 мин",
        "desc_ru": "🔍 Диагностика ходовой части:\n\n✅ Проверка амортизаторов\n✅ Проверка сайлентблоков\n✅ Проверка шаровых опор\n✅ Рекомендации по ремонту"
    },
    "tire_service": {
        "name_ru": "🌀 Шиномонтаж",
        "price_rub": 349,
        "duration_ru": "45 мин",
        "desc_ru": "🔄 Профессиональный шиномонтаж:\n\n✅ Демонтаж/монтаж шин\n✅ Балансировка колес\n✅ Проверка давления\n✅ Замена вентилей"
    },
    "brake_repair": {
        "name_ru": "🛑 Ремонт тормозов",
        "price_rub": 499,
        "duration_ru": "1 час",
        "desc_ru": "🛠️ Полный ремонт тормозной системы:\n\n✅ Проверка колодок\n✅ Замена тормозных колодок\n✅ Прокачка тормозов\n✅ Проверка тормозной жидкости"
    },
    "filter_replace": {
        "name_ru": "🌬️ Замена фильтров",
        "price_rub": 599,
        "duration_ru": "30 мин",
        "desc_ru": "🧹 Замена всех фильтров автомобиля:\n\n✅ Замена воздушного фильтра\n✅ Замена салонного фильтра\n✅ Замена топливного фильтра\n✅ Замена масляного фильтра"
    },
    "headlight_adjust": {
        "name_ru": "💡 Регулировка фар",
        "price_rub": 699,
        "duration_ru": "30 мин",
        "desc_ru": "🔦 Профессиональная регулировка света:\n\n✅ Настройка ближнего света\n✅ Настройка дальнего света\n✅ Проверка положения\n✅ Тест на стенде"
    },
    "timing_belt": {
        "name_ru": "🔧 Замена ремня ГРМ",
        "price_rub": 799,
        "duration_ru": "2 часа",
        "desc_ru": "⚙️ Замена ремня газораспределительного механизма:\n\n✅ Демонтаж старого ремня\n✅ Установка нового ремня\n✅ Натяжка и регулировка\n✅ Проверка работы двигателя"
    },
    "transmission_repair": {
        "name_ru": "⚙️ Ремонт АКПП",
        "price_rub": 899,
        "duration_ru": "3 часа",
        "desc_ru": "🔧 Диагностика и ремонт АКПП:\n\n✅ Полная диагностика\n✅ Замена масла в АКПП\n✅ Ремонт гидроблока\n✅ Замена фильтра АКПП"
    },
    "full_maintenance": {
        "name_ru": "📋 Комплексное ТО",
        "price_rub": 1499,
        "duration_ru": "4 часа",
        "desc_ru": "🔧 Полное техническое обслуживание:\n\n✅ Замена масла и фильтров\n✅ Проверка всех систем\n✅ Диагностика двигателя\n✅ Проверка ходовой\n✅ Проверка тормозов\n✅ Проверка электрики\n✅ Полный отчет"
    },
    "overhaul": {
        "name_ru": "🔩 Капитальный ремонт",
        "price_rub": 10000,
        "duration_ru": "5 дней",
        "desc_ru": "🏗️ Полный капитальный ремонт автомобиля:\n\n✅ Полная разборка\n✅ Дефектовка\n✅ Замена всех расходников\n✅ Сборка\n✅ Настройка\n✅ Гарантия 6 месяцев"
    }
}

# ==================================================
# ИНИЦИАЛИЗАЦИЯ
# ==================================================
storage = MemoryStorage()
session = AiohttpSession()
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML), session=session)
dp = Dispatcher(storage=storage)

# --- ФУНКЦИИ ---
async def create_rollypay_payment(amount: int, user_id: int, tariff_key: str, tariff_name: str) -> str:
    url = "https://rollypay.io/api/v1/payments"
    headers = {
        "X-API-Key": ROLLYPAY_API_KEY,
        "Content-Type": "application/json",
        "X-Nonce": str(uuid.uuid4())
    }
    payload = {
        "amount": str(amount),
        "payment_currency": "RUB",
        "order_id": f"auto_{user_id}_{tariff_key}_{int(datetime.now().timestamp())}",
        "description": f"Оплата услуги #{user_id}_{tariff_key}",
        "callback_url": ROLLYPAY_CALLBACK_URL,
        "success_url": "https://t.me/CenterDrombot",
        "fail_url": "https://t.me/CenterDrombot",
        "merchant_fee": "true"
    }
    
    async with aiohttp.ClientSession() as client:
        async with client.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("pay_url")
            else:
                error_text = await response.text()
                logging.error(f"Ошибка RollyPay: {response.status} - {error_text}")
                return None

# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    buttons = []
    for key, data in TARIFFS.items():
        buttons.append([InlineKeyboardButton(
            text=f"{data['name_ru']} — {data['price_rub']}₽",
            callback_data=f"tariff_{key}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_tariff_keyboard(tariff_key):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 ОПЛАТИТЬ", callback_data=f"pay_{tariff_key}")],
        [InlineKeyboardButton(text="👈 НАЗАД", callback_data="back_to_menu")]
    ])

def get_payment_action_keyboard(payment_url, tariff_key):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ПЕРЕЙТИ К ОПЛАТЕ", url=payment_url)],
        [InlineKeyboardButton(text="🔄 Новая ссылка", callback_data=f"refresh_{tariff_key}")],
        [InlineKeyboardButton(text="👈 НАЗАД", callback_data="back_to_menu")]
    ])

# --- ХЭНДЛЕРЫ ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(LANG["ru"]["start_welcome"])
    await message.answer(LANG["ru"]["main_menu"], reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(LANG["ru"]["main_menu"], reply_markup=get_main_keyboard())

@dp.callback_query(F.data.startswith("tariff_"))
async def show_tariff(callback: CallbackQuery, state: FSMContext):
    tariff_key = callback.data.replace("tariff_", "")
    
    if tariff_key not in TARIFFS:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return
    
    tariff = TARIFFS[tariff_key]
    await state.update_data(tariff_key=tariff_key)
    
    text = LANG["ru"]["tariff_desc"].format(
        name=tariff['name_ru'],
        price=tariff['price_rub'],
        duration=tariff['duration_ru'],
        desc=tariff['desc_ru']
    )
    
    await callback.message.edit_text(text, reply_markup=get_tariff_keyboard(tariff_key))
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery, state: FSMContext):
    tariff_key = callback.data.replace("pay_", "")
    
    if tariff_key not in TARIFFS:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return
    
    tariff = TARIFFS[tariff_key]
    user_id = callback.from_user.id
    amount = tariff['price_rub']
    
    await state.update_data(pending_tariff=tariff_key)
    
    payment_url = await create_rollypay_payment(amount, user_id, tariff_key, tariff['name_ru'])
    
    if payment_url:
        text = LANG["ru"]["pay_rub"].format(
            name=tariff['name_ru'],
            final=amount
        )
        await callback.message.edit_text(text, reply_markup=get_payment_action_keyboard(payment_url, tariff_key))
    else:
        await callback.answer("❌ Ошибка создания платежа. Попробуйте позже.", show_alert=True)

@dp.callback_query(F.data.startswith("refresh_"))
async def refresh_payment(callback: CallbackQuery, state: FSMContext):
    tariff_key = callback.data.replace("refresh_", "")
    
    if tariff_key not in TARIFFS:
        await callback.answer("❌ Услуга не найдена", show_alert=True)
        return
    
    tariff = TARIFFS[tariff_key]
    user_id = callback.from_user.id
    amount = tariff['price_rub']
    
    payment_url = await create_rollypay_payment(amount, user_id, tariff_key, tariff['name_ru'])
    
    if payment_url:
        await callback.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ ПЕРЕЙТИ К ОПЛАТЕ", url=payment_url)],
                [InlineKeyboardButton(text="🔄 Новая ссылка", callback_data=f"refresh_{tariff_key}")],
                [InlineKeyboardButton(text="👈 НАЗАД", callback_data="back_to_menu")]
            ])
        )
        await callback.answer("✅ Новая ссылка сгенерирована!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка создания ссылки.", show_alert=True)

# --- КОМАНДА ДЛЯ АДМИНА ---
@dp.message(Command("give"))
async def give_access(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    # /give user_id tariff_key
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ Используй: /give user_id tariff_key\n\nДоступные ключи:\n" + "\n".join(TARIFFS.keys()))
        return
    
    try:
        user_id = int(parts[1])
        tariff_key = parts[2]
    except:
        await message.answer("❌ Неверный формат! /give user_id tariff_key")
        return
    
    if tariff_key not in TARIFFS:
        await message.answer(f"❌ Тариф {tariff_key} не найден!\n\nДоступные ключи:\n" + "\n".join(TARIFFS.keys()))
        return
    
    await message.answer(f"✅ Пользователю {user_id} нужно выдать доступ к:\n{TARIFFS[tariff_key]['name_ru']} ({tariff_key})")

# ==================================================
# ЗАПУСК
# ==================================================
async def main():
    logging.basicConfig(level=logging.INFO)
    
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN_AUTO не задан в переменных окружения!")
        return
    
    if not ROLLYPAY_API_KEY:
        logging.warning("⚠️ ROLLYPAY_API_KEY не задан. Бот работает в режиме 'Связь с менеджером'")
    
    print("=" * 60)
    print("🚗 АВТОСЕРВИС БОТ ЗАПУЩЕН!")
    print("👤 Бот: @CenterDrombot")
    print("📞 Поддержка: @kasgd")
    print("=" * 60)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask запущен!")
    asyncio.run(main())
