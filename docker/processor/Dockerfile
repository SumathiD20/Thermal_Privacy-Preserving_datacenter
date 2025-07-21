FROM python:3.9-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the stream processor code (no model or key baked in)
COPY docker/processor/stream_processor.py  ./stream_processor.py
COPY iforest.joblib secret.key ./

# iforest.joblib and secret.key are mounted at runtime from /home/ubuntu/model
CMD ["python", "stream_processor.py"]
