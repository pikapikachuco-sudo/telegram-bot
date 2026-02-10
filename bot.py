import os
import logging
import asyncio
import re
from datetime import datetime
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import httpx

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ওয়ার্নিং স্টোর
user_warnings = {}

# অশ্লীল/খারাপ শব্দের তালিকা (বাংলা ও ইংরেজি)
BAD_WORDS = [
    # বাংলা অশ্লীল শব্দ
    'চোদ', 'চুদ', 'মাগি', 'মাগী', 'বেশ্যা', 'রেন্ডি', 'হারামি', 'হারামজাদা',
    'কুত্তা', 'কুত্তার', 'শুয়োর', 'শুয়রের', 'গাধা', 'গর্দভ', 'বাল', 'ভোদা',
    'পুটকি', 'মাদারচোদ', 'বোকাচোদা', 'হালা', 'হালায়', 'খানকি', 'খান্কি',
    'চুতিয়া', 'চুতমারানি', 'ধোন', 'ল্যাওড়া', 'নুনু', 'বাঁড়া', 'ভোস্দিকে',
    'তোর মা', 'তর মা', 'মায়ের', 'মাকে', 'বাপের', 'বাপরে', 'ছাগল', 
    'চুতমারানী', 'মাদারফাকার', 'বদমাইশ', 'হারামখোর', 'শালা', 'শালী',
    'কামিনা', 'কামিনী', 'গান্ডু', 'গাণ্ডু', 'ভোদায়', 'পুটকিত', 'ফাকার',
    
    # ইংরেজি অশ্লীল শব্দ
    'fuck', 'shit', 'bitch', 'ass', 'dick', 'cock', 'pussy', 'cunt',
    'bastard', 'damn', 'hell', 'whore', 'slut', 'motherfucker', 'asshole',
    'penis', 'vagina', 'sex', 'porn', 'nude', 'xxx', 'nsfw',
    
    # ভ্যারিয়েশন (স্পেস/ক্যারেক্টার দিয়ে লেখা)
    'c h o d', 'ch0d', 'm@gi', 'b!tch', 'f*ck', 'sh!t', 'a$$', 'fuk',
    'suck', 'wtf', 'stfu', 'milf', 'dilf', 'hentai', 'anal', 'oral',
]

# URL patterns (অশ্লীল লিংক ব্লক)
ADULT_URL_PATTERNS = [
    r'pornhub', r'xvideos', r'xnxx', r'redtube', r'youporn', r'xxx',
    r'porn', r'sex\.com', r'adult', r'nude', r'onlyfans', r'18\+',
]

def contains_bad_word(text):
    """মেসেজে অশ্লীল শব্দ আছে কিনা চেক করে"""
    if not text:
        return False, None
    
    # Lower case এ convert
    text_lower = text.lower()
    
    # বিশেষ ক্যারেক্টার রিমুভ (bypass prevention)
    cleaned_text = re.sub(r'[^\w\s]', '', text_lower)
    cleaned_text = re.sub(r'\s+', '', cleaned_text)  # সব স্পেস রিমুভ
    
    # Bad word check
    for bad_word in BAD_WORDS:
        bad_word_cleaned = re.sub(r'[^\w\s]', '', bad_word.lower())
        
        # Exact match
        if bad_word.lower() in text_lower:
            return True, bad_word
        
        # Cleaned version match (bypass চেক)
        if bad_word_cleaned in cleaned_text:
            return True, bad_word
        
        # Word boundary check
        pattern = r'\b' + re.escape(bad_word.lower()) + r'\b'
        if re.search(pattern, text_lower):
            return True, bad_word
    
    # URL pattern check
    for pattern in ADULT_URL_PATTERNS:
        if re.search(pattern, text_lower):
            return True, "inappropriate link"
    
    return False, None

# Message filter (auto-delete bad words)
async def message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """সব মেসেজ চেক করে এবং অশ্লীল শব্দ থাকলে ডিলিট করে"""
    
    if not update.message or not update.message.text:
        return
    
    message = update.message
    user = message.from_user
    chat = message.chat
    
    # প্রাইভেট চ্যাটে কাজ করবে না
    if chat.type == 'private':
        return
    
    # Admin দের মেসেজ চেক করবে না
    try:
        member = await chat.get_member(user.id)
        if member.status in ['creator', 'administrator']:
            return
    except:
        pass
    
    # মেসেজ চেক করা
    text = message.text
    has_bad_word, detected_word = contains_bad_word(text)
    
    if has_bad_word:
        try:
            # মেসেজ ডিলিট করা
            await message.delete()
            
            # Warning track
            user_id = user.id
            if user_id not in user_warnings:
                user_warnings[user_id] = 0
            user_warnings[user_id] += 1
            
            # সতর্কতা মেসেজ
            warning_msg = await context.bot.send_message(
                chat_id=chat.id,
                text=f"⚠️ {user.mention_html()}\n\n"
                     f"❌ অশ্লীল/অনুপযুক্ত বার্তা সনাক্ত করা হয়েছে!\n"
                     f"🚫 আপনার মেসেজ মুছে দেওয়া হয়েছে।\n\n"
                     f"⚠️ সতর্কতা: {user_warnings[user_id]}/3\n"
                     f"💡 গ্রুপের নিয়ম মেনে চলুন।",
                parse_mode=ParseMode.HTML
            )
            
            # 10 সেকেন্ড পর warning মেসেজ ডিলিট
            await asyncio.sleep(10)
            await warning_msg.delete()
            
            # Log করা
            logger.info(f"🚫 Deleted bad message from {user.username or user.first_name} (ID: {user_id})")
            logger.info(f"   Detected word: {detected_word}")
            
            # 3 সতর্কতায় mute
            if user_warnings[user_id] >= 3:
                try:
                    permissions = ChatPermissions(can_send_messages=False)
                    await chat.restrict_member(user_id, permissions)
                    
                    mute_msg = await context.bot.send_message(
                        chat_id=chat.id,
                        text=f"🔇 {user.mention_html()} কে 3টি সতর্কতার কারণে মিউট করা হয়েছে।",
                        parse_mode=ParseMode.HTML
                    )
                    
                    await asyncio.sleep(10)
                    await mute_msg.delete()
                    
                    user_warnings[user_id] = 0
                except Exception as e:
                    logger.error(f"Failed to mute user: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")

# স্টার্ট কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 হ্যালো! আমি একটি গ্রুপ ম্যানেজমেন্ট বট।\n\n"
        "✅ Auto Bad Word Filter: চালু আছে\n"
        "কমান্ড দেখতে /help টাইপ করুন।"
    )

# হেল্প কমান্ড
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 <b>Admin Commands:</b>

👤 <b>User Management:</b>
/ban - ইউজার ব্যান করুন (Reply করে)
/unban - ইউজার আনব্যান করুন (Reply করে)
/kick - ইউজার কিক করুন (Reply করে)
/mute - ইউজার মিউট করুন (Reply করে)
/unmute - ইউজার আনমিউট করুন (Reply করে)
/warn - ইউজারকে সতর্ক করুন (Reply করে)
/warnings - ইউজারের সতর্কতা দেখুন (Reply করে)

📋 <b>General Commands:</b>
/info - ইউজার ইনফো দেখুন (Reply করে)
/rules - গ্রুপের নিয়ম দেখুন
/pin - মেসেজ পিন করুন (Reply করে)
/unpin - মেসেজ আনপিন করুন
/status - বট স্ট্যাটাস দেখুন

🛡️ <b>Auto Features:</b>
✅ Bad Word Filter: চালু (স্বয়ংক্রিয়)
✅ Auto Delete: অশ্লীল মেসেজ মুছে ফেলা হবে
✅ Auto Warning: 3 সতর্কতায় মিউট
    """
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

# Welcome মেসেজ
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        welcome_text = f"""
🎉 স্বাগতম {member.mention_html()}!

আমাদের গ্রুপে আপনাকে স্বাগতম। 
গ্রুপের নিয়ম দেখতে /rules টাইপ করুন।

⚠️ মনে রাখবেন: অশ্লীল/অনুপযুক্ত বার্তা স্বয়ংক্রিয়ভাবে মুছে যাবে।

উপভোগ করুন! 🎊
        """
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)

# Ban কমান্ড
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ একটি মেসেজে রিপ্লাই করে এই কমান্ড ব্যবহার করুন।")
        return
    
    user = update.message.from_user
    chat = update.message.chat
    
    member = await chat.get_member(user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("❌ শুধুমাত্র অ্যাডমিনরা এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    
    user_to_ban = update.message.reply_to_message.from_user
    
    try:
        await chat.ban_member(user_to_ban.id)
        await update.message.reply_text(
            f"🚫 {user_to_ban.mention_html()} কে ব্যান করা হয়েছে।",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ ব্যান করতে সমস্যা হয়েছে: {str(e)}")

# Unban কমান্ড
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ একটি মেসেজে রিপ্লাই করে এই কমান্ড ব্যবহার করুন।")
        return
    
    user = update.message.from_user
    chat = update.message.chat
    
    member = await chat.get_member(user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("❌ শুধুমাত্র অ্যাডমিনরা এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    
    user_to_unban = update.message.reply_to_message.from_user
    
    try:
        await chat.unban_member(user_to_unban.id)
        await update.message.reply_text(
            f"✅ {user_to_unban.mention_html()} কে আনব্যান করা হয়েছে।",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ আনব্যান করতে সমস্যা হয়েছে: {str(e)}")

# Kick কমান্ড
async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ একটি মেসেজে রিপ্লাই করে এই কমান্ড ব্যবহার করুন।")
        return
    
    user = update.message.from_user
    chat = update.message.chat
    
    member = await chat.get_member(user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("❌ শুধুমাত্র অ্যাডমিনরা এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    
    user_to_kick = update.message.reply_to_message.from_user
    
    try:
        await chat.ban_member(user_to_kick.id)
        await chat.unban_member(user_to_kick.id)
        await update.message.reply_text(
            f"👢 {user_to_kick.mention_html()} কে কিক করা হয়েছে।",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ কিক করতে সমস্যা হয়েছে: {str(e)}")

# Mute কমান্ড
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ একটি মেসেজে রিপ্লাই করে এই কমান্ড ব্যবহার করুন।")
        return
    
    user = update.message.from_user
    chat = update.message.chat
    
    member = await chat.get_member(user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("❌ শুধুমাত্র অ্যাডমিনরা এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    
    user_to_mute = update.message.reply_to_message.from_user
    
    try:
        permissions = ChatPermissions(can_send_messages=False)
        await chat.restrict_member(user_to_mute.id, permissions)
        await update.message.reply_text(
            f"🔇 {user_to_mute.mention_html()} কে মিউট করা হয়েছে।",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ মিউট করতে সমস্যা হয়েছে: {str(e)}")

# Unmute কমান্ড
async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ একটি মেসেজে রিপ্লাই করে এই কমান্ড ব্যবহার করুন।")
        return
    
    user = update.message.from_user
    chat = update.message.chat
    
    member = await chat.get_member(user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("❌ শুধুমাত্র অ্যাডমিনরা এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    
    user_to_unmute = update.message.reply_to_message.from_user
    
    try:
        permissions = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        await chat.restrict_member(user_to_unmute.id, permissions)
        await update.message.reply_text(
            f"🔊 {user_to_unmute.mention_html()} কে আনমিউট করা হয়েছে।",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ আনমিউট করতে সমস্যা হয়েছে: {str(e)}")

# Warn কমান্ড
async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ একটি মেসেজে রিপ্লাই করে এই কমান্ড ব্যবহার করুন।")
        return
    
    user = update.message.from_user
    chat = update.message.chat
    
    member = await chat.get_member(user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("❌ শুধুমাত্র অ্যাডমিনরা এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    
    user_to_warn = update.message.reply_to_message.from_user
    user_id = user_to_warn.id
    
    if user_id not in user_warnings:
        user_warnings[user_id] = 0
    
    user_warnings[user_id] += 1
    
    if user_warnings[user_id] >= 3:
        try:
            await chat.ban_member(user_id)
            await update.message.reply_text(
                f"🚫 {user_to_warn.mention_html()} কে 3টি সতর্কতার কারণে ব্যান করা হয়েছে।",
                parse_mode=ParseMode.HTML
            )
            user_warnings[user_id] = 0
        except Exception as e:
            await update.message.reply_text(f"❌ ব্যান করতে সমস্যা হয়েছে: {str(e)}")
    else:
        await update.message.reply_text(
            f"⚠️ {user_to_warn.mention_html()} কে সতর্ক করা হয়েছে! "
            f"({user_warnings[user_id]}/3 সতর্কতা)",
            parse_mode=ParseMode.HTML
        )

# Warnings দেখা
async def warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ একটি মেসেজে রিপ্লাই করে এই কমান্ড ব্যবহার করুন।")
        return
    
    user_to_check = update.message.reply_to_message.from_user
    user_id = user_to_check.id
    
    warns = user_warnings.get(user_id, 0)
    await update.message.reply_text(
        f"⚠️ {user_to_check.mention_html()} এর সতর্কতা: {warns}/3",
        parse_mode=ParseMode.HTML
    )

# User Info
async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        user = update.message.from_user
    else:
        user = update.message.reply_to_message.from_user
    
    info_text = f"""
👤 <b>User Information:</b>

🆔 ID: <code>{user.id}</code>
👤 নাম: {user.mention_html()}
📝 Username: @{user.username if user.username else 'নেই'}
🤖 Bot: {'হ্যাঁ' if user.is_bot else 'না'}
    """
    
    await update.message.reply_text(info_text, parse_mode=ParseMode.HTML)

# Rules
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = """
📜 <b>গ্রুপের নিয়মাবলী:</b>

1️⃣ সবার সাথে সম্মানজনক আচরণ করুন
2️⃣ স্প্যাম করবেন না
3️⃣ অশ্লীল কনটেন্ট শেয়ার করবেন না
4️⃣ বিজ্ঞাপন নিষিদ্ধ (অনুমতি ছাড়া)
5️⃣ রাজনৈতিক/ধর্মীয় বিতর্ক এড়িয়ে চলুন
6️⃣ Admin দের সিদ্ধান্ত মেনে নিন

⚠️ নিয়ম ভঙ্গ করলে সতর্কতা/ব্যান করা হবে।
🛡️ অশ্লীল বার্তা স্বয়ংক্রিয়ভাবে মুছে যাবে।
    """
    await update.message.reply_text(rules_text, parse_mode=ParseMode.HTML)

# Pin মেসেজ
async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ একটি মেসেজে রিপ্লাই করে এই কমান্ড ব্যবহার করুন।")
        return
    
    user = update.message.from_user
    chat = update.message.chat
    
    member = await chat.get_member(user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("❌ শুধুমাত্র অ্যাডমিনরা এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    
    try:
        await update.message.reply_to_message.pin()
        await update.message.reply_text("📌 মেসেজ পিন করা হয়েছে!")
    except Exception as e:
        await update.message.reply_text(f"❌ পিন করতে সমস্যা হয়েছে: {str(e)}")

# Unpin মেসেজ
async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat = update.message.chat
    
    member = await chat.get_member(user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("❌ শুধুমাত্র অ্যাডমিনরা এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    
    try:
        await chat.unpin_all_messages()
        await update.message.reply_text("📌 সব পিন মেসেজ সরানো হয়েছে!")
    except Exception as e:
        await update.message.reply_text(f"❌ আনপিন করতে সমস্যা হয়েছে: {str(e)}")

# Status দেখা
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_text = f"""
🤖 <b>Bot Status:</b>

✅ Status: Online & Active
⏰ Current Time: {current_time}
🔄 Auto-Ping: Enabled (Every 5 min)
🛡️ Bad Word Filter: Active
💚 Server: Render.com

Bot সবসময় active থাকবে!
গ্রুপ সুরক্ষিত আছে! 🛡️
    """
    await update.message.reply_text(status_text, parse_mode=ParseMode.HTML)

# Self-ping ফাংশন
async def keep_alive():
    """প্রতি 5 মিনিটে নিজেকে ping করবে"""
    
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if not render_url:
        logger.warning("RENDER_EXTERNAL_URL not found. Self-ping disabled.")
        return
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                await asyncio.sleep(300)  # 5 মিনিট
                
                response = await client.get(render_url)
                current_time = datetime.now().strftime("%H:%M:%S")
                
                if response.status_code == 200:
                    logger.info(f"✅ Self-ping successful at {current_time}")
                else:
                    logger.warning(f"⚠️ Self-ping returned status {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Self-ping failed: {str(e)}")
                await asyncio.sleep(60)

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ BOT_TOKEN environment variable not found!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("kick", kick))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("warnings", warnings))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("pin", pin))
    application.add_handler(CommandHandler("unpin", unpin))
    application.add_handler(CommandHandler("status", status))
    
    # Message filter (MUST BE BEFORE other message handlers)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        message_filter
    ))
    
    # Welcome handler
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    print("🤖 Bot starting...")
    print("🔄 Self-ping enabled - Bot will stay active 24/7!")
    print("🛡️ Bad Word Filter enabled - Auto-delete inappropriate messages!")
    
    # Self-ping task
    loop = asyncio.get_event_loop()
    loop.create_task(keep_alive())
    
    # বট চালু করা
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()  
