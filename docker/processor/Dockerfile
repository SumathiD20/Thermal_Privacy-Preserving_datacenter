FROM python:3.9-slim

WORKDIR /app

COPY ../../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model, key, and processor script
COPY stream_processor.py iforest.joblib ./

CMD ["python", "stream_processor.py"]
