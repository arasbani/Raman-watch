import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = "8844649158:AAH1jJo_srUqta0XLQSDEPrdGTEysjEVxgY"

bot = Bot(token=TOKEN)
dp = Dispatcher()

class OrderState(StatesGroup):
    waiting_for_quantity = State()
    waiting_for_photos = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer(
        "أهلاً بك في بوت جملة (معرض رامان للساعات) ⌚\n\n"
        "كم عدد الساعات التي ترغب بطلبها (جملة)؟\n"
        "(الرجاء كتابة الرقم فقط، مثلاً: 12)"
    )
    await state.set_state(OrderState.waiting_for_quantity)

@dp.message(OrderState.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("الرجاء إدخال رقم صحيح لعدد الساعات.")
        return
    
    quantity = int(message.text)
    await state.update_data(quantity=quantity, photos_count=0)
    
    await message.answer(
        f"ممتاز! لقد اخترت طلب **{quantity} ساعة**.\n\n"
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

If __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
  
