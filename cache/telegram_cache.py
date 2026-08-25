# Copyright (c) 2026 Billiepy
# Licensed under the MIT License.
# This file is part of SiloHelper
import os
import logging
from pyrogram import Client
from config.settings import settings

logger = logging.getLogger(__name__)

class TelegramCache:
    def __init__(self):
        self.app = None
        self.is_connected = False
        
        # Determine if we should attempt connection based on token presence
        self.can_connect = bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CACHE_CHANNEL_ID)

    async def connect(self):
        if not self.can_connect:
            return
        if not self.app:
            self.app = Client(
                "cache_bot",
                api_id=settings.TELEGRAM_API_ID,
                api_hash=settings.TELEGRAM_API_HASH,
                bot_token=settings.TELEGRAM_BOT_TOKEN,
                workdir=os.path.dirname(__file__)
            )
        try:
            await self.app.start()
            self.is_connected = True
            logger.info("Telegram Cache Bot connected.")
            
            # Ensure the channel is resolved in Pyrogram's cache
            channel_id_str = settings.TELEGRAM_CACHE_CHANNEL_ID
            try:
                channel_id = int(channel_id_str)
                await self.app.get_chat(channel_id)
            except ValueError as e:
                if "Peer id invalid" in str(e):
                    logger.info("PeerIdInvalid encountered. Attempting HTTP API workaround...")
                    import httpx
                    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getChat"
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(url, json={"chat_id": channel_id})
                        data = resp.json()
                        if data.get("ok"):
                            username = data["result"].get("username")
                            if username:
                                await self.app.get_chat(username)
                                logger.info(f"Resolved channel via username @{username}")
                            else:
                                logger.error("Channel is private and has no username. Cannot resolve via HTTP API workaround.")
                        else:
                            logger.error(f"HTTP API getChat failed: {data}")
        except Exception as e:
            logger.error(f"Telegram connection error: {e}")

    async def disconnect(self):
        if self.is_connected and self.app:
            try:
                await self.app.stop()
                self.is_connected = False
                logger.info("Telegram Cache Bot disconnected.")
            except Exception as e:
                logger.error(f"Telegram disconnection error: {e}")

    async def upload_media(self, file_path: str, media_type: str, caption: str = "") -> dict | None:
        if not self.is_connected or not self.app:
            return None
            
        try:
            channel_id = int(settings.TELEGRAM_CACHE_CHANNEL_ID)
            
            import asyncio
            UPLOAD_TIMEOUT = 30
            
            if media_type == "audio":
                upload_coro = self.app.send_audio(
                    chat_id=channel_id,
                    audio=file_path,
                    caption=caption
                )
            else:
                upload_coro = self.app.send_video(
                    chat_id=channel_id,
                    video=file_path,
                    caption=caption
                )
                
            upload_task = asyncio.create_task(upload_coro)
            msg = await asyncio.wait_for(asyncio.shield(upload_task), timeout=UPLOAD_TIMEOUT)
            
            if media_type == "audio":
                file_id = msg.audio.file_id if msg.audio else None
            else:
                file_id = msg.video.file_id if msg.video else None

            if msg and file_id:
                return {
                    "telegram_channel_id": str(channel_id),
                    "telegram_message_id": msg.id,
                    "telegram_file_id": file_id
                }
            return None
        except asyncio.TimeoutError:
            logger.error(f"Telegram upload timed out after {UPLOAD_TIMEOUT} seconds")
            return None
        except Exception as e:
            logger.error(f"Telegram upload error: {e}")
            return None

    async def download_media(self, message_id: int, file_id: str, output_path: str) -> bool:
        if not self.is_connected or not self.app:
            return False
            
        try:
            channel_id = int(settings.TELEGRAM_CACHE_CHANNEL_ID)
            msg = await self.app.get_messages(chat_id=channel_id, message_ids=message_id)
            if not msg or msg.empty:
                logger.error("Message not found in cache channel.")
                return False
                
            # Download directly with pyrogram
            await self.app.download_media(msg, file_name=output_path)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
            return False
        except Exception as e:
            logger.error(f"Telegram download error: {e}")
            return False

telegram_cache = TelegramCache()
