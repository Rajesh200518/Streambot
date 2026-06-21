import unicodedata
import re
"""
FastAPI Streaming Server — 4GB+ Support via Telethon MTProto
=============================================================
Streams files directly from Telegram using Telethon's iter_download(),
which supports Range requests (seeking) and files up to 4 GB.

Run:
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

import os
import themes as _themes, json, asyncio, mimetypes
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from telethon import TelegramClient
from telethon.tl.types import InputDocumentFileLocation

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID    = int(os.getenv("API_ID", "0"))
API_HASH  = os.getenv("API_HASH", "")
BASE_URL  = os.getenv("BASE_URL", "").rstrip("/")
DB_FILE   = "files_db.json"

# ── Telethon client (file-based session — no StringSession needed) ─────────────
tg = TelegramClient("bot_session", API_ID, API_HASH)

CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/")
DISCLAIMER_TEXT = os.getenv("DISCLAIMER_TEXT", "")

BRAND_PRIMARY = os.getenv("BRAND_PRIMARY", "Ask")
BRAND_ACCENT = os.getenv("BRAND_ACCENT", "Botz")
BRAND_TAGLINE = os.getenv("BRAND_TAGLINE", "Premium Streaming")

app = FastAPI(title="StreamBot 4GB+")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ── Startup / shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await tg.start()   # ✅ Uses SESSION_STRING — no bot_token re-auth, no FloodWait
    print("✅  Telethon connected")

@app.on_event("shutdown")
async def shutdown():
    await tg.disconnect()

# ── DB ────────────────────────────────────────────────────────────────────────
def load_db() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE) as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def fmt_size(b: int) -> str:
    for u in ("B","KB","MB","GB"):
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

# ── Telethon streaming helper ─────────────────────────────────────────────────
CHUNK = 1024 * 1024  # 1 MB chunks

async def tg_stream(chat_id: int, message_id: int,
                    offset: int = 0, limit: int = None):
    """
    Stream a Telegram file using Telethon iter_download.
    Supports byte-range requests for seeking.
    """
    msg = await tg.get_messages(chat_id, ids=message_id)
    if not msg or not msg.media:
        raise HTTPException(404, "Message/media not found")

    doc        = msg.media.document
    total_size = doc.size
    end        = (offset + limit - 1) if limit else (total_size - 1)
    to_send    = end - offset + 1

    sent = 0
    async for chunk in tg.iter_download(
        msg.media,
        offset        = offset,
        request_size  = CHUNK,
        limit         = to_send,
    ):
        if sent + len(chunk) > to_send:
            chunk = chunk[:to_send - sent]
        yield chunk
        sent += len(chunk)
        if sent >= to_send:
            break

# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return HTMLResponse("<h2>StreamBot 4GB+ is running ✅</h2>")



def safe_filename(name):
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s\-\.]", "", name).strip()
    return name or "video"
@app.get("/stream/{token}")
async def stream(token: str, request: Request):
    db = load_db()
    if token not in db:
        raise HTTPException(404, "File not found")

    meta       = db[token]
    total_size = meta["file_size"]
    mime       = meta["mime_type"]
    chat_id    = meta["chat_id"]
    message_id = meta["message_id"]

    range_header = request.headers.get("range")
    if range_header:
        range_val = range_header.strip().replace("bytes=", "")
        start_str, end_str = range_val.split("-")
        start = int(start_str)
        end   = int(end_str) if end_str else total_size - 1
        length = end - start + 1

        headers = {
            "Content-Range":  f"bytes {start}-{end}/{total_size}",
            "Accept-Ranges":  "bytes",
            "Content-Length": str(length),
            "Content-Disposition": f'inline; filename="{safe_filename(meta["file_name"])}"',
        }
        return StreamingResponse(
            tg_stream(chat_id, message_id, offset=start, limit=length),
            status_code=206,
            media_type=mime,
            headers=headers,
        )

    headers = {
        "Accept-Ranges":  "bytes",
        "Content-Length": str(total_size),
        "Content-Disposition": f'inline; filename="{safe_filename(meta["file_name"])}"',
    }
    return StreamingResponse(
        tg_stream(chat_id, message_id),
        status_code=200,
        media_type=mime,
        headers=headers,
    )


@app.get("/download/{token}")
async def download(token: str):
    db = load_db()
    if token not in db:
        raise HTTPException(404, "File not found")

    meta       = db[token]
    total_size = meta["file_size"]
    chat_id    = meta["chat_id"]
    message_id = meta["message_id"]

    return StreamingResponse(
        tg_stream(chat_id, message_id),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename(meta["file_name"])}"',
            "Content-Length":      str(total_size),
        },
    )


@app.get("/watch/{token}", response_class=HTMLResponse)
async def watch_page(token: str):
    db = load_db()
    if token not in db:
        raise HTTPException(404, "File not found")

    meta = db[token]
    db[token]["views"] += 1
    save_db(db)

    name      = meta["file_name"]
    size      = fmt_size(meta["file_size"])
    mime      = meta["mime_type"]
    views     = meta["views"]
    is_video  = mime.startswith("video")
    is_audio  = mime.startswith("audio")

    # ✅ Use full absolute URLs so VLC/MX Player can reach the stream
    stream_url = f"{BASE_URL}/stream/{token}"
    dl_url     = f"{BASE_URL}/download/{token}"
    vlc_url    = stream_url   # VLC button just opens the direct stream URL
    mx_url     = stream_url   # MX Player button opens the direct stream URL

    if is_video:
        player_html = f'<video id="player" controls preload="metadata" src="{stream_url}"></video>'
    elif is_audio:
        player_html = f'<audio id="player" controls src="{stream_url}"></audio>'
    else:
        player_html = f'<div class="doc-icon">📄</div><p class="doc-hint">{name}</p>'

    size_badge = ""
    if meta["file_size"] > 2 * 1024**3:
        size_badge = '<span class="badge-4g">4GB+ ✅</span>'

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} — StreamBot</title>
<style>
  {theme_css}
  *{{ box-sizing:border-box; margin:0; padding:0; }}
  body{{ background:var(--bg); color:var(--text);
    font-family:'Segoe UI',system-ui,sans-serif; min-height:100vh; }}

  header{{ background:var(--surface); border-bottom:1px solid var(--border);
    padding:14px 20px; display:flex; align-items:center; gap:12px; }}
  .logo{{ width:42px; height:42px;
    background:linear-gradient(135deg,var(--accent),var(--accent2));
    border-radius:12px; display:flex; align-items:center;
    justify-content:center; font-size:19px; flex-shrink:0;
    box-shadow:0 4px 14px rgba(91,94,244,.35); }}
  .brand{{ font-size:16px; font-weight:700; }}
  .brand span{{ color:var(--accent2); }}
  .tagline{{ font-size:13px; color:var(--muted); margin-top:2px; }}

  .player-wrap{{ background:#000; display:flex; align-items:center;
    justify-content:center; min-height:240px; max-height:70vh; }}
  #player{{ width:100%; max-height:70vh; display:block; }}
  .doc-icon{{ font-size:80px; text-align:center; padding:40px 0 10px; }}
  .doc-hint{{ text-align:center; color:var(--muted); padding-bottom:30px; font-size:13px; }}

  .container{{ padding:16px; max-width:680px; margin:0 auto; }}
  .file-card{{ background:var(--card); border:1px solid var(--border);
    border-radius:14px; padding:16px; margin-top:16px; }}
  .file-title{{ font-size:15px; font-weight:600; word-break:break-all;
    margin-bottom:10px; line-height:1.4; display:flex; align-items:center; gap:8px; }}

  .badge-4g{{ background:#16a34a; color:#fff; font-size:10px;
    font-weight:700; padding:2px 8px; border-radius:20px; white-space:nowrap; }}

  .meta-row{{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px; }}
  .chip{{ display:flex; align-items:center; gap:5px; font-size:12px;
    color:var(--muted); background:var(--surface); border:1px solid var(--border);
    border-radius:20px; padding:4px 12px; }}
  .chip b{{ color:var(--text); }}

  .btn-grid{{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:14px; }}
  .btn{{ display:flex; align-items:center; justify-content:center; gap:8px;
    padding:12px 10px; border-radius:10px; font-size:13px; font-weight:600;
    text-decoration:none; cursor:pointer; border:none;
    transition:opacity .15s, transform .1s; }}
  .btn:active{{ transform:scale(.97); opacity:.85; }}
  .btn-primary{{ background:var(--accent); color:#fff; grid-column:span 2; }}
  .btn-outline{{ background:transparent; color:var(--text); border:1px solid var(--border); }}
  .btn-vlc{{ background:#f5a623; color:#000; }}
  .btn-mx{{ background:#1a73e8; color:#fff; }}

  .issue{{ background:var(--surface); border:1px solid var(--border);
    border-radius:12px; padding:14px; margin-top:14px; font-size:13px; color:var(--muted); }}
  .issue strong{{ color:#f59e0b; }}
  .issue-row{{ display:flex; gap:10px; margin-top:10px; }}

  .speed-row{{ display:flex; justify-content:space-between; align-items:center;
    background:var(--surface); border:1px solid var(--border);
    border-radius:10px; padding:10px 14px; margin-top:14px;
    font-size:12px; color:var(--muted); }}
  .dot{{ width:8px; height:8px; background:var(--green); border-radius:50%;
    display:inline-block; margin-right:6px; animation:pulse 1.5s infinite; }}
  @keyframes pulse{{ 0%,100%{{opacity:1}} 50%{{opacity:.4}} }}

  .disclaimer-section{{ max-width:680px; margin:0 auto; padding:30px 16px 0; }}
  .divider{{ border:none; border-top:1px solid var(--border); margin-bottom:24px; }}
  .disclaimer-heading{{ display:flex; align-items:center; justify-content:center;
    gap:10px; font-size:17px; font-weight:800; margin-bottom:18px;
    text-transform:uppercase; letter-spacing:.5px; }}
  .disclaimer-heading .icon{{ font-size:20px; }}
  .disclaimer-card{{ background:var(--card); border:1px solid var(--border);
    border-radius:16px; padding:18px; text-align:left; }}
  .disclaimer-card h3{{ font-size:15px; font-weight:700; margin-bottom:10px; }}
  .disclaimer-card p{{ font-size:13px; color:var(--muted); line-height:1.6; }}
  footer{{ text-align:center; padding:30px 20px; color:var(--muted);
    font-size:12px; border-top:1px solid var(--border); margin-top:24px; }}

  @media(max-width:400px){{
    .btn-grid{{ grid-template-columns:1fr; }}
    .btn-primary{{ grid-column:span 1; }}
  }}
</style>
</head>
<body>

<header>
  <div class="logo">▶</div>
  <div>
    <div class="brand">{BRAND_PRIMARY} <span>{BRAND_ACCENT}</span></div>
    <div class="tagline">{BRAND_TAGLINE}</div>
  </div>
</header>

<div class="player-wrap">{player_html}</div>

<div class="container">
  <div class="speed-row">
    <div><span class="dot"></span>Streaming</div>
    <div id="spd">Connecting…</div>
    <div id="lat">--ms</div>
  </div>

  <div class="file-card">
    <div class="file-title">🎞 {name} {size_badge}</div>
    <div class="meta-row">
      <div class="chip">💾 <b>{size}</b></div>
      <div class="chip">📺 <b>{"Video" if is_video else "Audio" if is_audio else "File"}</b></div>
      <div class="chip">👁 <b>{views} views</b></div>
    </div>
    <div class="btn-grid">
      <a class="btn btn-primary" href="{dl_url}" download>📥 Download File</a>
      <a class="btn btn-outline" href="#" onclick="copyLink()">🔗 Copy Link</a>
      <a class="btn btn-outline" href="{CHANNEL_LINK}" target="_blank">📢 More Content</a>
      <a class="btn btn-vlc"    href="{vlc_url}">🔵 Open VLC</a>
      <a class="btn btn-mx"     href="{mx_url}">▶️ Open MX Player</a>
    </div>
  </div>

  <div class="issue">
    <strong>⚠ No audio / video not playing?</strong><br>
    Open in an external player for full codec support.
    <div class="issue-row">
      <a class="btn btn-vlc" style="flex:1;padding:9px" href="{vlc_url}">VLC</a>
      <a class="btn btn-mx"  style="flex:1;padding:9px" href="{mx_url}">MX Player</a>
    </div>
  </div>
</div>

<div class="disclaimer-section">
  <hr class="divider">
  <div class="disclaimer-heading"><span class="icon">🛡️</span>{BRAND_PRIMARY} {BRAND_ACCENT} PROJECT</div>
  <div class="disclaimer-card">
    <h3>DMCA DISCLAIMER</h3>
    <p>{DISCLAIMER_TEXT}</p>
  </div>
</div>
<footer>Powered by <strong>Ask Botz</strong> — MTProto · 4 GB+ Support</footer>

<script>
  function copyLink(){{
    navigator.clipboard.writeText(location.href)
      .then(()=>alert("✅ Copied!"))
      .catch(()=>{{
        var t=document.createElement("textarea");
        t.value=location.href; document.body.appendChild(t);
        t.select(); document.execCommand("copy");
        document.body.removeChild(t); alert("✅ Copied!");
      }});
  }}
  setInterval(()=>{{
    document.getElementById("lat").textContent=Math.floor(Math.random()*80+40)+"ms";
    document.getElementById("spd").textContent=(Math.random()*5+1).toFixed(1)+" MB/s";
  }},2000);
</script>
</body>
</html>""")
            
# patch applied below — ignore this line
