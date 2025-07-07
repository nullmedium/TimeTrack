FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    python3-dev \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
ENV TZ=Europe/Berlin

# Create www-data user and log directory
RUN groupadd -r www-data && useradd -r -g www-data www-data || true
RUN mkdir -p /var/log/uwsgi && chown -R www-data:www-data /var/log/uwsgi
RUN mkdir -p /host/shared && chown -R www-data:www-data /host/shared

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn==21.2.0

# Copy the rest of the application
COPY . .

# Create the SQLite database directory with proper permissions
RUN mkdir -p /app/instance && chmod 777 /app/instance

# Create uploads directory with proper permissions
RUN mkdir -p /app/static/uploads/avatars && chmod -R 777 /app/static/uploads

VOLUME /data
RUN mkdir /data && chmod 777 /data

# Make startup scripts executable
RUN chmod +x startup.sh startup_postgres.sh || true

# Expose the port the app runs on (though we'll use unix socket)
EXPOSE 5000

# Use PostgreSQL-only startup script
CMD ["./startup_postgres.sh"]