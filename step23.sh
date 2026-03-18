curl -s -X POST http://localhost:8000/fraud \
  -H "Content-Type: application/json" \
  -d '{"input": "free money hack bypass", "user_id": "bad_actor", "order_amount": 9999}' \
  | python3 -m json.tool
