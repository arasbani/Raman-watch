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
    waiting_for_photo = State()
    choosing_category = State()
    waiting_for_quantity = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "أهلاً بك في بوت جملة (معرض رامان للساعات) ⌚\n\n"
        "الرجاء إرسال **صورة الساعة** المطلوبة من العروض أولاً:"
    )
    await state.set_state(OrderState.waiting_for_photo)

@dp.message(OrderState.waiting_for_photo)
async def handle_photo(message: types.Message, state: FSMContext):
    if message.photo:
        builder = InlineKeyboardBuilder()
        builder.button(text="ساعات بالقطعة (بالدولار $)", callback_data="cat_usd")
        builder.button(text="ساعات جملة (بالدينار العراقي)", callback_data="cat_iqd")
        builder.button(text="عروض الأزواج (Pairs)", callback_data="cat_pair")
        builder.adjust(1)

        await message.answer(
            "📸 تم استلام صورة الساعة بنجاح.\n\n"
            "يرجى تحديد فئة السعر الخاصة بهذا الموديل من القناة:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(OrderState.choosing_category)
    else:
        await message.answer("الرجاء إرسال صورة الساعة المطلوبة لنستكمل الطلب.")

@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    cat_type = callback.data.split("_")[1]
    await state.update_data(cat_type=cat_type)
    
    if cat_type == "usd":
        text = "أدخل السعر بالدولار للقطعة الواحدة (مثلاً: 8.5 أو 11):"
    elif cat_type == "iqd":
        text = "أدخل السعر بالدينار العراقي للقطعة أو الفئة (مثلاً: 8500):"
    else:
        text = "أدخل سعر العرض أو الزوج:"

    await callback.message.answer(text)
    await state.set_state(OrderState.waiting_for_quantity)
    await callback.answer()

@dp.message(OrderState.waiting_for_quantity)
async def process_price_and_calc(message: types.Message, state: FSMContext):
    try:
        unit_price = float(message.text)
    except ValueError:
        await message.answer("الرجاء إدخال رقم صحيح للسعر.")
        return

    await state.update_data(unit_price=unit_price)
    await message.answer("كم عدد القطع أو الكمية المطلوبة بهذا السعر؟ (اكتب الرقم فقط، مثلاً: 12)")
    
    # ننتقل للخطوة الأخيرة لحساب الكمية
    @dp.message()
    async def final_calculation(msg: types.Message, state: FSMContext):
        if not msg.text.isdigit():
            await msg.answer("الرجاء إدخال رقم صحيح للكمية.")
            return
        
        qty = int(msg.text)
        data = await state.get_data()
        price = data.get("unit_price")
        cat = data.get("cat_type")
        
        total = qty * price
        currency = "$" if cat == "usd" else "د.ع"
        
        await msg.answer(
            "✅ **تم حساب الطلب بنجاح!**\n\n"
            f"📦 الكمية: {qty}\n"
            f"💰 المجموع الكلي: {total} {currency}\n\n"
            "شكراً لتسوقك في معرض رامان للساعات. سيتم التواصل معك لتأكيد الطلب."
        )
        await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
        "الآن، قم بإرسال **صور الساعات** المطلوبة (يمكنك إرسالها دفعة واحدة أو صورة بصورة).\n"
        "وعند الانتهاء تماماً، اكتب كلمة **تم** ليتم حساب المجموع وإرسال الطلب."
    )
    await state.set_state(OrderState.waiting_for_photos)

@dp.message(OrderState.waiting_for_photos)
async def process_photos(message: types.Message, state: FSMContext):
    if message.text and message.text.lower() == "تم":
        data = await state.get_data()
        quantity = data.get("quantity", 0)
        photos_count = data.get("photos_count", 0)
        
        price_per_watch = 25 
        total_price = quantity * price_per_watch
        
        await message.answer(
            "✅ **تم استلام طلبك بنجاح!**\n\n"
            f"📦 عدد الساعات المطلوب: {quantity}\n"
            f"📸 عدد الصور المرسلة: {photos_count}\n"
            f"💰 المجموع الكلي للجملة: ${total_price}\n\n"
            "شكراً لتسوقك معنا في معرض رامان للساعات. سيتم التواصل معك لتأكيد الشحن والتوصيل."
        )
        await state.clear()
        return

    if message.photo:
        data = await state.get_data()
        photos_count = data.get("photos_count", 0) + 1
        await state.update_data(photos_count=photos_count)
        
        await message.answer(f"تم استلام الصورة رقم ({photos_count}). أرسل صور أخرى أو اكتب **تم** للحساب النهائي.")
    else:
        await message.answer("الرجاء إرسال صور الساعات المطلوبة، أو كتابة **تم** لإنهاء الطلب.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
  
