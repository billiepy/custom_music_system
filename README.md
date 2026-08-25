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
- `API_KEY`: A long, random secure string. The ShrutiMusic bot must use this same key.
- `MONGODB_URI`: Connection string for MongoDB (e.g., `mongodb://localhost:27017`).
- `MONGODB_DATABASE`: The name of the database to store cache metadata.
- `TELEGRAM_BOT_TOKEN`: The token of your caching bot.
- `TELEGRAM_CACHE_CHANNEL_ID`: The ID of the private Telegram channel where media is stored. (Bot must be an Admin).
- `YT_COOKIES_FILE`: (Optional) Absolute path to a valid `cookies.txt` for `yt-dlp`. Do not commit this file.

**Security Note:** Never commit your `.env`, cookies, or session files to source control. They are protected by `.gitignore`.

## Localhost Startup
```bash
source venv/bin/activate
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

## API Endpoints
**Health Check**
`GET /health`
Returns `{"status": "ok"}`

**Download Media**
`GET /download?url=<VIDEO_ID>&type=audio&api_key=<YOUR_KEY>`
`GET /download?url=<VIDEO_ID>&type=video&api_key=<YOUR_KEY>`
Returns binary media data matching the requested type (`audio/mpeg` or `video/mp4`).

## Docker Deployment
To deploy using Docker on a production VPS:
```bash
docker build -t custom_music_system .
docker run -d \
  --name custom-music-api \
  --env-file .env \
  -v /path/to/cookies.txt:/app/cookies.txt \
  -p 8000:8000 \
  custom_music_system
```
*(Only mount `cookies.txt` if you are actively using it, and ensure `YT_COOKIES_FILE=/app/cookies.txt` is set in your `.env`)*
