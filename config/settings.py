# Copyright (c) 2026 Billiepy
# Licensed under the MIT License.
# This file is part of SiloHelper
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

class Settings(BaseSettings):
    _project_root: str = os.path.dirname(os.path.dirname(__file__))
    
    API_KEYS: str = os.getenv("API_KEY", os.getenv("API_KEYS", "YOUR_SECURE_API_KEY_HERE"))
    
    COOKIES_URL: str = os.getenv("COOKIES_URL", "")
    
    @property
    def local_cookies_file(self) -> str:
        return os.path.join(self._project_root, "api", "cookies", "cookies.txt")

    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", "300"))
    TEMP_DIR: str = os.getenv("TEMP_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_downloads"))
    
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "custom_music_db")
    
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CACHE_CHANNEL_ID: str = os.getenv("TELEGRAM_CACHE_CHANNEL_ID", "")
    TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", "12345"))
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "dummy_hash")

    @property
    def valid_api_keys(self) -> list[str]:
        return [key.strip() for key in self.API_KEYS.split(",") if key.strip()]

settings = Settings()
