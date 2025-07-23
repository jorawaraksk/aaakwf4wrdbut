FROM python:3.10-slim

# Avoid prompts and ensure compatibility
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git build-essential libffi-dev libssl-dev curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /tmp/requirements.txt

# Setup working directory and copy project
WORKDIR /VJ-Forward-Bot
COPY . .

# Start your app and bot
CMD ["sh", "-c", "gunicorn app:app & python3 main.py"]
