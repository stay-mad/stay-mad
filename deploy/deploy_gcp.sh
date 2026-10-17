#!/usr/bin/env bash
# Stay Mad - Automated Google Cloud Run Deployment Script
# Authority: docs/architecture/J-cloud-run-architecture.md (§53-J), docs/decisions.md (DEC-0006)

set -euo pipefail

# ─── 0. Configuration & Parameters ───────────────────────────────────────────
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo "")}"
REGION="${REGION:-asia-southeast1}"
ARTIFACT_REPO="${ARTIFACT_REPO:-stay-mad}"
BACKEND_SERVICE="${BACKEND_SERVICE:-stay-mad-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-stay-mad-frontend}"
TAG="${TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo "v0.1.0")}"

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: PROJECT_ID is not set and could not be detected from gcloud config."
    echo "Usage: PROJECT_ID=my-gcp-project $0"
    exit 1
fi

echo "============================================================"
echo " Stay Mad - Google Cloud Run Deployment (Region: ${REGION})"
echo " Project: ${PROJECT_ID} | Tag: ${TAG}"
echo "============================================================"

# ─── 1. Configure Project & Enable Services ─────────────────────────────────
echo "==> [1/7] Setting project and enabling required Google Cloud APIs..."
gcloud config set project "$PROJECT_ID" --quiet

SERVICES=(
    "run.googleapis.com"
    "secretmanager.googleapis.com"
    "artifactregistry.googleapis.com"
    "sqladmin.googleapis.com"
    "iam.googleapis.com"
    "logging.googleapis.com"
)

for svc in "${SERVICES[@]}"; do
    echo "    Enabling ${svc}..."
    gcloud services enable "$svc" --quiet
done

# ─── 2. Artifact Registry Setup ─────────────────────────────────────────────
echo "==> [2/7] Ensuring Artifact Registry repository exists..."
if ! gcloud artifacts repositories describe "$ARTIFACT_REPO" --location="$REGION" >/dev/null 2>&1; then
    echo "    Creating repository ${ARTIFACT_REPO} in ${REGION}..."
    gcloud artifacts repositories create "$ARTIFACT_REPO" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Stay Mad container images" \
        --quiet
fi

# Configure Docker credentials helper
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/backend:${TAG}"
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/frontend:${TAG}"

# ─── 3. IAM Service Accounts Setup ──────────────────────────────────────────
echo "==> [3/7] Setting up IAM Service Accounts..."
BACKEND_SA="stay-mad-backend@${PROJECT_ID}.iam.gserviceaccount.com"
FRONTEND_SA="stay-mad-frontend@${PROJECT_ID}.iam.gserviceaccount.com"

# Create backend SA if needed
if ! gcloud iam service-accounts describe "$BACKEND_SA" >/dev/null 2>&1; then
    gcloud iam service-accounts create stay-mad-backend \
        --display-name="Stay Mad Backend Service Account" \
        --quiet
fi

# Assign roles to backend SA
BACKEND_ROLES=(
    "roles/cloudsql.client"
    "roles/secretmanager.secretAccessor"
    "roles/logging.logWriter"
)
for role in "${BACKEND_ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${BACKEND_SA}" \
        --role="$role" \
        --condition=None \
        --quiet >/dev/null
done

# Create frontend SA if needed
if ! gcloud iam service-accounts describe "$FRONTEND_SA" >/dev/null 2>&1; then
    gcloud iam service-accounts create stay-mad-frontend \
        --display-name="Stay Mad Frontend Service Account" \
        --quiet
fi

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${FRONTEND_SA}" \
    --role="roles/logging.logWriter" \
    --condition=None \
    --quiet >/dev/null

# ─── 4. Google Secret Manager Check ─────────────────────────────────────────
echo "==> [4/7] Verifying Secrets in Google Cloud Secret Manager..."
SECRETS=(
    "stay-mad-gemini-api-key"
    "stay-mad-database-url"
    "stay-mad-gemini-model"
    "stay-mad-embedding-model"
)

for secret in "${SECRETS[@]}"; do
    if ! gcloud secrets describe "$secret" >/dev/null 2>&1; then
        echo "    Notice: Secret ${secret} not found. Creating placeholder..."
        gcloud secrets create "$secret" --replication-policy="automatic" --quiet
        echo "    IMPORTANT: Add a version with secret payload:"
        echo "      echo -n 'VALUE' | gcloud secrets versions add ${secret} --data-file=-"
    else
        echo "    Secret ${secret} exists."
    fi
done

# ─── 5. Build & Push Container Images ───────────────────────────────────────
echo "==> [5/7] Building & Pushing Backend Image (${BACKEND_IMAGE})..."
docker build -t "$BACKEND_IMAGE" -t "${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/backend:latest" -f deploy/Dockerfile .
docker push "$BACKEND_IMAGE"
docker push "${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/backend:latest"

# ─── 6. Deploy Backend Service to Cloud Run ─────────────────────────────────
echo "==> [6/7] Deploying Backend to Cloud Run (${BACKEND_SERVICE})..."
gcloud run deploy "$BACKEND_SERVICE" \
    --image="$BACKEND_IMAGE" \
    --region="$REGION" \
    --platform=managed \
    --port=8080 \
    --cpu=1 \
    --memory=1Gi \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=300 \
    --concurrency=80 \
    --service-account="$BACKEND_SA" \
    --allow-unauthenticated \
    --set-env-vars="ENVIRONMENT=production,GEMINI_FIXTURE_MODE=false,DATA_MODE=live,LOG_FORMAT=json,RUN_MIGRATIONS=true" \
    --set-secrets="GEMINI_API_KEY=stay-mad-gemini-api-key:latest,DATABASE_URL=stay-mad-database-url:latest" \
    --quiet

BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" --region="$REGION" --format='value(status.url)')
echo "    Backend URL: ${BACKEND_URL}"

# ─── 7. Build & Deploy Frontend Service to Cloud Run ────────────────────────
echo "==> [7/7] Building & Deploying Frontend to Cloud Run (${FRONTEND_SERVICE})..."
docker build \
    --build-arg NEXT_PUBLIC_API_URL="${BACKEND_URL}" \
    -t "$FRONTEND_IMAGE" \
    -t "${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/frontend:latest" \
    frontend/
docker push "$FRONTEND_IMAGE"
docker push "${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/frontend:latest"

gcloud run deploy "$FRONTEND_SERVICE" \
    --image="$FRONTEND_IMAGE" \
    --region="$REGION" \
    --platform=managed \
    --port=3000 \
    --cpu=1 \
    --memory=512Mi \
    --min-instances=0 \
    --max-instances=5 \
    --service-account="$FRONTEND_SA" \
    --allow-unauthenticated \
    --set-env-vars="NEXT_PUBLIC_API_URL=${BACKEND_URL},NEXT_PUBLIC_DATA_MODE=live" \
    --quiet

FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" --region="$REGION" --format='value(status.url)')
echo "    Frontend URL: ${FRONTEND_URL}"

echo "============================================================"
echo " Deployment Complete!"
echo " Backend Healthcheck: curl ${BACKEND_URL}/health"
echo " Frontend App: ${FRONTEND_URL}"
echo "============================================================"
