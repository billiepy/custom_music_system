# Copyright (c) 2026 Billiepy
# Licensed under the MIT License.
# This file is part of SiloHelper
import os
import uuid
import asyncio
import yt_dlp
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

# Directory for temporary files
TEMP_DIR = settings.TEMP_DIR
os.makedirs(TEMP_DIR, exist_ok=True)

class DownloadError(Exception):
    pass

class MediaTooLargeError(Exception):
    pass

async def download_media_from_youtube(url: str, media_type: str) -> str:
    """
    Downloads media from youtube and returns the filepath.
    Uses asyncio to avoid blocking the main thread.
    """
    if media_type not in ["audio", "video"]:
        raise ValueError("Invalid media type. Must be 'audio' or 'video'.")

    file_id = str(uuid.uuid4())
    output_template = os.path.join(TEMP_DIR, f"{file_id}.%(ext)s")
    
    ydl_opts = {
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }

    if media_type == "audio":
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        final_ext = "mp3"
    else:
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        final_ext = "mp4"

    def _download():
        import urllib.request
        import tempfile
        
        cookie_file_path = None
        temp_cookie_path = None
        
        # Determine cookies
        cookies_urls = [u for u in settings.COOKIES_URL.split(" ") if u]
        local_fallback = settings.local_cookies_file
        
        for u in cookies_urls:
            try:
                req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    content = response.read()
                    
                fd, temp_path = tempfile.mkstemp(suffix=".txt", text=True)
                os.write(fd, content)
                os.close(fd)
                temp_cookie_path = temp_path
                cookie_file_path = temp_path
                break
            except Exception as e:
                logger.warning(f"Failed to fetch remote cookies from URL, trying next: {e}")
                if temp_cookie_path and os.path.exists(temp_cookie_path):
                    try:
                        os.remove(temp_cookie_path)
                    except Exception:
                        pass
                    temp_cookie_path = None
                continue
                
        if not cookie_file_path:
            if os.path.exists(local_fallback):
                cookie_file_path = local_fallback
                
        if cookie_file_path:
            ydl_opts['cookiefile'] = cookie_file_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Check duration/size roughly
                duration = info.get('duration')
                if duration and duration > settings.DOWNLOAD_TIMEOUT:
                     raise MediaTooLargeError(f"Media is too long: {duration} seconds.")
                
                ydl.download([url])
                
                # Extract metadata
                title = info.get('title', 'Unknown Title')
                if media_type == 'audio':
                    quality = '192kbps'  # Since we force it
                else:
                    quality = info.get('format_note', 'Unknown Quality')
                return {"title": title, "quality": quality}
        except yt_dlp.utils.DownloadError as e:
            raise DownloadError(f"Failed to download: {str(e)}")
        except Exception as e:
            raise DownloadError(f"Unexpected error during download: {str(e)}")
        finally:
            if temp_cookie_path and os.path.exists(temp_cookie_path):
                try:
                    os.remove(temp_cookie_path)
                except Exception:
                    pass
            
    # Run in thread pool
    try:
        metadata = await asyncio.to_thread(_download)
    except Exception as e:
        # Cleanup any partial files with this file_id
        import glob
        for f in glob.glob(os.path.join(TEMP_DIR, f"{file_id}.*")):
            try:
                os.remove(f)
            except Exception:
                pass
        raise e
    
    # Check if file exists
    expected_file = os.path.join(TEMP_DIR, f"{file_id}.{final_ext}")
    if not os.path.exists(expected_file):
        raise DownloadError("Download completed but file not found.")
        
    # Check file size
    file_size_mb = os.path.getsize(expected_file) / (1024 * 1024)
    if file_size_mb > settings.MAX_FILE_SIZE_MB:
        os.remove(expected_file)
        raise MediaTooLargeError(f"File size {file_size_mb:.2f}MB exceeds limit of {settings.MAX_FILE_SIZE_MB}MB.")
        
    return expected_file, metadata
