#!/bin/bash

set -e

# Ensure BRANCH_CONFIGURATION environment variable is set in action
if [ -z "$BRANCH_CONFIGURATION" ]; then
  echo "Error: BRANCH_CONFIGURATION is not set."
  exit 1
fi

# Ensure GITHUB_BRANCH environment variable is set in action
if [ -z "$GITHUB_BRANCH" ]; then
  echo "Error: GITHUB_BRANCH is not set."
  exit 1
fi

# Ensure GITOPS_REPOSITORY environment variable is set in action
if [ -z "$GITOPS_REPOSITORY" ]; then
  echo "Error: GITOPS_REPOSITORY is not set."
  exit 1
fi

# Ensure GITOPS_BRANCH environment variable is set in action
if [ -z "$GITOPS_BRANCH" ]; then
  echo "Error: GITOPS_BRANCH is not set."
  exit 1
fi

# Ensure GITOPS_USERNAME environment variable is set in action
if [ -z "$GITOPS_USERNAME" ]; then
  echo "Error: GITOPS_USERNAME is not set."
  exit 1
fi

# Ensure GITOPS_EMAIL environment variable is set in action
if [ -z "$GITOPS_EMAIL" ]; then
  echo "Error: GITOPS_EMAIL is not set."
  exit 1
fi

# Check if the branch exists in the configuration
BRANCH_EXISTS=$(echo -e "${BRANCH_CONFIGURATION}" | yq eval ".${GITHUB_BRANCH}" -)
if [ "$BRANCH_EXISTS" == "null" ]; then
  echo "Error: Branch '$GITHUB_BRANCH' does not exist in the configuration."
  exit 1
fi

# Extract tenant names from the branch configuration and convert to JSON array
TENANTS=$(echo -e "${BRANCH_CONFIGURATION}" | yq eval ".${GITHUB_BRANCH} | keys" -o=json)

# Check if TENANTS is empty or null
if [ -z "$TENANTS" ] || [ "$TENANTS" == "null" ]; then
  echo "No tenants found in the branch configuration for branch: $GITHUB_BRANCH"
  exit 0
fi

# Convert JSON array to newline-separated list
TENANT_LIST=$(echo "$TENANTS" | jq -r '.[]')

for TENANT in $TENANT_LIST; do
  echo -e "<--- Tenant: $TENANT --->"

  # Extract the kustomize filepath and images for the tenant
  TENANT_PATH=$(echo -e "${BRANCH_CONFIGURATION}" | yq eval ".${GITHUB_BRANCH}.${TENANT}.path" -) # Gitops helm images value file
  VALUES_FILE=$(echo -e "${BRANCH_CONFIGURATION}" | yq eval ".${GITHUB_BRANCH}.${TENANT}.valuesFile" -) # Gitops helm images value file
  IMAGES=$(echo -e "${BRANCH_CONFIGURATION}" | yq eval ".${GITHUB_BRANCH}.${TENANT}.images" -o=json) # Images block inside the tenant

  # Check if TENANT_PATH is set
  if [ "$TENANT_PATH" == "null" ]; then
    echo "Error: path for tenant > $GITHUB_BRANCH.$TENANT < is not set."
    continue
  else
    echo "> Tenant path: $TENANT_PATH"
  fi

  # Check if VALUES_FILE is set
  if [ "$VALUES_FILE" == "null" ]; then
    echo "Error: valuesFile for tenant > $GITHUB_BRANCH.$TENANT < is not set."
    continue
  else
    echo "> Tenant valuesFile: $VALUES_FILE"
  fi

  # Check if IMAGES is set
  if [ "$IMAGES" == "null" ]; then
    echo "Error: images for tenant > $TENANT < are not set."
    continue
  fi

  # Loop through each image and print its value
  IMAGE_KEYS=$(echo "$IMAGES" | yq eval 'keys' -o=json)
  IMAGE_LIST=$(echo "$IMAGE_KEYS" | jq -r '.[]')

  # Full filepath to change via yq
  VALUES_FILEPATH="$TENANT_PATH/$VALUES_FILE"

  if [ ! -f "$VALUES_FILEPATH" ]; then
    echo "File '$VALUES_FILEPATH' does not exist."
    exit 1
  fi

  for IMAGE in $IMAGE_LIST; do
    IMAGE_VALUE=$(echo $IMAGES | yq eval ".\"${IMAGE}\"" -)

    REGISTRY_DOMAIN=$(echo $IMAGE_VALUE | cut -d "/" -f 1)
    IMAGE_NAME=$(echo $IMAGE_VALUE | cut -d "/" -f 2)

    REGISTRY_ID=$(echo $REGISTRY_DOMAIN | cut -d "." -f 1)
    REGION=$(echo $REGISTRY_DOMAIN | cut -d "." -f 4)

    REPOSITORY_NAME=$(echo $IMAGE_NAME | cut -d ":" -f 1)
    IMAGE_TAG=$(echo $IMAGE_NAME | cut -d ":" -f 2)

    IMAGE_DETAILS=$(aws ecr describe-images --registry-id $REGISTRY_ID --region $REGION --repository-name $REPOSITORY_NAME --image-ids imageTag=$IMAGE_TAG --query 'imageDetails[0]' --output json)
    
    IMAGE_DIGEST=$(echo $IMAGE_DETAILS | jq -r ".imageDigest")
    
    yq eval -i ".${IMAGE} = \"$IMAGE_TAG@$IMAGE_DIGEST\"" "$VALUES_FILEPATH"

  done

  echo -e ">--- Tenant: $TENANT ---<\n"
done

# Push the changes to GitOps
echo -e "<--- Git: Pushing changes to $GITOPS_REPOSITORY@$GITOPS_BRANCH --->"
git config user.name $GITOPS_USERNAME
git config user.email $GITOPS_EMAIL
git pull
git add .
git commit -m ":robot: [:zap: Update image version]" --allow-empty

git push && echo -e ">--- Git: Changes pushed to $GITOPS_REPOSITORY@$GITOPS_BRANCH ---<"
