#!/bin/bash
set -e

echo "Stopping custom_music_system API..."

# Find pids matching uvicorn api.main:app
PIDS=$(ps aux | grep "uvicorn api.main:app" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "No running instances found for this project."
else
    for PID in $PIDS; do
        echo "Killing PID $PID..."
        kill $PID
    done
    sleep 2
    
    # Check if any are still running and force kill
    PIDS_CHECK=$(ps aux | grep "uvicorn api.main:app" | grep -v grep | awk '{print $2}')
    if [ ! -z "$PIDS_CHECK" ]; then
        for PID in $PIDS_CHECK; do
            echo "Force killing PID $PID..."
            kill -9 $PID
        done
    fi
    echo "Stopped successfully."
fi
