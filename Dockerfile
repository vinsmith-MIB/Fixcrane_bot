# Use an official Python runtime as a parent image
FROM python:3.11.3-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install system dependencies required for psycopg2 and psql
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev gcc postgresql-client unrar && \
    rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Copy the wait script and make it executable
COPY wait-for-db.sh /app/wait-for-db.sh
RUN chmod +x /app/wait-for-db.sh

# Run the wait script before starting the main application
CMD ["/app/wait-for-db.sh", "db", "python", "main.py"]
