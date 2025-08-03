# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install system dependencies required for psycopg2
RUN apt-get update && apt-get install -y build-essential libpq-dev gcc

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Run main.py when the container launches
CMD ["python", "main.py"]
