#!/bin/bash
set -e

IMAGE_NAME="contentog-worker-test"

echo "🛠️ Building test container..."
docker build -t $IMAGE_NAME .

echo "🏃 Running preflight check inside container..."
# We pass .env if it exists for local testing, but the container should be able
# to run with environment variables too.
if [ -f .env ]; then
  docker run --rm --env-file .env $IMAGE_NAME --mode preflight
  docker run --rm --env-file .env $IMAGE_NAME --mode bootstrap
else
  echo "⚠️ No .env file found. Container run might fail if credentials are missing."
  docker run --rm $IMAGE_NAME --mode preflight
fi

echo "✅ Container verification successful!"
