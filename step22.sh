curl -s -X POST http://localhost:8000/fraud \
  -H "Content-Type: application/json" \
  -d '{"input": "2 pizzas and a coke", "user_id": "normal_user", "order_amount": 25}' \
  | python3 -m json.tool
