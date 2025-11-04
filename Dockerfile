# Use official Python base image
FROM python:3.12-slim

# Prevent Python from writing pyc files & buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# 6️⃣ Copy and prepare startup script
RUN chmod +x scripts/wait_for_db.sh

# Expose Django port
EXPOSE 8000

# Run the Django server
CMD ["./scripts/wait_for_db.sh"]
