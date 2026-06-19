# 🎬 StreamBot — 4 GB+ Telegram File Streaming Bot

Stream your own files (up to **4 GB**) via Telegram with a beautiful web player.
Uses **Telethon MTProto** for large file support — no more 2 GB limit!

---

## ✨ Features

- ✅ Files up to **4 GB** (Telegram's maximum)
- ✅ Byte-range streaming (video seeking works perfectly)
- ✅ Beautiful dark web player
- ✅ VLC & MX Player direct links
- ✅ No file storage on your server (streamed from Telegram CDN)
- ✅ View count tracking
- ✅ Delete files via bot button

---

## 🚀 Setup (Step by Step)

### Step 1 — Create a Bot
1. Message **@BotFather** on Telegram
2. Send `/newbot`, follow prompts
3. Copy the **bot token**

### Step 2 — Get API credentials
1. Go to **https://my.telegram.org**
2. Log in → "API Development Tools"
3. Create an app → copy **API ID** and **API Hash**

### Step 3 — Get your User ID
Message **@userinfobot** on Telegram → copy your ID

### Step 4 — Install & configure

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in BOT_TOKEN, API_ID, API_HASH, BASE_URL, ADMIN_IDS
```

### Step 5 — Generate Session String (one-time only!)

```bash
python gen_session.py
```

Copy the printed `SESSION_STRING=...` into your `.env` file.

### Step 6 — Run

```bash
# Both bot + web server:
python run.py

# Or separately:
python bot.py
uvicorn server:app --host 0.0.0.0 --port 8000
```

---

## 📁 File Structure

```
streambot/
├── bot.py          # Telegram bot (Telethon + python-telegram-bot)
├── server.py       # FastAPI web server with MTProto streaming
├── run.py          # Run both together
├── gen_session.py  # One-time session string generator
├── files_db.json   # Auto-created file database
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🌐 URL Endpoints

| URL | Description |
|-----|-------------|
| `/watch/<token>` | Web player page |
| `/stream/<token>` | Direct stream (VLC/MX/browser) |
| `/download/<token>` | Force download |

---

## ☁️ Deploy on Railway (Free)

1. Push to GitHub
2. Railway → New Project → Deploy from GitHub
3. Add all `.env` variables in Railway dashboard
4. Create a `Procfile`:

```
web: uvicorn server:app --host 0.0.0.0 --port $PORT
worker: python bot.py
```

5. Use the Railway `.railway.app` domain as your `BASE_URL`

---

## ⚙️ How 4GB+ Works

| Method | Max Size | Seeking |
|--------|----------|---------|
| Old Bot API | 2 GB ❌ | Limited |
| **Telethon MTProto** ✅ | **4 GB** ✅ | **Full seek support** ✅ |

Telethon connects directly to Telegram's MTProto protocol,
bypassing the Bot API's 2 GB restriction. Files are streamed
in 1 MB chunks with proper `Range` header support so you can
seek to any position in a video instantly.

