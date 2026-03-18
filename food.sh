for i in 1 2 3 4 5 6 7 8; do
  version=$(curl -s -X POST http://localhost:8000/predict \
    -H "Content-Type: application/json" \
    -d "{\"input\": \"pizza\", \"user_id\": \"user_$i\"}" \
    | grep -o '"model_version":"[^"]*"' | cut -d'"' -f4)
  echo "user_$i → $version"
done
