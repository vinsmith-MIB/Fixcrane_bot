# Use an official Python runtime as a parent image
FROM python:3.11.3-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to leverage Docker cache
COPY requirements.txt .

# Add contrib/non-free, update, and install all system dependencies in one layer
RUN sed -i 's/ main/ main contrib non-free/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        postgresql-client \
        unrar \
        dos2unix \
        fontconfig && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Copy simsun.ttc font to system fonts and refresh font cache
RUN mkdir -p /usr/share/fonts/truetype/simsun && \
    cp /app/assets/simsun.ttc /usr/share/fonts/truetype/simsun/simsun.ttc && \
    fc-cache -f -v

# Convert the script's line endings to Unix format and make it executable
RUN dos2unix /app/wait-for-db.sh
RUN chmod +x /app/wait-for-db.sh

# Run the wait script before starting the main application
CMD ["/app/wait-for-db.sh", "db", "python", "main.py"]
