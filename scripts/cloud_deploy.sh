#!/bin/bash
# scripts/cloud_deploy.sh
# Automates the build and deployment of ContentOG stack to Google Cloud.
# Supports selective rollouts: --api, --ui, or --all (default).

set -e

# Configuration
REGION="us-central1"
REPO_NAME="contentog"
API_SERVICE="contentog-api"
UI_SERVICE="contentog-ui"

# Default Scope
SCOPE="all" # all, api, ui

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --api) SCOPE="api" ;;
        --ui) SCOPE="ui" ;;
        --all) SCOPE="all" ;;
        --help)
            echo "Usage: ./scripts/cloud_deploy.sh [OPTIONS]"
            echo "Options:"
            echo "  --api    Deploy only the Backend API"
            echo "  --ui     Deploy only the Frontend UI"
            echo "  --all    Deploy both services (default)"
            exit 0
            ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# 1. Environment Validation
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found in root directory."
    exit 1
fi

PROJECT_ID=$(grep "GCP_PROJECT_ID" .env | cut -d '=' -f2)
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
fi

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: GCP_PROJECT_ID not found in .env or gcloud config."
    exit 1
fi

# 2. Safety Prompt
echo "⚠️  Scope: $SCOPE"
echo "⚠️  Project: $PROJECT_ID"
echo "⚠️  Region: $REGION"
echo "--------------------------------------------------"
echo "Confirming deployment in 5 seconds... (Ctrl+C to cancel)"
sleep 5

COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
AR_HOSTNAME="${REGION}-docker.pkg.dev"
BACKEND_IMAGE="${AR_HOSTNAME}/${PROJECT_ID}/${REPO_NAME}/backend:latest"
UI_IMAGE="${AR_HOSTNAME}/${PROJECT_ID}/${REPO_NAME}/ui:latest"

# Cleanup failed/old resources
cleanup_resources() {
    echo "🧹 Cleaning up failed/old resources..."
    
    # 1. Delete source tarballs from failed builds
    if [ -n "$PROJECT_ID" ]; then
        FAILED_SOURCES=$(gcloud builds list --project "$PROJECT_ID" --filter="status=FAILURE" --format="value(source.storageSource.object)" --limit=5 2>/dev/null)
        BUCKET=$(gcloud builds list --project "$PROJECT_ID" --filter="status=FAILURE" --format="value(source.storageSource.bucket)" --limit=1 2>/dev/null)
        
        if [ -n "$FAILED_SOURCES" ] && [ -n "$BUCKET" ]; then
            for source in $FAILED_SOURCES; do
                echo "Deleting failed source: gs://$BUCKET/$source"
                gcloud storage rm "gs://$BUCKET/$source" 2>/dev/null || true
            done
        fi
    fi

    # 2. Prune old Cloud Run revisions
    SERVICES_TO_PRUNE=()
    if [[ "$SCOPE" == "api" || "$SCOPE" == "all" ]]; then SERVICES_TO_PRUNE+=("$API_SERVICE"); fi
    if [[ "$SCOPE" == "ui" || "$SCOPE" == "all" ]]; then SERVICES_TO_PRUNE+=("$UI_SERVICE"); fi

    for service in "${SERVICES_TO_PRUNE[@]}"; do
        if gcloud run services describe "$service" --region "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
            echo "Pruning old revisions for $service..."
            REVS=$(gcloud run revisions list --service "$service" --region "$REGION" --project "$PROJECT_ID" --format='value(metadata.name)' --sort-by='~metadata.creationTimestamp' | tail -n +6)
            for rev in $REVS; do
                if [ -n "$rev" ]; then
                    echo "Deleting revision: $rev"
                    gcloud run revisions delete "$rev" --region "$REGION" --project "$PROJECT_ID" --quiet || true
                fi
            done
        fi
    done
}

echo "🚀 Starting ContentOG Cloud Deployment ($SCOPE)"
cleanup_resources || echo "⚠️  Warning: Cleanup failed, proceeding anyway..."

# 3. Build and Push Images
# Set skip flags for Cloud Build
SKIP_BACKEND="false"
SKIP_UI="false"

if [[ "$SCOPE" == "api" ]]; then SKIP_UI="true"; fi
if [[ "$SCOPE" == "ui" ]]; then SKIP_BACKEND="true"; fi

echo "📦 Running Cloud Build..."
gcloud builds submit --config cloudbuild.yaml \
    --substitutions=COMMIT_SHA="$COMMIT_SHA",_AR_HOSTNAME="$AR_HOSTNAME",_AR_REPO_NAME="$REPO_NAME",_SKIP_BACKEND="$SKIP_BACKEND",_SKIP_UI="$SKIP_UI"

# 4. Deploy Services
if [[ "$SCOPE" == "api" || "$SCOPE" == "all" ]]; then
    echo "🌐 Deploying Backend API to Cloud Run..."
    ENV_VARS=$(grep -v '^#' .env | grep -v '^$' | grep -v 'BACKEND_API_URL' | paste -sd "," -)
    
    gcloud run deploy "$API_SERVICE" \
        --image "$BACKEND_IMAGE" \
        --region "$REGION" \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars "$ENV_VARS" \
        --quiet
fi

# Get API_URL even if we didn't deploy it, as UI might need it
API_URL=$(gcloud run services describe "$API_SERVICE" --region "$REGION" --format='value(status.url)' 2>/dev/null || echo "")

if [[ "$SCOPE" == "ui" || "$SCOPE" == "all" ]]; then
    echo "🎨 Deploying Frontend UI to Cloud Run..."
    if [ -z "$API_URL" ]; then
        echo "🚨 Warning: API URL not found. UI might not function correctly."
    fi

    gcloud run deploy "$UI_SERVICE" \
        --image "$UI_IMAGE" \
        --region "$REGION" \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars "BACKEND_API_URL=$API_URL" \
        --quiet
fi

# Final Summary
UI_URL=$(gcloud run services describe "$UI_SERVICE" --region "$REGION" --format='value(status.url)' 2>/dev/null || echo "N/A")

echo "--------------------------------------------------"
echo "🎉 ContentOG Stack Deployment Finished!"
echo "--------------------------------------------------"
echo "Scope: $SCOPE"
echo "Frontend UI: $UI_URL"
echo "Backend API: $API_URL"
echo "--------------------------------------------------"
