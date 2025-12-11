# services/dashboard/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (needed for Postgres driver)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project (to access shared modules)
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Command to run the dashboard
CMD ["streamlit", "run", "services/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]