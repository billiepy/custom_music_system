# Copyright (c) 2026 Billiepy
# Licensed under the MIT License.
# This file is part of SiloHelper
import os
import uuid
import asyncio
import logging
from cache.mongodb import mongo_cache
from cache.telegram_cache import telegram_cache
from api.services.downloader import download_media_from_youtube, TEMP_DIR

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        self.locks = {}
        self.locks_lock = asyncio.Lock()

    async def get_lock(self, key: str):
        async with self.locks_lock:
            if key not in self.locks:
                self.locks[key] = asyncio.Lock()
            return self.locks[key]

    async def release_lock(self, key: str):
        async with self.locks_lock:
            if key in self.locks:
                # We don't delete locks immediately to avoid race conditions 
                # where another request is waiting on the same lock object,
                # but we could implement a cleanup strategy later if memory is a concern.
                pass

    async def process_request(self, youtube_id: str, media_type: str, url: str, tg_context: dict = None) -> str:
        """
        Main entry point for media requests.
        Returns the absolute filepath to the requested media (downloaded or cached).
        """
        if tg_context is None:
            tg_context = {
                "group_title": "Unknown Group",
                "group_id": "Unknown",
                "user_name": "Unknown User",
                "user_id": "Unknown"
            }
            
        lock_key = f"{youtube_id}_{media_type}"
        lock = await self.get_lock(lock_key)
        
        async with lock:
            # 1. Check MongoDB Cache (CACHE HIT)
            cached_data = await mongo_cache.find_cached_media(youtube_id, media_type)
            if cached_data and cached_data.get("telegram_message_id"):
                logger.info(f"CACHE HIT: {youtube_id} ({media_type})")
                
                # Try to download from Telegram
                file_ext = "mp3" if media_type == "audio" else "mp4"
                output_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.{file_ext}")
                
                success = await telegram_cache.download_media(
                    cached_data["telegram_message_id"],
                    cached_data["telegram_file_id"],
                    output_path
                )
                
                if success:
                    await mongo_cache.update_cache_usage(youtube_id, media_type)
                    return output_path
                else:
                    logger.warning(f"Telegram download failed for cached item {youtube_id}. Treating as CACHE MISS.")
                    if os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                        except Exception:
                            pass
            
            # 2. CACHE MISS
            logger.info(f"CACHE MISS: {youtube_id} ({media_type})")
            
            # Download from YouTube
            filepath, metadata = await download_media_from_youtube(url, media_type)
            
            # Construct formatted caption
            import datetime
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            caption = (
                f"Title: {metadata.get('title', 'Unknown')}\n"
                f"Quality: {metadata.get('quality', 'Unknown')}\n"
                f"Source: YouTube\n"
                f"ID: {youtube_id}\n"
                f"Type: {media_type}\n"
                f"Group: {tg_context['group_title']} ({tg_context['group_id']})\n"
                f"Requested by: {tg_context['user_name']} ({tg_context['user_id']})\n"
                f"Timestamp: {timestamp}"
            )
            
            # Upload to Telegram cache channel
            tg_data = await telegram_cache.upload_media(filepath, media_type, caption)
            
            # Save to MongoDB if upload was successful
            if tg_data:
                cache_record = {
                    "youtube_id": youtube_id,
                    "media_type": media_type,
                    "title": metadata.get("title", youtube_id),
                    **tg_data
                }
                await mongo_cache.save_cached_media(cache_record)
            
            return filepath

cache_manager = CacheManager()
