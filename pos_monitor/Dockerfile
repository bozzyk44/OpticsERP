# pos_monitor/Dockerfile
# POS Monitor - Local dashboard for POS terminals

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create logs directory
RUN mkdir -p /app/logs

# Create placeholder for static files (frontend will be added later)
RUN mkdir -p /app/static && \
    echo '<html><body><h1>POS Monitor</h1><p>Frontend coming soon. API available at <a href="/api/docs">/api/docs</a></p></body></html>' > /app/static/index.html

# Expose port 8001
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8001/health', timeout=2)" || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
