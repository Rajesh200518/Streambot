"""
Telegram File Streaming Bot — 4GB+ Support via Telethon MTProto
================================================================
Uses Telethon (MTProto API) instead of Bot API to bypass the 2GB file limit.
Files up to 4GB (Telegram's hard limit for Premium) are fully supported.

Requirements:
  pip install -r requirements.txt

Config (.env):
  BOT_TOKEN    — from @BotFather
  API_ID       — from https://my.telegram.org
  API_HASH     — from https://my.telegram.org
  BASE_URL     — your public web server URL
  ADMIN_IDS    — your Telegram user ID
"""

import os, logging, json, asyncio, secrets
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ChatJoinRequestHandler, filters, ContextTypes,
)
from telethon import TelegramClient
from telethon.sessions import StringSession
import db
import settings
import fsub
import script

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
API_ID         = int(os.getenv("API_ID", "0"))
API_HASH       = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")   # generated once via gen_session.py
BASE_URL       = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_IDS      = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))
LOG_CHANNEL    = int(os.getenv("LOG_CHANNEL", "0"))
START_IMAGE    = os.getenv("START_IMAGE", "")
CHANNEL_NAME   = os.getenv("CHANNEL_NAME", "Our Channel")
BOT_VERSION    = os.getenv("BOT_VERSION", "v1.0.0")
BOT_HOSTING    = os.getenv("BOT_HOSTING", "VPS")
SOURCE_CODE    = os.getenv("SOURCE_CODE", "")
DEVELOPER      = os.getenv("DEVELOPER", "@Admin")
BOT_NAME       = os.getenv("BOT_NAME", "StreamBot")

DB_FILE        = "files_db.json"

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Telethon client (MTProto — handles files up to 4 GB) ─────────────────────
tg_client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID, API_HASH,
)

# ── DB ────────────────────────────────────────────────────────────────────────
def load_db() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f:
            return json.load(f)
    return {}

def save_db(db: dict):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

async def add_file(
    file_id: str, file_unique_id: str,
    file_name: str, file_size: int,
    mime_type: str, uploader_id: int,
    chat_id: int, message_id: int,
) -> str:
    import secrets
    file_num  = await db.get_next_file_number()
    short_key = secrets.token_urlsafe(4)[:6]
    token     = f"{file_num:06d}_{short_key}"
    fdb = load_db()
    fdb[token] = {
        "file_id":        file_id,
        "file_unique_id": file_unique_id,
        "file_name":      file_name,
        "file_size":      file_size,
        "mime_type":      mime_type,
        "uploader_id":    uploader_id,
        "chat_id":        chat_id,
        "message_id":     message_id,
        "uploaded_at":    datetime.utcnow().isoformat(),
        "views":          0,
        "file_number":    file_num,
    }
    save_db(fdb)
    return token

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_size(b: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS or ADMIN_IDS == [0]

# ── Commands ──────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    text = script.START_TEXT.format(name=name)
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📢 Join {CHANNEL_NAME}", url=os.getenv("CHANNEL_LINK", "https://t.me/"))],
        [InlineKeyboardButton("ℹ️ About", callback_data="start:about"),
         InlineKeyboardButton("❓ Help", callback_data="start:help")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="start:settings")],
    ])
    try:
        if START_IMAGE:
            await update.message.reply_photo(
                photo=START_IMAGE, caption=text,
                parse_mode="HTML", reply_markup=kb)
        else:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Home", callback_data="start:home"),
         InlineKeyboardButton("ℹ️ About", callback_data="start:about")],
        [InlineKeyboardButton("❌ Close", callback_data="start:close")],
    ])
    await update.message.reply_text(
        script.HELP_TEXT, parse_mode="HTML", reply_markup=kb)


async def about_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = []
    if SOURCE_CODE:
        rows.append([InlineKeyboardButton("📂 Source Code", url=SOURCE_CODE)])
    rows.append([InlineKeyboardButton("🏠 Home", callback_data="start:home"),
                 InlineKeyboardButton("❌ Close", callback_data="start:close")])
    kb = InlineKeyboardMarkup(rows)
    text = script.ABOUT_TEXT.format(
        bot_name=BOT_NAME, developer=DEVELOPER,
        channel_name=CHANNEL_NAME, version=BOT_VERSION, hosting=BOT_HOSTING)
    try:
        await update.message.reply_photo(
            photo=START_IMAGE, caption=text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)

async def start_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "start:help":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Home", callback_data="start:home"),
             InlineKeyboardButton("ℹ️ About", callback_data="start:about")],
            [InlineKeyboardButton("❌ Close", callback_data="start:close")],
        ])
        try:
            await q.edit_message_caption(
                caption=script.HELP_TEXT, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await q.edit_message_text(
                script.HELP_TEXT, parse_mode="HTML", reply_markup=kb)

    elif q.data == "start:about":
        rows = []
        if SOURCE_CODE:
            rows.append([InlineKeyboardButton("📂 Source Code", url=SOURCE_CODE)])
        rows.append([InlineKeyboardButton("🏠 Home", callback_data="start:home"),
                     InlineKeyboardButton("❌ Close", callback_data="start:close")])
        kb = InlineKeyboardMarkup(rows)
        text = script.ABOUT_TEXT.format(
            bot_name=BOT_NAME, developer=DEVELOPER,
            channel_name=CHANNEL_NAME, version=BOT_VERSION, hosting=BOT_HOSTING)
        try:
            await q.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

    elif q.data == "start:settings":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Bot PM Settings",   callback_data="set:pm")],
            [InlineKeyboardButton("📡 Channels Settings", callback_data="set:channels")],
            [InlineKeyboardButton("🏠 Home", callback_data="start:home"),
             InlineKeyboardButton("❌ Close", callback_data="start:close")],
        ])
        try:
            await q.edit_message_caption(
                caption="⚙️ <b>SETTINGS</b>\n\nChoose what to configure:",

                parse_mode="HTML", reply_markup=kb)
        except Exception:
            await q.edit_message_text(
                "⚙️ <b>SETTINGS</b>\n\nChoose what to configure:",

                parse_mode="HTML", reply_markup=kb)

    elif q.data == "start:home":
        name = q.from_user.first_name
        text = script.START_TEXT.format(name=name)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📢 Join {CHANNEL_NAME}",
                                  url=os.getenv("CHANNEL_LINK", "https://t.me/"))],
            [InlineKeyboardButton("ℹ️ About", callback_data="start:about"),
             InlineKeyboardButton("❓ Help", callback_data="start:help")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="start:settings")],
        ])
        try:
            await q.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)

    elif q.data == "start:close":
        try:
            await q.message.delete()
        except Exception:
            pass

async def my_files(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id if update.effective_user else (msg.chat_id if msg else 0)
    db  = load_db()
    mine = [(t, m) for t, m in db.items() if m["uploader_id"] == uid]
    if not mine:
        await update.message.reply_text("You have no uploaded files yet.")
        return
    lines = ["*Your Files (last 10):*\n"]
    for tok, meta in mine[-10:]:
        lines.append(
            f"📄 `{meta['file_name']}`\n"
            f"   {fmt_size(meta['file_size'])}  •  👁 {meta['views']}\n"
            f"   🔗 {BASE_URL}/watch/{tok.split(chr(95))[0]}?hash={tok.split(chr(95))[1] if chr(95) in tok else tok}\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def delete_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /delete <token>")
        return
    token = ctx.args[0]
    db    = load_db()
    if token not in db:
        await update.message.reply_text("❌ File not found.")
        return
    uid = update.effective_user.id if update.effective_user else (msg.chat_id if msg else 0)
    if db[token]["uploader_id"] != uid and not is_admin(uid):
        await update.message.reply_text("❌ Not your file.")
        return
    del db[token]
    save_db(db)
    await update.message.reply_text("✅ File deleted.")


# ── FSub Admin Commands ───────────────────────────────────────────────────────
async def setfsub_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text(
            "Usage: /setfsub @username or channel_id\n"
            "Then optionally: /setfsubmode normal|request")
        return
    target = ctx.args[0]
    try:
        chat = await ctx.bot.get_chat(target)
        mode = "normal"
        cfg  = await db.get_fsub()
        if cfg:
            mode = cfg.get("mode", "normal")
        link = f"https://t.me/{chat.username}" if chat.username else cfg.get("chat_link","") if cfg else ""
        await db.set_fsub(chat.id, chat.title or target, link, mode, True)
        await update.message.reply_text(
            f"✅ Force sub set to <b>{chat.title}</b>\n"
            f"Mode: <b>{mode}</b>\n"
            f"Link: {link}\n\n"
            f"Use /setfsubmode normal|request to change mode.\n"
            f"Use /setfsublink https://t.me/xxx to set invite link (for private channels).",
            parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def setfsubmode_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return
    if not ctx.args or ctx.args[0] not in ("normal", "request"):
        await update.message.reply_text("Usage: /setfsubmode normal|request")
        return
    mode = ctx.args[0]
    cfg  = await db.get_fsub()
    if not cfg:
        await update.message.reply_text("❌ Set a channel first with /setfsub")
        return
    await db.set_fsub(cfg["chat_id"], cfg["chat_title"], cfg.get("chat_link",""), mode, cfg.get("enabled", True))
    await update.message.reply_text(f"✅ FSub mode set to <b>{mode}</b>", parse_mode="HTML")

async def setfsublink_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /setfsublink https://t.me/xxx")
        return
    link = ctx.args[0]
    cfg  = await db.get_fsub()
    if not cfg:
        await update.message.reply_text("❌ Set a channel first with /setfsub")
        return
    await db.set_fsub(cfg["chat_id"], cfg["chat_title"], link, cfg.get("mode","normal"), cfg.get("enabled", True))
    await update.message.reply_text(f"✅ FSub link updated to: {link}")

async def removefsub_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return
    await db.disable_fsub()
    await update.message.reply_text("✅ Force subscription <b>disabled</b>.", parse_mode="HTML")

async def fsubstatus_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return
    cfg = await db.get_fsub()
    if not cfg or not cfg.get("enabled"):
        await update.message.reply_text("📊 Force sub: <b>Disabled</b>", parse_mode="HTML")
        return
    await update.message.reply_text(
        f"📊 <b>Force Sub Status</b>\n\n"
        f"📣 Channel: <b>{cfg.get('chat_title','?')}</b>\n"
        f"🆔 ID: <code>{cfg.get('chat_id','?')}</code>\n"
        f"🔗 Link: {cfg.get('chat_link','—')}\n"
        f"⚙️ Mode: <b>{cfg.get('mode','normal')}</b>\n"
        f"✅ Status: <b>Enabled</b>",
        parse_mode="HTML")

# ── process_file_data — called after fsub verified ────────────────────────────
async def process_file_data(bot, uid: int, pdata: dict):
    """Re-process a file after fsub verification. Sends result to user PM."""
    watch_url  = pdata["watch_url"]
    dl_url     = pdata["dl_url"]
    stream_url = pdata["stream_url"]
    file_name  = pdata["file_name"]
    icon       = pdata["icon"]
    size_bytes = pdata["size_bytes"]
    size_note  = pdata["size_note"]
    token      = pdata["token"]

    user_cfg  = await db.get_user(uid)
    short_en  = user_cfg.get("shortener_enabled", True)
    display_watch_url = watch_url
    if short_en and user_cfg.get("shortener_url") and user_cfg.get("shortener_api_key"):
        display_watch_url = await settings.shorten_url(
            user_cfg["shortener_url"], user_cfg["shortener_api_key"], watch_url)

    upload_mode = user_cfg.get("upload_mode", "buttons")
    pm_template = user_cfg.get("caption_template")

    if pm_template:
        caption = (pm_template
            .replace("{caption}",       file_name)
            .replace("{file_name}",     file_name)
            .replace("{stream_link}",   display_watch_url)
            .replace("{watch_url}",     display_watch_url)
            .replace("{download_link}", dl_url)
            .replace("{dl_url}",        dl_url)
            .replace("{size}",          fmt_size(size_bytes))
            .replace("{token}",         token))
    else:
        pm_note = script.PM_NOTE.format(
            channel_name=CHANNEL_NAME,
            channel_link=os.getenv("CHANNEL_LINK", ""))
        caption = (
            f"{icon} <b>{file_name}</b>\n\n"
            f"📦 Size: <code>{fmt_size(size_bytes)}</code>\n"
            f"🔑 Token: <code>{token}</code>"
            f"{size_note}\n\n"
            f"🔗 <b>Link:</b>\n<code>{display_watch_url}</code>"
            + pm_note
        )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Watch Online", url=display_watch_url)],
        [InlineKeyboardButton("📥 Download",    url=dl_url),
         InlineKeyboardButton("🔗 Stream URL",  url=stream_url)],
        [InlineKeyboardButton("🗑 Delete", callback_data=f"del:{token}")],
    ])
    try:
        await bot.send_message(uid, caption, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await bot.send_message(uid, caption, reply_markup=kb)


# ── Stats Command ─────────────────────────────────────────────────────────────
async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return

    async def _get_stats():
        users_count    = await db.users_col.count_documents({})
        channels_count = await db.channels_col.count_documents({})
        files_db       = load_db()
        files_count    = len(files_db)
        total_size     = sum(v.get("file_size", 0) for v in files_db.values())
        return users_count, channels_count, files_count, total_size

    users, channels, files, total_size = await _get_stats()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"📊 <b>Bot Statistics Dashboard</b>\n\n"
        f"👥 <b>Users Stats</b>\n"
        f"• Total Users: <b>{users}</b>\n\n"
        f"🤖 <b>Bot & Channel Stats</b>\n"
        f"• Total Channels: <b>{channels}</b>\n"
        f"• Total Files: <b>{files}</b>\n"
        f"• Total Size: <b>{fmt_size(total_size)}</b>\n\n"
        f"<i>Last Updated: {now}</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="stats:refresh"),
         InlineKeyboardButton("❌ Close",         callback_data="stats:close")],
    ])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)

async def stats_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "stats:close":
        try:
            await q.message.delete()
        except Exception:
            pass
        return
    # Refresh
    users    = await db.users_col.count_documents({})
    channels = await db.channels_col.count_documents({})
    files_db = load_db()
    files    = len(files_db)
    total_size = sum(v.get("file_size", 0) for v in files_db.values())
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"📊 <b>Bot Statistics Dashboard</b>\n\n"
        f"👥 <b>Users Stats</b>\n"
        f"• Total Users: <b>{users}</b>\n\n"
        f"🤖 <b>Bot & Channel Stats</b>\n"
        f"• Total Channels: <b>{channels}</b>\n"
        f"• Total Files: <b>{files}</b>\n"
        f"• Total Size: <b>{fmt_size(total_size)}</b>\n\n"
        f"<i>Last Updated: {now}</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh Stats", callback_data="stats:refresh"),
         InlineKeyboardButton("❌ Close",         callback_data="stats:close")],
    ])
    try:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass

# ── Broadcast Command ─────────────────────────────────────────────────────────
async def broadcast_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return
    if not ctx.args and not update.message.reply_to_message:
        await update.message.reply_text(
            "Usage: /broadcast <message>\n"
            "Or reply to a message with /broadcast")
        return

    # Get broadcast message
    if update.message.reply_to_message:
        bcast_msg = update.message.reply_to_message
    else:
        bcast_msg = None
        bcast_text = " ".join(ctx.args)

    # Get all users
    users_cursor = db.users_col.find({}, {"_id": 1})
    users = [u["_id"] async for u in users_cursor]

    status_msg = await update.message.reply_text(
        f"📣 Broadcasting to <b>{len(users)}</b> users...", parse_mode="HTML")

    success = failed = 0
    for user_id in users:
        try:
            if bcast_msg:
                await bcast_msg.forward(user_id)
            else:
                await ctx.bot.send_message(
                    user_id, bcast_text, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # avoid flood

    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete</b>\n\n"
        f"• Sent: <b>{success}</b>\n"
        f"• Failed: <b>{failed}</b>\n"
        f"• Total: <b>{len(users)}</b>",
        parse_mode="HTML")

# ── File Handler ──────────────────────────────────────────────────────────────
async def handle_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.channel_post
    uid = update.effective_user.id if update.effective_user else (msg.chat_id if msg else 0)

    if msg.video:
        f         = msg.video
        file_name = f.file_name or f"video_{f.file_unique_id}.mp4"
        mime      = f.mime_type or "video/mp4"
        icon      = "🎬"
    elif msg.document:
        f         = msg.document
        file_name = f.file_name or f"file_{f.file_unique_id}"
        mime      = f.mime_type or "application/octet-stream"
        icon      = "📄"
    elif msg.audio:
        f         = msg.audio
        file_name = f.file_name or f"audio_{f.file_unique_id}.mp3"
        mime      = f.mime_type or "audio/mpeg"
        icon      = "🎵"
    else:
        await msg.reply_text("Please send a video, audio, or document.")
        return

    size_bytes = f.file_size or 0

    # Warn if file is too large for Bot API download
    # (streaming via Telethon still works fine for any size)
    size_note = ""
    if size_bytes > 2 * 1024 ** 3:
        size_note = "\n⚡ *Large file* — streamed via MTProto (4 GB support)"

    proc = await msg.reply_text("⏳ Processing...")

    token = await add_file(
        file_id        = f.file_id,
        file_unique_id = f.file_unique_id,
        file_name      = file_name,
        file_size      = size_bytes,
        mime_type      = mime,
        uploader_id    = uid,
        chat_id        = msg.chat_id,
        message_id     = msg.message_id,
    )

    # Token format: 000001_a3f9k2 → URL: /watch/000001?hash=a3f9k2
    _num, _hash = token.split("_", 1) if "_" in token else (token, "")
    watch_url  = f"{BASE_URL}/watch/{_num}?hash={_hash}"
    dl_url     = f"{BASE_URL}/download/{_num}?hash={_hash}"
    stream_url = f"{BASE_URL}/stream/{_num}?hash={_hash}"
    is_channel = bool(update.channel_post)
    display_watch_url = watch_url

    if is_channel:
        ch_cfg = await db.get_channel(msg.chat_id)
        if ch_cfg and ch_cfg.get("shortener_url") and ch_cfg.get("shortener_api_key"):
            display_watch_url = await settings.shorten_url(
                ch_cfg["shortener_url"], ch_cfg["shortener_api_key"], watch_url
            )
        ch_template = ch_cfg.get("caption_template") if ch_cfg else None
        if ch_template:
            caption = (ch_template
                .replace("{caption}", file_name)
                .replace("{file_name}", file_name)
                .replace("{stream_link}", display_watch_url)
                .replace("{watch_url}", display_watch_url)
                .replace("{download_link}", dl_url)
                .replace("{dl_url}", dl_url)
                .replace("{size}", fmt_size(size_bytes))
                .replace("{token}", token))
        else:
            caption = (
                f"{icon} {file_name}\n\n"
                f"🔗 Watch: {display_watch_url}"
                f"{size_note}"
            )
        from telethon.tl.types import InputMediaEmpty
        from telethon import Button
        buttons_on = ch_cfg.get('buttons_enabled', True) if ch_cfg else True
        buttons_on = ch_cfg.get('buttons_enabled', True) if ch_cfg else True
        tl_buttons = [
            [Button.url("▶️ Watch Online", display_watch_url)],
            [Button.url("📥 Download", dl_url)],
        ]
        await proc.delete()
        try:
            await tg_client.edit_message(
                msg.chat_id,
                msg.message_id,
                text=caption,
                buttons=tl_buttons if buttons_on else None,
            )
        except Exception as e:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Watch Online", url=display_watch_url)],
                [InlineKeyboardButton("📥 Download", url=dl_url)],
            ])
            try:
                await msg.reply_text(caption, parse_mode="HTML", reply_markup=kb)
            except Exception:
                await msg.reply_text(caption, reply_markup=kb)
        # ── Log to log channel ────────────────────────────────────────────
        if LOG_CHANNEL:
            try:
                now = datetime.utcnow().strftime('%d %b %Y, %I:%M %p UTC')
                ch_username = f"@{msg.chat.username}" if msg.chat.username else "private"
                log_text = (
                    f"📡 <b>Channel File Upload</b>\n\n"
                    f"📣 Channel: <b>{msg.chat.title}</b> ({ch_username})\n"
                    f"🆔 ID: <code>{msg.chat_id}</code>\n"
                    f"📄 File: <b>{file_name}</b>\n"
                    f"📦 Size: <code>{fmt_size(size_bytes)}</code>\n"
                    f"🔗 Link: {watch_url}\n"
                    f"⏰ Time: {now}"
                )
                log_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Watch Online", url=watch_url)],
                    [InlineKeyboardButton("📥 Download", url=dl_url)],
                ])
                await ctx.bot.forward_message(
                    chat_id=LOG_CHANNEL,
                    from_chat_id=msg.chat_id,
                    message_id=msg.message_id,
                )
                await ctx.bot.send_message(
                    LOG_CHANNEL, log_text, parse_mode="HTML", reply_markup=log_kb)
            except Exception as e:
                logger.warning(f"Log channel error: {e}")
    else:
        # ── Force subscription check (PM only) ───────────────────────────────
        pdata = {
            "watch_url": watch_url, "dl_url": dl_url, "stream_url": stream_url,
            "file_name": file_name, "icon": icon, "size_bytes": size_bytes,
            "size_note": size_note, "token": token,
        }
        if not await fsub.fsub_check(update, ctx, pdata):
            await proc.delete()
            return
        # ─────────────────────────────────────────────────────────────────────
        user_cfg = await db.get_user(uid)
        upload_mode  = user_cfg.get("upload_mode", "buttons")
        short_en     = user_cfg.get("shortener_enabled", True)
        if short_en and user_cfg.get("shortener_url") and user_cfg.get("shortener_api_key"):
            display_watch_url = await settings.shorten_url(
                user_cfg["shortener_url"], user_cfg["shortener_api_key"], watch_url
            )

        if upload_mode == "files":
            # ── Files mode: edit original message caption (same as channel) ──
            pm_template = user_cfg.get("caption_template")
            if pm_template:
                caption = (pm_template
                    .replace("{caption}",       file_name)
                    .replace("{file_name}",     file_name)
                    .replace("{stream_link}",   display_watch_url)
                    .replace("{watch_url}",     display_watch_url)
                    .replace("{download_link}", dl_url)
                    .replace("{dl_url}",        dl_url)
                    .replace("{size}",          fmt_size(size_bytes))
                    .replace("{token}",         token))
            else:
                caption = (
                    f"{icon} {file_name}\n\n"
                    f"🔗 Watch: {display_watch_url}"
                    f"{size_note}"
                )
            from telethon import Button as TlButton
            buttons_on = user_cfg.get("buttons_enabled", True)
            tl_btns = [
                [TlButton.url("▶️ Watch Online", display_watch_url)],
                [TlButton.url("📥 Download", dl_url)],
            ]
            await proc.delete()
            try:
                await tg_client.edit_message(
                    msg.chat_id,
                    msg.message_id,
                    text=caption,
                    buttons=tl_btns if buttons_on else None,
                )
            except Exception:
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("▶️ Watch Online", url=display_watch_url)],
                    [InlineKeyboardButton("📥 Download", url=dl_url)],
                ])
                try:
                    await msg.reply_text(caption, parse_mode="HTML", reply_markup=kb)
                except Exception:
                    await msg.reply_text(caption, reply_markup=kb)
            # ── Log to log channel ────────────────────────────────────────
            if LOG_CHANNEL:
                try:
                    now = datetime.utcnow().strftime("%d %b %Y, %I:%M %p UTC")
                    user = update.effective_user
                    uname = f"@{user.username}" if user and user.username else "no username"
                    uname_str = user.first_name if user else "Unknown"
                    uid_str = uid
                    log_text = (
                        f"📤 <b>PM File Upload (Files Mode)</b>\n\n"
                        f"👤 User: <b>{uname_str}</b> ({uname})\n"
                        f"🆔 User ID: <code>{uid_str}</code>\n"
                        f"📄 File: <b>{file_name}</b>\n"
                        f"📦 Size: <code>{fmt_size(size_bytes)}</code>\n"
                        f"🔗 Link: {watch_url}\n"
                        f"⏰ Time: {now}"
                    )
                    log_kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ Watch Online", url=watch_url)],
                        [InlineKeyboardButton("📥 Download", url=dl_url)],
                    ])
                    await ctx.bot.forward_message(
                        chat_id=LOG_CHANNEL,
                        from_chat_id=msg.chat_id,
                        message_id=msg.message_id,
                    )
                    await ctx.bot.send_message(
                        LOG_CHANNEL, log_text,
                        parse_mode="HTML", reply_markup=log_kb)
                except Exception as e:
                    logger.warning(f"Log channel error: {e}")
        else:
            # ── Buttons mode: reply with inline keyboard (default) ──
            pm_template = user_cfg.get("caption_template")
            if pm_template:
                caption = (pm_template
                    .replace("{caption}",       file_name)
                    .replace("{file_name}",     file_name)
                    .replace("{stream_link}",   display_watch_url)
                    .replace("{watch_url}",     display_watch_url)
                    .replace("{download_link}", dl_url)
                    .replace("{dl_url}",        dl_url)
                    .replace("{size}",          fmt_size(size_bytes))
                    .replace("{token}",         token))
            else:
                caption = (
                    f"{icon} <b>{file_name}</b>\n\n"
                    f"📦 Size: <code>{fmt_size(size_bytes)}</code>\n"
                    f"🔑 Token: <code>{token}</code>"
                    f"{size_note}\n\n"
                    f"🔗 <b>Link:</b>\n<code>{display_watch_url}</code>"
                )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("▶️ Watch Online", url=display_watch_url)],
                [InlineKeyboardButton("📥 Download", url=dl_url)],
                [InlineKeyboardButton("🗑 Delete", callback_data=f"del:{token}")],
            ])
            await proc.delete()
            try:
                await msg.reply_text(caption, parse_mode="HTML", reply_markup=kb)
            except Exception:
                await msg.reply_text(caption, reply_markup=kb)
            # ── Log to log channel ────────────────────────────────────────
            if LOG_CHANNEL:
                try:
                    now = datetime.utcnow().strftime('%d %b %Y, %I:%M %p UTC')
                    user = update.effective_user
                    uname = f"@{user.username}" if user and user.username else "no username"
                    uname_str = user.first_name if user else "Unknown"
                    log_text = (
                        f"📤 <b>PM File Upload</b>\n\n"
                        f"👤 User: <b>{uname_str}</b> ({uname})\n"
                        f"🆔 User ID: <code>{uid}</code>\n"
                        f"📄 File: <b>{file_name}</b>\n"
                        f"📦 Size: <code>{fmt_size(size_bytes)}</code>\n"
                        f"🔗 Link: {watch_url}\n"
                        f"⏰ Time: {now}"
                    )
                    log_kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ Watch Online", url=watch_url)],
                        [InlineKeyboardButton("📥 Download", url=dl_url)],
                    ])
                    await ctx.bot.forward_message(
                        chat_id=LOG_CHANNEL,
                        from_chat_id=msg.chat_id,
                        message_id=msg.message_id,
                    )
                    await ctx.bot.send_message(
                        LOG_CHANNEL, log_text, parse_mode="HTML", reply_markup=log_kb)
                except Exception as e:
                    logger.warning(f"Log channel error: {e}")

# ── Callback ──────────────────────────────────────────────────────────────────
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.startswith("del:"):
        token = q.data[4:]
        db    = load_db()
        if token in db and db[token]["uploader_id"] == q.from_user.id:
            del db[token]
            save_db(db)
            await q.edit_message_text("✅ File deleted.")
        else:
            await q.answer("❌ Cannot delete.", show_alert=True)

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    await tg_client.start(bot_token=BOT_TOKEN)
    logger.info("Telethon MTProto client connected ✅")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("about",   about_cmd))
    app.add_handler(CallbackQueryHandler(start_callback, pattern="^start:"))
    app.add_handler(CommandHandler("help",    help_cmd))
    app.add_handler(CommandHandler("myfiles", my_files))
    app.add_handler(CommandHandler("delete",  delete_cmd))
    app.add_handler(CommandHandler("settings",    settings.settings_cmd))
    app.add_handler(CommandHandler("stats",      stats_cmd))
    app.add_handler(CommandHandler("broadcast",  broadcast_cmd))
    app.add_handler(CallbackQueryHandler(stats_callback, pattern="^stats:"))
    app.add_handler(CommandHandler("setfsub",     setfsub_cmd))
    app.add_handler(CommandHandler("removefsub",  removefsub_cmd))
    app.add_handler(CommandHandler("setfsubmode", setfsubmode_cmd))
    app.add_handler(CommandHandler("setfsublink", setfsublink_cmd))
    app.add_handler(CommandHandler("fsubstatus",  fsubstatus_cmd))
    app.add_handler(CallbackQueryHandler(fsub.handle_fsub_callback, pattern="^fsub:"))
    app.add_handler(ChatJoinRequestHandler(fsub.handle_join_request))
    app.add_handler(CallbackQueryHandler(settings.settings_callback, pattern="^set:"))
    app.add_handler(MessageHandler(
        filters.FORWARDED & settings.pending_add_filter,
        settings.handle_add_channel,
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & settings.pending_text_filter,
        settings.handle_settings_text,
    ))
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.Document.ALL | filters.AUDIO,
        handle_file,
    ))

    # Channel post handler
    app.add_handler(MessageHandler(
        filters.UpdateType.CHANNEL_POST & (filters.VIDEO | filters.Document.ALL | filters.AUDIO),
        handle_file,
    ))

    # Channel post handler (files sent to connected channels)
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot polling started ✅")

    # Use initialize/start/stop manually to avoid event loop conflict with Telethon
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Bot is running! Press Ctrl+C to stop.")
        await tg_client.run_until_disconnected()
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
  
