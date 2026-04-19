#!/bin/bash
# Menjalankan server Lavalink di background
java -jar Lavalink.jar &

# Beri waktu jeda 10 detik agar Lavalink server siap menerima koneksi
echo "Menunggu Lavalink (Java) menyala..."
sleep 10

# Mulai discord bot Python
echo "Memulai Discord Bot Music..."
python main.py
