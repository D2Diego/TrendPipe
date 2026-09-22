# Build the production React application.
FROM node:20-alpine AS frontend-build

WORKDIR /build/webui-react

COPY webui-react/package.json webui-react/package-lock.json ./
RUN npm ci

COPY webui-react/ ./

ARG VITE_APP_VERSION=1.3.3
RUN VITE_APP_VERSION="$VITE_APP_VERSION" npm run build

FROM python:3.12-slim-bullseye

# Set the working directory in the container
WORKDIR /TrendPipe

# Allow the runtime user to write to the application directory.
RUN chmod 777 /TrendPipe

ENV PYTHONPATH="/TrendPipe"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements.txt first to leverage Docker cache
COPY requirements.txt ./

RUN pip install --no-cache-dir --retries 3 --timeout 60 -r requirements.txt

# Now copy the rest of the codebase into the image
COPY . .

# Install the built frontend where FastAPI already serves static files from
# (app.asgi mounts /assets and falls back to this index.html for every other
# non-API route). One process now serves the UI and the API - no more
# separate Nginx container.
COPY --from=frontend-build /build/webui-react/dist/ ./resource/public/

EXPOSE 8080

CMD ["python3", "main.py"]

# 1. Build the Docker image using the following command
# docker build -t trendpipe .

# 2. Run the Docker container using the following command
# docker compose up
