FROM python:3.11-slim
WORKDIR /app
COPY services/inference-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/inference-service/ .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
