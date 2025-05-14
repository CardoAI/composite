#!/bin/bash

# Set default value for BUILD_DIRECTORY if it's not set
: ${BUILD_DIRECTORY:="dist"}

npm install -g yarn

echo "registry=https://registry.npmjs.org/" > .npmrc
echo "@cardoai:registry=$CODEARTIFACT_REGISTRY" >> .npmrc
echo "//$(echo $CODEARTIFACT_REGISTRY | sed -e 's|https://||'):_authToken=$CODEARTIFACT_AUTH_TOKEN" >> .npmrc

echo "Installing dependencies..."
yarn install --ignore-engines

echo "Building the project..."
NODE_OPTIONS='--max-old-space-size=4096' yarn build

if [ -d "$BUILD_DIRECTORY" ]; then
    echo "Syncing $BUILD_DIRECTORY to S3 bucket: $CLOUDFRONT_DISTRIBUTION_BUCKET..."
    aws s3 sync $BUILD_DIRECTORY s3://$CLOUDFRONT_DISTRIBUTION_BUCKET --delete
    echo "Sync completed successfully."
else
    echo "Error: $BUILD_DIRECTORY directory does not exist. Build may have failed."
    exit 1
fi

echo "Build and deployment completed successfully."
