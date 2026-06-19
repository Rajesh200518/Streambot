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

import os, logging, hashlib, json, asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
API_ID         = int(os.getenv("API_ID", "0"))
API_HASH       = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")   # generated once via gen_session.py
BASE_URL       = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_IDS      = list(map(int, os.getenv("ADMIN_IDS", "0").split(",")))
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

def add_file(
    file_id: str, file_unique_id: str,
    file_name: str, file_size: int,
    mime_type: str, uploader_id: int,
    chat_id: int, message_id: int,
) -> str:
    db = load_db()
    token = hashlib.sha256(
        f"{file_unique_id}{datetime.utcnow().isoformat()}".encode()
    ).hexdigest()[:16]
    db[token] = {
        "file_id":       file_id,
        "file_unique_id": file_unique_id,
        "file_name":     file_name,
        "file_size":     file_size,
        "mime_type":     mime_type,
        "uploader_id":   uploader_id,
        "chat_id":       chat_id,        # needed for Telethon streaming
        "message_id":    message_id,     # needed for Telethon streaming
        "uploaded_at":   datetime.utcnow().isoformat(),
        "views":         0,
    }
    save_db(db)
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
    await update.message.reply_text(
        f"👋 Hello *{name}*!\n\n"
        "I'm your *File Streaming Bot* with **4 GB+ support**.\n\n"
        "📤 Send me any file and I'll give you:\n"
        "• Browser streaming link\n"
        "• VLC & MX Player links\n"
        "• Direct download\n\n"
        "/help — all commands",
        parse_mode="Markdown",
    )

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Commands*\n\n"
        "/start     — Welcome\n"
        "/help      — This message\n"
        "/myfiles   — Your uploaded files (last 10)\n"
        "/delete \\<token\\> — Delete a file\n\n"
        "*Supported sizes:* Up to **4 GB** ✅\n"
        "*Supported types:* Video, Audio, Documents",
        parse_mode="Markdown",
    )

async def my_files(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
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
            f"   🔗 {BASE_URL}/watch/{tok}\n"
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
    uid = update.effective_user.id
    if db[token]["uploader_id"] != uid and not is_admin(uid):
        await update.message.reply_text("❌ Not your file.")
        return
    del db[token]
    save_db(db)
    await update.message.reply_text("✅ File deleted.")

# ── File Handler ──────────────────────────────────────────────────────────────
async def handle_file(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id

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

    token = add_file(
        file_id        = f.file_id,
        file_unique_id = f.file_unique_id,
        file_name      = file_name,
        file_size      = size_bytes,
        mime_type      = mime,
        uploader_id    = uid,
        chat_id        = msg.chat_id,
        message_id     = msg.message_id,
    )

    watch_url = f"{BASE_URL}/watch/{token}"
    dl_url    = f"{BASE_URL}/download/{token}"
    vlc_url   = f"vlc://{BASE_URL}/stream/{token}"
    mx_url    = f"intent:{BASE_URL}/stream/{token}#Intent;package=com.mxtech.videoplayer.ad;end"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Watch Online", url=watch_url)],
        [
            InlineKeyboardButton("📥 Download",  url=dl_url),
            InlineKeyboardButton("🔗 Copy Link", url=watch_url),
        ],
        [
            InlineKeyboardButton("🔵 VLC",       url=vlc_url),
            InlineKeyboardButton("▶️ MX Player", url=mx_url),
        ],
        [InlineKeyboardButton("🗑 Delete", callback_data=f"del:{token}")],
    ])

    caption = (
        f"{icon} *{file_name}*\n\n"
        f"📦 Size: `{fmt_size(size_bytes)}`\n"
        f"🔑 Token: `{token}`"
        f"{size_note}\n\n"
        f"🔗 *Link:*\n`{watch_url}`"
    )

    await proc.delete()
    await msg.reply_text(caption, parse_mode="Markdown", reply_markup=kb)

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
    app.add_handler(CommandHandler("help",    help_cmd))
    app.add_handler(CommandHandler("myfiles", my_files))
    app.add_handler(CommandHandler("delete",  delete_cmd))
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.Document.ALL | filters.AUDIO,
        handle_file,
    ))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot polling started ✅")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())

