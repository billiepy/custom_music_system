#!/bin/bash
# Copyright (c) 2026 Billiepy
# Licensed under the MIT License.
# This file is part of SiloHelper
set -e

# Change to the directory where the script is located
cd "$(dirname "$0")"

# Check if the process is already running on port 8000
PID=$(lsof -t -i:8000 || true)
if [ ! -z "$PID" ]; then
    echo "Stopping existing process on port 8000 (PID: $PID)..."
    kill $PID
    sleep 2
    # Force kill if still running
    PID_CHECK=$(lsof -t -i:8000 || true)
    if [ ! -z "$PID_CHECK" ]; then
        kill -9 $PID_CHECK
        sleep 1
    fi
fi

# Alternatively, check if uvicorn is running for this specific app
# We'll rely on the port for now, but also stop.sh logic is more precise

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting FastAPI/Uvicorn server..."
# Run uvicorn in the background
nohup uvicorn api.main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &

NEW_PID=$!
echo "Server started with PID: $NEW_PID"
echo "Listening on http://127.0.0.1:8000"
