FROM python:3.11-slim

# Fonts for Pillow-rendered graphics (DejaVu) — optional but sharper output.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist state + generated media across restarts by mounting these.
VOLUME ["/app/data", "/app/out"]

# Config comes from env / --env-file; nothing is baked into the image.
CMD ["python", "main.py"]
