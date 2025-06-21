FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2 (Postgres client)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Expose Flask port
EXPOSE 5000

# Set Flask env variable (optional)
ENV FLASK_ENV=development

# Run Flask app
CMD ["flask", "run", "--host=0.0.0.0"]
