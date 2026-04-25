# Remotion Video Renderer — Cloud Run Job (CPU)
# 8 vCPU / 16Gi RAM recommended for 1080p render
FROM node:20-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    chromium \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

RUN groupadd -r renderer && useradd -r -g renderer renderer && \
    chown -R renderer:renderer /app

USER renderer

CMD ["node", "dist/render.js"]
