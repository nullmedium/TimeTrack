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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create the SQLite database directory with proper permissions
RUN mkdir -p /app/instance && chmod 777 /app/instance

VOLUME /data
RUN mkdir /data && chmod 777 /data

# Expose the port the app runs on
EXPOSE 5000

# Database will be created at runtime when /data volume is mounted

# Command to run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]