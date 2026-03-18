FROM python:3.11-slim
WORKDIR /app
COPY event-system/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY event-system/ .
CMD ["python", "consumers/feedback_consumer.py"]
