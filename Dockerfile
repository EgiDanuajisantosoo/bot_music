FROM python:3.10-slim

# Install OpenJDK 17 (karena Lavalink butuh Java environment)
RUN apt-get update && \
    apt-get install -y openjdk-17-jre-headless && \
    apt-get clean;

WORKDIR /app

# Install pustaka Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy sisa file bot dan Lavalink.jar
COPY . /app

# Ubah start.sh agar bisa dieksekusi
RUN chmod +x start.sh

# Akses port (standar lavalink)
EXPOSE 2333

# Jalankan skrip bash utama
CMD ["./start.sh"]
