import os
import re
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from motor.motor_asyncio import AsyncIOMotorClient

# Railway Environment Variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")

# Database Setup
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client.rose_management_bot

app = Client("rose_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- ၁။ Welcome & SetWelcome (With Buttons) ---
@app.on_message(filters.command("setwelcome") & filters.group)
async def set_welcome(client, message):
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    if user.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        return

    # format: /setwelcome စာသား | ခလုတ်နာမည် | link
    if "|" not in message.text:
        return await message.reply_text("အသုံးပြုပုံ: /setwelcome ကြိုဆိုပါတယ် {user} | Channel | https://t.me/example")

    parts = message.text.split(None, 1)[1].split("|")
    text = parts[0].strip()
    btn_name = parts[1].strip() if len(parts) > 1 else None
    btn_url = parts[2].strip() if len(parts) > 2 else None

    await db.welcome.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"text": text, "btn_name": btn_name, "btn_url": btn_url}},
        upsert=True
    )
    await message.reply_text("Welcome Message ကို သိမ်းဆည်းလိုက်ပါပြီ။")

@app.on_message(filters.new_chat_members)
async def welcome_trigger(client, message):
    data = await db.welcome.find_one({"chat_id": message.chat.id})
    if data:
        welcome_text = data["text"].replace("{user}", message.new_chat_members[0].mention)
        reply_markup = None
        if data.get("btn_name") and data.get("btn_url"):
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(data["btn_name"], url=data["btn_url"])]])
        await message.reply_text(welcome_text, reply_markup=reply_markup)

# --- ၂။ Filters (Auto Reply) ---
@app.on_message(filters.command("filter") & filters.group)
async def add_filter(client, message):
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    if user.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]: return
    
    args = message.text.split(None, 2)
    if len(args) < 3: return await message.reply_text("အသုံးပြုပုံ: /filter [keyword] [reply]")
    
    await db.filters.update_one(
        {"chat_id": message.chat.id, "keyword": args[1].lower()},
        {"$set": {"reply": args[2]}}, upsert=True
    )
    await message.reply_text(f"Filter {args[1]} ကို ထည့်လိုက်ပါပြီ။")

# --- ၃။ Link Delete System ---
@app.on_message(filters.group & ~filters.service)
async def link_deleter(client, message):
    # Admin ပို့တဲ့ link ဆိုရင် မဖျက်ဘူး
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    if user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
        # Admin မဟုတ်ရင် Filter စစ်မယ်
        pass 
    else:
        if re.search(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.text or ""):
            await message.delete()
            return

    # Filter စစ်ဆေးခြင်း
    if message.text:
        found = await db.filters.find_one({"chat_id": message.chat.id, "keyword": message.text.lower()})
        if found: await message.reply_text(found["reply"])

# --- ၄။ Admin Tools (Ban, Mute, Rules, ID) ---
@app.on_message(filters.command("ban") & filters.group)
async def ban_user(client, message):
    if not message.reply_to_message: return
    await client.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
    await message.reply_text("နှင်ထုတ်ပြီးပါပြီ။")
 
@app.on_message(filters.command("mute") & filters.group)
async def mute_user(client, message):
    if not message.reply_to_message: return
    await client.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, ChatPermissions())
    await message.reply_text("စာပို့ခွင့် ပိတ်လိုက်ပါပြီ။")

@app.on_message(filters.command("id"))
async def show_id(client, message):
    await message.reply_text(f"User ID: {message.from_user.id}\nChat ID: {message.chat.id}")

@app.on_message(filters.command("rules") & filters.group)
async def show_rules(client, message):
    data = await db.rules.find_one({"chat_id": message.chat.id})
    text = data["text"] if data else "ဒီ Group မှာ စည်းကမ်းချက် မသတ်မှတ်ရသေးပါ။"
    await message.reply_text(text)

@app.on_message(filters.command("setrules") & filters.group)
async def set_rules(client, message):
    if len(message.command) < 2: return
    await db.rules.update_one({"chat_id": message.chat.id}, {"$set": {"text": message.text.split(None, 1)[1]}}, upsert=True)
    await message.reply_text("Rules ကို သိမ်းလိုက်ပါပြီ။")

print("Bot is running...")
app.run()
