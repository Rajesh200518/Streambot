#!/usr/bin/env python3
"""
Run both the Telegram bot and the web server concurrently.
Usage: python run.py
"""
import asyncio
import subprocess
import sys
import os
from dotenv import load_dotenv

load_dotenv()

async def run_all():
    bot_proc    = await asyncio.create_subprocess_exec(sys.executable, "bot.py")
    server_proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "uvicorn", "server:app",
        "--host", "0.0.0.0", "--port", "8000", "--reload"
    )
    print("✅ Bot started")
    print("✅ Web server started on http://0.0.0.0:8000")
    await asyncio.gather(bot_proc.wait(), server_proc.wait())

if __name__ == "__main__":
    asyncio.run(run_all())

