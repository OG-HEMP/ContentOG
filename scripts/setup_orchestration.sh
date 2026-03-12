#!/bin/bash
# scripts/setup_orchestration.sh
# Automates the setup of Google Cloud Pub/Sub for ContentOG Scale-out Orchestration.

set -e

# Load project ID from .env or environment
PROJECT_ID=$(grep "GCP_PROJECT_ID" .env | cut -d '=' -f2)

if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
fi

if [ -z "$PROJECT_ID" ]; then
    echo "Error: GCP_PROJECT_ID not found in .env or gcloud config. Please configure it first."
    exit 1
fi

TOPIC_ID=${CONTENTOG_PUBSUB_TOPIC:-"contentog-tasks"}
SUBSCRIPTION_ID="${TOPIC_ID}-sub"

echo "Setting up Pub/Sub in project: $PROJECT_ID"

# 1. Create Topic
echo "Checking for topic: $TOPIC_ID"
if ! gcloud pubsub topics describe "$TOPIC_ID" --project "$PROJECT_ID" > /dev/null 2>&1; then
    echo "Creating topic: $TOPIC_ID"
    gcloud pubsub topics create "$TOPIC_ID" --project "$PROJECT_ID"
else
    echo "Topic $TOPIC_ID already exists."
fi

# 2. Create Subscription (optional, useful for testing or local workers)
echo "Checking for subscription: $SUBSCRIPTION_ID"
if ! gcloud pubsub subscriptions describe "$SUBSCRIPTION_ID" --project "$PROJECT_ID" > /dev/null 2>&1; then
    echo "Creating subscription: $SUBSCRIPTION_ID"
    gcloud pubsub subscriptions create "$SUBSCRIPTION_ID" --topic "$TOPIC_ID" --project "$PROJECT_ID"
else
    echo "Subscription $SUBSCRIPTION_ID already exists."
fi

echo "Pub/Sub setup complete!"
echo "Topic: projects/$PROJECT_ID/topics/$TOPIC_ID"
echo "Subscription: projects/$PROJECT_ID/subscriptions/$SUBSCRIPTION_ID"
