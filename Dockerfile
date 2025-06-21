FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2 (Postgres client)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Expose the default Flask port
EXPOSE 5000

# Set environment variable for production mode
ENV FLASK_ENV=production

# Run the Flask app using python 
CMD ["python", "app.py"]
