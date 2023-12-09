#!/bin/bash

# exit immediately if a command exits with a non-zero status
#set -e

# Define some environment variables
export IMAGE_NAME="platepals-app-deployment"
export BASE_DIR=$(pwd)
export SECRETS_DIR=$(pwd)/../../../secrets/
export GCP_PROJECT="platepals-405005" # Change to your GCP Project
export GCP_ZONE="us-central1-a"
export GOOGLE_APPLICATION_CREDENTIALS=/../secrets/deployment.json
export GCS_BUCKET_NAME="platepals-trainer"
export GCS_SERVICE_ACCOUNT="data-service-account@platepals-405005.iam.gserviceaccount.com"
export GCP_REGION="us-central1"
export GCS_PACKAGE_URI="gs://platepals-trainer"

# Build the image based on the Dockerfile
docker build -t $IMAGE_NAME -f Dockerfile .
#docker build -t $IMAGE_NAME --platform=linux/amd64 -f Dockerfile .

# Run the container
winpty docker run --rm --name $IMAGE_NAME -ti \
-v //var/run/docker.sock:/var/run/docker.sock \
--mount type=bind,source="$BASE_DIR",target=/app \
--mount type=bind,source="$SECRETS_DIR",target=/secrets \
--mount type=bind,source="$HOME/.ssh",target=/home/app/.ssh \
--mount type=bind,source="$BASE_DIR/../api-service",target=/api-service \
--mount type=bind,source="$BASE_DIR/../frontend-react",target=/frontend-react \
--mount type=bind,source="$BASE_DIR/../preprocessing",target=/preprocessing \
-e GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS \
-e USE_GKE_GCLOUD_AUTH_PLUGIN=True \
-e GCP_PROJECT=$GCP_PROJECT \
-e GCP_ZONE=$GCP_ZONE \
-e GCS_BUCKET_NAME=$GCS_BUCKET_NAME \
-e GCS_SERVICE_ACCOUNT=$GCS_SERVICE_ACCOUNT \
-e GCP_REGION=$GCP_REGION \
-e GCS_PACKAGE_URI=$GCS_PACKAGE_URI \
$IMAGE_NAME

