FROM python:3.11-slim
WORKDIR /app
# Copy shared modules
COPY schemas/ ./schemas/
COPY observability/ ./observability/
# Copy service
COPY api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api-gateway/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
