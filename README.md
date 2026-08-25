# Custom Music System

A standalone YouTube media API and Telegram media-cache backend designed to be completely compatible with the existing ShrutiMusic bot.

## Project Structure
- `api/`: FastAPI application, endpoints, and background services.
- `cache/`: MongoDB caching layer and Telegram cache channel client.
- `config/`: Environment configuration management.
- `tests/`: Automated unit tests.

## Requirements
- Python 3.10+
- FFmpeg (required by `yt-dlp` for audio extraction and muxing)
- MongoDB (local or remote)

## Local Installation

```bash
cd /root/custom_music_system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration
Copy the environment template:
```bash
cp .env.example .env
```
Edit `.env` and fill in your details:
- `API_KEY`: A long, random secure string.
- `MONGODB_URI`: Connection string for MongoDB.
- `MONGODB_DATABASE`: The name of the database to store cache metadata.
- `TELEGRAM_BOT_TOKEN`: The token of your caching bot.
- `TELEGRAM_CACHE_CHANNEL_ID`: The ID of the private Telegram channel where media is stored. (Bot must be an Admin).
- `YT_COOKIES_FILE`: (Optional) Absolute path to a valid `cookies.txt` for `yt-dlp`. Do not commit this file.

**Security Note:** Never commit your `.env`, cookies, or session files to source control.

## Quick Start / Running the API

Start the API server (runs on `127.0.0.1:8000`):
```bash
cd /root/custom_music_system && ./start.sh
```

Stop the API server:
```bash
cd /root/custom_music_system && ./stop.sh
```

## Features & Cache Behavior

- **Audio Quality**: Audio downloads are strictly optimized to **192 kbps MP3** (balancing streaming quality, file size, and download speed).
- **Telegram Caching**:
  - **New song**: Downloads from YouTube -> Uploads ONE message to the Telegram cache channel -> Saves the MongoDB `telegram_file_id` cache.
  - **Same song request**: Reuses the cached Telegram file directly (based on YouTube video ID + media type) -> NO duplicate upload.
  - **Different song**: Fetches and performs a new Telegram upload.
- **Telegram Metadata**: Every new Telegram cache upload includes a detailed caption:
  - Title
  - Quality (e.g. 192kbps)
  - Source (YouTube)
  - ID
  - Type (audio)
  - Group (Title and ID)
  - Requested by (User name and ID)
  - Timestamp

## API Endpoints
**Health Check**
`GET /health`
Returns `{"status": "ok"}`

**Download Media**
`GET /download?url=<VIDEO_ID>&type=audio&api_key=<YOUR_KEY>&tg_group_title=...&tg_group_id=...&tg_user_name=...&tg_user_id=...`
Returns binary media data.

## Docker Deployment
To deploy using Docker:
```bash
docker build -t custom_music_system .
docker run -d \
  --name custom-music-api \
  --env-file .env \
  -p 8000:8000 \
  custom_music_system
```
