#!/bin/bash
set -e

# Default values
SERVICE_NAME="worker"
REGION="us-central1"
REPO_NAME="contentog"

# Get Project ID from .env, settings, or gcloud config
PROJECT_ID=$(grep "GCP_PROJECT_ID" .env | cut -d '=' -f2)

if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
fi

if [ -z "$PROJECT_ID" ]; then
  echo "Error: GCP Project ID not found in .env or gcloud config."
  echo "Please set GCP_PROJECT_ID in .env or run 'gcloud config set project [PROJECT_ID]'"
  exit 1
fi

# Get current commit SHA or fallback
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")

echo "🚀 Starting build for $SERVICE_NAME in project $PROJECT_ID (Tag: $COMMIT_SHA)..."

# Submit build to Cloud Build
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_SERVICE_NAME="$SERVICE_NAME",_AR_REPO_NAME="$REPO_NAME",COMMIT_SHA="$COMMIT_SHA"

echo "✅ Build complete."
echo "💡 To run this as a Cloud Run Job:"
echo "gcloud run jobs deploy $SERVICE_NAME --image us-central1-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$SERVICE_NAME:latest"
