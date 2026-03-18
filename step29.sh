for i in $(seq 1 20); do
  curl -s -X POST "http://localhost:8000/predict?v=v$((RANDOM % 2 + 1))" \
    -H "Content-Type: application/json" \
    -d "{\"input\": \"food $i\", \"user_id\": \"load_user_$i\"}" > /dev/null
done
echo "Done generating traffic"
