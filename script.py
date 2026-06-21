import os

# ── PM Note (appended to all PM captions unless user has custom caption) ──────
PM_NOTE = (
    "\n\n━━━━━━━━━━━━━━━━━━\n"
    "❤️ Join {channel_name} for more content!\n"
    "🔗 {channel_link}"
)

# ── Start Message ─────────────────────────────────────────────────────────────
START_TEXT = (
    "👋 <b>Hello {name}!</b>\n\n"
    "I'm a powerful <b>File to Link & Stream Bot</b> "
    "with <b>4GB+ support</b> 🤖\n\n"
    "📤 <b>What I can do:</b>\n"
    "┣ Generate stream & download links\n"
    "┣ Support files up to <b>4GB</b>\n"
    "┣ Custom captions & shorteners\n"
    "┣ Channel file automation\n"
    "┗ Force subscription support\n\n"
    "🚀 Send me any file to get started!"
)

# ── Help Message ──────────────────────────────────────────────────────────────
HELP_TEXT = (
    "📖 <b>Help & Commands</b>\n\n"
    "┣ /start — Welcome message\n"
    "┣ /help — This message\n"
    "┣ /myfiles — Your uploaded files (last 10)\n"
    "┣ /delete &lt;token&gt; — Delete a file\n"
    "┣ /settings — Manage your settings\n\n"
    "<b>⚙️ Settings Features:</b>\n"
    "┣ Custom caption template\n"
    "┣ URL shortener integration\n"
    "┣ Upload mode (Files/Buttons)\n"
    "┗ Channel management\n\n"
    "<b>📦 Supported:</b>\n"
    "┣ Files up to <b>4GB</b> ✅\n"
    "┗ Video, Audio, Documents\n\n"
    "<b>🔖 Caption Placeholders:</b>\n"
    "<code>{caption}</code> — file name\n"
    "<code>{stream_link}</code> — watch URL\n"
    "<code>{download_link}</code> — download URL\n"
    "<code>{size}</code> — file size\n"
    "<code>{token}</code> — token"
)

# ── About Message ─────────────────────────────────────────────────────────────
ABOUT_TEXT = (
    "🤖 <b>Bot Information</b>\n\n"
    "┌─── <b>Bot Details</b> ───┐\n"
    "┣ 📝 Name: <b>{bot_name}</b>\n"
    "┣ 👨‍💻 Developer: {developer}\n"
    "┣ 📢 Updates: {channel_name}\n"
    "└─────────────────────┘\n\n"
    "┌─── <b>Technical Specs</b> ───┐\n"
    "┣ 📦 Version: <b>{version}</b>\n"
    "┣ 🐍 Python: <b>3.12</b>\n"
    "┣ 🔧 Framework: <b>PTB 20.7 + Telethon</b>\n"
    "┣ 🗄 Database: <b>MongoDB</b>\n"
    "┗ ☁️ Hosted on: <b>{hosting}</b>\n\n"
    "⚡️ Built with ❤️ by {developer}"
)
