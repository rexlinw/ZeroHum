FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI from official Docker repo
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian trixie stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    docker-ce-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir flask requests prometheus-client docker

# Copy application files
COPY ui.py .
COPY templates/ ./templates/
COPY static/ ./static/

# Create data directory
RUN mkdir -p /app/data

# Environment
ENV FLASK_APP=ui.py
ENV LOG_LEVEL=INFO
ENV PROMETHEUS_URL=http://prometheus:9090

EXPOSE 8000

CMD ["python3", "ui.py"]
