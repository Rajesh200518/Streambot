
async def _safe_edit(q, text, **kwargs):
    """Edit message caption if photo message, else edit text."""
    try:
        await q.edit_message_caption(caption=text, **kwargs)
    except Exception:
        try:
            await _safe_edit(q, text, **kwargs)
        except Exception:
            pass

"""
/settings — User (PM) + Channel Settings, MongoDB-backed.
Supports: caption template (HTML bold), shortener toggle, buttons toggle, upload mode.
"""
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, filters
import db

pending: dict[int, str] = {}

class _PendingTextFilter(filters.MessageFilter):
    def filter(self, message):
        uid = message.from_user.id if message.from_user else None
        return uid in pending and pending[uid] != "ch_add"

class _PendingAddChannelFilter(filters.MessageFilter):
    def filter(self, message):
        uid = message.from_user.id if message.from_user else None
        return uid in pending and pending[uid] == "ch_add"

pending_text_filter = _PendingTextFilter()
pending_add_filter  = _PendingAddChannelFilter()

CAPTION_HELP = (
    "📝 <b>Caption Template</b>\n\n"
    "Placeholders:\n"
    "<code>{caption}</code> — file name\n"
    "<code>{stream_link}</code> — watch/stream URL\n"
    "<code>{download_link}</code> — download URL\n"
    "<code>{size}</code> — file size\n"
    "<code>{token}</code> — token\n\n"
    "HTML formatting supported:\n"
    "<code>&lt;b&gt;bold&lt;/b&gt;</code> → <b>bold</b>\n"
    "<code>&lt;i&gt;italic&lt;/i&gt;</code> → <i>italic</i>\n"
    "<code>&lt;code&gt;mono&lt;/code&gt;</code> → <code>mono</code>\n\n"
    "Example:\n"
    "<code>{caption}\n\n"
    "🔗Fast Download Link\n"
    "➡️ {download_link}\n\n"
    "❤️Join » @YourChannel</code>"
)

# ── Main menu ─────────────────────────────────────────────────────────────────

def _main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Bot PM Settings",   callback_data="set:pm")],
        [InlineKeyboardButton("📡 Channels Settings", callback_data="set:channels")],
    ])

async def settings_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙️ <b>SETTINGS</b>",
        parse_mode="HTML", reply_markup=_main_menu_kb(),
    )

# ── PM Settings ───────────────────────────────────────────────────────────────

async def _show_pm_settings(q):
    u           = await db.get_user(q.from_user.id)
    cap_set     = bool(u.get("caption_template"))
    short_on    = bool(u.get("shortener_url"))
    short_en    = u.get("shortener_enabled", True)
    buttons_on  = u.get("buttons_enabled",   True)
    mode        = u.get("upload_mode", "buttons")

    short_status   = ("✅ On" if short_en else "🔴 Off") if short_on else "❌ Not Set"
    buttons_status = "✅ On" if buttons_on else "🔴 Off"
    cap_status     = "✅ Set" if cap_set   else "❌ Not Set"
    mode_label     = "📁 Files" if mode == "files" else "🔘 Buttons"

    text = (
        "⚙️ <b>Bot PM Settings</b>\n\n"
        f"📝 Caption:     {cap_status}\n"
        f"🔗 Shortener:  {short_status}\n"
        f"🔘 Buttons:    {buttons_status}\n"
        f"📤 Upload Mode: {mode_label}"
    )
    btn_toggle  = "🔴 Disable Buttons"  if buttons_on else "✅ Enable Buttons"
    mode_toggle = "📁 Switch to Files"  if mode == "buttons" else "🔘 Switch to Buttons"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Caption Settings",   callback_data="set:pm:captionmenu")],
        [InlineKeyboardButton("🔗 Shortener Settings", callback_data="set:pm:shortmenu")],
        [InlineKeyboardButton(btn_toggle,              callback_data="set:pm:togglebtns")],
        [InlineKeyboardButton(mode_toggle,             callback_data="set:pm:togglemode")],
        [InlineKeyboardButton("🛠 Reset All",           callback_data="set:pm:reset")],
        [InlineKeyboardButton("◀️ Back",               callback_data="set:back")],
    ])
    await _safe_edit(q, text, parse_mode="HTML", reply_markup=kb)

async def _show_pm_caption_menu(q):
    u        = await db.get_user(q.from_user.id)
    template = u.get("caption_template")
    preview  = (template[:200] + "…") if template and len(template) > 200 else (template or "Not set")
    text = f"📝 <b>PM Caption Settings</b>\n\n<b>Current:</b>\n<code>{preview}</code>\n\n" + CAPTION_HELP
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Change Caption", callback_data="set:pm:caption")],
        [InlineKeyboardButton("🗑 Remove Caption", callback_data="set:pm:rmcaption")],
        [InlineKeyboardButton("◀️ Back",           callback_data="set:pm")],
    ])
    await _safe_edit(q, text, parse_mode="HTML", reply_markup=kb)

async def _show_pm_short_menu(q):
    u        = await db.get_user(q.from_user.id)
    short_on = bool(u.get("shortener_url"))
    short_en = u.get("shortener_enabled", True)
    domain   = u.get("shortener_url", "—")
    status   = ("✅ Enabled" if short_en else "🔴 Disabled") if short_on else "❌ Not Set"
    toggle   = "🔴 Disable Shortener" if short_en else "✅ Enable Shortener"

    text = (
        "🔗 <b>PM Shortener Settings</b>\n\n"
        f"🌐 Domain: <code>{domain}</code>\n"
        f"📊 Status: {status}"
    )
    rows = []
    if short_on:
        rows.append([InlineKeyboardButton(toggle, callback_data="set:pm:toggleshort")])
    rows.append([InlineKeyboardButton("✏️ Change Shortener", callback_data="set:pm:shortener")])
    if short_on:
        rows.append([InlineKeyboardButton("🗑 Remove Shortener", callback_data="set:pm:rmshort")])
    rows.append([InlineKeyboardButton("◀️ Back", callback_data="set:pm")])
    await _safe_edit(q, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))

# ── Channel List ──────────────────────────────────────────────────────────────

async def _show_channels_list(q):
    chans = await db.list_channels(added_by=q.from_user.id)
    rows  = [
        [InlineKeyboardButton(f"📣 {c['title']}", callback_data=f"set:ch:view:{c['_id']}")]
        for c in chans
    ]
    rows.append([InlineKeyboardButton("➕ Add Channel", callback_data="set:ch:add")])
    rows.append([InlineKeyboardButton("◀️ Back",        callback_data="set:back")])
    text = (
        "📣 <b>My Channels</b>\n\nSelect a channel to manage."
        if chans else
        "📣 <b>My Channels</b>\n\nNo channels added yet."
    )
    await _safe_edit(q, text, parse_mode="HTML",
                               reply_markup=InlineKeyboardMarkup(rows))

# ── Channel Detail ────────────────────────────────────────────────────────────

async def _show_channel_details(q, chat_id: int):
    c = await db.get_channel(chat_id)
    if not c:
        await _safe_edit(q, "❌ Channel not found.")
        return

    short_on   = bool(c.get("shortener_url"))
    short_en   = c.get("shortener_enabled", True)
    buttons_on = c.get("buttons_enabled",   True)
    cap_set    = bool(c.get("caption_template"))

    short_status   = ("✅ On" if short_en else "🔴 Off") if short_on else "❌ Not Set"
    buttons_status = "✅ On" if buttons_on else "🔴 Off"
    cap_status     = "✅ Set" if cap_set   else "❌ Not Set"

    text = (
        "📺 <b>Channel Settings</b>\n\n"
        "━━━━━ Basic Info ━━━━━\n"
        f"📣 Name: <code>{c['title']}</code>\n"
        f"🆔 ID: <code>{c['_id']}</code>\n"
        f"👤 Username: <code>{c.get('username') or 'private'}</code>\n\n"
        "━━━━━ Configuration ━━━━━\n"
        f"🔗 Shortener: {short_status}\n"
        f"🔘 Buttons:   {buttons_status}\n"
        f"📝 Caption:   {cap_status}"
    )
    btn_toggle = "🔴 Disable Buttons" if buttons_on else "✅ Enable Buttons"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Caption Settings",   callback_data=f"set:ch:captionmenu:{chat_id}")],
        [InlineKeyboardButton("🔗 Shortener Settings", callback_data=f"set:ch:shortmenu:{chat_id}")],
        [InlineKeyboardButton(btn_toggle,              callback_data=f"set:ch:togglebtns:{chat_id}")],
        [InlineKeyboardButton("❌ Delete Channel",     callback_data=f"set:ch:delete:{chat_id}"),
         InlineKeyboardButton("⚙️ Reset All",         callback_data=f"set:ch:reset:{chat_id}")],
        [InlineKeyboardButton("◀️ Back",              callback_data="set:channels")],
    ])
    await _safe_edit(q, text, parse_mode="HTML", reply_markup=kb)

async def _show_caption_menu(q, chat_id: int):
    c        = await db.get_channel(chat_id)
    template = c.get("caption_template") if c else None
    preview  = (template[:200] + "…") if template and len(template) > 200 else (template or "Not set")
    text = f"📝 <b>Channel Caption Settings</b>\n\n<b>Current:</b>\n<code>{preview}</code>\n\n" + CAPTION_HELP
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Change Caption", callback_data=f"set:ch:caption:{chat_id}")],
        [InlineKeyboardButton("🗑 Remove Caption", callback_data=f"set:ch:rmcaption:{chat_id}")],
        [InlineKeyboardButton("◀️ Back",           callback_data=f"set:ch:view:{chat_id}")],
    ])
    await _safe_edit(q, text, parse_mode="HTML", reply_markup=kb)

async def _show_short_menu(q, chat_id: int):
    c        = await db.get_channel(chat_id)
    short_on = bool(c.get("shortener_url") if c else False)
    short_en = c.get("shortener_enabled", True) if c else True
    domain   = c.get("shortener_url", "—") if c else "—"
    status   = ("✅ Enabled" if short_en else "🔴 Disabled") if short_on else "❌ Not Set"
    toggle   = "🔴 Disable Shortener" if short_en else "✅ Enable Shortener"

    text = (
        "🔗 <b>Channel Shortener Settings</b>\n\n"
        f"🌐 Domain: <code>{domain}</code>\n"
        f"📊 Status: {status}"
    )
    rows = []
    if short_on:
        rows.append([InlineKeyboardButton(toggle, callback_data=f"set:ch:toggleshort:{chat_id}")])
    rows.append([InlineKeyboardButton("✏️ Change Shortener", callback_data=f"set:ch:shortener:{chat_id}")])
    if short_on:
        rows.append([InlineKeyboardButton("🗑 Remove Shortener", callback_data=f"set:ch:rmshort:{chat_id}")])
    rows.append([InlineKeyboardButton("◀️ Back", callback_data=f"set:ch:view:{chat_id}")])
    await _safe_edit(q, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))

# ── Callback Router ───────────────────────────────────────────────────────────

async def settings_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data, uid = q.data, q.from_user.id

    # ── Main ──
    if data == "set:back":
        await _safe_edit(q, "⚙️ <b>SETTINGS</b>",
                                   parse_mode="HTML", reply_markup=_main_menu_kb())
    elif data == "set:pm":
        await _show_pm_settings(q)
    elif data == "set:channels":
        await _show_channels_list(q)

    # ── PM Caption ──
    elif data == "set:pm:captionmenu":
        await _show_pm_caption_menu(q)
    elif data == "set:pm:caption":
        pending[uid] = "pm_caption"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Cancel", callback_data="set:pm:captionmenu")]])
        await _safe_edit(q, 
            "📝 Send your caption template.\nHTML bold: <code>&lt;b&gt;text&lt;/b&gt;</code>",
            parse_mode="HTML", reply_markup=kb)
    elif data == "set:pm:rmcaption":
        await db.set_user_field(uid, "caption_template", "")
        await _show_pm_caption_menu(q)

    # ── PM Shortener ──
    elif data == "set:pm:shortmenu":
        await _show_pm_short_menu(q)
    elif data == "set:pm:shortener":
        pending[uid] = "pm_short_url"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Cancel", callback_data="set:pm:shortmenu")]])
        await _safe_edit(q, "🌐 Send your shortener domain (e.g. <code>gyanilinks.com</code>).",
                                   parse_mode="HTML", reply_markup=kb)
    elif data == "set:pm:rmshort":
        await db.set_user_field(uid, "shortener_url", "")
        await db.set_user_field(uid, "shortener_api_key", "")
        await db.set_user_field(uid, "shortener_enabled", True)
        await _show_pm_short_menu(q)
    elif data == "set:pm:toggleshort":
        u   = await db.get_user(uid)
        cur = u.get("shortener_enabled", True)
        await db.set_user_field(uid, "shortener_enabled", not cur)
        await _show_pm_short_menu(q)

    # ── PM Toggles ──
    elif data == "set:pm:togglebtns":
        u   = await db.get_user(uid)
        cur = u.get("buttons_enabled", True)
        await db.set_user_field(uid, "buttons_enabled", not cur)
        await _show_pm_settings(q)
    elif data == "set:pm:togglemode":
        u    = await db.get_user(uid)
        cur  = u.get("upload_mode", "buttons")
        new  = "files" if cur == "buttons" else "buttons"
        await db.set_user_field(uid, "upload_mode", new)
        await _show_pm_settings(q)
    elif data == "set:pm:reset":
        await db.reset_user(uid)
        await _safe_edit(q, "✅ Settings reset.",
                                   reply_markup=InlineKeyboardMarkup([
                                       [InlineKeyboardButton("◀️ Back", callback_data="set:pm")]]))

    # ── Add channel ──
    elif data == "set:ch:add":
        pending[uid] = "ch_add"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Cancel", callback_data="set:channels")]])
        await _safe_edit(q, 
            "➕ <b>Add Channel</b>\n\nForward any message from your channel "
            "(make sure I'm admin there).",
            parse_mode="HTML", reply_markup=kb)

    # ── Channel view ──
    elif data.startswith("set:ch:view:"):
        await _show_channel_details(q, int(data.split(":")[3]))

    # ── Channel Caption ──
    elif data.startswith("set:ch:captionmenu:"):
        await _show_caption_menu(q, int(data.split(":")[3]))
    elif data.startswith("set:ch:caption:"):
        chat_id = int(data.split(":")[3])
        pending[uid] = f"ch_caption:{chat_id}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Cancel",
                                    callback_data=f"set:ch:captionmenu:{chat_id}")]])
        await _safe_edit(q, 
            "📝 Send your caption template.\nHTML bold: <code>&lt;b&gt;text&lt;/b&gt;</code>",
            parse_mode="HTML", reply_markup=kb)
    elif data.startswith("set:ch:rmcaption:"):
        chat_id = int(data.split(":")[3])
        await db.set_channel_field(chat_id, "caption_template", "")
        await _show_caption_menu(q, chat_id)

    # ── Channel Shortener ──
    elif data.startswith("set:ch:shortmenu:"):
        await _show_short_menu(q, int(data.split(":")[3]))
    elif data.startswith("set:ch:shortener:"):
        chat_id = int(data.split(":")[3])
        pending[uid] = f"ch_short_url:{chat_id}"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Cancel",
                                    callback_data=f"set:ch:shortmenu:{chat_id}")]])
        await _safe_edit(q, "🌐 Send shortener domain for this channel.", reply_markup=kb)
    elif data.startswith("set:ch:rmshort:"):
        chat_id = int(data.split(":")[3])
        await db.set_channel_field(chat_id, "shortener_url", "")
        await db.set_channel_field(chat_id, "shortener_api_key", "")
        await db.set_channel_field(chat_id, "shortener_enabled", True)
        await _show_short_menu(q, chat_id)
    elif data.startswith("set:ch:toggleshort:"):
        chat_id = int(data.split(":")[3])
        c   = await db.get_channel(chat_id)
        cur = c.get("shortener_enabled", True) if c else True
        await db.set_channel_field(chat_id, "shortener_enabled", not cur)
        await _show_short_menu(q, chat_id)

    # ── Channel Buttons toggle ──
    elif data.startswith("set:ch:togglebtns:"):
        chat_id = int(data.split(":")[3])
        c   = await db.get_channel(chat_id)
        cur = c.get("buttons_enabled", True) if c else True
        await db.set_channel_field(chat_id, "buttons_enabled", not cur)
        await _show_channel_details(q, chat_id)

    # ── Channel Delete / Reset ──
    elif data.startswith("set:ch:delete:"):
        await db.delete_channel(int(data.split(":")[3]))
        await _show_channels_list(q)
    elif data.startswith("set:ch:reset:"):
        chat_id = int(data.split(":")[3])
        await db.reset_channel(chat_id)
        await _show_channel_details(q, chat_id)

# ── Text input handler ────────────────────────────────────────────────────────

async def handle_settings_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    text   = update.message.text.strip()
    action = pending.get(uid)
    if not action:
        return

    if action == "pm_caption":
        await db.set_user_field(uid, "caption_template", text)
        del pending[uid]
        await update.message.reply_text("✅ Caption saved.")

    elif action == "pm_short_url":
        pending[uid] = f"pm_short_key:{text}"
        await update.message.reply_text("🔑 Now send your API key for that shortener.")

    elif action.startswith("pm_short_key:"):
        domain = action.split(":", 1)[1]
        await db.set_user_field(uid, "shortener_url",     domain)
        await db.set_user_field(uid, "shortener_api_key", text)
        await db.set_user_field(uid, "shortener_enabled", True)
        del pending[uid]
        await update.message.reply_text("✅ Shortener saved.")

    elif action.startswith("ch_caption:"):
        chat_id = int(action.split(":")[1])
        await db.set_channel_field(chat_id, "caption_template", text)
        del pending[uid]
        await update.message.reply_text("✅ Channel caption saved.")

    elif action.startswith("ch_short_url:"):
        chat_id = int(action.split(":")[1])
        pending[uid] = f"ch_short_key:{chat_id}:{text}"
        await update.message.reply_text("🔑 Now send your API key for that shortener.")

    elif action.startswith("ch_short_key:"):
        _, chat_id, domain = action.split(":", 2)
        await db.set_channel_field(int(chat_id), "shortener_url",     domain)
        await db.set_channel_field(int(chat_id), "shortener_api_key", text)
        await db.set_channel_field(int(chat_id), "shortener_enabled", True)
        del pending[uid]
        await update.message.reply_text("✅ Channel shortener saved.")

# ── Add channel handler ───────────────────────────────────────────────────────

async def handle_add_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message
    origin_chat = None
    if getattr(msg, "forward_origin", None) and hasattr(msg.forward_origin, "chat"):
        origin_chat = msg.forward_origin.chat
    elif getattr(msg, "forward_from_chat", None):
        origin_chat = msg.forward_from_chat
    if not origin_chat:
        await msg.reply_text("❌ That doesn't look like a forwarded channel message.")
        return
    await db.add_channel(chat_id=origin_chat.id, title=origin_chat.title or "Unknown",
                          username=origin_chat.username, added_by=uid)
    del pending[uid]
    await msg.reply_text(f"✅ Channel <b>{origin_chat.title}</b> added.", parse_mode="HTML")

# ── URL shortener helper ──────────────────────────────────────────────────────

async def shorten_url(domain: str, api_key: str, long_url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://{domain}/api",
                params={"api": api_key, "url": long_url},
            )
            data = resp.json()
            short = data.get("shortenedUrl") or data.get("short") or data.get("short_url")
            return short or long_url
    except Exception:
        return long_url
