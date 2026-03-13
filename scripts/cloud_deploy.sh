#!/bin/bash
# scripts/cloud_deploy.sh
# Automates the build and deployment of ContentOG stack to Google Cloud.

set -e

# Configuration
REGION="us-central1"
REPO_NAME="contentog"
API_SERVICE="contentog-api"
UI_SERVICE="contentog-ui"

# Get Project ID
PROJECT_ID=$(grep "GCP_PROJECT_ID" .env | cut -d '=' -f2)
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
fi

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: GCP_PROJECT_ID not found. Please set it in .env or 'gcloud config set project'."
    exit 1
fi

COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
AR_HOSTNAME="${REGION}-docker.pkg.dev"
BACKEND_IMAGE="${AR_HOSTNAME}/${PROJECT_ID}/${REPO_NAME}/backend:latest"
UI_IMAGE="${AR_HOSTNAME}/${PROJECT_ID}/${REPO_NAME}/ui:latest"

# Cleanup failed/old resources to free up space/concurrency
cleanup_resources() {
    echo "🧹 Cleaning up failed/old resources..."
    
    # 1. Delete source tarballs from failed builds in GCS
    # We use -r to handle cases where there might be many or none
    FAILED_SOURCES=$(gcloud builds list --project "$PROJECT_ID" --filter="status=FAILURE" --format="value(source.storageSource.object)" --limit=10 2>/dev/null || echo "")
    BUCKET=$(gcloud builds list --project "$PROJECT_ID" --filter="status=FAILURE" --format="value(source.storageSource.bucket)" --limit=1 2>/dev/null || echo "")
    
    if [ -n "$FAILED_SOURCES" ] && [ -n "$BUCKET" ]; then
        for source in $FAILED_SOURCES; do
            echo "Deleting failed source: gs://$BUCKET/$source"
            gcloud storage rm "gs://$BUCKET/$source" 2>/dev/null || true
        done
    fi

    # 2. Prune old Cloud Run revisions (keep only latest 5)
    for service in "$API_SERVICE" "$UI_SERVICE"; do
        if gcloud run services describe "$service" --region "$REGION" >/dev/null 2>&1; then
            echo "Pruning old revisions for $service..."
            # Get revisions, skip the first 5 (latest), and delete the rest
            OLD_REVISIONS=$(gcloud run revisions list --service "$service" --region "$REGION" --format='value(metadata.name)' --sort-by='~metadata.creationTimestamp' | tail -n +6)
            for rev in $OLD_REVISIONS; do
                if [ -n "$rev" ]; then
                    echo "Deleting revision: $rev"
                    gcloud run revisions delete "$rev" --region "$REGION" --quiet || true
                fi
            done
        fi
    done
}

echo "🚀 Starting ContentOG Cloud Deployment for project: $PROJECT_ID"
cleanup_resources

# 1. Build and Push Images
echo "📦 Building and pushing images via Cloud Build..."
gcloud builds submit --config cloudbuild.yaml \
    --substitutions=COMMIT_SHA="$COMMIT_SHA",_AR_HOSTNAME="$AR_HOSTNAME",_AR_REPO_NAME="$REPO_NAME"

# 2. Deploy API Service
echo "🌐 Deploying Backend API to Cloud Run..."
# Extract environment variables from .env for deployment, handling potential spaces
# We filter out UI-specific local overrides
ENV_VARS=$(grep -v '^#' .env | grep -v '^$' | grep -v 'BACKEND_API_URL' | paste -sd "," -)

gcloud run deploy "$API_SERVICE" \
    --image "$BACKEND_IMAGE" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "$ENV_VARS" \
    --quiet

API_URL=$(gcloud run services describe "$API_SERVICE" --region "$REGION" --format='value(status.url)')
echo "✅ API deployed at: $API_URL"

# 3. Deploy UI Service
echo "🎨 Deploying Frontend UI to Cloud Run..."
# We pass the API_URL to the UI service as an environment variable for Next.js rewrites
gcloud run deploy "$UI_SERVICE" \
    --image "$UI_IMAGE" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "BACKEND_API_URL=$API_URL" \
    --quiet

UI_URL=$(gcloud run services describe "$UI_SERVICE" --region "$REGION" --format='value(status.url)')

echo "--------------------------------------------------"
echo "🎉 ContentOG Stack Successfully Deployed!"
echo "--------------------------------------------------"
echo "Frontend UI: $UI_URL"
echo "Backend API: $API_URL"
echo "--------------------------------------------------"
echo "💡 To run a background worker for this project:"
echo "gcloud run jobs deploy contentog-worker --image $BACKEND_IMAGE --command \"python\" --args \"scripts/run_worker.py,--mode,worker\" --region $REGION"
