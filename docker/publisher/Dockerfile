FROM python:3.9-slim

# 1. Set workdir
WORKDIR /app

# 2. Copy requirements & install
COPY ../../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy code and secret & data
COPY publisher.py .
COPY temp_reading.csv .

# 4. Run publisher
CMD ["python", "publisher.py"]
