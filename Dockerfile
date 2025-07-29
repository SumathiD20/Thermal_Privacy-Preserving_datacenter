# Use an official Python runtime
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the  Python script and required files into the container
COPY . .

# Install system dependencies and Python packages
RUN apt-get update && \
    apt-get install -y gcc && \
    pip install --no-cache-dir \
        numpy \
        joblib \
        scikit-learn \
        cryptography \
        paho-mqtt

# Expose MQTT port
EXPOSE 1883

# Run the Python script
CMD ["python3", "steam_processor.py"]
