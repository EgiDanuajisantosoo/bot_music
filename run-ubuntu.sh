#!/bin/bash

set -e

echo "========================================="
echo "  Menjalankan Bot Musik"
echo "========================================="

if [ ! -d "venv" ]; then
    echo "venv belum ada. Jalankan ./setup-ubuntu.sh dulu."
    exit 1
fi

source venv/bin/activate

if [ ! -f "Lavalink.jar" ]; then
    echo "ERROR: Lavalink.jar tidak ditemukan!"
    exit 1
fi

echo "Memulai Lavalink server..."
java -jar Lavalink.jar > ./logs/lavalink_stdout.log 2>&1 &
LAVALINK_PID=$!

cleanup() {
    kill "$LAVALINK_PID" 2>/dev/null || true
}

trap cleanup EXIT

echo "Menunggu Lavalink server siap..."
sleep 10

echo "Memulai Discord Bot + Web API di port 8081..."
python -u main.py > logs/bot.log 2>&1