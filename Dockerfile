# Use lightweight Python 3.12 image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer outputs
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source code
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Default command launches the Streamlit Web UI
CMD ["streamlit", "run", "jira_coder_ui.py", "--server.address=0.0.0.0", "--server.port=8501"]
