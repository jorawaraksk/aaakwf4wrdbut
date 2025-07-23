FROM python:3.10.8-slim-buster

# Avoid upgrade in slim images, install only required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git gcc g++ libffi-dev libssl-dev curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Use a clean path for dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

# Set up app directory
WORKDIR /VJ-Forward-Bot
COPY . .

# Start the bot
CMD ["sh", "-c", "gunicorn app:app & python3 main.py"]
