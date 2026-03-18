for i in $(seq 1 12); do
  echo -n "Request $i: "
  curl -s -X POST "http://localhost:8000/predict?v=v1" \
    -H "Content-Type: application/json" \
    -d '{"input": "pizza", "user_id": "rate_test_user"}' \
    | grep -o '"detail":"[^"]*"\|"model_version":"[^"]*"' | head -1 | cut -d'"' -f4
done
