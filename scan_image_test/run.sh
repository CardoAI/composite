#!/bin/bash
IMAGE_NAME=vulns
CONTAINER_NAME=vulns

AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id --profile root)
AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key --profile root)
AWS_SESSION_TOKEN=$(aws configure get aws_session_token --profile root)
AWS_REGION="eu-central-1"

# Build the Docker image
echo "Building the Docker image..."
docker build -t $IMAGE_NAME .

# Run the Docker container
echo "Running the Docker container..."
docker run --name $CONTAINER_NAME \
    --rm \
    -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
    -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
    -e AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN \
    -e AWS_REGION=$AWS_REGION \
    $IMAGE_NAME
