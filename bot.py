import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- আপনার দেওয়া গোপন তথ্যসমূহ ---
API_TOKEN = '8357626882:AAHvTFz6PotVnuq0wj36wQcZps6FS6uaZ_s'
# আপনি যে URL টি দিয়েছেন সেটি এখানে বসানো হয়েছে
BASE_URL = 'http://185.190.142.81/api/v1/' 
# আপনার দেওয়া API Key
API_KEY = 'nxa_f1d6a30ca658662d90f99e947ac800ac96d465e1'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ১. স্টার্ট কমান্ড
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 ফেসবুক নাম্বার রেঞ্জ দিন", callback_data="get_range")]
    ])
    await message.answer(
        f"আসসালামুয়ালাইকুম মাস্টার কিরা! 😊\n\nনাম্বার নিতে নিচের বাটনে ক্লিক করুন:",
        reply_markup=keyboard
    )

# ২. রেঞ্জ লিখার ইনস্ট্রাকশন
@dp.callback_query(F.data == "get_range")
async def range_handler(callback: types.CallbackQuery):
    await callback.message.answer(
        "আপনার প্যানেল থেকে রেঞ্জ কোডটি এখানে লিখে পাঠান (যেমন: 22507)"
    )

# ৩. নাম্বার এবং ওটিপি তুলে আনার কাজ
@dp.message()
async def fetch_process(message: types.Message):
    user_range = message.text.strip()
    
    if not user_range.isdigit():
        await message.answer("দয়া করে শুধু সংখ্যা (রেঞ্জ) লিখে পাঠান।")
        return

    wait_msg = await message.answer(f"⏳ রেঞ্জ `{user_range}` দিয়ে নাম্বার খোঁজা হচ্ছে...", parse_mode="Markdown")

    try:
        # নাম্বার রিকোয়েস্ট URL (সঠিক ফরম্যাটে)
        # আমরা URL এর সাথে ?key=... অংশটি জুড়ে দিচ্ছি
        num_url = f"{BASE_URL}get_number?key={API_KEY}&range={user_range}&service=facebook"
        response = requests.get(num_url, timeout=15).json()

        if response.get('status') == 'success':
            number = response.get('number')
            order_id = response.get('order_id')
            
            await wait_msg.edit_text(
                f"✅ নাম্বার পাওয়া গেছে!\n\n"
                f"📱 নাম্বার: `{number}`\n\n"
                f"এখন এই নাম্বারটি ফেসবুকে বসান। কোড আসলে আমি এখানে দিয়ে দিব।",
                parse_mode="Markdown"
            )

            # কোড চেক করার অটোমেটিক লুপ
            for _ in range(60): # ৫ মিনিট সময় নিবে
                await asyncio.sleep(5)
                code_url = f"{BASE_URL}get_code?key={API_KEY}&order_id={order_id}"
                code_res = requests.get(code_url, timeout=15).json()
                
                if code_res.get('code'):
                    await message.answer(
                        f"📩 **ওটিপি কোড এসেছে!**\n\n"
                        f"কোড: `{code_res.get('code')}`\n"
                        f"নাম্বার: `{number}`",
                        parse_mode="Markdown"
                    )
                    return
            
            await message.answer(f"❌ সময় শেষ! নাম্বার `{number}` এর জন্য কোনো কোড পাওয়া যায়নি।")
        else:
            await wait_msg.edit_text("❌ এই রেঞ্জে এখন কোনো নাম্বার নেই বা ব্যালেন্স শেষ।")
            
    except Exception as e:
        await wait_msg.edit_text("⚠️ ওয়েবসাইটের সাথে যোগাযোগ করা যাচ্ছে না। আপনার ইন্টারনেট বা API লিঙ্কটি চেক করুন।")

async def main():
    print("বট সচল হয়েছে...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
