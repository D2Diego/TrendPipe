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

# Local builds prefer regional mirrors. GitHub Actions uses the default mirrors
# to avoid slow cross-region downloads while publishing the GHCR image.
ARG DOCKER_BUILD_MIRROR=china
ARG PIP_USE_OFFICIAL=0

# Install system dependencies with retry logic
RUN if [ "$DOCKER_BUILD_MIRROR" = "china" ]; then \
        echo "deb http://mirrors.aliyun.com/debian bullseye main" > /etc/apt/sources.list && \
        echo "deb http://mirrors.aliyun.com/debian-security bullseye-security main" >> /etc/apt/sources.list; \
    else \
        echo "Using default Debian mirrors"; \
    fi && \
    ( \
        for i in 1 2 3; do \
            echo "Attempt $i: installing system dependencies"; \
            apt-get update && apt-get install -y --no-install-recommends \
                git \
                ffmpeg && break || \
            echo "Attempt $i failed, retrying..."; \
            if [ "$DOCKER_BUILD_MIRROR" = "china" ] && [ $i -eq 3 ]; then \
                echo "Aliyun mirror failed, switching to Tsinghua mirror"; \
                sed -i 's/mirrors.aliyun.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
                sed -i 's/mirrors.aliyun.com\/debian-security/mirrors.tuna.tsinghua.edu.cn\/debian-security/g' /etc/apt/sources.list && \
                ( \
                    apt-get update && apt-get install -y --no-install-recommends \
                        git \
                        ffmpeg || \
                    ( \
                        echo "Tsinghua mirror failed, switching to default Debian mirror"; \
                        sed -i 's/mirrors.tuna.tsinghua.edu.cn/deb.debian.org/g' /etc/apt/sources.list && \
                        sed -i 's/mirrors.tuna.tsinghua.edu.cn\/debian-security/security.debian.org/g' /etc/apt/sources.list; \
                        apt-get update && apt-get install -y --no-install-recommends \
                            git \
                            ffmpeg; \
                    ); \
                ); \
            fi; \
            sleep 5; \
        done \
    ) && rm -rf /var/lib/apt/lists/*

# Copy only the requirements.txt first to leverage Docker cache
COPY requirements.txt ./

# Local builds prefer regional PyPI mirrors. GHCR builds use official PyPI.
RUN if [ "$PIP_USE_OFFICIAL" = "1" ]; then \
        pip install --no-cache-dir --retries 3 --timeout 60 -r requirements.txt; \
    else \
        pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --retries 3 --timeout 60 -r requirements.txt || \
        pip install --no-cache-dir -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple/ --trusted-host mirrors.tuna.tsinghua.edu.cn --retries 3 --timeout 60 -r requirements.txt || \
        pip install --no-cache-dir --retries 3 --timeout 60 -r requirements.txt; \
    fi

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
