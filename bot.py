import asyncio
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- আপনার তথ্যসমূহ ---
API_TOKEN = '8357626882:AAHvTFz6PotVnuq0wj36wQcZps6FS6uaZ_s'
BASE_URL = 'http://185.190.142.81/api/v1/'
API_KEY = 'nxa_f1d6a30ca658662d90f99e947ac800ac96d465e1'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ১. স্টার্ট কমান্ড (বট চালু হলে যা দেখাবে)
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 ফেসবুক নাম্বার নিন", callback_data="get_range")]
    ])
    await message.answer(
        f"আসসালামুয়ালাইকুম মাস্টার কিরা! 😊\nআমি আপনার নাম্বার সার্ভিস বট।\n\n"
        f"নাম্বার নিতে নিচের বাটনে ক্লিক করুন:",
        reply_markup=keyboard
    )

# ২. রেঞ্জ দেখানোর ফাংশন
@dp.callback_query(F.data == "get_range")
async def range_handler(callback: types.CallbackQuery):
    # এখানে ইউজারকে ইনস্ট্রাকশন দেওয়া হচ্ছে
    await callback.message.answer(
        "আপনার প্যানেল থেকে রেঞ্জ কোডটি এখানে লিখে পাঠান।\n"
        "যেমন: `22507` অথবা `23762`",
        parse_mode="Markdown"
    )

# ৩. নাম্বার এবং ওটিপি প্রসেসিং
@dp.message()
async def process_request(message: types.Message):
    user_range = message.text.strip()
    
    # রেঞ্জটি শুধু সংখ্যা কি না তা চেক করা
    if not user_range.isdigit():
        await message.answer("অনুগ্রহ করে সঠিক রেঞ্জ সংখ্যাটি পাঠান।")
        return

    msg = await message.answer(f"⏳ রেঞ্জ `{user_range}` দিয়ে নাম্বার খোঁজা হচ্ছে...", parse_mode="Markdown")

    try:
        # ওয়েবসাইট থেকে নাম্বার রিকোয়েস্ট
        url = f"{BASE_URL}get_number?key={API_KEY}&range={user_range}&service=facebook"
        response = requests.get(url, timeout=10).json()

        if response.get('status') == 'success':
            number = response.get('number')
            order_id = response.get('order_id')
            
            await msg.edit_text(
                f"✅ নাম্বার পাওয়া গেছে!\n\n"
                f"📱 নাম্বার: `{number}`\n\n"
                f"বট এখন কোডের জন্য অপেক্ষা করছে। আপনার ফেসবুক অ্যাপে কোড পাঠান।",
                parse_mode="Markdown"
            )

            # কোড চেক করার লুপ (৫ সেকেন্ড পর পর চেক করবে)
            for _ in range(60): # ৫ মিনিট পর্যন্ত চেক করবে
                await asyncio.sleep(5)
                check_url = f"{BASE_URL}get_code?key={API_KEY}&order_id={order_id}"
                code_res = requests.get(check_url, timeout=10).json()
                
                if code_res.get('code'):
                    await message.answer(
                        f"📩 **ওটিপি কোড এসেছে!**\n\n"
                        f"কোড: `{code_res.get('code')}`\n"
                        f"নাম্বার: `{number}`",
                        parse_mode="Markdown"
                    )
                    return
            
            await message.answer(f"❌ নাম্বার `{number}` এর জন্য কোড পাওয়া যায়নি।")
        else:
            await msg.edit_text("❌ দুঃখিত, এই রেঞ্জে এখন কোনো নাম্বার খালি নেই।")
            
    except Exception as e:
        await msg.edit_text("⚠️ সার্ভারের সাথে সংযোগ বিচ্ছিন্ন হয়েছে। আবার চেষ্টা করুন।")

# ৪. বট রান করা
async def main():
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
