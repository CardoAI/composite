#!/bin/bash
# Set default value for BUILD_DIRECTORY if it's not set
: ${BUILD_DIRECTORY:="dist"}
# Set default value for NODE_OPTIONS if it's not set
: ${NODE_OPTIONS:="--max-old-space-size=2048"}
# Set default value for DELETE_OLD_ASSETS if it's not set
: ${CLEANUP_BUCKET:="false"}
# Ensure failure on any command failure (set -e)
set -euo pipefail

# Yarn 2+ (Berry) is selected by the "packageManager" field of package.json, anything else is Yarn classic (v1)
if grep -Eq '"packageManager"[[:space:]]*:[[:space:]]*"yarn@([2-9]|[1-9][0-9])\.' package.json; then
    echo "Detected Yarn 2+ (packageManager field), using Corepack"

    export YARN_ENABLE_TELEMETRY=0
    export COREPACK_ENABLE_DOWNLOAD_PROMPT=0

    command -v corepack &>/dev/null || npm install -g corepack
    corepack enable
    echo "Using Yarn $(yarn --version)"

    # Configure the CodeArtifact registry for the @cardoai scope.
    # Written to the user-level ~/.yarnrc.yml so the repository's .yarnrc.yml is left untouched.
    yarn config set --home 'npmScopes["cardoai"].npmRegistryServer' "$CODEARTIFACT_REGISTRY"
    yarn config set --home 'npmScopes["cardoai"].npmAlwaysAuth' true
    yarn config set --home 'npmScopes["cardoai"].npmAuthToken' "$CODEARTIFACT_AUTH_TOKEN"

    INSTALL_CMD=(yarn install --immutable)
else
    echo "No Yarn 2+ packageManager field found, using Yarn classic"

    # Install Yarn globally only if not already available
    command -v yarn &>/dev/null || npm install -g yarn

    # Configure npm registry
    echo "registry=https://registry.npmjs.org/" > .npmrc
    echo "@cardoai:registry=$CODEARTIFACT_REGISTRY" >> .npmrc
    echo "//$(echo $CODEARTIFACT_REGISTRY | sed -e 's|https://||'):_authToken=$CODEARTIFACT_AUTH_TOKEN" >> .npmrc

    INSTALL_CMD=(yarn install --frozen-lockfile --ignore-engines --prefer-offline)
fi

# Install dependencies
echo "Installing dependencies..."
"${INSTALL_CMD[@]}"

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
