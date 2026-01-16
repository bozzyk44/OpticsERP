#!/bin/bash
#
# Smoke test for KKT Adapter API
# Tests all endpoints with curl
#

BASE_URL="http://localhost:8001"

echo "=== KKT Adapter API Smoke Test ==="
echo ""

# Test 1: Root endpoint
echo "1. Testing GET /"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/")
http_code=$(echo "$response" | tail -1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    echo "✅ Root endpoint OK"
    echo "$body" | python -m json.tool
else
    echo "❌ Root endpoint failed (HTTP $http_code)"
    echo "$body"
fi

echo ""

# Test 2: Health check
echo "2. Testing GET /v1/health"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/v1/health")
http_code=$(echo "$response" | tail -1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    echo "✅ Health check OK"
    echo "$body" | python -m json.tool
else
    echo "❌ Health check failed (HTTP $http_code)"
    echo "$body"
fi

echo ""

# Test 3: Buffer status
echo "3. Testing GET /v1/kkt/buffer/status"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/v1/kkt/buffer/status")
http_code=$(echo "$response" | tail -1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    echo "✅ Buffer status OK"
    echo "$body" | python -m json.tool
else
    echo "❌ Buffer status failed (HTTP $http_code)"
    echo "$body"
fi

echo ""

# Test 4: Create receipt
echo "4. Testing POST /v1/kkt/receipt"
IDEMPOTENCY_KEY=$(python -c "import uuid; print(str(uuid.uuid4()))")

response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/v1/kkt/receipt" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d '{
    "pos_id": "POS-001",
    "type": "sale",
    "items": [
      {
        "name": "Product A",
        "price": 100.00,
        "quantity": 2,
        "total": 200.00,
        "vat_rate": 20
      }
    ],
    "payments": [
      {
        "type": "cash",
        "amount": 200.00
      }
    ]
  }')

http_code=$(echo "$response" | tail -1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    echo "✅ Receipt creation OK"
    echo "$body" | python -m json.tool
else
    echo "❌ Receipt creation failed (HTTP $http_code)"
    echo "$body"
fi

echo ""
echo "=== Smoke Test Complete ==="
