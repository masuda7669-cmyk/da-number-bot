import asyncio
import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===================== CONFIG =====================
TELEGRAM_TOKEN = "8357626882:AAHvTFz6PotVnuq0wj36wQcZps6FS6uaZ_s"
API_BASE = "http://185.190.142.81/api/v1"
API_KEY = "nxa_f1d6a30ca658662d90f99e947ac800ac96d465e1"
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}
# ==================================================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# প্রতিটা ইউজারের নাম্বার আলাদা রাখার জন্য
user_sessions = {}


# ============================================================
# NexaOTP Console থেকে Facebook Live রেঞ্জ আনার ফাংশন
# ============================================================
async def fetch_live_facebook_ranges() -> list:
    ranges_found = set()

    try:
        async with aiohttp.ClientSession() as session:

            # চেষ্টা ১: Console endpoint
            try:
                async with session.get(
                    f"{API_BASE}/console",
                    headers=HEADERS,
                    params={"service": "Facebook", "limit": 100},
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        _extract_ranges_from_data(data, ranges_found)
            except Exception as e:
                logger.warning(f"Console endpoint failed: {e}")

            # চেষ্টা ২: Numbers ranges endpoint
            if not ranges_found:
                try:
                    async with session.get(
                        f"{API_BASE}/numbers/ranges",
                        headers=HEADERS,
                        params={"service": "Facebook"},
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            _extract_ranges_from_data(data, ranges_found)
                except Exception as e:
                    logger.warning(f"Ranges endpoint failed: {e}")

            # চেষ্টা ৩: Messages endpoint
            if not ranges_found:
                try:
                    async with session.get(
                        f"{API_BASE}/messages",
                        headers=HEADERS,
                        params={"service": "Facebook", "limit": 100},
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            _extract_ranges_from_data(data, ranges_found)
                except Exception as e:
                    logger.warning(f"Messages endpoint failed: {e}")

    except Exception as e:
        logger.error(f"Range fetch error: {e}")

    return sorted(list(ranges_found))


def _extract_ranges_from_data(data, ranges_set):
    """API রেসপন্স থেকে নাম্বার বের করে রেঞ্জ তৈরি করে"""
    items = []

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ["data", "numbers", "messages", "ranges", "results", "items"]:
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        # সরাসরি range string list থাকলে
        if "ranges" in data and isinstance(data["ranges"], list):
            for r in data["ranges"]:
                if isinstance(r, str):
                    ranges_set.add(r)
            return

    for item in items:
        number = None
        if isinstance(item, str):
            number = item
        elif isinstance(item, dict):
            number = (
                item.get("number") or
                item.get("phone") or
                item.get("msisdn") or
                item.get("range") or
                item.get("prefix")
            )

        if number and isinstance(number, str):
            clean = number.replace("+", "").replace(" ", "").replace("-", "")
            digits_only = ''.join(c for c in clean if c.isdigit())
            if len(digits_only) >= 6:
                prefix = digits_only[:6]
                ranges_set.add(f"{prefix}XXX")


def _extract_otp(data):
    """API রেসপন্স থেকে OTP বের করে"""
    if isinstance(data, dict):
        otp = data.get("otp") or data.get("code") or data.get("sms_code")
        if otp:
            return str(otp)
        inner = data.get("data") or data.get("message") or data.get("messages")
        if isinstance(inner, dict):
            otp = inner.get("otp") or inner.get("code") or inner.get("body")
            if otp:
                return str(otp)
        if isinstance(inner, list) and len(inner) > 0:
            first = inner[0]
            if isinstance(first, dict):
                otp = first.get("otp") or first.get("code") or first.get("body")
                if otp:
                    return str(otp)
    elif isinstance(data, list) and len(data) > 0:
        first = data[0]
        if isinstance(first, dict):
            otp = first.get("otp") or first.get("code") or first.get("body")
            if otp:
                return str(otp)
    return None


# ============================================================
# /start কমান্ড
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 Facebook নাম্বার নিন", callback_data="get_fb_ranges")],
    ]
    await update.message.reply_text(
        "👋 *DA Number Bot-এ স্বাগতম!*\n\n"
        "এই বট NexaOTP থেকে *Facebook-এর লাইভ রেঞ্জ* দেখাবে।\n"
        "তারপর একটা নাম্বার দেবে এবং OTP আসলে তোমাকে জানাবে।\n\n"
        "নিচের বাটনে ক্লিক করো 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ============================================================
# Facebook Live রেঞ্জ দেখানো
# ============================================================
async def show_fb_ranges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "⏳ NexaOTP থেকে *Facebook-এর লাইভ রেঞ্জ* লোড হচ্ছে...\n"
        "একটু অপেক্ষা করো 🔄",
        parse_mode="Markdown"
    )

    ranges = await fetch_live_facebook_ranges()

    if not ranges:
        keyboard = [[InlineKeyboardButton("🔄 আবার চেষ্টা করো", callback_data="get_fb_ranges")]]
        await query.edit_message_text(
            "❌ এই মুহূর্তে কোনো Facebook লাইভ রেঞ্জ পাওয়া যায়নি।\n\n"
            "NexaOTP Console-এ Facebook-এর কোনো Live Signal নেই।\n"
            "কিছুক্ষণ পর আবার চেষ্টা করো।",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    keyboard = []
    for r in ranges[:20]:
        keyboard.append([
            InlineKeyboardButton(f"📞 {r}", callback_data=f"pick_{r}")
        ])
    keyboard.append([InlineKeyboardButton("🔄 রিফ্রেশ করো", callback_data="get_fb_ranges")])

    await query.edit_message_text(
        f"✅ *Facebook লাইভ রেঞ্জ পাওয়া গেছে!* ({len(ranges)}টা)\n\n"
        "যেকোনো একটা রেঞ্জ বেছে নাও 👇\n"
        "_(এগুলো NexaOTP Console থেকে LIVE আনা হয়েছে)_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ============================================================
# রেঞ্জ বেছে নিয়ে নাম্বার নেওয়া
# ============================================================
async def pick_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    range_val = query.data.replace("pick_", "")
    user_id = query.from_user.id
    username = query.from_user.first_name or "ইউজার"

    await query.edit_message_text(
        f"⏳ রেঞ্জ `{range_val}` দিয়ে Facebook নাম্বার খোঁজা হচ্ছে...",
        parse_mode="Markdown"
    )

    number = None
    number_id = None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/numbers/get",
                headers=HEADERS,
                json={"range": range_val, "service": "Facebook"},
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                data = await resp.json()
                logger.info(f"Get number response: {data}")

                if isinstance(data, dict):
                    inner = data.get("data", data)
                    if isinstance(inner, dict):
                        number = (
                            inner.get("number") or
                            inner.get("phone") or
                            inner.get("msisdn")
                        )
                        number_id = (
                            inner.get("id") or
                            inner.get("number_id") or
                            inner.get("uuid")
                        )
    except Exception as e:
        logger.error(f"Get number error: {e}")

    if not number:
        keyboard = [[InlineKeyboardButton("🔙 রেঞ্জ লিস্টে ফিরে যাও", callback_data="get_fb_ranges")]]
        await query.edit_message_text(
            f"❌ এই রেঞ্জে নাম্বার পাওয়া যায়নি।\n"
            f"রেঞ্জ: `{range_val}`\n\n"
            f"অন্য একটা রেঞ্জ চেষ্টা করো।",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    user_sessions[user_id] = {
        "number": number,
        "number_id": number_id,
        "range": range_val
    }

    sent_msg = await query.edit_message_text(
        f"✅ *নাম্বার পাওয়া গেছে, {username}!*\n\n"
        f"📱 তোমার নাম্বার: `{number}`\n"
        f"📋 রেঞ্জ: `{range_val}`\n\n"
        f"⏳ Facebook OTP-এর জন্য অপেক্ষা করছি...\n"
        f"_(প্রতি ১০ সেকেন্ডে চেক করা হচ্ছে, সর্বোচ্চ ৫ মিনিট)_",
        parse_mode="Markdown"
    )

    asyncio.create_task(
        poll_for_otp(
            bot=context.bot,
            user_id=user_id,
            number=number,
            number_id=number_id,
            chat_id=query.message.chat_id,
            msg_id=sent_msg.message_id
        )
    )


# ============================================================
# OTP পোলিং — প্রতি ১০ সেকেন্ডে চেক
# প্রতিটা ইউজার সম্পূর্ণ আলাদা
# ============================================================
async def poll_for_otp(bot, user_id, number, number_id, chat_id, msg_id):
    max_attempts = 30

    for attempt in range(1, max_attempts + 1):
        await asyncio.sleep(10)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{API_BASE}/numbers/{number_id}/messages",
                    headers=HEADERS,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    data = await resp.json()
                    logger.info(f"OTP check [{attempt}] for {number}: {data}")

            otp = _extract_otp(data)

            if otp:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=(
                        f"🎉 *OTP পাওয়া গেছে!*\n\n"
                        f"📱 নাম্বার: `{number}`\n"
                        f"🔑 *OTP কোড: `{otp}`*\n\n"
                        f"✅ কোডটি কপি করে ব্যবহার করো!\n\n"
                        f"নতুন নাম্বার নিতে /start করো।"
                    ),
                    parse_mode="Markdown"
                )
                if user_id in user_sessions:
                    del user_sessions[user_id]
                return

        except Exception as e:
            logger.warning(f"OTP poll [{attempt}] error: {e}")

        # প্রতি ১ মিনিটে status আপডেট
        if attempt % 6 == 0:
            elapsed_min = (attempt * 10) // 60
            remaining_min = 5 - elapsed_min
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=(
                        f"✅ নাম্বার: `{number}`\n\n"
                        f"⏳ OTP এখনো আসেনি...\n"
                        f"⏱ {elapsed_min} মিনিট হয়েছে, আরো {remaining_min} মিনিট অপেক্ষা করব।"
                    ),
                    parse_mode="Markdown"
                )
            except:
                pass

    # সময় শেষ
    try:
        keyboard = [[InlineKeyboardButton("🔄 নতুন নাম্বার নিন", callback_data="get_fb_ranges")]]
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=(
                f"⏰ *সময় শেষ!*\n\n"
                f"📱 নাম্বার: `{number}`\n\n"
                f"❌ ৫ মিনিটে কোনো Facebook OTP আসেনি।\n\n"
                f"নিচের বাটনে ক্লিক করে নতুন নাম্বার নাও।"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except:
        pass

    if user_id in user_sessions:
        del user_sessions[user_id]


# ============================================================
# Main
# ============================================================
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(show_fb_ranges, pattern="^get_fb_ranges$"))
    app.add_handler(CallbackQueryHandler(pick_range, pattern="^pick_"))

    print("=" * 40)
    print("✅ DA Number Bot চালু হয়েছে!")
    print("টেলিগ্রামে @da_number_bot খুঁজুন")
    print("বন্ধ করতে Ctrl+C চাপুন")
    print("=" * 40)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
