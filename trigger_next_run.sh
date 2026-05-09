#!/bin/bash

# MIRROR PROTOCOL: Temporal Stabilization
# Ensures a minimum 300-second (5-minute) delay between workflow dispatches
# to eliminate 429/401 burst-rate errors.

echo "Initiating Temporal Stabilization (300s sleep)..."

if [ -z "$GH_PAT" ]; then
  echo "ERROR: GH_PAT environment variable is missing."
  exit 1
fi

# Mandatory sleep to respect 5-minute cycle
echo "Waiting 300 seconds before triggering next run..."
sleep 300

REPO_NAME="${GITHUB_REPOSITORY}"
WORKFLOW_FILE="main.yml"

echo "Triggering workflow: $WORKFLOW_FILE in $REPO_NAME"

RESPONSE=$(curl -s -w "%{http_code}" -X POST \
  -H "Authorization: token $GH_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/${REPO_NAME}/actions/workflows/${WORKFLOW_FILE}/dispatches" \
  -d '{"ref":"main"}')

HTTP_CODE=$(echo "$RESPONSE" | tail -c 3)
echo "GitHub API Response Code: $HTTP_CODE"

if [ "$HTTP_CODE" -eq 204 ]; then
  echo "Success: Next run triggered."
else
  echo "Error: Failed to trigger next run (HTTP $HTTP_CODE)."
  echo "Response: $(echo "$RESPONSE" | head -c -3)"
  exit 1
fi
