import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8844649158:AAH1jJo_srUqta0XLQSDEPrdGTEysjEVxgY"
bot = Bot(token=TOKEN)
dp = Dispatcher()

class OrderState(StatesGroup):
    step = State()

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("أهلاً بك في بوت جملة (معرض رامان للساعات) ⌚\n\nالرجاء إرسال صورة الساعة المطلوبة أولاً:")
    await state.set_state(OrderState.step)

@dp.message(OrderState.step)
async def step_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    stage = data.get("stage", "photo")
    
    if stage == "photo":
        if message.photo:
            builder = InlineKeyboardBuilder()
            builder.button(text="ساعات بالدولار ($)", callback_data="usd")
            builder.button(text="ساعات بالدينار (د.ع)", callback_data="iqd")
            builder.adjust(1)
            await state.update_data(stage="price")
            await message.answer("📸 تم استلام الصورة.\n\nاختر نوع العملة السعرية:", reply_markup=builder.as_markup())
        else:
            await message.answer("الرجاء إرسال صورة الساعة المطلوبة أولاً.")
        return

    if stage == "qty":
        if not message.text or not message.text.isdigit():
            await message.answer("الرجاء إرسال رقم صحيح للكمية.")
            return
        qty = int(message.text)
        price = data.get("price")
        curr = data.get("curr")
        total = qty * price
        await message.answer(f"✅ تم الطلب بنجاح!\n\n📦 الكمية: {qty}\n💰 المجموع: {total} {curr}\n\nشكراً لتسوقك معنا.")
        await state.clear()

@dp.callback_query(lambda c: c.data in ["usd", "iqd"])
async def currency_callback(callback: types.CallbackQuery, state: FSMContext):
    curr = "$" if callback.data == "usd" else "د.ع"
    await state.update_data(curr=curr, stage="qty_input")
    await callback.message.answer(f"تم اختيار ({curr}). الآن أدخل السعر للقطعة الواحدة (أرقام فقط):")
    await callback.answer()

@dp.message(OrderState.step)
async def price_input(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get("stage") == "qty_input":
        try:
            price = float(message.text)
        except ValueError:
            await message.answer("الرجاء إرسال رقم صحيح للسعر.")
            return
        await state.update_data(price=price, stage="qty")
        await message.answer("كم عدد القطع المطلوبة بهذا السعر؟ (اكتب الرقم فقط):")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
        
