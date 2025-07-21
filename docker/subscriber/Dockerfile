FROM python:3.9-slim
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy subscriber code
COPY docker/subscriber/subscriber.py  ./subscriber.py
# secret.key will be mounted at runtime

CMD ["python", "subscriber.py"]

