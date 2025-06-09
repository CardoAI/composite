#! /bin/bash
set -e

# Ensure required environment variables are set
: "${GITHUB_BRANCH:?Error: GITHUB_BRANCH is not set.}"
: "${GITOPS_REPOSITORY:?Error: GITOPS_REPOSITORY is not set.}"
: "${GITOPS_BRANCH:?Error: GITOPS_BRANCH is not set.}"
: "${GITOPS_USERNAME:?Error: GITOPS_USERNAME is not set.}"
: "${GITOPS_EMAIL:?Error: GITOPS_EMAIL is not set.}"
: "${GITHUB_ACTION_RUN_URL:?Error: GITHUB_ACTION_RUN_URL is not set.}"
: "${MAX_RETRIES:?Error: MAX_RETRIES is not set.}"

git config user.name "${GITOPS_USERNAME}"
git config user.email "${GITOPS_EMAIL}"

# Commit changes first
git add .
git commit -m ":robot: Action URL: ${GITHUB_ACTION_RUN_URL}" --allow-empty

# Retry logic for pushing changes with rebase
RETRY_COUNT=0
while [ ${RETRY_COUNT} -lt ${MAX_RETRIES} ]; do
  # Pull with rebase before pushing
  if git pull --rebase origin "${GITOPS_BRANCH}"; then
    if git push origin "${GITOPS_BRANCH}"; then
      echo -e ">--- Git: Changes pushed to ${GITOPS_REPOSITORY}@${GITOPS_BRANCH} ---<"
      exit 0
    fi
  fi

  RETRY_COUNT=$((RETRY_COUNT+1))
  echo "Push failed, retrying (${RETRY_COUNT}/${MAX_RETRIES})..."
  sleep 2
done
echo "Failed to push after ${MAX_RETRIES} attempts"
exit 1