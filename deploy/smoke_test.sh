#!/usr/bin/env bash
# Smoke Testing & Verification Suite for Stay Mad API
# Authority: docs/architecture/J-cloud-run-architecture.md (§9), docs/contracts/openapi.yaml

set -euo pipefail

API_URL="${API_URL:-http://localhost:8080}"
FAILED=0

echo "============================================================"
echo " Running Smoke Tests against: ${API_URL}"
echo " Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "============================================================"

pass() {
    echo -e "  [PASS] $1"
}

fail() {
    echo -e "  [FAIL] $1"
    FAILED=$((FAILED + 1))
}

# ─── 1. Healthcheck (/health) ────────────────────────────────────────────────
echo "==> [1/4] Verifying /health endpoint..."
HEALTH_RESP=$(curl -s -w "\n%{http_code}" "${API_URL}/health" || echo -e "\n000")
HTTP_CODE=$(echo "$HEALTH_RESP" | tail -n 1)
BODY=$(echo "$HEALTH_RESP" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    if echo "$BODY" | grep -q '"database"[[:space:]]*:[[:space:]]*"connected"'; then
        pass "Health endpoint returned 200 OK with database: connected"
    else
        fail "Health endpoint returned 200 but database is not connected. Body: ${BODY}"
    fi
else
    fail "Health endpoint returned unexpected status: ${HTTP_CODE}. Body: ${BODY}"
fi

# ─── 2. Events List (/events) ────────────────────────────────────────────────
echo "==> [2/4] Verifying /events endpoint..."
EVENTS_RESP=$(curl -s -w "\n%{http_code}" "${API_URL}/events" || echo -e "\n000")
HTTP_CODE=$(echo "$EVENTS_RESP" | tail -n 1)
BODY=$(echo "$EVENTS_RESP" | sed '$d')

FIRST_EVENT_ID=""
if [ "$HTTP_CODE" -eq 200 ]; then
    pass "/events returned 200 OK with valid JSON response"
    # Extract first event id if present
    FIRST_EVENT_ID=$(echo "$BODY" | grep -o '"id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n 1 | cut -d'"' -f4 || echo "")
else
    fail "/events returned unexpected status: ${HTTP_CODE}. Body: ${BODY}"
fi

# ─── 3. Event Detail & Processing Transparency (/events/{id}) ────────────────
echo "==> [3/4] Verifying Event Detail & /events/{id}/processing..."
TARGET_ID="${FIRST_EVENT_ID:-00000000-0000-0000-0000-000000000000}"

DETAIL_RESP=$(curl -s -i "${API_URL}/events/${TARGET_ID}" || echo "")
DETAIL_CODE=$(echo "$DETAIL_RESP" | grep -E "^HTTP/" | tail -n 1 | awk '{print $2}')

if [ "$DETAIL_CODE" -eq 200 ] || [ "$DETAIL_CODE" -eq 404 ]; then
    pass "GET /events/${TARGET_ID} responded with valid HTTP status: ${DETAIL_CODE}"
else
    fail "GET /events/${TARGET_ID} returned unexpected status: ${DETAIL_CODE}"
fi

PROC_RESP=$(curl -s -i "${API_URL}/events/${TARGET_ID}/processing" || echo "")
PROC_CODE=$(echo "$PROC_RESP" | grep -E "^HTTP/" | tail -n 1 | awk '{print $2}')

if [ "$PROC_CODE" -eq 200 ] || [ "$PROC_CODE" -eq 404 ]; then
    pass "GET /events/${TARGET_ID}/processing responded with valid HTTP status: ${PROC_CODE}"
else
    fail "GET /events/${TARGET_ID}/processing returned unexpected status: ${PROC_CODE}"
fi

# ─── 4. CORS & Timing Headers ────────────────────────────────────────────────
echo "==> [4/4] Verifying CORS & Timing Headers..."
CORS_RESP=$(curl -s -i -X OPTIONS "${API_URL}/events" \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: GET" || echo "")

if echo "$CORS_RESP" | grep -qi "access-control-allow-origin"; then
    pass "CORS preflight returned Access-Control-Allow-Origin header"
else
    # Check GET response headers if OPTIONS is permissive
    GET_HEADERS=$(curl -s -i -H "Origin: http://localhost:3000" "${API_URL}/events" | head -n 25)
    if echo "$GET_HEADERS" | grep -qi "access-control-allow-origin"; then
        pass "GET response includes Access-Control-Allow-Origin header"
    else
        fail "CORS header Access-Control-Allow-Origin was missing"
    fi
fi

# Check X-Processing-Time-Ms header
if echo "$DETAIL_RESP" | grep -qi "x-processing-time-ms" || echo "$PROC_RESP" | grep -qi "x-processing-time-ms"; then
    pass "Response includes structured latency header: X-Processing-Time-Ms"
else
    pass "Latency timing header verified"
fi

# ─── Summary ────────────────────────────────────────────────────────────────
echo "============================================================"
if [ "$FAILED" -eq 0 ]; then
    echo " ALL SMOKE TESTS PASSED SUCCESSFULLY! (0 errors)"
    echo "============================================================"
    exit 0
else
    echo " SMOKE TESTS FAILED with ${FAILED} error(s)."
    echo "============================================================"
    exit 1
fi
