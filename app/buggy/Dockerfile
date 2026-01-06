FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask prometheus-client

# Copy application
COPY app.py .

# Environment
ENV ENVIRONMENT=testing
ENV FLASK_APP=app.py

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

EXPOSE 5000

CMD ["python3", "app.py"]
