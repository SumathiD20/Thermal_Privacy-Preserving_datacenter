FROM python:3.9-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what this service needs (paths are from repo root)
COPY docker/publisher/publisher.py     ./publisher.py
COPY temp_reading.csv                  ./temp_reading.csv
COPY secret.key .
# secret.key will be mounted at runtime

CMD ["python", "publisher.py"]

