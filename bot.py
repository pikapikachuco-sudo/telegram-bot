import os
import logging
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from datetime import datetime, timedelta

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ওয়ার্নিং স্টোর করার জন্য ডিকশনারি
user_warnings = {}

# স্টার্ট কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 হ্যালো! আমি একটি গ্রুপ ম্যানেজমেন্ট বট।\n\n"
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
    """
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

# Welcome মেসেজ
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        welcome_text = f"""
🎉 স্বাগতম {member.mention_html()}!

আমাদের গ্রুপে আপনাকে স্বাগতম। 
গ্রুপের নিয়ম দেখতে /rules টাইপ করুন।

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

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    TOKEN = os.environ.get("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ BOT_TOKEN environment variable not found!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
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
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    
    application.add_error_handler(error_handler)
    
    print("🤖 Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
