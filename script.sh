#!/bin/bash

set -e

# Check if the required arguments are provided
if [ "$#" -lt 4 ]; then
    echo "Usage: $0 <graph-name> <graph-data-path> <custom-graph-title> <git-branch>"
    exit 1
fi

# Verify GitHub Access Token is available
if [ -z "$GH_TOKEN" ]; then
    echo "Error: GH_TOKEN environment variable is not set."
    exit 1
fi

GRAPH_NAME=$1
GRAPH_DATA_PATH=$2
CUSTOM_GRAPH_TITLE=$3
GIT_BRANCH=${4:-main}  # Default to 'main' if not provided

echo "Processing: "
ls $GRAPH_DATA_PATH
# Configure Git
git config --global user.email "frink-okn@renci.org"
git config --global user.name "Frink documentation bot"

# Clone repository using HTTPS with access token
REPO_URL="https://${GH_TOKEN}@github.com/frink-okn/graph-descriptions.git"
rm -rf repo
git clone "$REPO_URL" repo

# Prepare repository directory
cd repo

# Fetch all remote branches to ensure visibility
git fetch origin

echo "Attempting to checkout or create branch: $GIT_BRANCH"
if git show-ref --verify --quiet "refs/remotes/origin/$GIT_BRANCH"; then
    echo "Branch $GIT_BRANCH exists on remote. Checking it out and updating..."
    git checkout "$GIT_BRANCH"
    git pull origin "$GIT_BRANCH" --rebase
else
    echo "Branch $GIT_BRANCH does not exist remotely. Creating it..."
    git checkout -b "$GIT_BRANCH"
fi

# Verify branch exists
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$GIT_BRANCH" ]; then
  echo "Error: Failed to create/checkout branch $GIT_BRANCH"
  exit 1
fi

# Push and set upstream
git push -u origin "$GIT_BRANCH"

test -d "$GRAPH_NAME" && rm -rf "$GRAPH_NAME"
mkdir -p "$GRAPH_NAME"
cd ..

# Generate schema
if [ -z "$CUSTOM_GRAPH_TITLE" ]; then
    python3 src/dump_yaml.py "$GRAPH_NAME" "$GRAPH_DATA_PATH"
else
    python3 src/dump_yaml.py "$GRAPH_NAME" "$GRAPH_DATA_PATH" "$CUSTOM_GRAPH_TITLE"
fi

# Generate documentation
DOCS_DIR="repo/$GRAPH_NAME"
python3 src/docgen-frink.py "/code/${GRAPH_NAME}.yaml" \
    --template-directory /code/src/docgen-frink-templates \
    --directory "$DOCS_DIR" \
    --include-top-level-diagram \
    --diagram-type mermaid_class_diagram \
    --no-mergeimports \
    --subfolder-type-separation


cp "/code/${GRAPH_NAME}.yaml" "${DOCS_DIR}"

echo "Schema and documentation generation completed successfully."

# Push changes to GitHub
cd repo
git add .
git commit -m "Updated documentation for $GRAPH_NAME"
git push -u origin "$GIT_BRANCH"

# Create pull request using GitHub CLI (GH_TOKEN is already used implicitly)
if gh pr view "$GIT_BRANCH" --repo frink-okn/graph-descriptions >/dev/null 2>&1; then
  # Retrieve the PR's state, number, and URL
  pr_state=$(gh pr view "$GIT_BRANCH" --repo frink-okn/graph-descriptions --json state -q '.state')
  pr_number=$(gh pr view "$GIT_BRANCH" --repo frink-okn/graph-descriptions --json number -q '.number')
  pr_url=$(gh pr view "$GIT_BRANCH" --repo frink-okn/graph-descriptions --json url -q '.url')

   if [ "$pr_state" = "OPEN" ]; then
    echo "PR is open, retrieving its URL..."
    pr_url=$(gh pr view "$GIT_BRANCH" --repo frink-okn/graph-descriptions --json url -q '.url')
  else
    echo "PR exists but is $pr_state. Creating a new PR..."
    pr_url=$(gh pr create \
      --title "$CUSTOM_GRAPH_TITLE" \
      --body "Automatically generated PR for documentation updates of $GRAPH_NAME." \
      --base main \
      --head "$GIT_BRANCH" \
      --repo frink-okn/graph-descriptions)
  fi
else
  echo "Creating PR for branch $GIT_BRANCH..."
  pr_url=$(gh pr create \
    --title "$CUSTOM_GRAPH_TITLE" \
    --body "Automatically generated PR for documentation updates of $GRAPH_NAME." \
    --base main \
    --head "$GIT_BRANCH" \
    --repo frink-okn/graph-descriptions)
fi


# Save PR URL
echo "PR URL: $pr_url"
echo "Saving to : ${WORKING_DIR}/pr.md"
echo "$pr_url","https://github.com/frink-okn/graph-descriptions/tree/$GIT_BRANCH/$GRAPH_NAME" > "${WORKING_DIR}/pr.md"
echo "Documentation updated and pushed to GitHub repository on branch $GIT_BRANCH."
# make sure files are written
sync