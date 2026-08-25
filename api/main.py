import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from api.security.auth import verify_api_key
from cache.mongodb import mongo_cache
from cache.telegram_cache import telegram_cache
from cache.cache_manager import cache_manager
from api.services.downloader import DownloadError, MediaTooLargeError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await mongo_cache.connect()
    await telegram_cache.connect()
    yield
    # Shutdown
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
        
    # Basic validation for YouTube URL or ID to prevent command injection / unexpected behavior
    import re
    if not re.match(r'^[a-zA-Z0-9_-]{11}$', url) and not url.startswith(('http://', 'https://')):
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
            
        filepath = await cache_manager.process_request(youtube_id, type, url, tg_context)
        
        # Determine media type for response
        media_type = "audio/mpeg" if type == "audio" else "video/mp4"
        filename = os.path.basename(filepath)
        
        # Add cleanup task to run after the response is sent
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

