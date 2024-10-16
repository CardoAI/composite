#!/bin/bash

set -e

# Ensure required environment variables are set
: "${BRANCH_CONFIGURATION:?Error: BRANCH_CONFIGURATION is not set.}"
: "${GITHUB_BRANCH:?Error: GITHUB_BRANCH is not set.}"
: "${GITOPS_REPOSITORY:?Error: GITOPS_REPOSITORY is not set.}"
: "${GITOPS_BRANCH:?Error: GITOPS_BRANCH is not set.}"
: "${GITOPS_USERNAME:?Error: GITOPS_USERNAME is not set.}"
: "${GITOPS_EMAIL:?Error: GITOPS_EMAIL is not set.}"
: "${GITHUB_ACTION_RUN_URL:?Error: GITHUB_ACTION_RUN_URL is not set.}"

# Check if the branch exists in the configuration
BRANCH_EXISTS=$(echo -e "${BRANCH_CONFIGURATION}" | yq eval ".${GITHUB_BRANCH}" -)
if [ "$BRANCH_EXISTS" == "null" ]; then
  echo "Error: Branch '$GITHUB_BRANCH' does not exist in the configuration."
  exit 1
fi

# Extract tenant names from the branch configuration
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
  TENANT_PATH=$(echo -e "${BRANCH_CONFIGURATION}" | yq eval ".${GITHUB_BRANCH}.${TENANT}.path" -)
  if [ "$TENANT_PATH" == "null" ]; then
    echo "Error: path for tenant > $GITHUB_BRANCH.$TENANT < is not set."
    continue
  else
    echo "> Tenant path: $TENANT_PATH"
  fi

  VALUES_FILE=$(echo -e "${BRANCH_CONFIGURATION}" | yq eval ".${GITHUB_BRANCH}.${TENANT}.valuesFile" -)
  if [ "$VALUES_FILE" == "null" ]; then
    echo "Error: valuesFile for tenant > $GITHUB_BRANCH.$TENANT < is not set."
    continue
  else
    echo "> Tenant valuesFile: $VALUES_FILE"
  fi

  echo

  # Full filepath to change via yq
  VALUES_FILEPATH="$TENANT_PATH/$VALUES_FILE"
  if [ ! -f "$VALUES_FILEPATH" ]; then
    echo "File '$VALUES_FILEPATH' does not exist."
    exit 1
  fi

  SERVICES=$(echo -e "${BRANCH_CONFIGURATION}" | yq eval ".${GITHUB_BRANCH}.${TENANT}.services" -o=json)

  # Check if SERVICES is empty or null
  if [ -z "$SERVICES" ] || [ "$SERVICES" == "null" ]; then
    echo "Error: services for tenant > $GITHUB_BRANCH.$TENANT < is not set."
    continue
  fi

  # Convert JSON array to a Bash array
  SERVICE_LIST=$(echo "$SERVICES" | jq -r '.[]')
  
  VALUES=$(yq -r "$VALUES_FILEPATH")
  
  for SERVICE in $SERVICE_LIST; do
    REPOSITORY=$(echo "$VALUES" | yq eval ".${SERVICE}.image.repository" -)
    TAG=$(echo "$VALUES" | yq eval ".${SERVICE}.image.tag" -)

    if [ "$REPOSITORY" == "null" ]; then
      echo "Error: repository for tenant > $TENANT < is not set for service $SERVICE in file $VALUES_FILEPATH"
      continue
    fi

    if [ "$TAG" == "null" ]; then
      echo "Error: repository for tenant > $TENANT < is not set for service $SERVICE in file $VALUES_FILEPATH"
      continue
    fi

    REGISTRY=$(echo "$REPOSITORY" | cut -d "/" -f 1)
    REPOSITORY_NAME=$(echo "$REPOSITORY" | cut -d "/" -f 2)

    REGISTRY_ID=$(echo "$REGISTRY" | cut -d "." -f 1)

    REGISTRY_REGION=$(echo "$REGISTRY" | cut -d "." -f 4)
    IMAGE_DETAILS=$(aws ecr describe-images --registry-id "$REGISTRY_ID" --region "$REGISTRY_REGION" --repository-name "$REPOSITORY_NAME" --image-ids imageTag="$TAG" --query 'imageDetails[0]' --output json)

    if [ "$(echo "$IMAGE_DETAILS" | jq -r '.')" == "null" ]; then
      echo "Error: No image details found for image > $IMAGE <."
      continue
    fi
    
    IMAGE_DIGEST=$(echo "$IMAGE_DETAILS" | jq -r ".imageDigest")
    if [ -z "$IMAGE_DIGEST" ]; then
      echo "Error: Image digest for > $IMAGE < could not be retrieved."
      continue
    fi

    yq eval -i ".${SERVICE}.image.digest = \"$IMAGE_DIGEST\"" "$VALUES_FILEPATH" && echo "> Service $SERVICE: Digest updated" || echo "> Service $SERVICE: Digest could not be updated"
  done

  echo -e ">--- Tenant: $TENANT ---<\n"
done

# Push the changes to GitOps (optional)
echo -e "<--- Git: Pushing changes to $GITOPS_REPOSITORY@$GITOPS_BRANCH --->"
git config user.name "$GITOPS_USERNAME"
git config user.email "$GITOPS_EMAIL"
git pull
git add .
git commit -m ":robot: Action URL: $GITHUB_ACTION_RUN_URL" --allow-empty
git push && echo -e ">--- Git: Changes pushed to $GITOPS_REPOSITORY@$GITOPS_BRANCH ---<"
