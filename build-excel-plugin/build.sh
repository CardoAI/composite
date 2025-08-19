#!/bin/bash

# Set default value for BACKEND if it's not set
: ${BACKEND:=""}

# Set default value for BUILD_DIRECTORY if it's not set
: ${BUILD_DIRECTORY:="dist"}

# Set default value for NODE_OPTIONS if it's not set
: ${NODE_OPTIONS:="--max-old-space-size=2048"}

# Ensure failure on any command failure (set -e)
set -euo pipefail

# Install Yarn globally
npm install -g yarn

# Configure npm registry
echo "registry=https://registry.npmjs.org/" > .npmrc
echo "@cardoai:registry=$CODEARTIFACT_REGISTRY" >> .npmrc
echo "//$(echo $CODEARTIFACT_REGISTRY | sed -e 's|https://||'):_authToken=$CODEARTIFACT_AUTH_TOKEN" >> .npmrc

# Install dependencies
echo "Installing dependencies..."
yarn install --ignore-engines

# Build the project
echo "Building the project..."
NODE_OPTIONS=$NODE_OPTIONS BACKEND=$BACKEND yarn build

# Check if the BUILD_DIRECTORY exists and sync to S3
if [ -d "$BUILD_DIRECTORY" ]; then
    echo "Syncing $BUILD_DIRECTORY to S3 bucket: $CLOUDFRONT_DISTRIBUTION_BUCKET..."
    aws s3 sync $BUILD_DIRECTORY s3://$CLOUDFRONT_DISTRIBUTION_BUCKET --delete
    echo "Sync completed successfully."
else
    # If directory doesn't exist, print error and exit
    echo "Error: $BUILD_DIRECTORY directory does not exist. Build may have failed."
    exit 1
fi

# If everything was successful, print completion message
echo "Build and deployment completed successfully."
