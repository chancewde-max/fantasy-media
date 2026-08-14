FROM python:3.11-slim

# Fonts for Pillow-rendered graphics (DejaVu) — optional but sharper output.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# State + generated media live in /app/data and /app/out. To persist them
# across restarts:
#   - Docker:  docker run -v $PWD/data:/app/data -v $PWD/out:/app/out ...
#   - Railway: attach a Volume with mount path /app/data (Service > Settings > Volumes)
# Railway does not support the Dockerfile VOLUME instruction, so it's omitted here.

# Config comes from env / --env-file; nothing is baked into the image.
CMD ["python", "main.py"]
