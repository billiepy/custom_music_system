import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings

logger = logging.getLogger(__name__)

class MongoCache:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None

    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URI)
            self.db = self.client[settings.MONGODB_DATABASE]
            self.collection = self.db["media_cache"]
            
            # Create unique index on youtube_id and media_type
            await self.collection.create_index(
                [("youtube_id", 1), ("media_type", 1)],
                unique=True,
                background=True
            )
            logger.info("MongoDB connected and index verified.")
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")

    async def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB disconnected.")

    async def find_cached_media(self, youtube_id: str, media_type: str) -> dict | None:
        if not self.collection:
            return None
        try:
            return await self.collection.find_one({"youtube_id": youtube_id, "media_type": media_type})
        except Exception as e:
            logger.error(f"MongoDB find error: {e}")
            return None

    async def save_cached_media(self, data: dict) -> bool:
        if not self.collection:
            return False
        try:
            now = datetime.now(timezone.utc)
            data["created_at"] = data.get("created_at", now)
            data["last_used_at"] = now
            data["play_count"] = 1

            await self.collection.update_one(
                {"youtube_id": data["youtube_id"], "media_type": data["media_type"]},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"MongoDB save error: {e}")
            return False

    async def update_cache_usage(self, youtube_id: str, media_type: str) -> bool:
        if not self.collection:
            return False
        try:
            await self.collection.update_one(
                {"youtube_id": youtube_id, "media_type": media_type},
                {
                    "$set": {"last_used_at": datetime.now(timezone.utc)},
                    "$inc": {"play_count": 1}
                }
            )
            return True
        except Exception as e:
            logger.error(f"MongoDB update usage error: {e}")
            return False

mongo_cache = MongoCache()
