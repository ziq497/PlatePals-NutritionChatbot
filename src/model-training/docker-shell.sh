#!/bin/bash

set -e

export IMAGE_NAME=model-training
export BASE_DIR=$(pwd)
export SECRETS_DIR=$(pwd)/../../../secrets/
export GCS_BUCKET_URI="gs://platepals-trainer"
export GCS_BUCKET_NAME="platepals-trainer"
export GCP_PROJECT="platepals-405005" # CHANGE THIS
export GCP_ZONE="us-east1"
export GCP_REGION="us-east1"

# Check to see if path to secrets is correct
if [ ! -f "$SECRETS_DIR/model-trainer.json" ]; then
    echo "model-trainer.json not found at the path you have provided."
    exit 1
fi

# Build the image based on the Dockerfile
docker build -t $IMAGE_NAME -f Dockerfile .
# M1/2 chip macs use this line
#docker build -t $IMAGE_NAME --platform=linux/arm64/v8 -f Dockerfile .

# Run Container
winpty docker run --rm --name $IMAGE_NAME -ti \
--mount type=bind,source="$BASE_DIR",target=/app \
--mount type=bind,source="$SECRETS_DIR",target=/secrets \
-e GOOGLE_APPLICATION_CREDENTIALS=/../secrets/model-trainer.json \
-e GCP_PROJECT=$GCP_PROJECT \
-e GCS_BUCKET_URI=$GCS_BUCKET_URI \
-e GCS_BUCKET_NAME=$GCS_BUCKET_NAME \
-e GCP_ZONE=$GCP_ZONE \
-e GCP_REGION=$GCP_REGION \
$IMAGE_NAME