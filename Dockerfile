# Use an official Python runtime as a parent image
FROM python:3.11-slim-bullseye

# Set the working directory in the container
WORKDIR /MoneyPrinterTurbo

# Allow the runtime user to write to the application directory.
RUN chmod 777 /MoneyPrinterTurbo

ENV PYTHONPATH="/MoneyPrinterTurbo"

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

# Expose the port the app runs on
EXPOSE 8501

# The container must listen on 0.0.0.0; the Docker port mapping still limits
# host access to 127.0.0.1. browser.serverAddress does not replace server.address.
CMD ["streamlit", "run", "./webui/Main.py", "--server.address=0.0.0.0", "--server.port=8501", "--browser.serverAddress=127.0.0.1", "--server.enableCORS=True", "--browser.gatherUsageStats=False", "--client.toolbarMode=minimal", "--logger.hideWelcomeMessage=True", "--server.showEmailPrompt=False"]

# 1. Build the Docker image using the following command
# docker build -t moneyprinterturbo .

# 2. Run the Docker container using the following command
## For Linux or MacOS:
# docker run -v $(pwd)/config.toml:/MoneyPrinterTurbo/config.toml -v $(pwd)/storage:/MoneyPrinterTurbo/storage -p 127.0.0.1:8501:8501 moneyprinterturbo
## For Windows:
# docker run -v ${PWD}/config.toml:/MoneyPrinterTurbo/config.toml -v ${PWD}/storage:/MoneyPrinterTurbo/storage -p 127.0.0.1:8501:8501 moneyprinterturbo
