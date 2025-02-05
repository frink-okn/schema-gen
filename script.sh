#!/bin/bash

set -e

# Check if the required arguments are provided
if [ "$#" -lt 4 ]; then
    echo "Usage: $0 <graph-name> <graph-data-path> <custom-graph-title> <git-branch>"
    exit 1
fi

GRAPH_NAME=$1
GRAPH_DATA_PATH=$2
CUSTOM_GRAPH_TITLE=$3
GIT_BRANCH=${4:-main}  # Default to 'main' if not provided

# Set up SSH configuration
SSH_DIR="${HOME}/.ssh"
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

# Add GitHub to known hosts
KNOWN_HOSTS="$SSH_DIR/known_hosts"
ssh-keyscan -H github.com >> "$KNOWN_HOSTS"
chmod 600 "$KNOWN_HOSTS"

# Configure SSH key from environment variable
DEPLOY_KEY_FILE="/ssh/id_ed25519"
#echo "$DEPLOY_KEY" > "$DEPLOY_KEY_FILE"
chmod 600 "$DEPLOY_KEY_FILE"

# Start SSH agent
eval "$(ssh-agent -s)"
ssh-add "$DEPLOY_KEY_FILE"

# Configure Git
git config --global user.email "frink-okn@renci.org"
git config --global user.name "Frink documentation bot"
git config --global core.sshCommand "ssh -i $DEPLOY_KEY_FILE -F /dev/null"

# Clone the repository using SSH
REPO_URL="git@github.com:frink-okn/graph-descriptions.git"
rm -rf repo
if [ ! -d "repo" ]; then
  git clone "$REPO_URL" repo
fi
# Prepare repository directory
cd repo
git checkout "$GIT_BRANCH" || git checkout -b "$GIT_BRANCH"
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

cp ${GRAPH_NAME}_untyped.txt ${DOCS_DIR}

echo "Schema and documentation generation completed successfully."

# Push to GitHub repository
cd repo
git add .
git commit -m "Updated documentation for $GRAPH_NAME"
git push -u origin "$GIT_BRANCH"
gh pr create \
  --title "$CUSTOM_GRAPH_TITLE" \
  --body "Automatically generated PR for documentation updates of $GRAPH_NAME." \
  --base main \
  --head "$GIT_BRANCH"

echo "Documentation updated and pushed to GitHub repository on branch $GIT_BRANCH."