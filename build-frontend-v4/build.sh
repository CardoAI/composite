#!/bin/bash
# Set default value for BUILD_DIRECTORY if it's not set
: ${BUILD_DIRECTORY:="dist"}
# Set default value for NODE_OPTIONS if it's not set
: ${NODE_OPTIONS:="--max-old-space-size=2048"}
# Set default value for DELETE_OLD_ASSETS if it's not set
: ${CLEANUP_BUCKET:="false"}
# Ensure failure on any command failure (set -e)
set -euo pipefail

export YARN_ENABLE_TELEMETRY=0
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0

# Yarn 4 is provisioned by Corepack, using the "packageManager" field of package.json
command -v corepack &>/dev/null || npm install -g corepack
corepack enable

if ! grep -Eq '"packageManager"[[:space:]]*:[[:space:]]*"yarn@([4-9]|[1-9][0-9])\.' package.json; then
    echo "Error: package.json must declare \"packageManager\": \"yarn@4.x.x\" (run 'yarn set version stable')."
    exit 1
fi
echo "Using Yarn $(yarn --version)"

# Configure the CodeArtifact registry for the @cardoai scope.
# Written to the user-level ~/.yarnrc.yml so the repository's .yarnrc.yml is left untouched.
yarn config set --home 'npmScopes["cardoai"].npmRegistryServer' "$CODEARTIFACT_REGISTRY"
yarn config set --home 'npmScopes["cardoai"].npmAlwaysAuth' true
yarn config set --home 'npmScopes["cardoai"].npmAuthToken' "$CODEARTIFACT_AUTH_TOKEN"

# Install dependencies
echo "Installing dependencies..."
yarn install --immutable

# Build the project
echo "Building the project..."
NODE_OPTIONS=$NODE_OPTIONS yarn build

# Check if the BUILD_DIRECTORY exists and sync to S3
if [ -d "$BUILD_DIRECTORY" ]; then

    DELETE_FLAG=""
    if [ "$CLEANUP_BUCKET" = "true" ]; then
        echo "DELETE_FLAG set to true. Deleting old assets from S3..."
        DELETE_FLAG="--delete"
    fi


    echo "Syncing hashed assets to S3 (no delete, long cache, immutable)..."
    aws s3 sync "$BUILD_DIRECTORY" "s3://$CLOUDFRONT_DISTRIBUTION_BUCKET" \
        $DELETE_FLAG \
        --exclude "index.html" \
        --cache-control "public,max-age=31536000,immutable"

    echo "Uploading index.html last (no-cache, always revalidated)..."
    aws s3 cp "$BUILD_DIRECTORY/index.html" "s3://$CLOUDFRONT_DISTRIBUTION_BUCKET/index.html" \
        --cache-control "no-cache,no-store,must-revalidate"

    echo "Sync completed successfully."
else
    # If directory doesn't exist, print error and exit
    echo "Error: $BUILD_DIRECTORY directory does not exist. Build may have failed."
    exit 1
fi

echo "Build and deployment completed successfully."
