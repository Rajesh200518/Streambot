"""
Force Subscription — Streambot
Uses Telethon MTProto for reliable private channel membership check.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import db

logger = logging.getLogger(__name__)
pending_files: dict[int, dict] = {}


async def get_member_status(bot, uid: int, chat_id: int) -> str:
    """Check membership using Telethon first (reliable for private channels), fallback to Bot API."""
    from bot import tg_client
    from telethon.tl.functions.channels import GetParticipantRequest
    from telethon.errors import UserNotParticipantError, ChannelPrivateError

    try:
        result = await tg_client(GetParticipantRequest(channel=chat_id, participant=uid))
        from telethon.tl.types import (
            ChannelParticipant, ChannelParticipantAdmin,
            ChannelParticipantCreator, ChannelParticipantBanned,
            ChannelParticipantLeft
        )
        p = result.participant
        ptype = type(p).__name__
        logger.info(f"[FSUB] Telethon uid={uid} type={ptype}")
        if isinstance(p, ChannelParticipantBanned):
            return "kicked"
        if isinstance(p, ChannelParticipantLeft):
            return "left"
        return "member"
    except UserNotParticipantError:
        logger.info(f"[FSUB] Telethon: uid={uid} not in channel")
        return "left"
    except ChannelPrivateError:
        logger.warning(f"[FSUB] Telethon: channel {chat_id} is private/inaccessible")
    except Exception as e:
        logger.warning(f"[FSUB] Telethon error uid={uid}: {e}")

    # Fallback: Bot API
    try:
        member = await bot.get_chat_member(chat_id, uid)
        logger.info(f"[FSUB] BotAPI uid={uid} status={member.status}")
        return member.status
    except Exception as e:
        logger.warning(f"[FSUB] BotAPI error uid={uid}: {e}")
        return "left"


async def is_subscribed(bot, uid: int, chat_id: int, mode: str) -> bool:
    status = await get_member_status(bot, uid, chat_id)
    if status in ("member", "administrator", "creator", "restricted"):
        return True
    if status == "kicked":
        return False
    # left
    if mode == "request":
        return await db.has_join_request(uid, chat_id)
    return False


async def fsub_check(update: Update, ctx: ContextTypes.DEFAULT_TYPE,
                     pending_data: dict) -> bool:
    cfg = await db.get_fsub()
    if not cfg or not cfg.get("enabled"):
        return True

    msg = update.message or update.channel_post
    uid = update.effective_user.id if update.effective_user else None
    if uid is None:
        return True

    from bot import ADMIN_IDS
    if uid in ADMIN_IDS:
        return True

    chat_id = cfg["chat_id"]
    mode    = cfg.get("mode", "normal")

    if await is_subscribed(ctx.bot, uid, chat_id, mode):
        return True

    pending_files[uid] = pending_data
    chat_link  = cfg.get("chat_link", "")
    chat_name  = cfg.get("chat_title", "our channel")
    join_label = "📨 Request to Join" if mode == "request" else "📢 Join Channel"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(join_label, url=chat_link)],
        [InlineKeyboardButton("✅ I Joined", callback_data=f"fsub:check:{chat_id}")],
    ])
    await msg.reply_text(
        f"👋 <b>Welcome!</b>\n\n"
        f"⚠️ You must join <b>{chat_name}</b> to use this bot.\n\n"
        f"1️⃣ Click <b>{join_label}</b> below\n"
        f"2️⃣ Come back and tap <b>✅ I Joined</b>",
        parse_mode="HTML",
        reply_markup=kb,
    )
    return False


async def handle_fsub_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q       = update.callback_query
    uid     = q.from_user.id
    chat_id = int(q.data.split(":")[2])
    await q.answer()

    cfg    = await db.get_fsub()
    mode   = cfg.get("mode", "normal") if cfg else "normal"

    if await is_subscribed(ctx.bot, uid, chat_id, mode):
        await _grant_access(q, ctx, uid)
        return

    chat_link  = cfg.get("chat_link", "") if cfg else ""
    chat_name  = cfg.get("chat_title", "our channel") if cfg else "our channel"
    join_label = "📨 Request to Join" if mode == "request" else "📢 Join Channel"
    extra      = " or send a join request." if mode == "request" else "."
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(join_label, url=chat_link)],
        [InlineKeyboardButton("✅ I Joined", callback_data=f"fsub:check:{chat_id}")],
    ])
    try:
        await q.edit_message_text(
            f"❌ <b>Not verified!</b>\n\nPlease join <b>{chat_name}</b> first{extra}",
            parse_mode="HTML",
            reply_markup=kb,
        )
    except Exception:
        pass


async def _grant_access(q, ctx, uid: int):
    pdata = pending_files.pop(uid, None)
    try:
        await q.edit_message_text(
            "✅ <b>Access granted!</b> Processing your file...",
            parse_mode="HTML")
    except Exception:
        pass
    if pdata:
        from bot import process_file_data
        await process_file_data(ctx.bot, uid, pdata)
    else:
        await ctx.bot.send_message(
            uid, "✅ <b>Verified!</b> Please resend your file.", parse_mode="HTML")


async def handle_join_request(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    if req:
        await db.set_join_request(req.from_user.id, req.chat.id)
        logger.info(f"[FSUB] Join request recorded uid={req.from_user.id}")
