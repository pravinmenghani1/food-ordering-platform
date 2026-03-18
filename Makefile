.PHONY: up down test logs clean

up:
	docker-compose up --build -d
	@echo "✅ SmartFood AI Platform is running!"
	@echo "  API Gateway:    http://localhost:8000/docs"
	@echo "  Grafana:        http://localhost:3000  (admin/admin)"
	@echo "  Prometheus:     http://localhost:9090"
	@echo "  Jaeger UI:      http://localhost:16686"

down:
	docker-compose down -v
	@echo "✅ All services stopped."

logs:
	docker-compose logs -f api-gateway inference-service

test:
	@echo "🧪 Running smoke tests..."
	@curl -s -X POST http://localhost:8000/predict \
		-H "Content-Type: application/json" \
		-d '{"input": "I love spicy food", "user_id": "user_001"}' | python3 -m json.tool
	@echo "\n🧪 Testing fraud detection..."
	@curl -s -X POST http://localhost:8000/fraud \
		-H "Content-Type: application/json" \
		-d '{"input": "free money order hack", "user_id": "user_002"}' | python3 -m json.tool
	@echo "\n🧪 Testing legacy image..."
	@curl -s http://localhost:8000/image/legacy?item=pizza | python3 -m json.tool
	@echo "\n🧪 Testing AI image generation..."
	@curl -s -X POST http://localhost:8000/image/generate \
		-H "Content-Type: application/json" \
		-d '{"item_name": "Spicy Margherita Pizza", "description": "crispy crust, fresh basil"}' | python3 -m json.tool

clean:
	docker-compose down -v --rmi all
