#!/bin/bash

set -e

echo "========================================="
echo "  Setup Bot Musik untuk Ubuntu"
echo "========================================="

echo "egi@VPS" | sudo -S apt-get update
echo "egi@VPS" | sudo -S apt-get install -y python3-pip python3-venv python3-dev openjdk-17-jre-headless curl

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if ! command -v cloudflared >/dev/null 2>&1; then
    curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    echo "egi@VPS" | sudo -S dpkg -i cloudflared.deb || echo "egi@VPS" | sudo -S apt-get -f install -y
    rm -f cloudflared.deb
fi

if [ ! -f "Lavalink.jar" ] || ! grep -q "4.2.0" version.txt 2>/dev/null; then
    echo "Mendownload Lavalink.jar v4.2.0..."
    rm -f Lavalink.jar
    curl -L -o Lavalink.jar https://github.com/lavalink-devs/Lavalink/releases/download/4.2.0/Lavalink.jar
    echo "4.2.0" > version.txt
fi

echo "Setup selesai. Jalankan ./run-ubuntu.sh"