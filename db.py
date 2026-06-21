import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "")
_client = AsyncIOMotorClient(MONGO_URI)
db = _client["streambot"]
users_col = db["users"]
channels_col = db["channels"]


async def get_user(uid: int) -> dict:
    doc = await users_col.find_one({"_id": uid})
    return doc or {"_id": uid, "caption_template": None,
                    "shortener_url": None, "shortener_api_key": None}


async def set_user_field(uid: int, field: str, value):
    await users_col.update_one({"_id": uid}, {"$set": {field: value}}, upsert=True)


async def reset_user(uid: int):
    await users_col.delete_one({"_id": uid})


async def get_channel(chat_id: int):
    return await channels_col.find_one({"_id": chat_id})


async def list_channels(added_by: int):
    return [c async for c in channels_col.find({"added_by": added_by})]


async def add_channel(chat_id: int, title: str, username, added_by: int):
    await channels_col.update_one(
        {"_id": chat_id},
        {"$set": {"title": title, "username": username, "added_by": added_by},
         "$setOnInsert": {"caption_template": None, "shortener_url": None,
                           "shortener_api_key": None}},
        upsert=True,
    )


async def set_channel_field(chat_id: int, field: str, value):
    await channels_col.update_one({"_id": chat_id}, {"$set": {field: value}})


async def delete_channel(chat_id: int):
    await channels_col.delete_one({"_id": chat_id})


async def reset_channel(chat_id: int):
    await channels_col.update_one(
        {"_id": chat_id},
        {"$set": {"caption_template": None, "shortener_url": None,
                   "shortener_api_key": None}},
    )

# ── FSub ──────────────────────────────────────────────────────────────────────

async def get_fsub() -> dict | None:
    col = _db()["fsub"]
    return await col.find_one({"_id": "config"})

async def set_fsub(chat_id: int, chat_title: str, chat_link: str,
                   mode: str = "normal", enabled: bool = True):
    col = _db()["fsub"]
    await col.update_one(
        {"_id": "config"},
        {"$set": {
            "chat_id":    chat_id,
            "chat_title": chat_title,
            "chat_link":  chat_link,
            "mode":       mode,
            "enabled":    enabled,
        }},
        upsert=True,
    )

async def disable_fsub():
    col = _db()["fsub"]
    await col.update_one({"_id": "config"}, {"$set": {"enabled": False}}, upsert=True)

async def has_join_request(uid: int, chat_id: int) -> bool:
    col = _db()["join_requests"]
    doc = await col.find_one({"uid": uid, "chat_id": chat_id})
    return doc is not None

async def set_join_request(uid: int, chat_id: int):
    col = _db()["join_requests"]
    await col.update_one(
        {"uid": uid, "chat_id": chat_id},
        {"$set": {"uid": uid, "chat_id": chat_id}},
        upsert=True,
    )

# ── FSub ──────────────────────────────────────────────────────────────────────
fsub_col    = db["fsub"]
jreq_col    = db["join_requests"]

async def get_fsub() -> dict | None:
    return await fsub_col.find_one({"_id": "config"})

async def set_fsub(chat_id: int, chat_title: str, chat_link: str,
                   mode: str = "normal", enabled: bool = True):
    await fsub_col.update_one(
        {"_id": "config"},
        {"$set": {
            "chat_id":    chat_id,
            "chat_title": chat_title,
            "chat_link":  chat_link,
            "mode":       mode,
            "enabled":    enabled,
        }},
        upsert=True,
    )

async def disable_fsub():
    await fsub_col.update_one(
        {"_id": "config"}, {"$set": {"enabled": False}}, upsert=True)

async def has_join_request(uid: int, chat_id: int) -> bool:
    doc = await jreq_col.find_one({"uid": uid, "chat_id": chat_id})
    return doc is not None

async def set_join_request(uid: int, chat_id: int):
    await jreq_col.update_one(
        {"uid": uid, "chat_id": chat_id},
        {"$set": {"uid": uid, "chat_id": chat_id}},
        upsert=True,
    )
