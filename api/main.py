# Copyright (c) 2026 Billiepy
# Licensed under the MIT License.
# This file is part of SiloHelper
import os
import re
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from api.security.auth import verify_api_key, failed_attempts, banned_ips, FAILED_ATTEMPT_WINDOW_SECONDS
from cache.mongodb import mongo_cache
from cache.telegram_cache import telegram_cache
from cache.cache_manager import cache_manager
from api.services.downloader import DownloadError, MediaTooLargeError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_valid_youtube_url(url: str) -> bool:
    import re
    from urllib.parse import urlparse
    
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return True
        
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
            
        hostname = parsed.hostname
        if not hostname:
            return False
            
        hostname = hostname.lower()
        if hostname in ('youtube.com', 'youtu.be'):
            return True
        if hostname.endswith('.youtube.com') or hostname.endswith('.youtu.be'):
            return True
            
        return False
    except Exception:
        return False


async def cleanup_bans():
    while True:
        try:
            await asyncio.sleep(300)
            now = time.time()
            
            expired_bans = [ip for ip, expiry in banned_ips.items() if now > expiry]
            for ip in expired_bans:
                del banned_ips[ip]
                
            empty_ips = []
            for ip, attempts in failed_attempts.items():
                valid = [ts for ts in attempts if now - ts < FAILED_ATTEMPT_WINDOW_SECONDS]
                if not valid:
                    empty_ips.append(ip)
                else:
                    failed_attempts[ip] = valid
            for ip in empty_ips:
                del failed_attempts[ip]
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in ban cleanup task: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    cleanup_task = asyncio.create_task(cleanup_bans())
    await mongo_cache.connect()
    await telegram_cache.connect()
    yield
    # Shutdown
    cleanup_task.cancel()
    await mongo_cache.disconnect()
    await telegram_cache.disconnect()

app = FastAPI(title="Custom Music API", version="1.0.0", lifespan=lifespan)

def cleanup_file(filepath: str):
    """Background task to remove file after response is sent."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Cleaned up file: {filepath}")
    except Exception as e:
        logger.error(f"Error cleaning up file {filepath}: {e}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/download")
async def download_media(
    background_tasks: BackgroundTasks,
    url: str = Query(..., description="YouTube Video ID or URL"),
    type: str = Query(..., description="audio or video"),
    api_key: str = Depends(verify_api_key),
    tg_group_title: str = Query(None, description="Telegram group title"),
    tg_group_id: str = Query(None, description="Telegram group ID"),
    tg_user_name: str = Query(None, description="Telegram user display name"),
    tg_user_id: str = Query(None, description="Telegram user ID")
):
    if type not in ["audio", "video"]:
        raise HTTPException(status_code=400, detail="Invalid media type. Must be 'audio' or 'video'.")
        
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL parameter.")
        
    if not is_valid_youtube_url(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or Video ID.")

    try:
        # Extract youtube_id from URL - simple parsing for this example
        youtube_id = url.split("v=")[-1].split("&")[0] if "v=" in url else url
        if not re.match(r'^[a-zA-Z0-9_-]{11}$', youtube_id):
            # If we couldn't parse a valid 11-char ID, just use a sanitized version for the lock
            youtube_id = "".join(c for c in youtube_id if c.isalnum() or c in "_-")[:20]
            
        tg_context = {
            "group_title": tg_group_title or "Unknown Group",
            "group_id": tg_group_id or "Unknown",
            "user_name": tg_user_name or "Unknown User",
            "user_id": tg_user_id or "Unknown"
        }
            
        filepath, response_sent_event = await cache_manager.process_request(youtube_id, type, url, tg_context)
        
        # Determine media type for response
        media_type = "audio/mpeg" if type == "audio" else "video/mp4"
        filename = os.path.basename(filepath)
        
        if response_sent_event is not None:
            # Cache MISS: the background caching task (Telegram upload + Mongo
            # save) owns file cleanup once it's done with the file. Signal it
            # that the response has been fully sent, so it knows it's safe to
            # delete the file without racing this FileResponse's own read.
            background_tasks.add_task(response_sent_event.set)
        else:
            # Cache HIT: same behavior as before, clean up right after sending.
            background_tasks.add_task(cleanup_file, filepath)
        
        return FileResponse(
            path=filepath, 
            media_type=media_type, 
            filename=filename
        )
        
    except MediaTooLargeError as e:
        logger.warning(f"Media too large: {e}")
        raise HTTPException(status_code=413, detail="Media file is too large.")
    except DownloadError as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail="Failed to download or process media.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")

